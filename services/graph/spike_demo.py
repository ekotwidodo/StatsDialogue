#!/usr/bin/env python3
"""Spike 001 — SPARQL schema-linking queries over the sample statistics KG.

Runs six representative queries from PRD section 4.2 (RDF-based GraphRAG):

  Q1  filterable dimensions of a dataflow (DSD grounding, section 5.1)
  Q2  entity resolution: "West Java" / "Jawa Barat" -> geo code 32 (SKOS)
  Q3  lexical + graph hop: "gaji / worker wage" -> measure -> DSD -> table
  Q4  multi-hop property paths: dataflows supporting GEO x TIME filters
  Q5  minimal LLM context vs raw schema dump (token-cost sketch, E1 preview)
  Q6  PROV-O lineage walk for an answer (section 8.2)

Usage:  .venv/bin/python services/graph/spike_demo.py
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_sample_graph import OUT, build  # noqa: E402

RAW_DDL = """\
CREATE TABLE fact_inflation (
  time_period VARCHAR,
  geo_code VARCHAR,
  inflation_rate DOUBLE,
  unit VARCHAR
);
CREATE TABLE fact_poverty (
  time_period VARCHAR,
  geo_code VARCHAR,
  poverty_rate DOUBLE,
  poor_pop BIGINT
);
CREATE TABLE fact_min_wage (
  time_period VARCHAR,
  geo_code VARCHAR,
  min_wage BIGINT
);
"""

QUERIES: list[tuple[str, str, str]] = [
    (
        "Q1 — Filterable dimensions of DF_INFLATION (DSD grounding)",
        """
        SELECT ?dim ?label WHERE {
          stats:DF_INFLATION stats:structure/stats:hasDimension ?dim .
          OPTIONAL { ?dim rdfs:label|skos:prefLabel ?label . FILTER(lang(?label) = "en") }
        } ORDER BY ?dim
        """,
        "text",
    ),
    (
        'Q2 — Resolve "West Java" / "Jawa Barat" to a geo code (SKOS labels)',
        """
        SELECT DISTINCT ?code ?en ?idn WHERE {
          ?c a skos:Concept ; skos:inScheme stats:CL_GEO ; stats:code ?code .
          ?c skos:prefLabel|skos:altLabel ?lab .
          FILTER(CONTAINS(LCASE(STR(?lab)), "west java")
              || CONTAINS(LCASE(STR(?lab)), "jawa barat"))
          OPTIONAL { ?c skos:prefLabel ?en . FILTER(lang(?en) = "en") }
          OPTIONAL { ?c skos:prefLabel ?idn . FILTER(lang(?idn) = "id") }
        }
        """,
        "text",
    ),
    (
        'Q3 — "gaji / worker wage" -> measure -> DSD -> sql table/column (multi-hop)',
        """
        SELECT DISTINCT ?m ?mlabel ?df ?table ?col WHERE {
          ?m a stats:Measure ;
             skos:prefLabel|skos:altLabel ?lab ;
             skos:prefLabel ?mlabel ;
             stats:sqlColumn ?col .
          FILTER(lang(?mlabel) = "en")
          FILTER(CONTAINS(LCASE(STR(?lab)), "worker wage")
              || CONTAINS(LCASE(STR(?lab)), "gaji"))
          ?dsd stats:hasMeasure ?m .
          ?df stats:structure ?dsd ; stats:sqlTable ?table .
        } LIMIT 10
        """,
        "text",
    ),
    (
        "Q4 — Dataflows supporting GEO x TIME filtering (property paths)",
        """
        SELECT ?df ?table (GROUP_CONCAT(DISTINCT ?mname; separator=", ") AS ?measures) WHERE {
          ?df stats:structure ?dsd ; stats:sqlTable ?table .
          ?dsd stats:hasDimension stats:DIM_GEO , stats:DIM_TIME ;
               stats:hasMeasure ?m .
          ?m skos:prefLabel ?mname . FILTER(lang(?mname) = "en")
        } GROUP BY ?df ?table ORDER BY ?df
        """,
        "text",
    ),
    (
        'Q5 — Minimal LLM context for "inflation in West Java 2024" vs raw dump',
        """
        CONSTRUCT {
          ?df a stats:Dataflow ; stats:sqlTable ?table ; rdfs:label ?dflab .
          stats:DSD_INFLATION stats:hasDimension ?dim ; stats:hasMeasure ?m .
          ?dim rdfs:label ?dimlab ; stats:sqlColumn ?dimcol .
          ?m stats:sqlColumn ?mcol ; stats:unit ?unit ; skos:prefLabel ?mlab .
          stats:GEO_32 a skos:Concept ; stats:code ?code ; skos:prefLabel ?geolab .
        }
        WHERE {
          ?df stats:structure stats:DSD_INFLATION ; stats:sqlTable ?table ; rdfs:label ?dflab .
          stats:DSD_INFLATION stats:hasDimension ?dim ; stats:hasMeasure ?m .
          ?dim rdfs:label ?dimlab ; stats:sqlColumn ?dimcol .
          ?m stats:sqlColumn ?mcol ; stats:unit ?unit ; skos:prefLabel ?mlab .
          FILTER(lang(?mlab) = "en")
          stats:GEO_32 stats:code ?code ; skos:prefLabel ?geolab .
          FILTER(lang(?geolab) = "en")
        }
        """,
        "ttl",
    ),
    (
        "Q6 — PROV-O lineage: answer -> activity -> agent + source (section 8.2)",
        """
        SELECT ?answer ?activity ?agent ?source WHERE {
          ?answer a prov:Entity ; prov:wasGeneratedBy ?activity ; prov:wasDerivedFrom ?source .
          ?activity prov:wasAssociatedWith ?agent .
        }
        """,
        "text",
    ),
]


def tokens(text: str) -> int:
    """Approximate token count (~4 chars/token) — E1 uses the same estimator."""
    return math.ceil(len(text) / 4)


def main() -> None:
    # Deterministic: always rebuild the sample graph so the demo is fresh.
    g = build()
    g.serialize(OUT, format="turtle")
    print(f"loaded sample graph: {len(g)} triples -> {OUT.name}\n")

    for title, query, fmt in QUERIES:
        print("=" * 78)
        print(title)
        print("-" * 78)
        rows = g.query(query)
        if fmt == "ttl":
            raw_ctx = rows.serialize(format="turtle")
            context = raw_ctx.decode("utf-8") if isinstance(raw_ctx, (bytes, bytearray)) else str(raw_ctx)
            print(context.strip())
            print(f"\n  [KG context: {tokens(context)} tokens | raw 3-table DDL: {tokens(RAW_DDL)} tokens"
                  f" | raw/context = {tokens(RAW_DDL) / max(tokens(context), 1):.2f}"
                  f" — toy scale; see spike report for interpretation]")
        else:
            if not len(rows.vars):
                print("(no bindings)")
            else:
                print(" | ".join(str(v).split("#")[-1] for v in rows.vars))
                for row in rows:
                    print(" | ".join("" if x is None else str(x) for x in row))
        print()


if __name__ == "__main__":
    main()
