# ADR-0001: RDF triple store over Labeled Property Graph for the knowledge graph layer

- **Status:** Accepted
- **Date:** 2026-10-27
- **Related:** PRD §4.2 (Knowledge Graph and GraphRAG), PRD §11 (Knowledge Graph & GraphRAG Service), `docs/positioning.md` (Claim A)

---

## Context

StatsDialogue needs a knowledge graph to ground schema linking and GraphRAG retrieval (PRD §4.2). Two data-model families were on the table:

- **RDF triple store** queried with SPARQL (W3C) — the semantic-web stack.
- **Labeled Property Graph (LPG)** queried with ISO GQL (ISO/IEC 39075:2024) — Neo4j, Memgraph, Ultipa GQLDB.

Pressures shaping the decision:

1. **Standards alignment.** The metadata the system must consume is already RDF-native: PROV-O for provenance (PRD §8.2) is a W3C RDF ontology; SDMX has a dedicated RDF vocabulary; the W3C Data Cube Vocabulary models statistical observations; SDMX Codelists map directly to SKOS concept schemes.
2. **Positioning.** The primary novelty claim (`docs/positioning.md`, Claim A: *standards-grounded CQA*) is strengthened by using these standards as-is, and weakened if they must be flattened into a different model.
3. **Scale.** The graph holds metadata only — DSDs, codelists, and query history: thousands to low millions of triples. Fact data (millions of rows) lives in DuckDB (PRD §6). Traversal performance is therefore not a differentiator at this scale.
4. **Ecosystem pull.** Mainstream GraphRAG tooling (Microsoft GraphRAG, LangChain integrations) and the published evidence for token/accuracy gains (PRD refs [29], [30]) target Neo4j/Cypher — a genuine pull toward LPG.
5. **Options explored.** Ultipa GQLDB was specifically evaluated: native ISO GQL, built-in vector & LLM functions, single binary, free community edition, strong reported traversal performance.

## Decision

**We will represent the knowledge graph as RDF triples queried with SPARQL 1.1.**

- **Ontology stack:** SDMX-Metadata RDF vocabulary (structure) · W3C Data Cube Vocabulary (observations) · SKOS (codelists) · W3C PROV-O (lineage) · thin custom ontology mapping BPS WebAPI domains/variables/periods onto the SDMX model.
- **Prototype store:** `rdflib` (embedded, pure Python) for development; Apache Jena Fuseki (server) when service deployment is needed. Oxigraph / GraphDB Free remain open alternatives.
- **Access pattern:** the store sits behind a repository interface (`GraphBackend`), keeping the implementation swappable.
- **Query split:** SPARQL over metadata/ontology (schema linking) + SQL over facts (DuckDB) — the OBDA pattern (PRD §4.2, §4.4).

## Options Considered

### 1. LPG — Neo4j (Community) — rejected

- **For:** largest ecosystem (GraphRAG frameworks, first-class LangChain/LlamaIndex support), largest community, familiar to NLP reviewers; GPLv3 community edition.
- **Against:** SDMX/PROV-O/SKOS/Data Cube would have to be flattened into node and edge properties, losing formal semantics; openCypher is legacy with the GQL transition in progress; adds nothing to the standards-grounding claim.

### 2. LPG — Memgraph — rejected

- **For:** strong write and traversal performance; streaming support.
- **Against:** same model mismatch with the RDF-native standards; smaller ecosystem than Neo4j; licensing varies by edition — would require a procurement review.

### 3. LPG — Ultipa GQLDB — rejected

- **For:** vendor-claimed 100% ISO GQL compliance; AI-native built-in vector/LLM functions; single-binary deployment; free community edition; strong reported traversal performance; SOC2 Type II.
- **Against:** still an LPG — **GQL standardizes *property-graph* querying, so ISO GQL compliance and RDF suitability are orthogonal**; PROV-O and the SDMX vocabularies remain non-native and would be flattened; youngest ecosystem of the three (limited community resources, no first-class GraphRAG framework integrations); proprietary product line — vendor-lock-in scrutiny in government procurement.

### 4. Hybrid — RDF canonical + LPG retrieval cache — rejected

- **For:** best of both worlds if the graph ever becomes large.
- **Against:** over-engineering at metadata scale; two stores to keep consistent. Revisit only if the triggers below fire.

### 5. RDF triple store — ✅ accepted

- **For:** all required vocabularies used verbatim with RDFS/OWL semantics; strengthens positioning Claim A; PROV-O lineage is a native SPARQL query, not an emulation; coherent all-W3C/ISO story for governance (PRD §9); no performance loss at metadata scale; tooling free (rdflib BSD-3, Fuseki Apache-2.0).
- **Against:** SPARQL fluency required instead of Cypher; the mainstream GraphRAG ecosystem must be adapted manually; smaller community than Neo4j's.

## Consequences

**Positive**

- Statistical and provenance vocabularies applied as-is — no semantic flattening; schema linking results carry formal meaning.
- The dual-channel architecture (SPARQL metadata / SQL facts) aligns with the OBDA literature — an additional positioning anchor.
- No cost pressure: the full RDF toolchain is free and open for both prototype and deployment phases.

**Negative (accepted knowingly)**

- GraphRAG-style retrieval (embedding + graph traversal) must be built manually over SPARQL property paths — no drop-in framework.
- Evidence for the 20–30% token / ~10pp accuracy gains (PRD refs [29], [30]) comes from LPG deployments — it motivates the *approach* but is not directly comparable unless an LPG baseline is also run.
- Team must be fluent in SPARQL; documentation and community resources are smaller than Neo4j's.

**Neutral / follow-ups**

- Add an LPG baseline (Neo4j or Ultipa) to evaluation experiment **E1** so the data model is *measured*, not only argued (`docs/positioning.md` §6).
- Keep `GraphBackend` thin: a future switch to LPG requires only a new adapter.

## Revisit Triggers

Reopen this decision if:

1. **E1 shows** SPARQL retrieval latency or recall materially worse than an LPG baseline;
2. the graph grows **beyond tens of millions of triples** (still unlikely for metadata);
3. a target venue or collaborator **requires replication** of the Neo4j-based GraphRAG results (refs [29], [30]) in their native stack.

Superseding this ADR requires a **new ADR** with status `supersedes ADR-0001` — this record is not edited in place.
