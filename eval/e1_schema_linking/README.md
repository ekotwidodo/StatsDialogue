# E1 — Schema-Linking Context Ablation

**Phase:** 1 of 2 (phase 1 = context construction, no LLM; phase 2 = generation + execution accuracy)
**Claims:** `docs/positioning.md` → Claim A (standards-grounded), Claim C (orchestration)
**Protocol status:** phase 1 executed 2026-10-27 → see [`results.md`](results.md)

## Goal

Measure what a statistics-native knowledge graph buys in the context handed to the
Text-to-SQL generator, compared against dumping raw relational DDL.

## Hypotheses

| ID | Hypothesis |
|---|---|
| **H1** | KG-based contexts retain gold schema recall while removing irrelevant schema (precision). |
| **H2** | KG-based contexts cut context token cost as schema width grows (BPS: thousands of sub-tables, PRD §4.1). |
| **H3** | KG-based contexts carry semantic labels (units, bilingual names) that raw DDL never has. |

## Design

- **Dataset:** `dataset.json` — 10 questions (English + Indonesian), each with gold
  tables, columns, and semantic label probes. Synthetic domain (3 tables), closed
  vocabulary shared with the sample KG.
- **Conditions:**
  - `raw` — full DDL dump from `schema_ddl.sql` (no semantic layer)
  - `raw_wide` — `raw` + 200 distractor tables (BPS-scale width simulation)
  - `kg` — label-containment retrieval + ontology expansion → compact schema cards
  - `kg_hybrid` — BM25 ranked retrieval (top-6) + ontology expansion (vector stage: TODO)
- **Metrics:**
  - `tokens` — chars/4 estimator (same as spike 001)
  - `recall` — gold columns present in context
  - `extra tables / extra cols` — non-gold schema dragged in (noise)
  - `labels` — gold semantic labels present (raw has none by design)

## How to run

```bash
.venv/bin/python eval/e1_schema_linking/run_e1.py          # phase 1
.venv/bin/python eval/e1_schema_linking/run_e1.py --llm     # phase 2 gate info
```

## Phase 1 outcome (2026-10-27)

| condition | mean tokens | gold recall | extra tables | extra cols | label coverage |
|---|---:|---:|---:|---:|---:|
| raw | 120 | 1.00 | 2.0 | 4.7 | 0.00 |
| raw_wide | 5692 | 1.00 | 202.0 | 4.7 | 0.00 |
| kg | 74 | 1.00 | 0.2 | 1.4 | 1.00 |
| kg_hybrid | 74 | 1.00 | 0.2 | 1.4 | 1.00 |

- **H1 ✅** — unrelated tables −90%, unrelated columns −70%, recall held at 1.00.
- **H2 ✅** — at BPS-scale width: 5692 → 74 tokens (**≈77×**). At toy width the gap
  is modest (120 → 74) — the advantage is driven by schema width, as predicted.
- **H3 ✅** — label coverage 0.00 → 1.00 (units, bilingual measure & region names).
- **Honest note:** `kg` and `kg_hybrid` are *identical* on this corpus — BM25 ranking
  and containment converge at n=18 resources. Differentiation needs a larger corpus
  and the vector (semantic) stage.

## Phase 2 (gated)

Requires: (1) an LLM API key (`OPENAI_API_KEY` / `ANTHROPIC_API_KEY`), (2) fact
fixtures or `BPS_API_KEY`, (3) DuckDB already in `.venv`. Metric: Execution Accuracy
(EX) + Exact Match (EM) per condition — the accuracy half of Claim A.

## Threats to validity

- Synthetic 3-table domain; closed vocabulary shared with the KG (recall ceiling is
  optimistic; paraphrase/semantic queries would expose lexical misses — the vector
  stage is the designed mitigation).
- Token counts use chars/4, not a real tokenizer.
- Single-turn questions; dialogue history (C-DIC) is out of E1 scope.
