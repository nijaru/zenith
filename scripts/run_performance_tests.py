#!/usr/bin/env python3
"""Performance test runner for Zenith framework."""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path


def run_performance_tests(
    test_pattern: str | None = None,
    include_slow: bool = False,
    verbose: bool = False,
    output_file: str | None = None,
):
    """Run performance tests with specified options."""

    # Base command
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/performance/",
        "--tb=short",
        "-v" if verbose else "-q",
    ]

    # Add test pattern if specified
    if test_pattern:
        cmd.extend(["-k", test_pattern])

    # Handle slow tests
    if not include_slow:
        cmd.extend(["-m", "not slow"])

    # Add performance markers
    cmd.extend(["--strict-markers"])

    # Set environment
    env = {
        "SECRET_KEY": "performance-test-key-long-enough-for-testing",
        "PYTHONPATH": str(Path(__file__).parent),
    }

    print("=" * 60)
    print("Zenith Framework Performance Test Suite")
    print("=" * 60)
    print(f"Command: {' '.join(cmd)}")
    print(f"Including slow tests: {include_slow}")
    print(f"Test pattern: {test_pattern or 'all'}")
    print("=" * 60)

    start_time = time.time()

    try:
        # Run tests
        if output_file:
            with open(output_file, "w") as f:
                result = subprocess.run(
                    cmd,
                    env={**os.environ, **env},
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                print(f"Output written to: {output_file}")
        else:
            result = subprocess.run(cmd, env={**os.environ, **env}, text=True)

        elapsed = time.time() - start_time

        print("=" * 60)
        print(f"Performance tests completed in {elapsed:.1f}s")
        print(f"Exit code: {result.returncode}")

        if result.returncode == 0:
            print("✅ All performance tests passed!")
        else:
            print("❌ Some performance tests failed!")

        return result.returncode

    except KeyboardInterrupt:
        print("\n⚠️  Performance tests interrupted by user")
        return 130
    except Exception as e:
        print(f"❌ Error running performance tests: {e}")
        return 1


def run_quick_benchmark():
    """Run a quick performance benchmark."""
    print("Running quick Zenith performance benchmark...")

    try:
        import asyncio

        from benchmarks.simple_bench import main as bench_main

        # Run the simple benchmark
        asyncio.run(bench_main())
        return 0

    except ImportError:
        print("Benchmark module not found, running basic performance tests instead")
        return run_performance_tests(
            test_pattern="test_simple_endpoint_performance or test_json_endpoint_performance",
            verbose=True,
        )
    except Exception as e:
        print(f"Error running benchmark: {e}")
        return 1


def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description="Run Zenith framework performance tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Run all performance tests (excluding slow)
  %(prog)s --slow                   # Run all performance tests (including slow)
  %(prog)s -k middleware            # Run only middleware performance tests
  %(prog)s -k "not memory"          # Skip memory-related tests
  %(prog)s --quick                  # Run quick benchmark
  %(prog)s --output results.txt     # Save output to file
  %(prog)s --verbose                # Verbose output
        """,
    )

    parser.add_argument("-k", "--pattern", help="Test name pattern to match")

    parser.add_argument("--slow", action="store_true", help="Include slow/load tests")

    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    parser.add_argument("-o", "--output", help="Save output to file")

    parser.add_argument("--quick", action="store_true", help="Run quick benchmark only")

    args = parser.parse_args()

    if args.quick:
        return run_quick_benchmark()
    else:
        return run_performance_tests(
            test_pattern=args.pattern,
            include_slow=args.slow,
            verbose=args.verbose,
            output_file=args.output,
        )


if __name__ == "__main__":
    sys.exit(main())
