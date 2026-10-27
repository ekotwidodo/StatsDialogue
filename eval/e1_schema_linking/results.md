# E1 Results — Schema-Linking Context & Execution Ablation (Phases 1 & 2)

- Date: 2026-10-27
- Dataset: 15 questions (`dataset.json`: 10 lexical + 5 semantic/paraphrase)
- Engines: `RdflibBackend` (SPARQL + BM25 + semantic vector RRF) + `DuckDBSandbox` (read-only OLAP + W3C PROV-O)
- Phase 2 generator mode: deterministic context-strict synthesizer

## Aggregate (All 15 Questions)

| condition | mean tokens | gold recall | extra tables | extra cols | label coverage | EX (all) | EM (all) | PROV-O |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| raw | 120 | 1.00 | 2.0 | 4.5 | 0.00 | 0.00 | 0.00 | 0.40 |
| raw_wide | 5692 | 1.00 | 202.0 | 4.5 | 0.00 | 0.00 | 0.00 | 0.40 |
| kg | 43 | 0.67 | 0.0 | 0.7 | 0.67 | 0.47 | 0.47 | 0.67 |
| kg_hybrid | 62 | 1.00 | 0.0 | 0.9 | 1.00 | 1.00 | 1.00 | 1.00 |

## Slice Breakdown: Lexical (`q01`–`q10`) vs Semantic/Paraphrase (`q11`–`q15`)

| condition | recall (lexical) | EX (lexical) | recall (semantic) | EX (semantic) | labels (semantic) |
|---|---:|---:|---:|---:|---:|
| raw | 1.00 | 0.00 | 1.00 | 0.00 | 0.00 |
| raw_wide | 1.00 | 0.00 | 1.00 | 0.00 | 0.00 |
| kg | 1.00 | 0.70 | 0.00 | 0.00 | 0.00 |
| kg_hybrid | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

## Per Question

| id | slice | condition | tokens | recall | extra tbl | extra col | labels | EX | EM |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| q01 | lexical | raw | 120 | 1.00 | 2 | 4 | 0.00 | 0 | 0 |
| q01 | lexical | raw_wide | 5692 | 1.00 | 202 | 4 | 0.00 | 0 | 0 |
| q01 | lexical | kg | 77 | 1.00 | 0 | 0 | 1.00 | 1 | 1 |
| q01 | lexical | kg_hybrid | 77 | 1.00 | 0 | 0 | 1.00 | 1 | 1 |
| q02 | lexical | raw | 120 | 1.00 | 2 | 4 | 0.00 | 0 | 0 |
| q02 | lexical | raw_wide | 5692 | 1.00 | 202 | 4 | 0.00 | 0 | 0 |
| q02 | lexical | kg | 83 | 1.00 | 0 | 1 | 1.00 | 0 | 0 |
| q02 | lexical | kg_hybrid | 83 | 1.00 | 0 | 1 | 1.00 | 1 | 1 |
| q03 | lexical | raw | 120 | 1.00 | 2 | 4 | 0.00 | 0 | 0 |
| q03 | lexical | raw_wide | 5692 | 1.00 | 202 | 4 | 0.00 | 0 | 0 |
| q03 | lexical | kg | 51 | 1.00 | 0 | 0 | 1.00 | 1 | 1 |
| q03 | lexical | kg_hybrid | 51 | 1.00 | 0 | 0 | 1.00 | 1 | 1 |
| q04 | lexical | raw | 120 | 1.00 | 2 | 5 | 0.00 | 0 | 0 |
| q04 | lexical | raw_wide | 5692 | 1.00 | 202 | 5 | 0.00 | 0 | 0 |
| q04 | lexical | kg | 83 | 1.00 | 0 | 2 | 1.00 | 0 | 0 |
| q04 | lexical | kg_hybrid | 83 | 1.00 | 0 | 2 | 1.00 | 1 | 1 |
| q05 | lexical | raw | 120 | 1.00 | 2 | 5 | 0.00 | 0 | 0 |
| q05 | lexical | raw_wide | 5692 | 1.00 | 202 | 5 | 0.00 | 0 | 0 |
| q05 | lexical | kg | 44 | 1.00 | 0 | 1 | 1.00 | 1 | 1 |
| q05 | lexical | kg_hybrid | 44 | 1.00 | 0 | 1 | 1.00 | 1 | 1 |
| q06 | lexical | raw | 120 | 1.00 | 2 | 5 | 0.00 | 0 | 0 |
| q06 | lexical | raw_wide | 5692 | 1.00 | 202 | 5 | 0.00 | 0 | 0 |
| q06 | lexical | kg | 72 | 1.00 | 0 | 2 | 1.00 | 1 | 1 |
| q06 | lexical | kg_hybrid | 72 | 1.00 | 0 | 2 | 1.00 | 1 | 1 |
| q07 | lexical | raw | 120 | 1.00 | 2 | 4 | 0.00 | 0 | 0 |
| q07 | lexical | raw_wide | 5692 | 1.00 | 202 | 4 | 0.00 | 0 | 0 |
| q07 | lexical | kg | 74 | 1.00 | 0 | 0 | 1.00 | 0 | 0 |
| q07 | lexical | kg_hybrid | 74 | 1.00 | 0 | 0 | 1.00 | 1 | 1 |
| q08 | lexical | raw | 120 | 1.00 | 2 | 5 | 0.00 | 0 | 0 |
| q08 | lexical | raw_wide | 5692 | 1.00 | 202 | 5 | 0.00 | 0 | 0 |
| q08 | lexical | kg | 54 | 1.00 | 0 | 1 | 1.00 | 1 | 1 |
| q08 | lexical | kg_hybrid | 54 | 1.00 | 0 | 1 | 1.00 | 1 | 1 |
| q09 | lexical | raw | 120 | 1.00 | 2 | 5 | 0.00 | 0 | 0 |
| q09 | lexical | raw_wide | 5692 | 1.00 | 202 | 5 | 0.00 | 0 | 0 |
| q09 | lexical | kg | 49 | 1.00 | 0 | 1 | 1.00 | 1 | 1 |
| q09 | lexical | kg_hybrid | 49 | 1.00 | 0 | 1 | 1.00 | 1 | 1 |
| q10 | lexical | raw | 120 | 1.00 | 2 | 6 | 0.00 | 0 | 0 |
| q10 | lexical | raw_wide | 5692 | 1.00 | 202 | 6 | 0.00 | 0 | 0 |
| q10 | lexical | kg | 60 | 1.00 | 0 | 3 | 1.00 | 1 | 1 |
| q10 | lexical | kg_hybrid | 60 | 1.00 | 0 | 3 | 1.00 | 1 | 1 |
| q11 | semantic | raw | 120 | 1.00 | 2 | 4 | 0.00 | 0 | 0 |
| q11 | semantic | raw_wide | 5692 | 1.00 | 202 | 4 | 0.00 | 0 | 0 |
| q11 | semantic | kg | 0 | 0.00 | 0 | 0 | 0.00 | 0 | 0 |
| q11 | semantic | kg_hybrid | 54 | 1.00 | 0 | 0 | 1.00 | 1 | 1 |
| q12 | semantic | raw | 120 | 1.00 | 2 | 4 | 0.00 | 0 | 0 |
| q12 | semantic | raw_wide | 5692 | 1.00 | 202 | 4 | 0.00 | 0 | 0 |
| q12 | semantic | kg | 0 | 0.00 | 0 | 0 | 0.00 | 0 | 0 |
| q12 | semantic | kg_hybrid | 49 | 1.00 | 0 | 0 | 1.00 | 1 | 1 |
| q13 | semantic | raw | 120 | 1.00 | 2 | 4 | 0.00 | 0 | 0 |
| q13 | semantic | raw_wide | 5692 | 1.00 | 202 | 4 | 0.00 | 0 | 0 |
| q13 | semantic | kg | 0 | 0.00 | 0 | 0 | 0.00 | 0 | 0 |
| q13 | semantic | kg_hybrid | 61 | 1.00 | 0 | 1 | 1.00 | 1 | 1 |
| q14 | semantic | raw | 120 | 1.00 | 2 | 5 | 0.00 | 0 | 0 |
| q14 | semantic | raw_wide | 5692 | 1.00 | 202 | 5 | 0.00 | 0 | 0 |
| q14 | semantic | kg | 0 | 0.00 | 0 | 0 | 0.00 | 0 | 0 |
| q14 | semantic | kg_hybrid | 60 | 1.00 | 0 | 2 | 1.00 | 1 | 1 |
| q15 | semantic | raw | 120 | 1.00 | 2 | 4 | 0.00 | 0 | 0 |
| q15 | semantic | raw_wide | 5692 | 1.00 | 202 | 4 | 0.00 | 0 | 0 |
| q15 | semantic | kg | 0 | 0.00 | 0 | 0 | 0.00 | 0 | 0 |
| q15 | semantic | kg_hybrid | 62 | 1.00 | 0 | 0 | 1.00 | 1 | 1 |

## Key Findings

1. **H1 & H2 (Precision & Token Efficiency):** At BPS-scale width (`raw_wide`), `kg_hybrid` cuts mean prompt context from **5692 → 62 tokens (~92×)** while maintaining **1.00 gold column recall** across both slices.
2. **H3 & Phase 2 EX (Standards Grounding → Execution Accuracy):** Raw DDL (`raw`, `raw_wide`) achieves **0.00 EX** because database column identifiers carry no SKOS region codes (`'32'` for West Java) or bilingual measure definitions.
3. **H4 (`kg` vs `kg_hybrid` Differentiation):** On the lexical slice (`q01`–`q10`), `kg` and `kg_hybrid` both achieve **0.70 EX**. On the semantic/paraphrase slice (`q11`–`q15`, e.g., *"cost of living in Bandung's province"*, *"penghasilan bulanan buruh di Pulau Dewata"*), lexical containment (`kg`) drops to **0.00 recall / 0.00 EX**, whereas `kg_hybrid` (BM25 + concept/n-gram vector cosine fused via RRF) holds **1.00 recall / 1.00 EX** (overall EX: **0.47 → 1.00**).
4. **W3C PROV-O Completeness (Claim A / E3 preview):** 100% of queries executed under `kg_hybrid` emit a complete `prov:Entity → prov:Activity → prov:Agent + stats:Dataflow` lineage chain.
