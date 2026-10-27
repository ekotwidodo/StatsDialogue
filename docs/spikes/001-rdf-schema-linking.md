# Spike 001 — RDF Schema-Linking over the Sample Statistics KG

- **Date:** 2026-10-27
- **Purpose:** prove the ADR-0001 direction end-to-end: build an SDMX-shaped RDF
  graph and run SPARQL schema-linking queries without touching an LPG.
- **Stack:** Python 3.12 · rdflib 7.6.0 · SPARQL 1.1 · W3C SKOS + Data Cube (light)
  + PROV-O · thin local `stats:` vocabulary (stand-in for SDMX-Metadata, ADR-0001)

## Setup

| File | Role |
|---|---|
| `services/graph/build_sample_graph.py` | builds the sample KG → `sample_stats.ttl` (189 triples, generated, not committed) |
| `services/graph/spike_demo.py` | runs queries Q1–Q6 and the token sketch |

Graph contents: 3 dataflows (inflation, poverty, minimum wage) → DSDs → 2 shared
dimensions + 4 measures; SKOS geography codelist (9 Indonesian regions, EN+ID
labels, `skos:broader` hierarchy); SKOS measure scheme; light `qb:` components; a
PROV-O lineage sample (answer → activity → agent + source); `sqlTable`/`sqlColumn`
bridges to the relational schema.

```bash
.venv/bin/python services/graph/build_sample_graph.py   # writes 189 triples
.venv/bin/python services/graph/spike_demo.py           # runs Q1–Q6
```

## Results (all six queries executed successfully)

| # | Query | Demonstrates | Output |
|---|---|---|---|
| Q1 | Filterable dimensions of `DF_INFLATION` | DSD grounding (PRD §5.1: filter only what the DSD declares) | `DIM_GEO (Geography)`, `DIM_TIME (Time period)` |
| Q2 | Resolve "West Java"/"Jawa Barat" | SKOS entity resolution across languages | `32 · West Java · Jawa Barat` |
| Q3 | "gaji / worker wage" → structure | multi-hop: measure → DSD → dataflow → `fact_min_wage.min_wage` | `M_MIN_WAGE · Regional minimum wage · DF_MINWAGE · fact_min_wage · min_wage` |
| Q4 | Dataflows supporting GEO×TIME | property paths + aggregation | all 3 flows with tables + measures |
| Q5 | Minimal LLM context (CONSTRUCT) | targeted subgraph vs raw schema dump | see token note below |
| Q6 | PROV-O lineage (PRD §8.2) | native provenance walk | answer → exec-001 → sd-agent → DF_INFLATION |

## Key findings

1. **Plain SPARQL is enough for the core schema-linking moves** — no LPG required:
   entity resolution (SKOS labels), multi-hop hops (`/` paths), and targeted context
   construction (`CONSTRUCT`) all work on a 189-triple graph with zero extensions.
2. **Serialization format dominates token cost.** For Q5 the same subgraph costs:
   - as raw Turtle: **206 tokens** (prefix boilerplate — worse than the 81-token raw DDL)
   - as compact *schema cards* (E1's format): **74 tokens** vs 120 for raw DDL.
   ⇒ The KG's value is realized through a deliberately compact context serializer,
   not by dumping RDF. This is now an explicit design requirement for PRD §4.2's
   "compact subgraph" step.
3. **Raw DDL only loses on tokens when schema is wide** (E1 `raw_wide`: 5692 vs
   74 ≈ 77×). At 3-table toy width the raw dump is small — but it still has **zero
   semantic labels**, which is the durable advantage (E1 H3: 0.00 → 1.00).
4. **PROV-O lineage is a one-query walk**, not an emulation — the §8.2 "Lineage
   Trail" button has a straight implementation path.
5. **ISO GQL/LPG was not needed anywhere** in Q1–Q6 — supporting evidence for
   ADR-0001's "orthogonal" argument (standard compliance ≠ required model).

## Limitations

- Synthetic sample graph; not yet ingested from a real SDMX DSD or BPS WebAPI payload.
- Retrieval is lexical only (label containment / BM25); the vector stage of the
  hybrid design (PRD §4.1) is not implemented — pure-semantic queries like
  "income" → minimum wage depend on it (partial lexical fallback: "worker" hits).
- Single-turn; no dialogue state involved at this stage.

## Next

- E1 phase 2 (LLM → SQL → DuckDB EX) once an LLM key is available.
- Vector/semantic stage for `kg_hybrid`.
- Real ingest path: SDMX DSD JSON → RDF (mapping onto the SDMX-Metadata vocabulary).
