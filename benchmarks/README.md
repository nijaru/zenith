# Zenith Performance Benchmarks

Comprehensive performance comparison between Zenith, FastAPI, Flask, and Django.

## Benchmark Scenarios

1. **Hello World** - Simple JSON response
2. **Database Query** - Single record fetch
3. **Database Bulk** - 100 record fetch with joins
4. **Validation** - Pydantic model validation
5. **Authentication** - JWT token validation overhead
6. **Dependency Injection** - DI system performance
7. **Concurrent Requests** - High concurrency handling
8. **File Upload** - 10MB file processing

## Running Benchmarks

```bash
# Install all frameworks
pip install -e ".[benchmark]"

# Run all benchmarks
python benchmarks/run_all.py

# Run specific benchmark
python benchmarks/run_all.py --test hello_world

# Generate report
python benchmarks/generate_report.py
```

## Results Summary

### Hello World Benchmark (Requests/Second)

| Framework | Requests/sec | vs Zenith | 
|-----------|-------------|-----------|
| **Zenith**    | **2,089**       | 100%      |
| FastAPI   | 2,027       | 97%       |
| Flask     | 1,081       | 52%       |

### Performance Highlights

- **Zenith is 3% faster than FastAPI** on simple JSON responses
- **Zenith is 93% faster than Flask** (nearly 2x performance)
- Minimal memory footprint comparable to FastAPI
- Zero-overhead routing and dependency injection

## Hardware

Benchmarks run on:
- CPU: Apple Silicon / Intel
- RAM: 16GB+
- OS: macOS 14.x
- Python: 3.13.x

## Methodology

- Tool: `wrk` for HTTP benchmarking
- Duration: 30 seconds per test
- Connections: 100 concurrent
- Threads: 12
- Metrics: Requests/sec, Latency (p50, p95, p99), Memory usage