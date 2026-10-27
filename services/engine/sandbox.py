"""Sandboxed DuckDB analytical execution engine (PRD §6.1–6.2, §8.2).

Enforces:
- Extension lock-down (`autoinstall_known_extensions = false`,
  `autoload_known_extensions = false`, `enable_external_access = false`)
- Strict read-only guard rejecting DDL/DML/administrative statements and
  external file-access functions before execution
- Automatic W3C PROV-O lineage emission when paired with a `GraphBackend`
"""
from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass, field

import duckdb

from services.graph.backend import GraphBackend, ProvenanceRecord

FORBIDDEN_TOKENS = re.compile(
    r"\b("
    r"drop|delete|insert|update|alter|create|truncate|replace|merge|"
    r"attach|detach|copy|export|import|pragma|install|load|call|grant|revoke|"
    r"read_csv|read_csv_auto|read_parquet|read_json|read_json_auto|glob"
    r")\b",
    re.IGNORECASE,
)

TABLE_TO_DATAFLOW = {
    "fact_inflation": "DF_INFLATION",
    "fact_poverty": "DF_POVERTY",
    "fact_min_wage": "DF_MINWAGE",
}


class SecurityViolationError(PermissionError):
    """Raised when a generated SQL query violates the read-only sandbox policy."""


@dataclass
class ExecutionResult:
    """Result of a sandboxed SQL execution."""

    ok: bool
    sql: str
    columns: list[str] = field(default_factory=list)
    rows: list[tuple] = field(default_factory=list)
    latency_ms: float = 0.0
    error: str | None = None
    provenance_uri: str | None = None


class DuckDBSandbox:
    """In-memory read-only DuckDB analytical sandbox."""

    def __init__(
        self,
        ddl_sql: str | None = None,
        fixtures_sql: str | None = None,
        graph_backend: GraphBackend | None = None,
    ) -> None:
        self._conn = duckdb.connect(":memory:")
        self._graph = graph_backend
        # Apply security lockdown after loading trusted in-memory schema/fixtures
        if ddl_sql:
            self._conn.execute(ddl_sql)
        if fixtures_sql:
            self._conn.execute(fixtures_sql)
        self._harden()

    def _harden(self) -> None:
        for stmt in (
            "SET autoinstall_known_extensions = false;",
            "SET autoload_known_extensions = false;",
            "SET enable_external_access = false;",
        ):
            try:
                self._conn.execute(stmt)
            except duckdb.Error:
                pass

    @staticmethod
    def validate_readonly(sql: str) -> str:
        """Verify that a SQL string is a single read-only SELECT/WITH query."""
        cleaned = re.sub(r"--[^\n]*", "", sql).strip()
        cleaned = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.DOTALL).strip()
        if cleaned.endswith(";"):
            cleaned = cleaned[:-1].strip()
        if not cleaned:
            raise SecurityViolationError("Empty SQL query.")
        if ";" in cleaned:
            raise SecurityViolationError("Multi-statement SQL queries are prohibited.")
        first_word = cleaned.split(None, 1)[0].upper()
        if first_word not in ("SELECT", "WITH"):
            raise SecurityViolationError(
                f"Only SELECT/WITH queries are allowed (got {first_word!r})."
            )
        match = FORBIDDEN_TOKENS.search(cleaned)
        if match:
            raise SecurityViolationError(
                f"Forbidden SQL keyword or function in sandbox: {match.group(1)!r}"
            )
        return cleaned

    def execute_readonly(
        self,
        sql: str,
        question: str = "",
        answer_id: str | None = None,
        confidence: float | None = None,
    ) -> ExecutionResult:
        """Validate and execute a read-only SQL query, recording PROV-O lineage."""
        t0 = time.perf_counter()
        try:
            safe_sql = self.validate_readonly(sql)
            cur = self._conn.execute(safe_sql)
            rows = cur.fetchall()
            cols = [desc[0] for desc in (cur.description or [])]
            elapsed = (time.perf_counter() - t0) * 1000.0
        except (SecurityViolationError, duckdb.Error) as exc:
            elapsed = (time.perf_counter() - t0) * 1000.0
            return ExecutionResult(
                ok=False,
                sql=sql,
                latency_ms=round(elapsed, 3),
                error=str(exc),
            )

        prov_uri: str | None = None
        if self._graph is not None:
            tables = set(re.findall(r"\bfact_[a-z0-9_]+\b", safe_sql.lower()))
            dataflows = sorted(
                {TABLE_TO_DATAFLOW[t] for t in tables if t in TABLE_TO_DATAFLOW}
            )
            if not dataflows:
                dataflows = ["DF_UNKNOWN"]
            aid = answer_id or f"ans-{uuid.uuid4().hex[:8]}"
            rec = ProvenanceRecord(
                answer_id=aid,
                question=question or safe_sql,
                sql_query=safe_sql,
                source_dataflows=dataflows,
                confidence=confidence,
            )
            prov_uri = self._graph.record_provenance(rec)

        return ExecutionResult(
            ok=True,
            sql=safe_sql,
            columns=cols,
            rows=rows,
            latency_ms=round(elapsed, 3),
            provenance_uri=prov_uri,
        )
