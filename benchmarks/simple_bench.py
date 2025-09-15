#!/usr/bin/env python
"""Simple benchmark using just the Zenith TestClient for comparison."""

import asyncio
import os
import time

from zenith import Zenith
from zenith.testing import TestClient

# Set up environment
os.environ["SECRET_KEY"] = "benchmark-secret-key-for-testing-long-enough"


async def benchmark_zenith():
    """Benchmark Zenith using TestClient."""
    print("Benchmarking Zenith with TestClient...")

    # Create minimal app
    app = Zenith(debug=False, middleware=[])  # Minimal middleware for speed

    @app.get("/")
    async def hello():
        return {"message": "Hello, World!"}

    @app.get("/json")
    async def json_response():
        return {
            "users": [
                {"id": i, "name": f"User {i}", "email": f"user{i}@example.com"}
                for i in range(10)
            ]
        }

    # Benchmark simple endpoint
    async with TestClient(app) as client:
        # Warmup
        for _ in range(10):
            await client.get("/")

        # Benchmark hello endpoint
        start = time.perf_counter()
        iterations = 1000

        for _ in range(iterations):
            response = await client.get("/")
            assert response.status_code == 200

        elapsed = time.perf_counter() - start
        hello_rps = iterations / elapsed

        # Benchmark JSON endpoint
        start = time.perf_counter()
        iterations = 500

        for _ in range(iterations):
            response = await client.get("/json")
            assert response.status_code == 200
            data = response.json()
            assert len(data["users"]) == 10

        elapsed = time.perf_counter() - start
        json_rps = iterations / elapsed

    print("Results:")
    print(f"  Simple endpoint: {hello_rps:.1f} req/s")
    print(f"  JSON endpoint:   {json_rps:.1f} req/s")
    print(f"  Average:         {(hello_rps + json_rps) / 2:.1f} req/s")

    return hello_rps, json_rps


async def benchmark_with_middleware():
    """Benchmark Zenith with full middleware stack."""
    print("\nBenchmarking Zenith with full middleware...")

    # Create app with middleware
    app = Zenith(debug=False)  # Full middleware stack

    @app.get("/")
    async def hello():
        return {"message": "Hello, World!"}

    # Benchmark with middleware
    async with TestClient(app) as client:
        # Warmup
        for _ in range(10):
            await client.get("/")

        start = time.perf_counter()
        iterations = 1000

        for _ in range(iterations):
            response = await client.get("/")
            assert response.status_code == 200

        elapsed = time.perf_counter() - start
        middleware_rps = iterations / elapsed

    print("Results:")
    print(f"  With middleware: {middleware_rps:.1f} req/s")

    return middleware_rps


async def main():
    print("=" * 50)
    print("Zenith Performance Benchmark")
    print("=" * 50)

    # Run benchmarks
    hello_rps, json_rps = await benchmark_zenith()
    middleware_rps = await benchmark_with_middleware()

    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"Simple endpoint (no middleware): {hello_rps:>8.1f} req/s")
    print(f"JSON endpoint (no middleware):   {json_rps:>8.1f} req/s")
    print(f"Simple endpoint (middleware):    {middleware_rps:>8.1f} req/s")

    # Middleware overhead
    overhead_pct = ((hello_rps - middleware_rps) / hello_rps) * 100
    print(f"\nMiddleware overhead: {overhead_pct:.1f}%")

    # Performance tiers
    if hello_rps > 1000:
        print("✅ Performance: Excellent (>1000 req/s)")
    elif hello_rps > 500:
        print("✅ Performance: Good (>500 req/s)")
    else:
        print("⚠️  Performance: Below expectations (<500 req/s)")

    # Write results to JSON for GitHub Actions
    import json
    import time

    results = {
        "timestamp": time.time(),
        "benchmarks": [
            {
                "name": "Simple endpoint (no middleware)",
                "unit": "req/s",
                "value": hello_rps,
            },
            {
                "name": "JSON endpoint (no middleware)",
                "unit": "req/s",
                "value": json_rps,
            },
            {
                "name": "Simple endpoint (with middleware)",
                "unit": "req/s",
                "value": middleware_rps,
            },
            {"name": "Middleware overhead", "unit": "%", "value": overhead_pct},
        ],
    }

    with open("benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\n✅ Results written to benchmark_results.json")


if __name__ == "__main__":
    asyncio.run(main())
