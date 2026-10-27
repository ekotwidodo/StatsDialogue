"""Secure analytical execution engine (DuckDB read-only sandbox)."""

from .sandbox import DuckDBSandbox, ExecutionResult, SecurityViolationError

__all__ = [
    "DuckDBSandbox",
    "ExecutionResult",
    "SecurityViolationError",
]
