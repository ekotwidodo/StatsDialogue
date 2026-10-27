# Positioning & Contributions — StatsDialogue

> **Internal working document.** Purpose: fix the novelty claims *before* selecting a publication venue. Venue is a consequence of the strongest defensible delta — never the starting point.
>
> Status: draft v0.2 · Last updated: 2026-10-27

---

## 1. Problem Statement (the gap)

Official statistics — SDMX-governed data from national statistics offices such as BPS — remain exploration-hostile: users need dashboards, SQL, or API spelunking to answer even simple questions. Three failures block conversational access to this domain:

1. **Schema blindness.** Existing conversational Text-to-SQL systems ground against raw database structure. Statistical metadata (DSDs, codelists, methodological definitions) is invisible to them, so they guess column semantics that the standards already define precisely.
2. **No provenance.** An official statistic without lineage cannot be published, audited, or defended. Consumer-grade QA systems return numbers with no traceable source → transformation chain.
3. **Unaccountable confidence.** For institutions, a *confident wrong number* is a liability, not a 60% answer. Calibration and abstention are mandatory, not optional.

Meanwhile the official-statistics community has stated the vision — SISCC's **SDMX+AI** initiative calls for *"universal, natural language and conversational access to statistical sources"* — but **no evaluated system exists** that turns this vision into a working, measurable architecture.

**One-line problem:** *How can a conversational agent answer questions over official statistics such that every answer is standards-grounded (SDMX), lineage-verified (PROV-O), and confidence-calibrated (conformal) — without sacrificing analytical accuracy?*

---

## 2. Prior Art Scan (honest inventory)

| Work | What it does | Residual gap StatsDialogue targets |
|---|---|---|
| **PACIFIC** (EMNLP '22) | Proactive CQA dataset, financial domain | Not official statistics; no SDMX, no provenance, no calibration |
| **Tab-CQA** (ACL Industry '23) | Tabular CQA over financial reports | No standards grounding; no trust/provenance layer |
| **BIRD-INTERACT** (ICLR '26) | Interactive Text-to-SQL eval with clarification budgets | Generic schemas; single-domain eval; no provenance, no metadata ontology |
| **Adaptive Abstention** (arXiv '25, ref [4]) | Conformal abstention for Text-to-SQL | Generic domains; no dialogue memory; no standards; abstention reasons not domain-grounded |
| **Gov-Transparency Multi-Agent CQA** (2025) ¹ | Conversational Text-to-SQL over government data | Raw schemas (no statistical metadata); no calibration or provenance claims |
| **SDMX+AI / SISCC** | Community vision: NL + conversational access over SDMX | Vision/initiative only — no system, no evaluation |
| **Text-to-SPARQL line** (mKGQAgent, KnowledgeNLP '25, Ontotext NL2SPARQL) | NL → SPARQL over generic knowledge graphs | Not statistical metadata; no SQL fact channel; no multi-turn calibration |
| **StatsDialogue** | *(proposed)* | Standards-grounded + provenance-first + calibrated + multi-dialect, on official statistics |

¹ *Based on public abstract — verify details during the formal related-work pass.*

**Key implication:** every individual component of the PRD (C-DIC, AST decomposition, GraphRAG, conformal prediction, hybrid RAG) exists in prior work and is cited as such. The contribution must be defined as the **delta**, not the assembly.

---

## 3. Contribution Claims

### Primary A — Standards-grounded conversational QA over official statistics

**Claim:** first CQA system that uses official-statistics metadata standards as the *substrate* of query construction — SDMX DSD/codelists for schema linking, VTL for validated statistical transforms, and W3C PROV-O as a first-class payload of every answer.

- **Delta:** closes the SDMX+AI vision with an evaluated architecture; vs. government Text-to-SQL systems that see only raw schemas.
- **Evidence required:** ablation (KG on/off) on schema-linking accuracy and execution accuracy; provenance completeness audit (% of answers with a full PROV-O chain); end-to-end evaluation on BPS/SDMX data.
- **Reviewer risk:** *"integration/system paper."* **Counter:** new problem domain + standards-grounded mechanism + ablation proving each standard contributes measurable accuracy/trust — plus the domain itself is not served by any existing system.

### Primary C — Multi-dialect orchestration in one dialogue (SQL + SPARQL + VTL)

**Claim:** a single conversation routes across three formalisms with distinct engines: SPARQL over the metadata ontology (what *can* be asked), SQL over DuckDB (facts), VTL (validated statistical transforms).

- **Delta:** no prior conversational system orchestrates three standards-backed query dialects with confidence calibration over the routing decision.
- **Evidence required:** cross-dialect benchmark (questions requiring metadata traversal + fact aggregation + transform); accuracy and latency vs. single-dialect baselines; routing-error analysis.

### Secondary B — Calibrated trust for institutional statistics

**Claim:** conformal prediction + consistency calibration + adaptive abstention where *abstention reasons are domain-grounded* (citing missing metadata bounds, absent dimension ranges), not generic refusal.

- **Delta vs. ref [4]:** generic correctness abstention → abstention bound to official-statistics metadata and provenance. Must be framed as **secondary** to avoid the "incremental on [4]" objection.
- **Evidence required:** ECE, AUROC (error detection), abstention quality study; comparison against ref [4]'s protocol.

### Amplifier D — Official-Statistics CQA evaluation set

**Claim:** a benchmark with proactivity, calibration, and provenance metrics — the PACIFIC/Tab-CQA template (both are in our own reference list) applied to a new, unserved domain.

- **Why it matters:** datasets are the most legible contribution for reviewers across venues; they also force reproducibility of claims A/B/C.
- **Scope decision (open):** BPS-only vs. multi-NSO; Indonesian vs. bilingual; ground truth in SQL, SPARQL, or both.

---

## 4. Gap Matrix

| System | Official-stats domain | Multi-turn | SDMX metadata grounding | Provenance | Calibration / abstention | Cross-dialect | Dataset |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| PACIFIC | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✓ |
| Tab-CQA | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✓ |
| BIRD-INTERACT | ✗ | ~ | ✗ | ✗ | ~ (clarify) | ✗ | ✓ |
| Adaptive Abstention [4] | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Gov-Transparency CQA '25 | ~ (gov) | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| SDMX+AI (SISCC) | ✓ | ✓ (vision) | ✓ (vision) | ✗ | ✗ | ✗ | ✗ |
| Text-to-SPARQL line | ✗ | ✗ | ✗ | ✗ | ✗ | SPARQL only | ✗ |
| **StatsDialogue** | **✓** | **✓** | **✓** | **✓** | **✓** | **✓** | planned (D) |

The empty cells of the columns *combined* (SDMX grounding + provenance + calibration + cross-dialect) are the defensible territory.

---

## 5. Positioning & Venue Consequences

**One-sentence pitch:**

> *StatsDialogue is the first conversational question-answering system that answers official-statistics questions with standards-grounded queries (SDMX), provenance-verified lineage (PROV-O), and calibrated confidence (conformal prediction) — turning the SDMX+AI vision into an evaluated, auditable system.*

**Venue follows from where the experiments land strongest:**

| If strongest results are… | Venue family | Precedent |
|---|---|---|
| Claims A + D (system + dataset) | NLP: ACL / EMNLP main, findings, or industry | PACIFIC, Tab-CQA |
| Claims A + C (standards + orchestration) | Semantic Web: ISWC / ESWC / SEMANTiCS; statistics community: SDMX conferences, Journal of Official Statistics | linked-statistics / OBDA line |
| Claim B (calibration) | Trustworthy-AI / NLP reliability venues | ref [4] — *most crowded claim; keep secondary* |

**Recommendation:** A primary, C second, B secondary, D amplifier. This keeps **all three venue families open** until E1/E2 experiments (below) reveal where the delta is strongest.

---

## 6. Experiments tied to claims

| ID | Experiment | Proves | Claim |
|---|---|---|---|
| E1 | Schema-linking ablation: raw schema vs. +KG vs. +KG+hybrid retrieval → EX, EM, token cost | Standards grounding buys accuracy and efficiency | A, C |

**E1 status (2026-10-27):** phases 1 & 2 executed over 15 bilingual questions (10 lexical + 5 semantic/paraphrase) using `RdflibBackend` + `DuckDBSandbox`:
- **Context efficiency (H1/H2):** at BPS-scale schema width (`raw_wide`), `kg_hybrid` cuts context tokens **~92×** (5692 → 62) and eliminates unrelated tables (202.0 → 0.0) while holding **1.00 gold recall**.
- **Execution accuracy (H3):** `raw` / `raw_wide` score **0.00 EX** on DuckDB because raw DDL lacks SKOS `geo_code` bindings and bilingual measure definitions; `kg_hybrid` achieves **1.00 EX** and **1.00 PROV-O lineage completeness**.
- **Hybrid vs. lexical KG (H4):** on semantic paraphrases (`q11`–`q15`) and multi-token Java province disambiguation, `kg_hybrid` (BM25 + semantic vector RRF) lifts overall recall **0.67 → 1.00** and EX **0.47 → 1.00** (lexical EX: 0.70 → 1.00; semantic EX: 0.00 → 1.00).
Artifacts: [`eval/e1_schema_linking/`](../eval/e1_schema_linking/), [`services/graph/backend.py`](../services/graph/backend.py), [`services/engine/sandbox.py`](../services/engine/sandbox.py), [runtime spike](spikes/001-rdf-schema-linking.md).
| E2 | Calibration: ECE, AUROC, abstention quality with domain-grounded refusal reasons | Trust layer works; knows what it doesn't know | B |
| E3 | Provenance completeness audit: % answers with full PROV-O chain | Auditability claim is real | A |
| E4 | Multi-turn stability: perplexity flat over >20 turns (PRD §10.2) | C-DIC works at conversation scale | system |
| E5 | (Optional, enables D) Release evaluation set + metrics | Reproducibility; benchmark contribution | D |

---

## 7. Open Questions

1. **Dataset scope** — BPS-only or multi-NSO? Indonesian, English, or bilingual?
2. **Venue decision gate** — decide *after* E1/E2, not before. No venue-driven scope changes.
3. ~~**ADR-0001 (graph model: RDF)**~~ — **resolved:** `docs/adr/0001-graph-model-rdf-over-lpg.md` records the decision, the considered options (Neo4j, Memgraph, Ultipa, hybrid), consequences, and revisit triggers.
4. ~~**README sync**~~ — **resolved:** README now reflects the RDF/SPARQL direction (capabilities, architecture diagram, tech stack, docs structure).
5. **Related-work verification** — Gov-Transparency paper (2025) and SISCC SDMX+AI materials need a full read during the formal related-work pass.
6. ~~**Is plain SPARQL sufficient for the KG's role?**~~ — **resolved (spike 001):** entity resolution, multi-hop linking, targeted `CONSTRUCT` context, and PROV-O lineage all execute without an LPG. New derived requirement: the KG's token advantage depends on a **compact schema-card serializer** — dumping raw Turtle *loses* to raw DDL (206 vs 81 tokens at toy scale); see [`docs/spikes/001-rdf-schema-linking.md`](spikes/001-rdf-schema-linking.md) finding 2.

---

## References (positioning-specific)

- Prior art entries map to PRD reference numbers where applicable: PACIFIC [^7], Tab-CQA [^6], BIRD-INTERACT [^14], Adaptive Abstention [^4].
- SDMX+AI (SISCC): <https://siscc.org/sdmxai/>
- Gov-Transparency Multi-Agent CQA (2025): ResearchGate publication 397818645
- mKGQAgent / Text-to-SPARQL: <https://arxiv.org/abs/2507.16971>
