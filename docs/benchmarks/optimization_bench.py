#!/usr/bin/env python
"""
Benchmark script to test Zenith optimizations.

Tests performance with and without optimizations:
- uvloop vs standard asyncio
- msgspec vs orjson vs standard json
- Overall request handling performance
"""

import asyncio
import json
import time
from datetime import datetime
from decimal import Decimal
from statistics import mean, median, stdev
from uuid import uuid4

# Test with standard libraries first
print("=" * 60)
print("ZENITH OPTIMIZATION BENCHMARKS")
print("=" * 60)

# Check available optimizations
optimizations_available = {"uvloop": False, "msgspec": False, "orjson": False}

try:
    import uvloop

    optimizations_available["uvloop"] = True
    print("✅ uvloop available")
except ImportError:
    print("❌ uvloop not available (install with: pip install uvloop)")

try:
    import msgspec

    optimizations_available["msgspec"] = True
    print("✅ msgspec available")
except ImportError:
    print("❌ msgspec not available (install with: pip install msgspec)")

try:
    import orjson

    optimizations_available["orjson"] = True
    print("✅ orjson available")
except ImportError:
    print("❌ orjson not available (install with: pip install orjson)")

print("-" * 60)

# Import Zenith after checking libraries

from pydantic import BaseModel  # noqa: E402

from zenith import Zenith  # noqa: E402
from zenith.optimizations import get_optimization_status  # noqa: E402
from zenith.testing import TestClient  # noqa: E402


# Test data models
class UserData(BaseModel):
    id: int
    name: str
    email: str
    created_at: datetime
    balance: Decimal
    tags: list[str]
    metadata: dict


def create_test_data(count: int = 100) -> list[dict]:
    """Create test data for JSON serialization."""
    return [
        {
            "id": i,
            "name": f"User {i}",
            "email": f"user{i}@example.com",
            "created_at": datetime.now(),
            "balance": Decimal(f"{i * 100.50}"),
            "uuid": str(uuid4()),
            "tags": ["tag1", "tag2", "tag3"] * (i % 3 + 1),
            "metadata": {
                "key1": "value1",
                "key2": i * 2,
                "nested": {"deep": "data", "level": i},
            },
        }
        for i in range(count)
    ]


async def benchmark_json_serialization():
    """Benchmark JSON serialization with different libraries."""
    print("\n📊 JSON Serialization Benchmarks")
    print("-" * 40)

    test_data = create_test_data(1000)
    iterations = 100

    # Standard JSON
    print("\n1. Standard JSON:")
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        json.dumps(test_data, default=str)
        times.append(time.perf_counter() - start)

    std_avg = mean(times) * 1000
    print(f"   Average: {std_avg:.2f}ms")
    print(f"   Median:  {median(times) * 1000:.2f}ms")
    print(f"   StdDev:  {stdev(times) * 1000:.2f}ms")

    # orjson if available
    if optimizations_available["orjson"]:
        import orjson

        print("\n2. orjson:")

        def default(obj):
            if isinstance(obj, Decimal):
                return str(obj)
            raise TypeError

        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            orjson.dumps(test_data, default=default)
            times.append(time.perf_counter() - start)

        orjson_avg = mean(times) * 1000
        speedup = std_avg / orjson_avg
        print(f"   Average: {orjson_avg:.2f}ms")
        print(f"   Median:  {median(times) * 1000:.2f}ms")
        print(f"   StdDev:  {stdev(times) * 1000:.2f}ms")
        print(f"   Speedup: {speedup:.1f}x faster than standard")

    # msgspec if available
    if optimizations_available["msgspec"]:
        import msgspec

        print("\n3. msgspec:")

        def enc_hook(obj):
            if isinstance(obj, Decimal):
                return str(obj)
            raise TypeError

        encoder = msgspec.json.Encoder(enc_hook=enc_hook)
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            encoder.encode(test_data)
            times.append(time.perf_counter() - start)

        msgspec_avg = mean(times) * 1000
        speedup = std_avg / msgspec_avg
        print(f"   Average: {msgspec_avg:.2f}ms")
        print(f"   Median:  {median(times) * 1000:.2f}ms")
        print(f"   StdDev:  {stdev(times) * 1000:.2f}ms")
        print(f"   Speedup: {speedup:.1f}x faster than standard")


async def benchmark_zenith_app(enable_optimizations: bool):
    """Benchmark Zenith application with/without optimizations."""
    # Create app with test secret key
    from zenith import Config

    config = Config(
        secret_key="test-secret-key-for-benchmarking-123456789012345678901234567890",
        debug=False,
    )

    app = Zenith(
        config=config,
        middleware=[],  # Minimal middleware for pure speed test
        enable_optimizations=enable_optimizations,
    )

    # Add test endpoints
    @app.get("/simple")
    async def simple():
        return {"message": "Hello, World!"}

    @app.get("/json")
    async def json_endpoint():
        return create_test_data(10)

    @app.post("/echo")
    async def echo(data: UserData):
        return data.model_dump()

    # Benchmark simple endpoint
    async with TestClient(app) as client:
        # Warmup
        for _ in range(10):
            await client.get("/simple")

        # Benchmark
        iterations = 500
        times = []

        for _ in range(iterations):
            start = time.perf_counter()
            response = await client.get("/simple")
            elapsed = time.perf_counter() - start
            assert response.status_code == 200
            times.append(elapsed)

        avg_time = mean(times) * 1000
        rps = 1000 / avg_time

        return {
            "avg_ms": avg_time,
            "median_ms": median(times) * 1000,
            "stddev_ms": stdev(times) * 1000,
            "rps": rps,
        }


async def main():
    """Run all benchmarks."""

    # JSON serialization benchmarks
    await benchmark_json_serialization()

    # Zenith app benchmarks
    print("\n📊 Zenith Application Benchmarks")
    print("-" * 40)

    # Without optimizations
    print("\n1. Without optimizations:")
    results_no_opt = await benchmark_zenith_app(enable_optimizations=False)
    print(f"   Average:  {results_no_opt['avg_ms']:.2f}ms")
    print(f"   Median:   {results_no_opt['median_ms']:.2f}ms")
    print(f"   StdDev:   {results_no_opt['stddev_ms']:.2f}ms")
    print(f"   Req/sec:  {results_no_opt['rps']:.1f}")

    # With optimizations
    print("\n2. With optimizations:")
    results_with_opt = await benchmark_zenith_app(enable_optimizations=True)
    print(f"   Average:  {results_with_opt['avg_ms']:.2f}ms")
    print(f"   Median:   {results_with_opt['median_ms']:.2f}ms")
    print(f"   StdDev:   {results_with_opt['stddev_ms']:.2f}ms")
    print(f"   Req/sec:  {results_with_opt['rps']:.1f}")

    # Calculate improvement
    if results_no_opt["avg_ms"] > 0:
        improvement = (
            (results_no_opt["avg_ms"] - results_with_opt["avg_ms"])
            / results_no_opt["avg_ms"]
        ) * 100
        speedup = results_with_opt["rps"] / results_no_opt["rps"]
        print(f"\n   ⚡ Performance improvement: {improvement:.1f}%")
        print(f"   ⚡ Speedup: {speedup:.2f}x")

    # Show optimization status
    print("\n📊 Optimization Status")
    print("-" * 40)
    status = get_optimization_status()
    for key, value in status.items():
        print(f"   {key}: {value}")

    print("\n" + "=" * 60)
    print("Benchmark complete!")
    print("=" * 60)


if __name__ == "__main__":
    # Try to use uvloop if available
    if optimizations_available["uvloop"]:
        import uvloop

        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        print("Running with uvloop event loop")
    else:
        print("Running with standard asyncio event loop")

    asyncio.run(main())
