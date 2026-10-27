# E1 — Schema-Linking Context & Execution Ablation (Phases 1 & 2)

**Phase:** 1 & 2 executed (Phase 1 = context construction; Phase 2 = SQL generation + DuckDB execution accuracy + W3C PROV-O audit)
**Claims:** `docs/positioning.md` → Claim A (standards-grounded), Claim C (orchestration)
**Protocol status:** Phases 1 & 2 executed 2026-10-27 → see [`results.md`](results.md)

## Goal

Measure what a statistics-native RDF knowledge graph and hybrid GraphRAG retrieval buy in:
1. **Context quality & token efficiency (Phase 1)** compared against dumping raw relational DDL.
2. **Downstream DuckDB Execution Accuracy (`EX`), Exact Match (`EM`), and W3C PROV-O lineage completeness (Phase 2)**.

## Hypotheses

| ID | Hypothesis |
|---|---|
| **H1** | KG-based contexts retain gold schema recall while removing irrelevant schema (precision). |
| **H2** | KG-based contexts cut context token cost as schema width grows (BPS: thousands of sub-tables, PRD §4.1). |
| **H3** | KG-based contexts carry semantic labels and SKOS codelist bindings (units, bilingual names, numeric `geo_code`) that raw DDL lacks, directly enabling executable SQL (EX). |
| **H4** | Hybrid retrieval (`kg_hybrid`: BM25 + semantic vector cosine fused via RRF) outperforms unranked lexical containment (`kg`) on both ambiguous multi-token region names (*Jawa Barat / Tengah / Timur*) and pure-semantic paraphrases (`q11`–`q15`). |

## Design

- **Dataset:** [`dataset.json`](dataset.json) — 15 bilingual questions (EN + ID) with gold tables, columns, semantic labels, and ground-truth DuckDB SQL:
  - **Lexical slice (`q01`–`q10`):** surface terms overlap with `skos:prefLabel` / `skos:altLabel` in the ontology.
  - **Semantic/paraphrase slice (`q11`–`q15`):** colloquial or conceptual phrasings with zero surface-label overlap (e.g., *"cost of living in Bandung's province"*, *"penghasilan bulanan buruh di Pulau Dewata"*, *"warga prasejahtera di provinsi Kota Pelajar"*).
- **Fact fixtures:** [`fixtures.sql`](fixtures.sql) — deterministic BPS-style provincial panel (2021–2025 across 9 `CL_GEO` codes) loaded into [`DuckDBSandbox`](../../services/engine/sandbox.py).
- **Conditions:**
  - `raw` — full 3-table DDL dump from [`schema_ddl.sql`](schema_ddl.sql) (no semantic layer)
  - `raw_wide` — `raw` + 200 distractor tables (BPS-scale width simulation)
  - `kg` — label-containment retrieval (`RdflibBackend.retrieve_lexical`) + ontology expansion → compact schema cards
  - `kg_hybrid` — BM25 + concept/char-n-gram vector cosine similarity fused via Reciprocal Rank Fusion (`RdflibBackend.retrieve_hybrid`, top-6) + ontology expansion
- **Metrics:**
  - `tokens` — chars/4 estimator (same as spike 001)
  - `recall` — gold columns present in context
  - `extra tables / extra cols` — non-gold schema dragged in (noise)
  - `labels` — gold semantic labels present
  - `EX` — DuckDB Execution Accuracy (generated SQL result set matches gold SQL result set)
  - `EM` — Normalized SQL Exact Match
  - `PROV-O` — Fraction of answers with a complete W3C PROV-O lineage chain (`prov:Entity → prov:Activity → prov:Agent + stats:Dataflow`)

## How to run

```bash
.venv/bin/python eval/e1_schema_linking/run_e1.py          # phases 1 & 2 (deterministic context-strict synthesizer)
.venv/bin/python eval/e1_schema_linking/run_e1.py --llm    # uses live OpenAI API if OPENAI_API_KEY is set
```

## Outcome (2026-10-27)

### Aggregate (All 15 Questions)

| condition | mean tokens | gold recall | extra tables | extra cols | label coverage | EX (all) | EM (all) | PROV-O |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| raw | 120 | 1.00 | 2.0 | 4.5 | 0.00 | 0.00 | 0.00 | 0.40 |
| raw_wide | 5692 | 1.00 | 202.0 | 4.5 | 0.00 | 0.00 | 0.00 | 0.40 |
| kg | 43 | 0.67 | 0.0 | 0.7 | 0.67 | 0.47 | 0.47 | 0.67 |
| kg_hybrid | 62 | 1.00 | 0.0 | 0.9 | 1.00 | 1.00 | 1.00 | 1.00 |

### Slice Breakdown: Lexical (`q01`–`q10`) vs Semantic/Paraphrase (`q11`–`q15`)

| condition | recall (lexical) | EX (lexical) | recall (semantic) | EX (semantic) | labels (semantic) |
|---|---:|---:|---:|---:|---:|
| raw | 1.00 | 0.00 | 1.00 | 0.00 | 0.00 |
| raw_wide | 1.00 | 0.00 | 1.00 | 0.00 | 0.00 |
| kg | 1.00 | 0.70 | 0.00 | 0.00 | 0.00 |
| kg_hybrid | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

- **H1 & H2 ✅** — `kg_hybrid` removes 100% of unrelated tables (202.0 → 0.0) and cuts BPS-scale prompt context tokens **~92×** (5692 → 62) while holding 1.00 gold column recall.
- **H3 ✅** — `raw` and `raw_wide` score **0.00 EX** because raw DDL lacks SKOS `geo_code` mappings (e.g., `'32'` for West Java) and bilingual measure labels.
- **H4 ✅** — `kg_hybrid` outperforms `kg` both on the lexical slice (**1.00 vs 0.70 EX**, because unranked substring containment matches `"Jawa"`/`"Java"` across all Java provinces in URI order, whereas BM25+vector RRF ranks the exact province first) and on the semantic paraphrase slice (**1.00 vs 0.00 recall and EX**).
