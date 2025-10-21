#!/usr/bin/env python
"""Run performance benchmarks for all frameworks."""

import asyncio
import json
import subprocess
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import httpx
import psutil

# Configuration
FRAMEWORKS = {
    "zenith": {"file": "zenith_minimal.py", "port": 8100},
    "fastapi": {"file": "fastapi_app.py", "port": 8001},
    "flask": {"file": "flask_app.py", "port": 8002},
}

TESTS = [
    {
        "name": "hello_world",
        "method": "GET",
        "path": "/",
        "description": "Simple JSON response",
    },
    {
        "name": "get_user",
        "method": "GET",
        "path": "/users/1",
        "description": "Single database query",
    },
    {
        "name": "list_users",
        "method": "GET",
        "path": "/users?limit=100",
        "description": "Bulk database query",
    },
    {
        "name": "create_user",
        "method": "POST",
        "path": "/users",
        "body": {"name": "Test User", "email": "test@example.com"},
        "description": "Create with validation",
    },
    {
        "name": "validate",
        "method": "POST",
        "path": "/validate",
        "body": {"name": "Test", "email": "test@example.com"},
        "description": "Pydantic validation only",
    },
]


class BenchmarkRunner:
    def __init__(self):
        self.results = defaultdict(dict)
        self.processes = {}

    async def start_server(self, framework: str, config: dict):
        """Start a framework server."""
        print(f"Starting {framework} server...")

        venv_python = Path(__file__).parent.parent / ".venv" / "bin" / "python"
        cmd = [str(venv_python), config["file"]]
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=Path(__file__).parent,
        )

        self.processes[framework] = process

        # Wait for server to be ready
        url = f"http://127.0.0.1:{config['port']}/"
        async with httpx.AsyncClient() as client:
            for _ in range(30):  # 30 second timeout
                try:
                    response = await client.get(url)
                    if response.status_code == 200:
                        print(f"  {framework} server ready")
                        return
                except (httpx.ConnectError, httpx.RequestError):
                    pass
                await asyncio.sleep(1)

        raise RuntimeError(f"Failed to start {framework} server")

    def stop_server(self, framework: str):
        """Stop a framework server."""
        if framework in self.processes:
            process = self.processes[framework]
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            del self.processes[framework]

    async def run_warmup(self, port: int, test: dict):
        """Warm up the server before benchmarking."""
        url = f"http://127.0.0.1:{port}{test['path']}"
        async with httpx.AsyncClient() as client:
            for _ in range(100):
                try:
                    if test["method"] == "GET":
                        await client.get(url)
                    else:
                        await client.post(url, json=test.get("body", {}))
                except (httpx.RequestError, httpx.HTTPStatusError):
                    pass

    async def run_benchmark(
        self, framework: str, port: int, test: dict, duration: int = 10
    ):
        """Run a single benchmark test."""
        print(f"  Running {test['name']}...")

        # Warm up
        await self.run_warmup(port, test)

        # Prepare request
        url = f"http://127.0.0.1:{port}{test['path']}"

        # Track metrics
        start_time = time.time()
        request_count = 0
        latencies = []
        errors = 0

        # Get initial memory
        process = self.processes[framework]
        proc = psutil.Process(process.pid)
        initial_memory = proc.memory_info().rss / 1024 / 1024  # MB

        # Run benchmark
        async with httpx.AsyncClient() as client:
            tasks = []

            async def make_request():
                nonlocal request_count, errors
                try:
                    start = time.perf_counter()
                    if test["method"] == "GET":
                        response = await client.get(url)
                    else:
                        response = await client.post(url, json=test.get("body", {}))

                    if response.status_code < 400:
                        request_count += 1
                        latencies.append((time.perf_counter() - start) * 1000)  # ms
                    else:
                        errors += 1
                except Exception:
                    errors += 1

            # Run for duration seconds with concurrent requests
            end_time = start_time + duration
            while time.time() < end_time:
                # Maintain 100 concurrent requests
                while len(tasks) < 100:
                    tasks.append(asyncio.create_task(make_request()))

                # Wait for some to complete
                _done, tasks = await asyncio.wait(
                    tasks, timeout=0.1, return_when=asyncio.FIRST_COMPLETED
                )
                tasks = list(tasks)

        # Wait for remaining tasks
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        # Calculate results
        elapsed = time.time() - start_time
        final_memory = proc.memory_info().rss / 1024 / 1024  # MB

        if latencies:
            latencies.sort()
            p50 = latencies[int(len(latencies) * 0.50)]
            p95 = latencies[int(len(latencies) * 0.95)]
            p99 = latencies[int(len(latencies) * 0.99)]
        else:
            p50 = p95 = p99 = 0

        return {
            "requests_per_second": request_count / elapsed,
            "total_requests": request_count,
            "errors": errors,
            "latency_p50": p50,
            "latency_p95": p95,
            "latency_p99": p99,
            "memory_initial_mb": initial_memory,
            "memory_final_mb": final_memory,
            "memory_delta_mb": final_memory - initial_memory,
        }

    async def run_all_benchmarks(self):
        """Run all benchmarks for all frameworks."""
        print("=" * 60)
        print("Running Performance Benchmarks")
        print("=" * 60)

        for framework, config in FRAMEWORKS.items():
            print(f"\nBenchmarking {framework.upper()}")
            print("-" * 40)

            # Start server
            await self.start_server(framework, config)

            # Run tests
            for test in TESTS:
                result = await self.run_benchmark(
                    framework,
                    config["port"],
                    test,
                    duration=10,  # 10 seconds per test
                )
                self.results[framework][test["name"]] = result

                # Print immediate results
                print(f"    {test['name']}:")
                print(f"      RPS: {result['requests_per_second']:.1f}")
                print(f"      Latency P50: {result['latency_p50']:.2f}ms")
                print(f"      Latency P95: {result['latency_p95']:.2f}ms")
                print(f"      Memory: {result['memory_delta_mb']:.1f}MB")

            # Stop server
            self.stop_server(framework)

        return self.results

    def print_summary(self):
        """Print benchmark summary."""
        print("\n" + "=" * 60)
        print("BENCHMARK SUMMARY")
        print("=" * 60)

        for test in TESTS:
            print(f"\n{test['description']} ({test['name']})")
            print("-" * 40)
            print(
                f"{'Framework':<12} {'RPS':>10} {'P50 (ms)':>10} {'P95 (ms)':>10} {'Memory Δ':>10}"
            )
            print("-" * 40)

            for framework in FRAMEWORKS:
                if test["name"] in self.results[framework]:
                    r = self.results[framework][test["name"]]
                    print(
                        f"{framework:<12} {r['requests_per_second']:>10.1f} "
                        f"{r['latency_p50']:>10.2f} {r['latency_p95']:>10.2f} "
                        f"{r['memory_delta_mb']:>9.1f}MB"
                    )

        # Overall winner analysis
        print("\n" + "=" * 60)
        print("PERFORMANCE RANKINGS")
        print("=" * 60)

        scores = defaultdict(int)
        for test in TESTS:
            # Rank by RPS
            rps_scores = sorted(
                [
                    (f, self.results[f][test["name"]]["requests_per_second"])
                    for f in FRAMEWORKS
                ],
                key=lambda x: x[1],
                reverse=True,
            )
            for i, (framework, _) in enumerate(rps_scores):
                scores[framework] += 3 - i  # 3 points for 1st, 2 for 2nd, 1 for 3rd

        print("\nOverall Performance Score:")
        for framework, score in sorted(
            scores.items(), key=lambda x: x[1], reverse=True
        ):
            print(f"  {framework}: {score} points")

    def save_results(self):
        """Save results to JSON file."""
        output = {
            "timestamp": datetime.now().isoformat(),
            "system": {
                "cpu_count": psutil.cpu_count(),
                "memory_gb": psutil.virtual_memory().total / (1024**3),
                "python_version": subprocess.run(
                    ["python", "--version"], capture_output=True, text=True
                ).stdout.strip(),
            },
            "results": self.results,
        }

        with Path("benchmark_results.json").open("w") as f:
            json.dump(output, f, indent=2)

        print("\nResults saved to benchmark_results.json")


async def main():
    runner = BenchmarkRunner()

    try:
        await runner.run_all_benchmarks()
        runner.print_summary()
        runner.save_results()
    finally:
        # Clean up any remaining processes
        for framework in list(runner.processes.keys()):
            runner.stop_server(framework)


if __name__ == "__main__":
    asyncio.run(main())
