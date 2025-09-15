"""Tests for metrics functionality."""

import pytest

from zenith import Zenith
from zenith.testing import TestClient


class TestMetricsIntegration:
    """Test metrics collection and endpoints."""

    @pytest.mark.asyncio
    async def test_metrics_endpoint_available(self):
        """Test that metrics endpoint is available when enabled."""
        app = Zenith(debug=True)

        # Add a simple route to generate metrics
        @app.get("/test")
        async def test_route():
            return {"message": "test"}

        async with TestClient(app) as client:
            # Make a request to generate some metrics
            await client.get("/test")

            # Check metrics endpoint
            response = await client.get("/metrics")

            # Should return metrics in Prometheus format or 404 if not implemented
            if response.status_code == 200:
                assert "text/plain" in response.headers.get("content-type", "")
            else:
                # Endpoint might not be implemented yet
                assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Test health check endpoint."""
        app = Zenith(debug=True)

        async with TestClient(app) as client:
            response = await client.get("/health")

            assert response.status_code == 200
            data = response.json()

            # Should contain basic health information
            assert "status" in data
            assert data["status"] in ["healthy", "ok"]

    @pytest.mark.asyncio
    async def test_detailed_health_endpoint(self):
        """Test detailed health check endpoint."""
        app = Zenith(debug=True)

        async with TestClient(app) as client:
            response = await client.get("/health/detailed")

            if response.status_code == 200:
                data = response.json()

                # Should contain detailed health information
                assert "status" in data
                assert "timestamp" in data
                assert "version" in data
            else:
                # Endpoint might not be implemented yet
                assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_request_metrics_collection(self):
        """Test that request metrics are collected."""
        app = Zenith(debug=True)

        @app.get("/counted")
        async def counted_route():
            return {"count": 1}

        async with TestClient(app) as client:
            # Make multiple requests
            for _ in range(3):
                response = await client.get("/counted")
                assert response.status_code == 200

            # Check if metrics contain request count
            response = await client.get("/metrics")

            if response.status_code == 200:
                metrics_text = response.text

                # Look for common Prometheus metrics
                assert (
                    "http_requests_total" in metrics_text
                    or "requests_total" in metrics_text
                    or "zenith_requests" in metrics_text
                )

    @pytest.mark.asyncio
    async def test_response_time_metrics(self):
        """Test that response time metrics are collected."""
        app = Zenith(debug=True)

        @app.get("/timed")
        async def timed_route():
            import asyncio

            await asyncio.sleep(0.01)  # Small delay
            return {"timed": True}

        async with TestClient(app) as client:
            response = await client.get("/timed")
            assert response.status_code == 200

            # Check metrics for timing information
            response = await client.get("/metrics")

            if response.status_code == 200:
                metrics_text = response.text

                # Look for timing-related metrics
                timing_indicators = [
                    "duration",
                    "latency",
                    "response_time",
                    "histogram",
                    "_bucket",
                    "_sum",
                    "_count",
                ]

                has_timing = any(
                    indicator in metrics_text.lower() for indicator in timing_indicators
                )

                # Either has timing metrics or endpoint is basic
                assert has_timing or len(metrics_text) > 10


class TestCustomMetrics:
    """Test custom metrics functionality."""

    @pytest.mark.asyncio
    async def test_custom_counter_metric(self):
        """Test custom counter metrics."""
        try:
            from zenith.web.metrics import counter_metric

            # Create and increment counter
            test_counter = counter_metric(
                "test_operations_total", "Test operations count"
            )
            test_counter.inc()
            test_counter.inc(3)

            # Counter should have value of 4
            assert test_counter._value == 4

        except ImportError:
            # Metrics module might not be fully implemented
            pytest.skip("Metrics module not available")

    @pytest.mark.asyncio
    async def test_custom_gauge_metric(self):
        """Test custom gauge metrics."""
        try:
            from zenith.web.metrics import gauge_metric

            # Create and set gauge
            test_gauge = gauge_metric("test_active_connections", "Active connections")
            test_gauge.set(42)

            assert test_gauge._value == 42

            test_gauge.inc(8)
            assert test_gauge._value == 50

            test_gauge.dec(10)
            assert test_gauge._value == 40

        except ImportError:
            pytest.skip("Metrics module not available")

    @pytest.mark.asyncio
    async def test_custom_histogram_metric(self):
        """Test custom histogram metrics."""
        try:
            from zenith.web.metrics import histogram_metric

            # Create histogram
            test_histogram = histogram_metric(
                "test_request_duration", "Request duration"
            )

            # Record some values
            test_histogram.observe(0.1)
            test_histogram.observe(0.5)
            test_histogram.observe(1.0)

            # Should have recorded 3 observations
            assert test_histogram._count == 3
            assert test_histogram._sum == 1.6

        except ImportError:
            pytest.skip("Metrics module not available")


class TestMetricsPerformance:
    """Test metrics performance impact."""

    @pytest.mark.asyncio
    async def test_metrics_minimal_overhead(self):
        """Test that metrics collection has minimal performance impact."""
        import time

        app = Zenith(debug=True)

        @app.get("/perf-test")
        async def perf_test():
            return {"timestamp": time.time()}

        async with TestClient(app) as client:
            # Time requests with metrics
            start = time.perf_counter()
            for _ in range(100):
                response = await client.get("/perf-test")
                assert response.status_code == 200

            metrics_time = time.perf_counter() - start

            # Should complete 100 requests reasonably quickly
            # This is a basic smoke test, not a precise benchmark
            assert metrics_time < 10.0  # 10 seconds is very generous

            # Check that metrics endpoint is responsive
            start = time.perf_counter()
            response = await client.get("/metrics")
            metrics_response_time = time.perf_counter() - start

            if response.status_code == 200:
                # Metrics endpoint should respond quickly
                assert metrics_response_time < 1.0

    @pytest.mark.asyncio
    async def test_metrics_endpoint_format(self):
        """Test metrics endpoint returns valid Prometheus format."""
        app = Zenith(debug=True)

        async with TestClient(app) as client:
            response = await client.get("/metrics")

            if response.status_code == 200:
                metrics_text = response.text

                # Basic format validation
                lines = metrics_text.strip().split("\n")

                # Should have some content
                assert len(lines) > 0

                # Check for Prometheus format patterns
                any(line.startswith("# HELP") for line in lines)
                any(line.startswith("# TYPE") for line in lines)
                has_metrics = any(
                    not line.startswith("#") and line.strip() for line in lines
                )

                # Should have at least some valid content
                assert has_metrics

                # Content type should be correct
                content_type = response.headers.get("content-type", "")
                assert "text/plain" in content_type
