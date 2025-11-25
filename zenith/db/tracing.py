"""
Database query tracing and slow query logging.

Provides automatic query timing, slow query detection, and query statistics
using SQLAlchemy events.
"""

from __future__ import annotations

import time
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from sqlalchemy import event
from sqlalchemy.engine import Engine

from zenith.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection
    from sqlalchemy.engine.interfaces import DBAPICursor, ExecutionContext

logger = get_logger("zenith.db.tracing")

# Context variable for query timing
_query_start_time: ContextVar[float] = ContextVar("query_start_time")


@dataclass(slots=True)
class QueryStats:
    """Statistics for database queries."""

    total_queries: int = 0
    total_time_ms: float = 0.0
    slow_queries: int = 0
    slowest_query_ms: float = 0.0
    slowest_query_sql: str = ""
    queries_by_type: dict[str, int] = field(default_factory=dict)

    def record(self, sql: str, duration_ms: float, slow_threshold_ms: float) -> None:
        """Record a query execution."""
        self.total_queries += 1
        self.total_time_ms += duration_ms

        if duration_ms > slow_threshold_ms:
            self.slow_queries += 1

        if duration_ms > self.slowest_query_ms:
            self.slowest_query_ms = duration_ms
            self.slowest_query_sql = sql[:200]  # Truncate for memory

        # Categorize by query type
        query_type = sql.strip().split()[0].upper() if sql.strip() else "UNKNOWN"
        self.queries_by_type[query_type] = self.queries_by_type.get(query_type, 0) + 1

    def reset(self) -> None:
        """Reset statistics."""
        self.total_queries = 0
        self.total_time_ms = 0.0
        self.slow_queries = 0
        self.slowest_query_ms = 0.0
        self.slowest_query_sql = ""
        self.queries_by_type.clear()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging/API response."""
        return {
            "total_queries": self.total_queries,
            "total_time_ms": round(self.total_time_ms, 2),
            "avg_time_ms": round(self.total_time_ms / self.total_queries, 2)
            if self.total_queries > 0
            else 0,
            "slow_queries": self.slow_queries,
            "slowest_query_ms": round(self.slowest_query_ms, 2),
            "queries_by_type": self.queries_by_type,
        }


class QueryTracer:
    """
    Database query tracer with slow query logging.

    Hooks into SQLAlchemy events to time all queries and log slow ones.

    Example:
        from zenith.db.tracing import QueryTracer

        tracer = QueryTracer(slow_threshold_ms=100)
        tracer.attach(engine)

        # Queries are now traced
        # Slow queries (>100ms) are logged as warnings
    """

    def __init__(
        self,
        slow_threshold_ms: float = 100.0,
        log_all_queries: bool = False,
        collect_stats: bool = True,
    ):
        """
        Initialize the query tracer.

        Args:
            slow_threshold_ms: Threshold in ms for slow query warnings (default 100ms)
            log_all_queries: Log all queries, not just slow ones (default False)
            collect_stats: Collect query statistics (default True)
        """
        self.slow_threshold_ms = slow_threshold_ms
        self.log_all_queries = log_all_queries
        self.collect_stats = collect_stats
        self.stats = QueryStats() if collect_stats else None
        self._attached_engines: set[int] = set()

    def attach(self, engine: Engine) -> None:
        """
        Attach tracing to a SQLAlchemy engine.

        Args:
            engine: SQLAlchemy engine (sync or async underlying engine)
        """
        # Get the sync engine for async engines
        sync_engine = getattr(engine, "sync_engine", engine)
        engine_id = id(sync_engine)

        # Avoid double-attaching
        if engine_id in self._attached_engines:
            return

        event.listen(sync_engine, "before_cursor_execute", self._before_execute)
        event.listen(sync_engine, "after_cursor_execute", self._after_execute)

        self._attached_engines.add(engine_id)
        logger.info(
            "query_tracing_enabled",
            slow_threshold_ms=self.slow_threshold_ms,
            log_all=self.log_all_queries,
        )

    def detach(self, engine: Engine) -> None:
        """
        Detach tracing from a SQLAlchemy engine.

        Args:
            engine: SQLAlchemy engine
        """
        sync_engine = getattr(engine, "sync_engine", engine)
        engine_id = id(sync_engine)

        if engine_id not in self._attached_engines:
            return

        event.remove(sync_engine, "before_cursor_execute", self._before_execute)
        event.remove(sync_engine, "after_cursor_execute", self._after_execute)

        self._attached_engines.discard(engine_id)
        logger.info("query_tracing_disabled")

    def _before_execute(
        self,
        conn: Connection,
        cursor: DBAPICursor,
        statement: str,
        parameters: tuple | dict,
        context: ExecutionContext | None,
        executemany: bool,
    ) -> None:
        """Record query start time."""
        _query_start_time.set(time.perf_counter())

    def _after_execute(
        self,
        conn: Connection,
        cursor: DBAPICursor,
        statement: str,
        parameters: tuple | dict,
        context: ExecutionContext | None,
        executemany: bool,
    ) -> None:
        """Log query execution time and check for slow queries."""
        try:
            start_time = _query_start_time.get()
        except LookupError:
            return  # No start time recorded

        duration_ms = (time.perf_counter() - start_time) * 1000

        # Collect stats if enabled
        if self.stats:
            self.stats.record(statement, duration_ms, self.slow_threshold_ms)

        # Format SQL for logging (truncate and clean)
        sql_preview = self._format_sql(statement)

        # Log slow queries as warnings
        if duration_ms > self.slow_threshold_ms:
            logger.warning(
                "slow_query",
                duration_ms=round(duration_ms, 2),
                threshold_ms=self.slow_threshold_ms,
                sql=sql_preview,
                executemany=executemany,
            )
        elif self.log_all_queries:
            logger.debug(
                "query_executed",
                duration_ms=round(duration_ms, 2),
                sql=sql_preview,
                executemany=executemany,
            )

    def _format_sql(self, statement: str, max_length: int = 200) -> str:
        """Format SQL statement for logging."""
        # Remove excessive whitespace
        sql = " ".join(statement.split())
        # Truncate if too long
        if len(sql) > max_length:
            sql = sql[:max_length] + "..."
        return sql

    def get_stats(self) -> dict[str, Any] | None:
        """Get query statistics."""
        return self.stats.to_dict() if self.stats else None

    def reset_stats(self) -> None:
        """Reset query statistics."""
        if self.stats:
            self.stats.reset()


# Global tracer instance for convenience
_global_tracer: QueryTracer | None = None


def enable_query_tracing(
    engine: Engine,
    slow_threshold_ms: float = 100.0,
    log_all_queries: bool = False,
    collect_stats: bool = True,
) -> QueryTracer:
    """
    Enable query tracing on a database engine.

    Args:
        engine: SQLAlchemy engine
        slow_threshold_ms: Threshold for slow query warnings (default 100ms)
        log_all_queries: Log all queries, not just slow ones
        collect_stats: Collect query statistics

    Returns:
        QueryTracer instance

    Example:
        from zenith.db import Database
        from zenith.db.tracing import enable_query_tracing

        db = Database("postgresql+asyncpg://...")
        enable_query_tracing(db.engine, slow_threshold_ms=50)
    """
    global _global_tracer

    tracer = QueryTracer(
        slow_threshold_ms=slow_threshold_ms,
        log_all_queries=log_all_queries,
        collect_stats=collect_stats,
    )
    tracer.attach(engine)
    _global_tracer = tracer
    return tracer


def disable_query_tracing(engine: Engine) -> None:
    """
    Disable query tracing on a database engine.

    Args:
        engine: SQLAlchemy engine
    """
    global _global_tracer

    if _global_tracer:
        _global_tracer.detach(engine)
        _global_tracer = None


def get_query_stats() -> dict[str, Any] | None:
    """
    Get current query statistics from the global tracer.

    Returns:
        Query statistics dict or None if tracing not enabled
    """
    return _global_tracer.get_stats() if _global_tracer else None


def reset_query_stats() -> None:
    """Reset query statistics in the global tracer."""
    if _global_tracer:
        _global_tracer.reset_stats()


__all__ = [
    "QueryStats",
    "QueryTracer",
    "disable_query_tracing",
    "enable_query_tracing",
    "get_query_stats",
    "reset_query_stats",
]
