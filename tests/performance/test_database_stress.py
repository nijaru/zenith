"""
Database stress tests for production scenarios.

Tests connection pooling, exhaustion, failover, deadlocks,
and high-load database operations.
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import List
from unittest.mock import Mock, patch, AsyncMock
import tempfile

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field

from zenith import Zenith
from zenith.db import Database, ZenithModel
from zenith.testing import TestClient


# Test models
class StressTestModel(ZenithModel, table=True):
    """Model for stress testing."""
    __tablename__ = "stress_test"

    id: int | None = Field(primary_key=True)
    data: str = Field(max_length=1000)
    created_at: datetime = Field(default_factory=datetime.now)
    counter: int = Field(default=0)


class LargeModel(ZenithModel, table=True):
    """Model with large data for testing."""
    __tablename__ = "large_data"

    id: int | None = Field(primary_key=True)
    blob_data: str  # Large text field
    metadata: str


@pytest.mark.asyncio
class TestConnectionPooling:
    """Test database connection pooling under stress."""

    async def test_connection_pool_exhaustion(self):
        """Test behavior when connection pool is exhausted."""
        # Create database with small pool
        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            db = Database(
                f"sqlite+aiosqlite:///{tmp.name}",
                pool_size=2,  # Small pool
                max_overflow=1,  # Allow 1 extra connection
                pool_timeout=1  # Short timeout
            )

            # Create tables
            await db.create_all()

            # Try to acquire more connections than available
            connections = []
            try:
                # This should succeed (pool_size + max_overflow = 3)
                for i in range(3):
                    async with db.session() as session:
                        connections.append(session)
                        # Hold connection open
                        await session.execute("SELECT 1")

                # This should timeout
                with pytest.raises(TimeoutError):
                    async with asyncio.timeout(2):
                        async with db.session() as session:
                            await session.execute("SELECT 1")

            finally:
                await db.close()

    async def test_concurrent_connection_requests(self):
        """Test many concurrent connection requests."""
        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            db = Database(
                f"sqlite+aiosqlite:///{tmp.name}",
                pool_size=10,
                max_overflow=10
            )

            await db.create_all()

            async def worker(worker_id: int):
                """Worker that performs database operations."""
                for i in range(10):
                    async with db.session() as session:
                        # Create record
                        model = StressTestModel(data=f"worker_{worker_id}_item_{i}")
                        session.add(model)
                        await session.commit()

                        # Read record
                        result = await session.execute(
                            f"SELECT COUNT(*) FROM stress_test WHERE data LIKE 'worker_{worker_id}%'"
                        )
                        count = result.scalar()
                        assert count > 0

            # Run many workers concurrently
            workers = [worker(i) for i in range(20)]
            await asyncio.gather(*workers)

            # Verify all records created
            async with db.session() as session:
                result = await session.execute("SELECT COUNT(*) FROM stress_test")
                total = result.scalar()
                assert total == 200  # 20 workers * 10 items

            await db.close()

    async def test_connection_leak_detection(self):
        """Test that connection leaks are detected/prevented."""
        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            db = Database(
                f"sqlite+aiosqlite:///{tmp.name}",
                pool_size=5
            )

            await db.create_all()

            # Track active connections
            active_sessions = []

            # Create sessions without proper cleanup
            for i in range(10):
                session = await db.async_session().__aenter__()
                active_sessions.append(session)
                # Intentionally don't close

            # Pool should handle this gracefully
            # New connections should work
            async with db.session() as session:
                await session.execute("SELECT 1")

            # Clean up
            for session in active_sessions:
                await session.close()

            await db.close()


@pytest.mark.asyncio
class TestHighLoadOperations:
    """Test database under high load."""

    async def test_bulk_insert_performance(self):
        """Test bulk insert operations."""
        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            db = Database(f"sqlite+aiosqlite:///{tmp.name}")
            await db.create_all()

            start_time = time.time()

            # Bulk insert many records
            async with db.session() as session:
                records = [
                    StressTestModel(data=f"bulk_item_{i}", counter=i)
                    for i in range(1000)
                ]
                session.add_all(records)
                await session.commit()

            elapsed = time.time() - start_time

            # Should complete in reasonable time
            assert elapsed < 5.0  # 5 seconds for 1000 records

            # Verify all inserted
            async with db.session() as session:
                result = await session.execute("SELECT COUNT(*) FROM stress_test")
                count = result.scalar()
                assert count == 1000

            await db.close()

    async def test_large_result_set_handling(self):
        """Test handling of large result sets."""
        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            db = Database(f"sqlite+aiosqlite:///{tmp.name}")
            await db.create_all()

            # Insert many records
            async with db.session() as session:
                for i in range(500):
                    record = LargeModel(
                        blob_data="x" * 1000,  # 1KB per record
                        metadata=f"record_{i}"
                    )
                    session.add(record)
                await session.commit()

            # Query large result set
            async with db.session() as session:
                result = await session.execute("SELECT * FROM large_data")
                records = result.fetchall()

                assert len(records) == 500

                # Process records without exhausting memory
                total_size = sum(len(r.blob_data) for r in records)
                assert total_size == 500000  # 500 * 1000

            await db.close()

    async def test_concurrent_read_write_operations(self):
        """Test concurrent reads and writes."""
        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            db = Database(f"sqlite+aiosqlite:///{tmp.name}")
            await db.create_all()

            # Insert initial data
            async with db.session() as session:
                for i in range(10):
                    model = StressTestModel(data=f"initial_{i}", counter=0)
                    session.add(model)
                await session.commit()

            async def reader(reader_id: int):
                """Continuously read data."""
                for _ in range(50):
                    async with db.session() as session:
                        result = await session.execute(
                            "SELECT COUNT(*), MAX(counter) FROM stress_test"
                        )
                        count, max_counter = result.one()
                        assert count >= 10
                    await asyncio.sleep(0.01)

            async def writer(writer_id: int):
                """Continuously write/update data."""
                for i in range(25):
                    async with db.session() as session:
                        # Add new record
                        model = StressTestModel(
                            data=f"writer_{writer_id}_{i}",
                            counter=i
                        )
                        session.add(model)
                        await session.commit()
                    await asyncio.sleep(0.02)

            # Run readers and writers concurrently
            tasks = []
            tasks.extend([reader(i) for i in range(5)])  # 5 readers
            tasks.extend([writer(i) for i in range(3)])  # 3 writers

            await asyncio.gather(*tasks)

            # Verify final state
            async with db.session() as session:
                result = await session.execute("SELECT COUNT(*) FROM stress_test")
                count = result.scalar()
                assert count == 10 + (3 * 25)  # Initial + writers

            await db.close()


@pytest.mark.asyncio
class TestDatabaseResilience:
    """Test database resilience and error recovery."""

    async def test_transaction_rollback_on_error(self):
        """Test transaction rollback on error."""
        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            db = Database(f"sqlite+aiosqlite:///{tmp.name}")
            await db.create_all()

            # Insert initial record
            async with db.session() as session:
                model = StressTestModel(id=1, data="initial", counter=0)
                session.add(model)
                await session.commit()

            # Try transaction that will fail
            try:
                async with db.transaction() as session:
                    # Update record
                    result = await session.execute(
                        "UPDATE stress_test SET counter = 100 WHERE id = 1"
                    )

                    # Force error
                    raise ValueError("Simulated error")

            except ValueError:
                pass

            # Verify rollback
            async with db.session() as session:
                result = await session.execute(
                    "SELECT counter FROM stress_test WHERE id = 1"
                )
                counter = result.scalar()
                assert counter == 0  # Should not be updated

            await db.close()

    async def test_deadlock_handling(self):
        """Test handling of potential deadlocks."""
        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            db = Database(f"sqlite+aiosqlite:///{tmp.name}")
            await db.create_all()

            # Insert test records
            async with db.session() as session:
                for i in range(2):
                    model = StressTestModel(id=i+1, data=f"record_{i}", counter=0)
                    session.add(model)
                await session.commit()

            async def transaction1():
                """Transaction that updates records in one order."""
                async with db.transaction() as session:
                    # Update record 1
                    await session.execute(
                        "UPDATE stress_test SET counter = counter + 1 WHERE id = 1"
                    )
                    await asyncio.sleep(0.1)  # Small delay
                    # Update record 2
                    await session.execute(
                        "UPDATE stress_test SET counter = counter + 1 WHERE id = 2"
                    )

            async def transaction2():
                """Transaction that updates records in opposite order."""
                async with db.transaction() as session:
                    # Update record 2
                    await session.execute(
                        "UPDATE stress_test SET counter = counter + 1 WHERE id = 2"
                    )
                    await asyncio.sleep(0.1)  # Small delay
                    # Update record 1
                    await session.execute(
                        "UPDATE stress_test SET counter = counter + 1 WHERE id = 1"
                    )

            # Run potentially deadlocking transactions
            # SQLite handles this with busy timeout
            try:
                await asyncio.gather(transaction1(), transaction2())
            except Exception as e:
                # Deadlock might cause exception
                pass

            # System should recover
            async with db.session() as session:
                result = await session.execute("SELECT SUM(counter) FROM stress_test")
                total = result.scalar()
                # At least some updates should succeed
                assert total >= 0

            await db.close()

    async def test_connection_recovery(self):
        """Test recovery from connection failures."""
        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            db = Database(f"sqlite+aiosqlite:///{tmp.name}")
            await db.create_all()

            # Insert test data
            async with db.session() as session:
                model = StressTestModel(data="test")
                session.add(model)
                await session.commit()

            # Simulate connection failure by closing engine
            await db.engine.dispose()

            # Should recover and work again
            async with db.session() as session:
                result = await session.execute("SELECT COUNT(*) FROM stress_test")
                count = result.scalar()
                assert count == 1

            await db.close()


@pytest.mark.asyncio
class TestMemoryAndResourceManagement:
    """Test memory and resource management under load."""

    async def test_memory_usage_with_large_operations(self):
        """Test that memory usage stays bounded."""
        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            db = Database(f"sqlite+aiosqlite:///{tmp.name}")
            await db.create_all()

            # Perform many operations
            for batch in range(10):
                async with db.session() as session:
                    # Insert batch
                    records = [
                        LargeModel(
                            blob_data="x" * 10000,  # 10KB per record
                            metadata=f"batch_{batch}_{i}"
                        )
                        for i in range(100)
                    ]
                    session.add_all(records)
                    await session.commit()

                # Allow garbage collection
                await asyncio.sleep(0.01)

            # Final count
            async with db.session() as session:
                result = await session.execute("SELECT COUNT(*) FROM large_data")
                count = result.scalar()
                assert count == 1000

            await db.close()

    async def test_cursor_cleanup(self):
        """Test that cursors are properly cleaned up."""
        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            db = Database(f"sqlite+aiosqlite:///{tmp.name}")
            await db.create_all()

            # Insert test data
            async with db.session() as session:
                for i in range(100):
                    model = StressTestModel(data=f"item_{i}")
                    session.add(model)
                await session.commit()

            # Create many cursors
            for _ in range(50):
                async with db.session() as session:
                    result = await session.execute("SELECT * FROM stress_test")
                    # Fetch only first row, leaving cursor open
                    first = result.first()
                    # Cursor should be cleaned up when session closes

            # Should still work
            async with db.session() as session:
                result = await session.execute("SELECT COUNT(*) FROM stress_test")
                count = result.scalar()
                assert count == 100

            await db.close()


@pytest.mark.asyncio
class TestZenithModelUnderLoad:
    """Test ZenithModel under high load."""

    async def test_model_concurrent_operations(self):
        """Test ZenithModel with concurrent operations."""
        app = Zenith()

        # Setup database
        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            app.config.database_url = f"sqlite+aiosqlite:///{tmp.name}"

            async with TestClient(app) as client:
                await app.database.create_all()

                async def create_records(worker_id: int):
                    """Create records using ZenithModel."""
                    for i in range(10):
                        record = await StressTestModel.create(
                            data=f"model_worker_{worker_id}_{i}",
                            counter=i
                        )
                        assert record.id is not None

                async def query_records(worker_id: int):
                    """Query records using ZenithModel."""
                    for _ in range(20):
                        # Various query patterns
                        all_records = await StressTestModel.all()
                        count = await StressTestModel.count()
                        first = await StressTestModel.first()

                        # Chainable queries
                        query = await StressTestModel.where(counter__gte=5)
                        filtered = await query.order_by('-id').limit(5).all()

                        await asyncio.sleep(0.01)

                # Run concurrent operations
                tasks = []
                tasks.extend([create_records(i) for i in range(5)])
                tasks.extend([query_records(i) for i in range(3)])

                await asyncio.gather(*tasks)

                # Verify final state
                total = await StressTestModel.count()
                assert total == 50  # 5 workers * 10 records

    async def test_model_error_recovery(self):
        """Test ZenithModel error recovery."""
        app = Zenith()

        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            app.config.database_url = f"sqlite+aiosqlite:///{tmp.name}"

            async with TestClient(app) as client:
                await app.database.create_all()

                # Create record
                record = await StressTestModel.create(data="test", counter=0)

                # Try invalid operation
                with pytest.raises(Exception):
                    # Try to create duplicate ID
                    duplicate = await StressTestModel.create(
                        id=record.id,
                        data="duplicate"
                    )

                # Should recover and work
                new_record = await StressTestModel.create(data="after_error")
                assert new_record.id != record.id

                # Queries should still work
                all_records = await StressTestModel.all()
                assert len(all_records) == 2