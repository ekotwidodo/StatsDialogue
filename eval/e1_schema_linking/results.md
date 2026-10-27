# E1 Phase 1 Results — Schema-Linking Context Ablation

- Date: 2026-10-27
- Dataset: 10 questions (`dataset.json`), graph: 189 triples
- Token estimator: chars/4 (same as spike 001)
- Retrieval: `kg` = label containment + graph expansion; `kg_hybrid` = BM25 top-6 + graph expansion (vector stage: TODO)

## Aggregate

| condition | mean tokens | gold recall | extra tables | extra cols | label coverage |
|---|---:|---:|---:|---:|---:|
| raw | 120 | 1.00 | 2.0 | 4.7 | 0.00 |
| raw_wide | 5692 | 1.00 | 202.0 | 4.7 | 0.00 |
| kg | 74 | 1.00 | 0.2 | 1.4 | 1.00 |
| kg_hybrid | 74 | 1.00 | 0.2 | 1.4 | 1.00 |

## Per question

| id | condition | tokens | recall | extra tbl | extra col | labels |
|---|---|---:|---:|---:|---:|---:|
| q01 | raw | 120 | 1.00 | 2 | 4 | 0.00 |
| q01 | raw_wide | 5692 | 1.00 | 202 | 4 | 0.00 |
| q01 | kg | 126 | 1.00 | 1 | 2 | 1.00 |
| q01 | kg_hybrid | 126 | 1.00 | 1 | 2 | 1.00 |
| q02 | raw | 120 | 1.00 | 2 | 4 | 0.00 |
| q02 | raw_wide | 5692 | 1.00 | 202 | 4 | 0.00 |
| q02 | kg | 83 | 1.00 | 0 | 1 | 1.00 |
| q02 | kg_hybrid | 83 | 1.00 | 0 | 1 | 1.00 |
| q03 | raw | 120 | 1.00 | 2 | 4 | 0.00 |
| q03 | raw_wide | 5692 | 1.00 | 202 | 4 | 0.00 |
| q03 | kg | 51 | 1.00 | 0 | 0 | 1.00 |
| q03 | kg_hybrid | 51 | 1.00 | 0 | 0 | 1.00 |
| q04 | raw | 120 | 1.00 | 2 | 5 | 0.00 |
| q04 | raw_wide | 5692 | 1.00 | 202 | 5 | 0.00 |
| q04 | kg | 83 | 1.00 | 0 | 2 | 1.00 |
| q04 | kg_hybrid | 83 | 1.00 | 0 | 2 | 1.00 |
| q05 | raw | 120 | 1.00 | 2 | 5 | 0.00 |
| q05 | raw_wide | 5692 | 1.00 | 202 | 5 | 0.00 |
| q05 | kg | 44 | 1.00 | 0 | 1 | 1.00 |
| q05 | kg_hybrid | 44 | 1.00 | 0 | 1 | 1.00 |
| q06 | raw | 120 | 1.00 | 2 | 5 | 0.00 |
| q06 | raw_wide | 5692 | 1.00 | 202 | 5 | 0.00 |
| q06 | kg | 115 | 1.00 | 1 | 3 | 1.00 |
| q06 | kg_hybrid | 115 | 1.00 | 1 | 3 | 1.00 |
| q07 | raw | 120 | 1.00 | 2 | 4 | 0.00 |
| q07 | raw_wide | 5692 | 1.00 | 202 | 4 | 0.00 |
| q07 | kg | 74 | 1.00 | 0 | 0 | 1.00 |
| q07 | kg_hybrid | 74 | 1.00 | 0 | 0 | 1.00 |
| q08 | raw | 120 | 1.00 | 2 | 5 | 0.00 |
| q08 | raw_wide | 5692 | 1.00 | 202 | 5 | 0.00 |
| q08 | kg | 54 | 1.00 | 0 | 1 | 1.00 |
| q08 | kg_hybrid | 54 | 1.00 | 0 | 1 | 1.00 |
| q09 | raw | 120 | 1.00 | 2 | 5 | 0.00 |
| q09 | raw_wide | 5692 | 1.00 | 202 | 5 | 0.00 |
| q09 | kg | 49 | 1.00 | 0 | 1 | 1.00 |
| q09 | kg_hybrid | 49 | 1.00 | 0 | 1 | 1.00 |
| q10 | raw | 120 | 1.00 | 2 | 6 | 0.00 |
| q10 | raw_wide | 5692 | 1.00 | 202 | 6 | 0.00 |
| q10 | kg | 60 | 1.00 | 0 | 3 | 1.00 |
| q10 | kg_hybrid | 60 | 1.00 | 0 | 3 | 1.00 |

## Notes

- `raw` always has full recall on this toy schema but drags every table/column
  and carries **zero** semantic labels — the LLM sees names only.
- `raw_wide` = raw + 200 distractor tables, simulating BPS-scale schema width
  (PRD 4.1: thousands of sub-tables). This is where the token advantage (H2) bites.
- KG conditions carry labels/units (H3) and drop unrelated tables (H1).
- Phase 2 (LLM -> SQL -> DuckDB execution accuracy) awaits an LLM key: `--llm`.
