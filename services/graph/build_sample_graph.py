#!/usr/bin/env python3
"""Build the sample statistics knowledge graph (RDF) for the graph spike and E1 harness.

The graph is synthetic but structurally faithful to what StatsDialogue ingests:

- SDMX-style structure: Dataflow -> DSD -> dimensions/measures.
  A thin local ``stats:`` vocabulary stands in for the SDMX-Metadata RDF
  vocabulary (production maps onto it — see ADR-0001, PRD section 4.2).
- SKOS concept schemes for geography and measures (W3C SKOS).
- Light W3C Data Cube usage (qb:component / qb:dimension / qb:measure on DSDs).
- A small W3C PROV-O lineage sample for the provenance demo.
- ``sqlTable`` / ``sqlColumn`` links bridging the KG to the relational schema
  (used by the E1 gold mappings).

Output: sample_stats.ttl (generated artifact, not committed).
"""
from __future__ import annotations

from pathlib import Path

from rdflib import BNode, Graph, Literal, Namespace, RDF, RDFS

STATS = Namespace("https://statsdialogue.local/ns/stats#")
QB = Namespace("http://www.w3.org/ns/qb#")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
PROV = Namespace("http://www.w3.org/ns/prov#")
EX = Namespace("https://statsdialogue.local/ns/ex#")

OUT = Path(__file__).parent / "sample_stats.ttl"

# (code, concept-local-name, label@id, label@en, extra altLabels, is-national)
GEO: list[tuple[str, str, str, str, list[str], bool]] = [
    ("00", "GEO_00", "Indonesia", "Indonesia", ["national", "nasional"], True),
    ("11", "GEO_11", "Aceh", "Aceh", [], False),
    ("12", "GEO_12", "Sumatera Utara", "North Sumatra", ["Sumut"], False),
    ("31", "GEO_31", "DKI Jakarta", "Jakarta", ["DKI", "Jakarta"], False),
    ("32", "GEO_32", "Jawa Barat", "West Java", ["Jabar"], False),
    ("33", "GEO_33", "Jawa Tengah", "Central Java", ["Jateng"], False),
    ("34", "GEO_34", "DI Yogyakarta", "Yogyakarta", ["DIY", "Jogja"], False),
    ("35", "GEO_35", "Jawa Timur", "East Java", ["Jatim"], False),
    ("51", "GEO_51", "Bali", "Bali", [], False),
]

# (local-name, labels, unit, sql-column)
MEASURES: list[tuple[str, dict[str, list[str]], str, str]] = [
    (
        "M_INFLATION_RATE",
        {"en": ["Inflation rate", "CPI inflation"], "id": ["laju inflasi", "inflasi"]},
        "% (year-on-year)",
        "inflation_rate",
    ),
    (
        "M_POVERTY_RATE",
        {"en": ["Poverty percentage", "poverty rate"], "id": ["persentase penduduk miskin", "kemiskinan"]},
        "%",
        "poverty_rate",
    ),
    (
        "M_POVERTY_POP",
        {"en": ["Number of poor population", "poor people"], "id": ["jumlah penduduk miskin", "penduduk miskin"]},
        "persons",
        "poor_pop",
    ),
    (
        "M_MIN_WAGE",
        {"en": ["Regional minimum wage", "minimum wage", "wage", "worker wage"], "id": ["upah minimum", "UMR", "gaji minimum", "gaji"]},
        "IDR/month",
        "min_wage",
    ),
]

DIMS: dict[str, tuple[str, str, str]] = {
    "DIM_TIME": ("Time period", "Periode waktu", "time_period"),
    "DIM_GEO": ("Geography", "Wilayah", "geo_code"),
}

# (local-name, label, measure-local-names, sql-table, bps-domain)
FLOWS: list[tuple[str, str, list[str], str, str]] = [
    ("DF_INFLATION", "Consumer Price Index & Inflation", ["M_INFLATION_RATE"], "fact_inflation", "0000"),
    (
        "DF_POVERTY",
        "Poverty Statistics",
        ["M_POVERTY_RATE", "M_POVERTY_POP"],
        "fact_poverty",
        "0000",
    ),
    ("DF_MINWAGE", "Regional Minimum Wage (UMR)", ["M_MIN_WAGE"], "fact_min_wage", "0000"),
]


def _label(g: Graph, s, en: str, idn: str | None = None) -> None:
    g.add((s, RDFS.label, Literal(en, lang="en")))
    if idn and idn != en:
        g.add((s, RDFS.label, Literal(idn, lang="id")))


def build() -> Graph:
    g = Graph()
    g.bind("stats", STATS)
    g.bind("qb", QB)
    g.bind("skos", SKOS)
    g.bind("prov", PROV)
    g.bind("ex", EX)

    # --- Dimensions -------------------------------------------------------
    for dim, (en, idn, col) in DIMS.items():
        g.add((STATS[dim], RDF.type, STATS.Dimension))
        g.add((STATS[dim], RDF.type, QB.DimensionProperty))
        _label(g, STATS[dim], en, idn)
        g.add((STATS[dim], STATS.sqlColumn, Literal(col)))
    g.add((STATS["DIM_GEO"], STATS.hasCodeList, STATS.CL_GEO))

    # --- Geography codelist (SKOS) ---------------------------------------
    g.add((STATS.CL_GEO, RDF.type, SKOS.ConceptScheme))
    _label(g, STATS.CL_GEO, "Indonesian geography codes", "Kode wilayah Indonesia")
    national = None
    provinces = []
    for code, local, idn, en, alts, is_nat in GEO:
        c = STATS[local]
        if is_nat:
            national = c
        else:
            provinces.append(c)
        g.add((c, RDF.type, SKOS.Concept))
        g.add((c, SKOS.inScheme, STATS.CL_GEO))
        g.add((c, STATS.code, Literal(code)))
        g.add((c, SKOS.prefLabel, Literal(idn, lang="id")))
        g.add((c, SKOS.prefLabel, Literal(en, lang="en")))
        for a in alts:
            g.add((c, SKOS.altLabel, Literal(a, lang="en")))
    for p in provinces:
        g.add((p, SKOS.broader, national))
        g.add((national, SKOS.hasTopConcept, p))
        g.add((p, SKOS.topConceptOf, STATS.CL_GEO))

    # --- Measures (stats:Measure + skos:Concept) -------------------------
    g.add((STATS.CL_MEASURE, RDF.type, SKOS.ConceptScheme))
    _label(g, STATS.CL_MEASURE, "Statistical measures", "Metrik statistik")
    for local, labels, unit, col in MEASURES:
        m = STATS[local]
        g.add((m, RDF.type, STATS.Measure))
        g.add((m, RDF.type, SKOS.Concept))
        g.add((m, SKOS.inScheme, STATS.CL_MEASURE))
        g.add((m, SKOS.prefLabel, Literal(labels["en"][0], lang="en")))
        g.add((m, SKOS.prefLabel, Literal(labels["id"][0], lang="id")))
        for lang in ("en", "id"):
            for extra in labels[lang][1:]:
                g.add((m, SKOS.altLabel, Literal(extra, lang=lang)))
        g.add((m, STATS.unit, Literal(unit)))
        g.add((m, STATS.sqlColumn, Literal(col)))

    # --- Dataflows & DSDs (structure + light Data Cube) ------------------
    for df_local, df_label, measure_locals, table, domain in FLOWS:
        df, dsd = STATS[df_local], STATS["DSD_" + df_local.split("_", 1)[1]]
        g.add((df, RDF.type, STATS.Dataflow))
        _label(g, df, df_label)
        g.add((df, STATS.structure, dsd))
        g.add((df, STATS.sqlTable, Literal(table)))
        g.add((df, STATS.bpsDomain, Literal(domain)))

        g.add((dsd, RDF.type, STATS.DSD))
        _label(g, dsd, f"DSD for {df_label}")
        comp = BNode()
        g.add((dsd, QB.component, comp))
        for dim in DIMS:
            g.add((dsd, STATS.hasDimension, STATS[dim]))
            g.add((comp, QB.dimension, STATS[dim]))
        for m_local in measure_locals:
            g.add((dsd, STATS.hasMeasure, STATS[m_local]))
            g.add((comp, QB.measure, STATS[m_local]))

    # --- PROV-O lineage sample ------------------------------------------
    ans, act, agent = EX["answer-infl-wj-2024"], EX["exec-001"], EX["sd-agent"]
    g.add((ans, RDF.type, PROV.Entity))
    _label(g, ans, "Answer: West Java inflation 2024 (sample)")
    g.add((ans, PROV.wasGeneratedBy, act))
    g.add((ans, PROV.wasDerivedFrom, STATS.DF_INFLATION))
    g.add((act, RDF.type, PROV.Activity))
    _label(g, act, "DuckDB execution of generated SQL (sample)")
    g.add((act, PROV.wasAssociatedWith, agent))
    g.add((agent, RDF.type, PROV.Agent))
    _label(g, agent, "StatsDialogue Text-to-SQL generator (sample)")

    return g


if __name__ == "__main__":
    graph = build()
    graph.serialize(destination=OUT, format="turtle")
    print(f"wrote {OUT.name}: {len(graph)} triples")
