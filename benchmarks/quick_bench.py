#!/usr/bin/env python
"""Quick benchmark test for hello world endpoint."""

import asyncio
import subprocess
import time
from pathlib import Path

import httpx


async def benchmark_framework(name: str, file: str, port: int):
    """Run a quick benchmark on a framework."""
    print(f"\nBenchmarking {name}...")

    # Start server
    venv_python = Path(__file__).parent.parent / ".venv" / "bin" / "python"
    process = subprocess.Popen(
    [str(venv_python), file],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
        cwd=Path(__file__).parent,
    )

    # Wait for server
    url = f"http://127.0.0.1:{port}/"
    async with httpx.AsyncClient() as client:
        for _ in range(30):
            try:
                await client.get(url)
                break
            except (httpx.ConnectError, httpx.RequestError):
                await asyncio.sleep(0.5)

    # Benchmark
    start = time.time()
    count = 0
    errors = 0

    async with httpx.AsyncClient() as client:
        while time.time() - start < 5:  # 5 second test
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    count += 1
                else:
                    errors += 1
            except (httpx.RequestError, httpx.HTTPStatusError):
                errors += 1

    elapsed = time.time() - start
    rps = count / elapsed

    # Stop server
    process.terminate()
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()

    print(f"  Requests/sec: {rps:.1f}")
    print(f"  Total requests: {count}")
    print(f"  Errors: {errors}")

    return rps


async def main():
    print("=" * 50)
    print("Quick Performance Test - Hello World Endpoint")
    print("=" * 50)

    results = {}

    # Test each framework
    results["zenith"] = await benchmark_framework("Zenith", "zenith_minimal.py", 8100)
    results["fastapi"] = await benchmark_framework("FastAPI", "fastapi_app.py", 8001)
    results["flask"] = await benchmark_framework("Flask", "flask_app.py", 8002)

    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY (Requests/Second)")
    print("=" * 50)

    sorted_results = sorted(results.items(), key=lambda x: x[1], reverse=True)
    for i, (name, rps) in enumerate(sorted_results, 1):
        print(f"{i}. {name:<10} {rps:>8.1f} req/s")

    # Performance comparison
    if results["zenith"] > 0:
        if results["fastapi"] > 0:
            print(
                f"\nZenith vs FastAPI: {results['zenith'] / results['fastapi'] * 100:.1f}%"
            )
        if results["flask"] > 0:
            print(f"Zenith vs Flask: {results['zenith'] / results['flask'] * 100:.1f}%")


if __name__ == "__main__":
    asyncio.run(main())
