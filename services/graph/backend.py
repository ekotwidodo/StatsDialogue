"""Repository interface and rdflib implementation for the RDF Knowledge Graph.

Implements ADR-0001 ("the store sits behind a repository interface
`GraphBackend`, keeping the implementation swappable") and PRD §4.1–4.2, §8.2:

- Lexical retrieval (`retrieve_lexical`) for the `kg` condition
- Hybrid retrieval (`retrieve_hybrid`) combining BM25 + semantic vector cosine
  similarity via Reciprocal Rank Fusion (RRF) for the `kg_hybrid` condition
- Ontology traversal & compact schema-card serialization (`expand_schema_cards`)
- W3C PROV-O lineage recording and SPARQL lineage audit (`record_provenance`,
  `get_lineage`)
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol, runtime_checkable

from rdflib import Graph, Literal, RDF, RDFS, URIRef, XSD

from .build_sample_graph import EX, PROV, SKOS, STATS, build

STOP = {
    "the", "a", "an", "of", "in", "on", "at", "is", "are", "was", "were",
    "what", "which", "how", "many", "show", "compare", "between", "over",
    "last", "above", "average", "have", "and", "to", "for", "with", "from",
    "by", "its", "it", "that", "this", "please", "give", "me", "rate",
    "level", "levels", "number", "numbers", "data", "statistics", "statistic",
    "year", "years", "tahun", "berapa", "bagaimana", "tampilkan", "bandingkan",
    "di", "ke", "dari", "yang", "untuk", "pada", "ini", "itu", "dan",
    "atau", "adalah", "apa", "banyak", "juga", "tolong", "kondisi", "tingkat",
}

# Bilingual domain concept neighborhoods used by the local embedding vectorizer
# to bridge pure-semantic paraphrases (e.g., "cost of living" -> inflation,
# "welfare / low-income / prasejahtera" -> poverty, "take-home pay / buruh" -> wage,
# regional nicknames -> official province concepts).
SEMANTIC_EXPANSIONS: dict[str, str] = {
    str(STATS.M_INFLATION_RATE): (
        "cost of living price hike consumer price index kenaikan harga barang "
        "mahalnya biaya hidup daya beli masyarakat harga kebutuhan pokok cpi"
    ),
    str(STATS.M_POVERTY_RATE): (
        "destitution deprivation welfare ratio low income share proporsi warga "
        "prasejahtera kurang mampu kemiskinan kesejahteraan sosial"
    ),
    str(STATS.M_POVERTY_POP): (
        "impoverished citizens underprivileged residents headcount warga tidak "
        "mampu keluarga prasejahtera masyarakat miskin kepala keluarga"
    ),
    str(STATS.M_MIN_WAGE): (
        "worker earnings salary compensation take home pay penghasilan buruh "
        "bayaran pekerja standar gaji bulanan pendapatan tenaga kerja ump umk"
    ),
    str(STATS.GEO_00): "nationwide seluruh provinsi tanah air republik indonesia nasional",
    str(STATS.GEO_31): "ibu kota metropolitan jabodetabek jakarta raya",
    str(STATS.GEO_32): "tanah pasundan priangan bandung jawa barat",
    str(STATS.GEO_33): "semarang solo surakarta jawa tengah",
    str(STATS.GEO_34): "kota pelajar kesultanan ngayogyakarta jogjakarta sleman",
    str(STATS.GEO_35): "surabaya malang bumi majapahit jawa timur",
    str(STATS.GEO_51): "pulau dewata denpasar badung bali",
}

# Concept-cluster synonym groups mapped onto shared latent concept tokens so
# query vectors and resource vectors align in cosine space even with zero
# surface-word overlap.
LATENT_CLUSTERS: list[tuple[str, set[str]]] = [
    (
        "__concept_inflation__",
        {
            "inflation", "inflasi", "cpi", "price", "prices", "harga",
            "cost", "living", "biaya", "hidup", "kebutuhan", "pokok", "mahal",
            "mahalnya", "kenaikan",
        },
    ),
    (
        "__concept_poverty_rate__",
        {
            "poverty", "kemiskinan", "destitution", "deprivation", "prasejahtera",
            "proporsi", "proportion", "share", "persentase", "percentage", "rasio",
        },
    ),
    (
        "__concept_poverty_pop__",
        {
            "poor", "miskin", "impoverished", "underprivileged", "headcount",
            "jumlah", "penduduk", "warga", "citizens", "residents", "people",
            "keluarga", "mampu",
        },
    ),
    (
        "__concept_min_wage__",
        {
            "wage", "upah", "umr", "ump", "umk", "gaji", "salary", "income",
            "earnings", "compensation", "pay", "penghasilan", "bayaran",
            "pendapatan", "buruh", "pekerja", "worker", "labor", "tenaga",
        },
    ),
    ("__geo_00__", {"indonesia", "national", "nasional", "nationwide", "tanah", "air"}),
    ("__geo_31__", {"jakarta", "dki", "jabodetabek", "metropolitan"}),
    ("__geo_32__", {"west", "barat", "jabar", "pasundan", "priangan", "bandung"}),
    ("__geo_33__", {"central", "tengah", "jateng", "semarang", "surakarta", "solo"}),
    ("__geo_34__", {"yogyakarta", "jogja", "jogjakarta", "diy", "pelajar"}),
    ("__geo_35__", {"east", "timur", "jatim", "surabaya", "majapahit", "malang"}),
    ("__geo_51__", {"bali", "dewata", "denpasar"}),
]


def tokenize(text: str) -> list[str]:
    """Normalize and stem tokens (light EN/ID morphological normalization)."""
    out: list[str] = []
    for t in re.findall(r"[a-z0-9]+", text.lower()):
        if t in STOP:
            continue
        if len(t) > 4 and t.endswith("s"):
            t = t[:-1]
        out.append(t)
    return out


def semantic_vector(text: str) -> dict[str, float]:
    """Build a sparse unit-normalized semantic + character n-gram vector.

    Combines:
    1. Latent concept cluster activations (weight 2.5) for cross-lingual and
       paraphrase alignment.
    2. Normalized word tokens (weight 1.5).
    3. Character 4-grams (weight 0.4) for morphological robustness (e.g.
       'kemiskinan' <-> 'miskin', 'penghasilan' <-> 'hasil').
    """
    raw_words = set(re.findall(r"[a-z0-9]+", text.lower()))
    toks = tokenize(text)
    vec: dict[str, float] = {}

    for tok in toks:
        vec[f"w:{tok}"] = vec.get(f"w:{tok}", 0.0) + 1.5
        if len(tok) >= 4:
            for i in range(len(tok) - 3):
                ng = f"g:{tok[i:i+4]}"
                vec[ng] = vec.get(ng, 0.0) + 0.4

    for concept_id, vocab in LATENT_CLUSTERS:
        overlap = raw_words & vocab
        if overlap:
            vec[concept_id] = vec.get(concept_id, 0.0) + 2.5 * len(overlap)

    norm = math.sqrt(sum(v * v for v in vec.values()))
    if norm > 0:
        vec = {k: v / norm for k, v in vec.items()}
    return vec


def cosine_sim(v1: dict[str, float], v2: dict[str, float]) -> float:
    if not v1 or not v2:
        return 0.0
    if len(v1) > len(v2):
        v1, v2 = v2, v1
    return sum(val * v2.get(k, 0.0) for k, val in v1.items())


@dataclass
class SchemaCardContext:
    """Compact schema-card representation produced by ontology expansion."""

    text: str
    tables: list[str] = field(default_factory=list)
    columns: list[str] = field(default_factory=list)
    geo_codes: dict[str, str] = field(default_factory=dict)  # code -> label
    retrieved_uris: list[str] = field(default_factory=list)


@dataclass
class ProvenanceRecord:
    """W3C PROV-O lineage payload for an executed analytical answer (PRD §8.2)."""

    answer_id: str
    question: str
    sql_query: str
    source_dataflows: list[str]
    agent_id: str = "sd-agent"
    activity_id: str = ""
    confidence: float | None = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@runtime_checkable
class GraphBackend(Protocol):
    """Swappable Knowledge Graph repository interface (ADR-0001)."""

    def sparql_select(self, query: str) -> list[dict[str, str]]: ...
    def retrieve_lexical(self, question: str) -> list[str]: ...
    def retrieve_hybrid(self, question: str, top_k: int = 6) -> list[str]: ...
    def expand_schema_cards(self, uris: list[str]) -> SchemaCardContext: ...
    def record_provenance(self, record: ProvenanceRecord) -> str: ...
    def get_lineage(self, answer_uri: str) -> dict[str, object]: ...


class RdflibBackend:
    """Embedded RDF/SPARQL backend powered by rdflib (ADR-0001 prototype store)."""

    def __init__(self, graph: Graph | None = None) -> None:
        self.graph: Graph = graph if graph is not None else build()
        self.labels: dict[str, list[str]] = {}
        self.docs: dict[str, str] = {}
        self.vectors: dict[str, dict[str, float]] = {}
        self._index()

    def _index(self) -> None:
        g = self.graph
        self.labels.clear()
        self.docs.clear()
        self.vectors.clear()

        def register(uri: str, surface: list[str]) -> None:
            clean = [p for p in surface if p]
            self.labels[uri] = clean
            lexical_doc = " ".join(clean)
            self.docs[uri] = lexical_doc
            sem_extra = SEMANTIC_EXPANSIONS.get(uri, "")
            self.vectors[uri] = semantic_vector(f"{lexical_doc} {sem_extra}")

        for s in g.subjects(RDF.type, STATS.Measure):
            labs = [str(x) for x in g.objects(s, SKOS.prefLabel)]
            labs += [str(x) for x in g.objects(s, SKOS.altLabel)]
            col = g.value(s, STATS.sqlColumn)
            unit = g.value(s, STATS.unit)
            register(
                str(s),
                labs + ([str(col)] if col else []) + ([str(unit)] if unit else []),
            )

        for s in g.subjects(SKOS.inScheme, STATS.CL_GEO):
            labs = [str(x) for x in g.objects(s, SKOS.prefLabel)]
            labs += [str(x) for x in g.objects(s, SKOS.altLabel)]
            code = g.value(s, STATS.code)
            register(str(s), labs + ([f"code {code}"] if code else []))

        for s in g.subjects(RDF.type, STATS.Dimension):
            lab = g.value(s, RDFS.label)
            col = g.value(s, STATS.sqlColumn)
            register(str(s), ([str(lab)] if lab else []) + ([str(col)] if col else []))

        for s in g.subjects(RDF.type, STATS.Dataflow):
            lab = g.value(s, RDFS.label)
            tbl = g.value(s, STATS.sqlTable)
            register(str(s), ([str(lab)] if lab else []) + ([str(tbl)] if tbl else []))

    def sparql_select(self, query: str) -> list[dict[str, str]]:
        res = self.graph.query(query)
        vars_ = [str(v) for v in res.vars]
        out: list[dict[str, str]] = []
        for row in res:
            out.append(
                {vars_[i]: ("" if val is None else str(val)) for i, val in enumerate(row)}
            )
        return out

    def retrieve_lexical(self, question: str) -> list[str]:
        """Label-containment retrieval (`kg` baseline)."""
        q = question.lower()
        qtoks = tokenize(question)
        hits: list[str] = []
        for uri, labs in self.labels.items():
            for lab in labs:
                low = lab.lower()
                if low in q:
                    hits.append(uri)
                    break
                if any(len(t) >= 4 and t in low for t in qtoks):
                    hits.append(uri)
                    break
        return hits

    def _bm25_scores(self, question: str) -> dict[str, float]:
        tokdocs = {u: tokenize(t) for u, t in self.docs.items()}
        n = len(tokdocs)
        avgdl = sum(len(d) for d in tokdocs.values()) / max(n, 1)
        q = tokenize(question)
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
                scores[u] = round(s, 4)
        return scores

    def _vector_scores(self, question: str, min_sim: float = 0.16) -> dict[str, float]:
        qvec = semantic_vector(question)
        scores: dict[str, float] = {}
        for uri, dvec in self.vectors.items():
            sim = cosine_sim(qvec, dvec)
            if sim >= min_sim:
                scores[uri] = round(sim, 4)
        return scores

    def retrieve_hybrid(self, question: str, top_k: int = 6) -> list[str]:
        """Hybrid BM25 + semantic vector retrieval fused with RRF (PRD §4.1)."""
        bm25 = self._bm25_scores(question)
        vec = self._vector_scores(question)
        lex = set(self.retrieve_lexical(question))

        bm25_ranked = sorted(bm25, key=bm25.get, reverse=True)
        vec_ranked = sorted(vec, key=vec.get, reverse=True)

        rrf: dict[str, float] = {}
        k_rrf = 60.0
        for rank, u in enumerate(bm25_ranked):
            rrf[u] = rrf.get(u, 0.0) + 1.0 / (k_rrf + rank + 1)
        for rank, u in enumerate(vec_ranked):
            # Only admit vector-only candidates when their cosine similarity is strong
            if u in bm25 or u in lex or vec[u] >= 0.22:
                rrf[u] = rrf.get(u, 0.0) + 1.0 / (k_rrf + rank + 1)
        for u in lex:
            rrf[u] = rrf.get(u, 0.0) + 0.5 / (k_rrf + 1)

        ranked = sorted(rrf, key=rrf.get, reverse=True)[:top_k]
        return ranked

    def expand_schema_cards(self, uris: list[str]) -> SchemaCardContext:
        """Traverse the ontology from retrieved URIs to build compact schema cards."""
        g = self.graph
        geo_uris = [u for u in uris if (URIRef(u), SKOS.inScheme, STATS.CL_GEO) in g]
        non_geo = [u for u in uris if u not in geo_uris]

        tables: dict[str, dict] = {}

        def dsds_for(uri: URIRef) -> list[URIRef]:
            if (uri, RDF.type, STATS.Measure) in g:
                return list(g.subjects(STATS.hasMeasure, uri))
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
                mlab = next(
                    (p for p in prefs if p.language == "en"),
                    prefs[0] if prefs else None,
                )
                unit = g.value(m, STATS.unit)
                desc = str(mlab) if mlab else str(m)
                if unit:
                    desc += f" [{unit}]"
                t["cols"].setdefault(str(col), desc)

        for uri in sorted(set(non_geo)):
            u = URIRef(uri)
            for dsd in dsds_for(u):
                put_table(dsd)

        lines: list[str] = []
        all_cols: list[str] = []
        for tbl in sorted(tables):
            info = tables[tbl]
            lines.append(f"table {tbl}  # {info['df']}")
            for col in sorted(info["cols"]):
                lines.append(f"  col {col} : {info['cols'][col]}")
                if col not in all_cols:
                    all_cols.append(col)

        geo_map: dict[str, str] = {}
        for gu in geo_uris:
            u = URIRef(gu)
            code = str(g.value(u, STATS.code) or "")
            prefs = list(g.objects(u, SKOS.prefLabel))
            en_l = next((str(p) for p in prefs if p.language == "en"), "")
            id_l = next((str(p) for p in prefs if p.language == "id"), "")
            label_pair = f"{en_l or id_l} / {id_l or en_l}"
            lines.append(f"geo resolved : {code} = {label_pair}")
            if code:
                geo_map[code] = en_l or id_l

        text = "\n".join(lines) + ("\n" if lines else "")
        return SchemaCardContext(
            text=text,
            tables=sorted(tables.keys()),
            columns=all_cols,
            geo_codes=geo_map,
            retrieved_uris=list(uris),
        )

    def record_provenance(self, record: ProvenanceRecord) -> str:
        """Insert a W3C PROV-O lineage subgraph for an executed answer (PRD §8.2)."""
        g = self.graph
        ans_uri = EX[record.answer_id]
        act_id = record.activity_id or f"exec-{record.answer_id}"
        act_uri = EX[act_id]
        agent_uri = EX[record.agent_id]

        g.add((ans_uri, RDF.type, PROV.Entity))
        g.add((ans_uri, RDFS.label, Literal(f"Answer: {record.question}", lang="en")))
        g.add((ans_uri, PROV.wasGeneratedBy, act_uri))
        g.add(
            (
                ans_uri,
                PROV.generatedAtTime,
                Literal(record.timestamp, datatype=XSD.dateTime),
            )
        )
        if record.confidence is not None:
            g.add(
                (
                    ans_uri,
                    STATS.confidenceScore,
                    Literal(round(record.confidence, 4), datatype=XSD.double),
                )
            )

        for df_name in record.source_dataflows:
            df_uri = STATS[df_name] if not df_name.startswith("http") else URIRef(df_name)
            g.add((ans_uri, PROV.wasDerivedFrom, df_uri))

        g.add((act_uri, RDF.type, PROV.Activity))
        g.add((act_uri, RDFS.label, Literal(f"SQL execution: {record.sql_query}", lang="en")))
        g.add((act_uri, STATS.executedSQL, Literal(record.sql_query)))
        g.add((act_uri, PROV.wasAssociatedWith, agent_uri))

        g.add((agent_uri, RDF.type, PROV.Agent))
        g.add((agent_uri, RDFS.label, Literal("StatsDialogue Analytical Agent", lang="en")))
        return str(ans_uri)

    def get_lineage(self, answer_uri: str) -> dict[str, object]:
        """Query the full W3C PROV-O lineage chain for a given answer URI."""
        target = answer_uri if answer_uri.startswith("http") else str(EX[answer_uri])
        query = f"""
        SELECT ?answer ?activity ?sql ?agent ?source ?time ?conf WHERE {{
          BIND(<{target}> AS ?answer)
          ?answer a prov:Entity ;
                  prov:wasGeneratedBy ?activity ;
                  prov:wasDerivedFrom ?source .
          ?activity prov:wasAssociatedWith ?agent .
          OPTIONAL {{ ?activity stats:executedSQL ?sql }}
          OPTIONAL {{ ?answer prov:generatedAtTime ?time }}
          OPTIONAL {{ ?answer stats:confidenceScore ?conf }}
        }}
        """
        rows = self.sparql_select(query)
        if not rows:
            return {"complete": False, "answer": target, "sources": []}
        first = rows[0]
        sources = sorted({r["source"] for r in rows if r.get("source")})
        return {
            "complete": bool(
                first.get("answer")
                and first.get("activity")
                and first.get("agent")
                and sources
            ),
            "answer": first["answer"],
            "activity": first["activity"],
            "agent": first["agent"],
            "sql": first.get("sql", ""),
            "timestamp": first.get("time", ""),
            "confidence": float(first["conf"]) if first.get("conf") else None,
            "sources": sources,
        }
