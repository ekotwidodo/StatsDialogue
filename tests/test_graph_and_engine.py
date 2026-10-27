"""Unit tests for GraphBackend (RdflibBackend) and DuckDBSandbox."""
from __future__ import annotations

import unittest
from pathlib import Path

from services.engine.sandbox import DuckDBSandbox, SecurityViolationError
from services.graph.backend import GraphBackend, RdflibBackend

EVAL_DIR = Path(__file__).resolve().parents[1] / "eval" / "e1_schema_linking"


class TestGraphAndEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.backend = RdflibBackend()
        ddl = (EVAL_DIR / "schema_ddl.sql").read_text(encoding="utf-8")
        fixtures = (EVAL_DIR / "fixtures.sql").read_text(encoding="utf-8")
        cls.sandbox = DuckDBSandbox(
            ddl_sql=ddl,
            fixtures_sql=fixtures,
            graph_backend=cls.backend,
        )

    def test_backend_implements_protocol(self) -> None:
        self.assertIsInstance(self.backend, GraphBackend)

    def test_hybrid_resolves_semantic_paraphrase(self) -> None:
        q = "How fast did the cost of living rise in Bandung's province in 2024?"
        lex_hits = self.backend.retrieve_lexical(q)
        hyb_hits = self.backend.retrieve_hybrid(q)
        self.assertEqual(len(lex_hits), 0)
        cards = self.backend.expand_schema_cards(hyb_hits)
        self.assertIn("fact_inflation", cards.tables)
        self.assertIn("inflation_rate", cards.columns)
        self.assertIn("32", cards.geo_codes)

    def test_sandbox_readonly_guard_blocks_mutations(self) -> None:
        for bad_sql in (
            "DROP TABLE fact_inflation",
            "DELETE FROM fact_poverty WHERE 1=1",
            "INSERT INTO fact_min_wage VALUES ('2026', '31', 6000000)",
            "SELECT * FROM fact_inflation; DROP TABLE fact_inflation",
            "SELECT * FROM read_csv('secret.csv')",
        ):
            with self.assertRaises(SecurityViolationError):
                self.sandbox.validate_readonly(bad_sql)
            res = self.sandbox.execute_readonly(bad_sql)
            self.assertFalse(res.ok)

    def test_sandbox_execution_and_provo_lineage(self) -> None:
        sql = "SELECT inflation_rate FROM fact_inflation WHERE geo_code = '32' AND time_period = '2024'"
        res = self.sandbox.execute_readonly(
            sql,
            question="West Java inflation 2024",
            answer_id="test-ans-001",
            confidence=0.96,
        )
        self.assertTrue(res.ok)
        self.assertEqual(res.rows, [(2.91,)])
        self.assertIsNotNone(res.provenance_uri)
        lineage = self.backend.get_lineage(res.provenance_uri or "")
        self.assertTrue(lineage["complete"])
        self.assertEqual(lineage["confidence"], 0.96)
        self.assertTrue(any(s.endswith("DF_INFLATION") for s in lineage["sources"]))


if __name__ == "__main__":
    unittest.main()
