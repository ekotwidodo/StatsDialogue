#!/usr/bin/env python3
"""E1 (phase 1) — schema-linking context ablation for StatsDialogue.

Three context-building conditions are compared on a fixed question set:

  raw        full relational DDL dump (no semantic layer — baseline)
  kg         label-containment retrieval + graph expansion (schema cards)
  kg_hybrid  BM25 ranked retrieval (top-k) + graph expansion

Metrics per question (see README.md for the protocol):

  tokens         ~ len(context)/4 — same estimator as the spike
  recall         fraction of gold columns present in the context
  extra tables   non-gold tables dragged into the context (noise)
  extra cols     non-gold columns dragged into the context (noise)
  labels         gold semantic labels present (raw DDL has none by design)

Phase 2 (LLM generation -> DuckDB execution accuracy) is gated on an LLM API
key:  run with --llm to see what is needed.

Usage:
  .venv/bin/python eval/e1_schema_linking/run_e1.py
"""
from __future__ import annotations

import json
import math
import re
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).parent
GRAPH_DIR = HERE.parents[1] / "services" / "graph"
sys.path.insert(0, str(GRAPH_DIR))

from build_sample_graph import SKOS, STATS, build  # noqa: E402

from rdflib import RDF, RDFS, URIRef  # noqa: E402

ALL_COLUMNS = [
    "time_period", "geo_code", "inflation_rate",
    "poverty_rate", "poor_pop", "min_wage", "unit",
]
TOP_K = 6

STOP = {
    "the", "a", "an", "of", "in", "on", "at", "is", "are", "was", "were",
    "what", "which", "how", "many", "show", "compare", "between", "over",
    "last", "above", "average", "have", "and", "to", "for", "with", "from",
    "by", "its", "it", "that", "this", "please", "give", "me",
    "di", "ke", "dari", "yang", "untuk", "pada", "ini", "itu", "dan",
    "atau", "adalah", "apa", "banyak", "juga", "tolong",
}


# --------------------------------------------------------------------------- #
# tokenization / scoring
# --------------------------------------------------------------------------- #
def tokens_of(text: str) -> list[str]:
    out = []
    for t in re.findall(r"[a-z0-9]+", text.lower()):
        if t in STOP:
            continue
        if len(t) > 4 and t.endswith("s"):
            t = t[:-1]  # crude plural folding: workers -> worker
        out.append(t)
    return out


def approx_tokens(text: str) -> int:
    return math.ceil(len(text) / 4)


def wide_ddl(base: str, n: int = 200) -> str:
    """Simulate BPS-scale schema width: base schema + n distractor tables
    (PRD 4.1: the BPS metric space spans thousands of sub-tables)."""
    blocks = [
        f"CREATE TABLE fact_series_{i:03d} (\n"
        f"  time_period VARCHAR,\n  geo_code VARCHAR,\n  value_{i} DOUBLE,\n  unit VARCHAR\n);"
        for i in range(n)
    ]
    return base + "\n" + "\n".join(blocks)


def bm25_scores(query: str, docs: dict[str, str]) -> dict[str, float]:
    """Standard BM25 (k1=1.5, b=0.75) over per-resource documents."""
    tokdocs = {u: tokens_of(t) for u, t in docs.items()}
    n, avgdl = len(tokdocs), sum(len(d) for d in tokdocs.values()) / max(len(tokdocs), 1)
    q = tokens_of(query)
    scores: dict[str, float] = {}
    for u, dtoks in tokdocs.items():
        tf: dict[str, int] = {}
        for t in dtoks:
            tf[t] = tf.get(t, 0) + 1
        s = 0.0
        for term in q:
            f = tf.get(term, 0)
            if not f:
                continue
            df = sum(1 for d in tokdocs.values() if term in d)
            idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
            s += idf * f * 2.5 / (f + 1.5 * (0.25 + 0.75 * len(dtoks) / avgdl))
        if s > 0:
            scores[u] = round(s, 3)
    return scores


def lexical_hits(question: str, labels: dict[str, list[str]]) -> list[str]:
    """Label-containment matching (the 'kg' condition): a resource hits when
    any of its labels appears in the question, or a >=4-char question token
    appears inside any label."""
    q = question.lower()
    qtoks = tokens_of(question)
    hits = []
    for uri, labs in labels.items():
        for lab in labs:
            low = lab.lower()
            if low in q:
                hits.append(uri)
                break
            if any(len(t) >= 4 and t in low for t in qtoks):
                hits.append(uri)
                break
    return hits


# --------------------------------------------------------------------------- #
# graph indexing
# --------------------------------------------------------------------------- #
def index_graph(g):
    labels: dict[str, list[str]] = {}
    docs: dict[str, str] = {}

    def add(uri: str, parts: list[str]) -> None:
        parts = [p for p in parts if p]
        labels[uri] = parts
        docs[uri] = " ".join(parts)

    for s in g.subjects(RDF.type, STATS.Measure):
        labs = [str(x) for x in g.objects(s, SKOS.prefLabel)]
        labs += [str(x) for x in g.objects(s, SKOS.altLabel)]
        col = g.value(s, STATS.sqlColumn)
        unit = g.value(s, STATS.unit)
        add(str(s), labs + ([str(col)] if col else []) + ([str(unit)] if unit else []))
    for s in g.subjects(SKOS.inScheme, STATS.CL_GEO):
        labs = [str(x) for x in g.objects(s, SKOS.prefLabel)]
        labs += [str(x) for x in g.objects(s, SKOS.altLabel)]
        code = g.value(s, STATS.code)
        add(str(s), labs + ([f"code {code}"] if code else []))
    for s in g.subjects(RDF.type, STATS.Dimension):
        lab = g.value(s, RDFS.label)
        col = g.value(s, STATS.sqlColumn)
        add(str(s), ([str(lab)] if lab else []) + ([str(col)] if col else []))
    for s in g.subjects(RDF.type, STATS.Dataflow):
        lab = g.value(s, RDFS.label)
        tbl = g.value(s, STATS.sqlTable)
        add(str(s), ([str(lab)] if lab else []) + ([str(tbl)] if tbl else []))
    return labels, docs


# --------------------------------------------------------------------------- #
# graph expansion -> schema-card context
# --------------------------------------------------------------------------- #
def expand_cards(g, uris: list[str], geo_uris: list[str]) -> str:
    """Expand retrieved resources through the ontology into LLM-ready cards."""
    tables: dict[str, dict] = {}  # table -> {df: str, cols: {col: desc}}

    def dsds_for(uri: URIRef) -> list[URIRef]:
        if (uri, RDF.type, STATS.Measure) in g:
            return [d for d in g.subjects(STATS.hasMeasure, uri)]
        if (uri, RDF.type, STATS.DSD) in g:
            return [uri]
        if (uri, RDF.type, STATS.Dataflow) in g:
            d = g.value(uri, STATS.structure)
            return [d] if d else []
        if (uri, RDF.type, STATS.Dimension) in g:
            return list(g.subjects(STATS.hasDimension, uri))
        return []

    def put_table(dsd: URIRef) -> None:
        df = g.value(None, STATS.structure, dsd)
        tbl = g.value(df, STATS.sqlTable) if df else None
        if not tbl:
            return
        t = tables.setdefault(str(tbl), {"df": "", "cols": {}})
        if df:
            t["df"] = str(g.value(df, RDFS.label) or df)
        for dim in g.objects(dsd, STATS.hasDimension):
            col, lab = g.value(dim, STATS.sqlColumn), g.value(dim, RDFS.label)
            if col:
                t["cols"].setdefault(str(col), str(lab) if lab else str(dim))
        for m in g.objects(dsd, STATS.hasMeasure):
            col = g.value(m, STATS.sqlColumn)
            if not col:
                continue
            prefs = list(g.objects(m, SKOS.prefLabel))
            mlab = next((p for p in prefs if p.language == "en"), prefs[0] if prefs else None)
            unit = g.value(m, STATS.unit)
            desc = str(mlab) if mlab else str(m)
            if unit:
                desc += f" [{unit}]"
            t["cols"].setdefault(str(col), desc)

    for uri in sorted(set(uris)):
        u = URIRef(uri)
        for dsd in dsds_for(u):
            put_table(dsd)

    lines: list[str] = []
    for tbl in sorted(tables):
        info = tables[tbl]
        lines.append(f"table {tbl}  # {info['df']}")
        for col in sorted(info["cols"]):
            lines.append(f"  col {col} : {info['cols'][col]}")
    for gu in geo_uris:
        u = URIRef(gu)
        code = g.value(u, STATS.code)
        prefs = list(g.objects(u, SKOS.prefLabel))
        en_l = next((str(p) for p in prefs if p.language == "en"), "")
        id_l = next((str(p) for p in prefs if p.language == "id"), "")
        lines.append(f"geo resolved : {code} = {en_l or id_l} / {id_l or en_l}")
    return "\n".join(lines) + ("\n" if lines else "")


# --------------------------------------------------------------------------- #
# conditions
# --------------------------------------------------------------------------- #
def build_context(condition: str, question: str, g, labels, docs, ddl: str) -> str:
    if condition in ("raw", "raw_wide"):
        return ddl if condition == "raw" else wide_ddl(ddl)
    if condition == "kg":
        hits = lexical_hits(question, labels)
    else:  # kg_hybrid
        scores = bm25_scores(question, docs)
        hits = sorted(scores, key=scores.get, reverse=True)[:TOP_K]
    geo = [u for u in hits if (URIRef(u), SKOS.inScheme, STATS.CL_GEO) in g]
    non_geo = [u for u in hits if u not in geo]
    return expand_cards(g, non_geo, geo)


# --------------------------------------------------------------------------- #
# metrics + reporting
# --------------------------------------------------------------------------- #
def evaluate(condition: str, question: str, ctx: str, gold: dict) -> dict:
    ctx_l = ctx.lower()
    found_cols = [c for c in gold["columns"] if c in ctx_l]
    found_tbl = [t for t in gold["tables"] if t in ctx_l]
    tables_seen = set(re.findall(r"fact_[a-z0-9_]+", ctx_l))
    extra_tbl = [t for t in tables_seen if t not in gold["tables"]]
    extra_col = [c for c in ALL_COLUMNS if c in ctx_l and c not in gold["columns"]]
    found_lab = [l for l in gold["labels"] if l.lower() in ctx_l]
    return {
        "condition": condition,
        "tokens": approx_tokens(ctx),
        "recall": len(found_cols) / len(gold["columns"]),
        "gold_cols_missing": [c for c in gold["columns"] if c not in found_cols],
        "extra_tables": len(extra_tbl),
        "extra_cols": len(extra_col),
        "labels": len(found_lab) / len(gold["labels"]),
        "labels_missing": [l for l in gold["labels"] if l not in found_lab],
        "_tables_found": len(found_tbl),
    }


def main() -> None:
    if "--llm" in sys.argv:
        print(
            "E1 phase 2 (LLM generation -> DuckDB EX) is gated:\n"
            "  1. set OPENAI_API_KEY or ANTHROPIC_API_KEY\n"
            "  2. provide fact fixtures (or a BPS_API_KEY for live data)\n"
            "  3. run: run_e1.py --llm   (harness ready; phase 1 unaffected)"
        )
        return

    g = build()
    labels, docs = index_graph(g)
    dataset = json.loads((HERE / "dataset.json").read_text(encoding="utf-8"))
    ddl = (HERE / "schema_ddl.sql").read_text(encoding="utf-8")
    conditions = ["raw", "raw_wide", "kg", "kg_hybrid"]

    rows: list[dict] = []
    for item in dataset:
        for cond in conditions:
            ctx = build_context(cond, item["question"], g, labels, docs, ddl)
            m = evaluate(cond, item["question"], ctx, item["gold"])
            m["id"], m["question"] = item["id"], item["question"]
            rows.append(m)

    # ---- aggregates
    agg = {}
    for cond in conditions:
        rs = [r for r in rows if r["condition"] == cond]
        agg[cond] = {
            "tokens": sum(r["tokens"] for r in rs) / len(rs),
            "recall": sum(r["recall"] for r in rs) / len(rs),
            "extra_tables": sum(r["extra_tables"] for r in rs) / len(rs),
            "extra_cols": sum(r["extra_cols"] for r in rs) / len(rs),
            "labels": sum(r["labels"] for r in rs) / len(rs),
        }

    # ---- stdout report
    print(f"E1 phase 1 — schema-linking context ablation  ({len(dataset)} questions, "
          f"graph {len(g)} triples)")
    print(f"{'cond':<10} {'mean tokens':>12} {'recall':>8} {'extra tbl':>10} "
          f"{'extra col':>10} {'labels':>8}")
    for cond in conditions:
        a = agg[cond]
        print(f"{cond:<10} {a['tokens']:>12.0f} {a['recall']:>8.2f} "
              f"{a['extra_tables']:>10.1f} {a['extra_cols']:>10.1f} {a['labels']:>8.2f}")

    misses = [r for r in rows if r["recall"] < 1.0]
    if misses:
        print("\nrecall misses:")
        for r in misses:
            print(f"  {r['id']} [{r['condition']}] missing: {r['gold_cols_missing']}")

    # ---- results.md
    out = [
        "# E1 Phase 1 Results — Schema-Linking Context Ablation",
        "",
        f"- Date: {date.today().isoformat()}",
        f"- Dataset: {len(dataset)} questions (`dataset.json`), graph: {len(g)} triples",
        f"- Token estimator: chars/4 (same as spike 001)",
        f"- Retrieval: `kg` = label containment + graph expansion; "
        f"`kg_hybrid` = BM25 top-{TOP_K} + graph expansion (vector stage: TODO)",
        "",
        "## Aggregate",
        "",
        "| condition | mean tokens | gold recall | extra tables | extra cols | label coverage |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for cond in conditions:
        a = agg[cond]
        out.append(f"| {cond} | {a['tokens']:.0f} | {a['recall']:.2f} | "
                   f"{a['extra_tables']:.1f} | {a['extra_cols']:.1f} | {a['labels']:.2f} |")
    out += ["", "## Per question", "",
            "| id | condition | tokens | recall | extra tbl | extra col | labels |",
            "|---|---|---:|---:|---:|---:|---:|"]
    for r in rows:
        out.append(f"| {r['id']} | {r['condition']} | {r['tokens']} | {r['recall']:.2f} | "
                   f"{r['extra_tables']} | {r['extra_cols']} | {r['labels']:.2f} |")
    out += ["", "## Notes", "",
            "- `raw` always has full recall on this toy schema but drags every table/column",
            "  and carries **zero** semantic labels — the LLM sees names only.",
            "- `raw_wide` = raw + 200 distractor tables, simulating BPS-scale schema width",
            "  (PRD 4.1: thousands of sub-tables). This is where the token advantage (H2) bites.",
            "- KG conditions carry labels/units (H3) and drop unrelated tables (H1).",
            "- Phase 2 (LLM -> SQL -> DuckDB execution accuracy) awaits an LLM key: `--llm`.",
            ""]
    (HERE / "results.md").write_text("\n".join(out), encoding="utf-8")
    print(f"\nwrote {HERE.name}/results.md")


if __name__ == "__main__":
    main()
