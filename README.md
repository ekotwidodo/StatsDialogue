# StatsDialogue

**Conversational Question Answering (CQA) system for official statistics.**

StatsDialogue is an analytical AI agent that lets you explore official statistics — such as those from Statistics Indonesia (BPS) and international agencies — through natural conversation. Instead of writing SQL or navigating static dashboards, you simply ask questions, and StatsDialogue translates them into verified analytical queries with traceable, auditable results.

> **Status:** 🚧 In development — research prototype.

---

## Why StatsDialogue?

Access to official statistics is critical for policymakers, analysts, academics, and the public. Yet most data exploration tools still demand technical skills — SQL, dashboard filters, or spreadsheet gymnastics — which blocks true data democratization.

Existing Text-to-SQL and CQA systems struggle with the realities of statistical data:

- **Hybrid content** — numbers live alongside footnotes, methodologies, and definitions.
- **Ambiguous questions** — users ask incomplete or underspecified queries.
- **Multi-step reasoning** — real analysis requires more than a single lookup.
- **Long conversations** — context degrades as dialogue turns accumulate.

StatsDialogue is built specifically to address these gaps, combining recent NLP research with hardened, production-grade engineering.

---

## Key Capabilities

| Capability | Description |
|---|---|
| **Multi-turn dialogue** | Maintains coherent context across long conversations via incremental memory compression and coreference resolution. |
| **Proactive clarification** | Detects ambiguous or unanswerable questions and asks for clarification instead of guessing. |
| **Grounded Text-to-SQL** | Translates natural language into SQL through schema linking, AST decomposition, and self-correction — never free-form hallucination. |
| **Semantic consistency** | Centralized metric definitions ensure calculations stay reproducible and consistent with official methodology. |
| **Confidence calibration** | Conformal prediction and consistency-based scoring quantify uncertainty; the system abstains when confidence is low. |
| **Full provenance** | Every answer comes with a traceable lineage: source → transformation → result. |
| **Privacy-preserving** | Aggregate-only execution, sandboxed compute, and differential privacy for sensitive microdata. |

---

## Data Sources

StatsDialogue natively integrates with two complementary standards:

- **[SDMX 3.0](https://sdmx.org/)** — ISO 17369 standard for statistical data and metadata exchange, used by the UN, IMF, World Bank, Eurostat, and others. StatsDialogue leverages dataflows, data structure definitions (DSDs), and codelhs for precise schema grounding.
- **[BPS WebAPI](https://webapi.bps.go.id/)** — Open data portal from Statistics Indonesia, covering 1,000+ official datasets, including SDG and SDDS catalogs.

---

## Architecture (High-Level)

```
┌─────────────────────────────────────────────────────────┐
│                    Conversational UI                     │
└───────────────────────────┬─────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────┐
│     Dialogue Understanding & Context Management          │
│   (incremental memory · coreference · DST · abstention)  │
└───────────────────────────┬─────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────┐
│         Query Generation & Confidence Layer              │
│   (hybrid RAG · schema linking · AST decomposition ·     │
│    conformal calibration · semantic layer)               │
└───────────────────────────┬─────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────┐
│         Secure Analytical Engine (read-only sandbox)     │
│   (in-memory OLAP · differential privacy · k-anonymity) │
└───────────────────────────┬─────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────┐
│        Data Integration & Provenance Layer               │
│   (BPS WebAPI · SDMX 3.0 · VTL · W3C PROV-O lineage)    │
└─────────────────────────────────────────────────────────┘
```

The system runs as a set of asynchronous microservices: a metadata/integration service, a dialogue memory service, a query generation and calibration service, and a sandboxed compute engine.

---

## Tech Stack (Planned)

| Layer | Technology |
|---|---|
| Language & runtime | Python 3.11+ |
| Analytical engine | DuckDB (in-memory, columnar OLAP) |
| Query mediation | Semantic layer (MetricFlow / Cube / Malloy) |
| Data standards | SDMX 3.0, VTL 2.x |
| Retrieval | Hybrid search (BM25 + vector embeddings) |
| Provenance | W3C PROV-O |
| Governance | ISO/IEC 42001, NIST AI RMF |

---

## Evaluation

StatsDialogue targets state-of-the-art results on established benchmarks:

- **BIRD-SQL** — logical and execution accuracy on large-scale, noisy real-world schemas.
- **Multi-turn CQA** — context retention and fluency stability over 20+ dialogue turns.
- **Calibration** — Expected Calibration Error (ECE) and AUROC for error detection and abstention behavior.

---

## Getting Started

> _Not yet available — this repository is in active development._

Planned quickstart:

```bash
git clone https://github.com/<org>/statsdialogue.git
cd statsdialogue
cp .env.example .env      # add your BPS API key
make install
make run
```

---

## Project Structure

```
statsdialogue/
├── README.md
├── PRD.md               # full product requirements (local only)
├── services/
│   ├── metadata/        # BPS WebAPI & SDMX integration
│   ├── dialog/          # dialogue state & memory management
│   ├── generator/       # Text-to-SQL & confidence calibration
│   └── engine/          # sandboxed analytical compute
├── semantic/            # metric & dimension definitions
├── provenance/          # lineage tracking (PROV-O)
├── eval/                # benchmarks & evaluation harness
└── docs/
```

---

## Responsible AI

StatsDialogue is designed for high-stakes public data dissemination. Trust is not a feature — it is an architectural requirement:

- **Transparency** — every result is traceable to its source.
- **Calibration** — the system knows what it does not know, and says so.
- **Privacy** — sensitive data never leaves a controlled, audited boundary.
- **Accountability** — aligned with ISO/IEC 42001 and NIST AI RMF.

---

## License

_[To be determined — pending institutional review.]_

---

## Author

**Eko Teguh Widodo** — [id.ekoteguh@gmail.com](mailto:id.ekoteguh@gmail.com)

---

## Acknowledgements

This project builds on research and tooling from the communities behind [BIRD-SQL](https://bird-bench.github.io/), [SDMX](https://sdmx.org/), [DuckDB](https://duckdb.org/), [PACIFIC](https://aclanthology.org/2022.emnlp-main.469/), and [Tab-CQA](https://aclanthology.org/2023.acl-industry.20/).
