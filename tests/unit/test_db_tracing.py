"""Tests for database query tracing."""

import pytest

from zenith.db.tracing import QueryStats, QueryTracer


class TestQueryStats:
    """Test QueryStats dataclass."""

    def test_record_query(self):
        """Test recording a query."""
        stats = QueryStats()
        stats.record("SELECT * FROM users", 50.0, 100.0)

        assert stats.total_queries == 1
        assert stats.total_time_ms == 50.0
        assert stats.slow_queries == 0
        assert stats.queries_by_type == {"SELECT": 1}

    def test_record_slow_query(self):
        """Test recording a slow query."""
        stats = QueryStats()
        stats.record("SELECT * FROM users", 150.0, 100.0)

        assert stats.total_queries == 1
        assert stats.slow_queries == 1
        assert stats.slowest_query_ms == 150.0

    def test_record_multiple_queries(self):
        """Test recording multiple queries."""
        stats = QueryStats()
        stats.record("SELECT * FROM users", 50.0, 100.0)
        stats.record("INSERT INTO users VALUES (1)", 30.0, 100.0)
        stats.record("UPDATE users SET name = 'test'", 200.0, 100.0)

        assert stats.total_queries == 3
        assert stats.total_time_ms == 280.0
        assert stats.slow_queries == 1
        assert stats.slowest_query_ms == 200.0
        assert stats.queries_by_type == {"SELECT": 1, "INSERT": 1, "UPDATE": 1}

    def test_reset(self):
        """Test resetting statistics."""
        stats = QueryStats()
        stats.record("SELECT * FROM users", 50.0, 100.0)
        stats.reset()

        assert stats.total_queries == 0
        assert stats.total_time_ms == 0.0
        assert stats.slow_queries == 0
        assert stats.queries_by_type == {}

    def test_to_dict(self):
        """Test converting to dictionary."""
        stats = QueryStats()
        stats.record("SELECT * FROM users", 50.0, 100.0)
        stats.record("SELECT * FROM posts", 150.0, 100.0)

        result = stats.to_dict()

        assert result["total_queries"] == 2
        assert result["total_time_ms"] == 200.0
        assert result["avg_time_ms"] == 100.0
        assert result["slow_queries"] == 1
        assert result["slowest_query_ms"] == 150.0
        assert result["queries_by_type"] == {"SELECT": 2}


class TestQueryTracer:
    """Test QueryTracer class."""

    def test_init_defaults(self):
        """Test default initialization."""
        tracer = QueryTracer()

        assert tracer.slow_threshold_ms == 100.0
        assert tracer.log_all_queries is False
        assert tracer.collect_stats is True
        assert tracer.stats is not None

    def test_init_custom(self):
        """Test custom initialization."""
        tracer = QueryTracer(
            slow_threshold_ms=50.0,
            log_all_queries=True,
            collect_stats=False,
        )

        assert tracer.slow_threshold_ms == 50.0
        assert tracer.log_all_queries is True
        assert tracer.stats is None

    def test_format_sql(self):
        """Test SQL formatting."""
        tracer = QueryTracer()

        # Test whitespace normalization
        sql = "SELECT   *\n  FROM    users"
        assert tracer._format_sql(sql) == "SELECT * FROM users"

        # Test truncation
        long_sql = "SELECT " + "a, " * 100 + "b FROM users"
        formatted = tracer._format_sql(long_sql, max_length=50)
        assert len(formatted) <= 53  # 50 + "..."
        assert formatted.endswith("...")

    def test_get_stats(self):
        """Test getting statistics."""
        tracer = QueryTracer()
        assert tracer.get_stats() == {
            "total_queries": 0,
            "total_time_ms": 0,
            "avg_time_ms": 0,
            "slow_queries": 0,
            "slowest_query_ms": 0,
            "queries_by_type": {},
        }

    def test_get_stats_disabled(self):
        """Test getting stats when disabled."""
        tracer = QueryTracer(collect_stats=False)
        assert tracer.get_stats() is None

    def test_reset_stats(self):
        """Test resetting statistics."""
        tracer = QueryTracer()
        tracer.stats.record("SELECT 1", 50.0, 100.0)
        tracer.reset_stats()

        assert tracer.stats.total_queries == 0


class TestTracingIntegration:
    """Integration tests with actual database."""

    @pytest.fixture
    def db_url(self):
        """Get test database URL."""
        return "sqlite+aiosqlite:///:memory:"

    @pytest.mark.asyncio
    async def test_enable_tracing_on_database(self, db_url):
        """Test enabling tracing on Database class."""
        from zenith.db import Database

        db = Database(db_url)
        tracer = db.enable_tracing(slow_threshold_ms=1000)

        # Execute a query
        async with db.session() as session:
            from sqlalchemy import text

            await session.execute(text("SELECT 1"))

        # Check stats were collected
        stats = tracer.get_stats()
        assert stats["total_queries"] >= 1
        assert "SELECT" in stats["queries_by_type"]

        await db.close()

    @pytest.mark.asyncio
    async def test_slow_query_detection(self, db_url):
        """Test slow query detection."""
        from zenith.db import Database

        db = Database(db_url)
        # Set very low threshold to catch all queries as "slow"
        tracer = db.enable_tracing(slow_threshold_ms=0.001)

        async with db.session() as session:
            from sqlalchemy import text

            await session.execute(text("SELECT 1"))

        stats = tracer.get_stats()
        # Query should be detected as slow with 0.001ms threshold
        assert stats["slow_queries"] >= 1

        await db.close()
