"""Performance test configuration and fixtures."""

import pytest
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Set test environment
os.environ["ZENITH_ENV"] = "test"
os.environ["SECRET_KEY"] = "test-secret-key-for-performance-testing-long-enough"


def pytest_configure(config):
    """Configure pytest for performance tests."""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")


def pytest_collection_modifyitems(config, items):
    """Modify test collection for performance tests."""
    for item in items:
        # Add performance marker to all tests in performance directory
        item.add_marker(pytest.mark.performance)
        
        # Mark certain tests as slow
        if "load" in item.name.lower() or "sustained" in item.name.lower():
            item.add_marker(pytest.mark.slow)


@pytest.fixture(scope="session")
def performance_config():
    """Performance test configuration."""
    return {
        "iterations": {
            "basic": 200,
            "middleware": 100, 
            "load": 50,
            "memory": 500
        },
        "thresholds": {
            "response_time_ms": 20,
            "requests_per_second": 100,
            "memory_mb": 50,
            "middleware_overhead_pct": 50
        },
        "timeouts": {
            "test": 60,
            "load": 300
        }
    }


@pytest.fixture
def perf_monitor():
    """Performance monitoring fixture."""
    import time
    import psutil
    import os
    
    class PerformanceMonitor:
        def __init__(self):
            self.process = psutil.Process(os.getpid())
            self.start_time = None
            self.start_memory = None
            self.measurements = []
        
        def start(self):
            """Start monitoring."""
            self.start_time = time.perf_counter()
            self.start_memory = self.process.memory_info().rss / 1024 / 1024
            
        def measure(self, label: str = "measurement"):
            """Take a measurement."""
            if self.start_time is None:
                self.start()
            
            elapsed = time.perf_counter() - self.start_time
            current_memory = self.process.memory_info().rss / 1024 / 1024
            memory_delta = current_memory - self.start_memory
            
            measurement = {
                "label": label,
                "elapsed": elapsed,
                "memory_mb": current_memory,
                "memory_delta_mb": memory_delta
            }
            
            self.measurements.append(measurement)
            return measurement
        
        def stop(self):
            """Stop monitoring and return final measurement."""
            return self.measure("final")
        
        def report(self):
            """Generate performance report."""
            if not self.measurements:
                return "No measurements taken"
            
            final = self.measurements[-1]
            report = []
            report.append(f"Performance Report:")
            report.append(f"  Total time: {final['elapsed']:.3f}s")
            report.append(f"  Final memory: {final['memory_mb']:.1f}MB")
            report.append(f"  Memory delta: {final['memory_delta_mb']:+.1f}MB")
            
            if len(self.measurements) > 1:
                report.append(f"  Measurements: {len(self.measurements)}")
            
            return "\n".join(report)
    
    return PerformanceMonitor()


@pytest.fixture
def benchmark():
    """Benchmarking utility fixture."""
    import time
    from statistics import mean, median, stdev
    
    class Benchmark:
        def __init__(self):
            self.results = {}
        
        def time_function(self, func, *args, iterations=100, warmup=10, **kwargs):
            """Time a function execution."""
            # Warmup
            for _ in range(warmup):
                func(*args, **kwargs)
            
            # Benchmark
            times = []
            for _ in range(iterations):
                start = time.perf_counter()
                result = func(*args, **kwargs)
                elapsed = time.perf_counter() - start
                times.append(elapsed)
            
            stats = {
                "mean": mean(times),
                "median": median(times),
                "min": min(times),
                "max": max(times),
                "std": stdev(times) if len(times) > 1 else 0,
                "rps": 1 / mean(times),
                "iterations": iterations
            }
            
            return stats, result
        
        async def time_async_function(self, func, *args, iterations=100, warmup=10, **kwargs):
            """Time an async function execution."""
            # Warmup
            for _ in range(warmup):
                await func(*args, **kwargs)
            
            # Benchmark
            times = []
            for _ in range(iterations):
                start = time.perf_counter()
                result = await func(*args, **kwargs)
                elapsed = time.perf_counter() - start
                times.append(elapsed)
            
            stats = {
                "mean": mean(times),
                "median": median(times),
                "min": min(times),
                "max": max(times),
                "std": stdev(times) if len(times) > 1 else 0,
                "rps": 1 / mean(times),
                "iterations": iterations
            }
            
            return stats, result
        
        def compare(self, name1: str, stats1: dict, name2: str, stats2: dict):
            """Compare two benchmark results."""
            speedup = stats1["mean"] / stats2["mean"]
            rps_improvement = (stats2["rps"] - stats1["rps"]) / stats1["rps"] * 100
            
            return {
                "speedup": speedup,
                "faster": name2 if speedup > 1 else name1,
                "rps_improvement_pct": rps_improvement,
                "time_diff_ms": (stats1["mean"] - stats2["mean"]) * 1000
            }
    
    return Benchmark()


# Custom assertion helpers
def assert_performance(actual_rps: float, min_rps: float, test_name: str = "test"):
    """Assert performance meets minimum requirements."""
    assert actual_rps >= min_rps, (
        f"{test_name} performance below threshold: "
        f"{actual_rps:.1f} req/s < {min_rps} req/s required"
    )


def assert_response_time(actual_time_ms: float, max_time_ms: float, test_name: str = "test"):
    """Assert response time meets maximum requirements."""
    assert actual_time_ms <= max_time_ms, (
        f"{test_name} response time above threshold: "
        f"{actual_time_ms:.1f}ms > {max_time_ms}ms maximum"
    )


def assert_memory_usage(actual_mb: float, max_mb: float, test_name: str = "test"):
    """Assert memory usage meets maximum requirements."""
    assert actual_mb <= max_mb, (
        f"{test_name} memory usage above threshold: "
        f"{actual_mb:.1f}MB > {max_mb}MB maximum"
    )


def assert_overhead(baseline: float, actual: float, max_overhead_pct: float, test_name: str = "test"):
    """Assert overhead percentage meets maximum requirements."""
    overhead_pct = ((actual - baseline) / baseline) * 100
    assert overhead_pct <= max_overhead_pct, (
        f"{test_name} overhead above threshold: "
        f"{overhead_pct:.1f}% > {max_overhead_pct}% maximum"
    )