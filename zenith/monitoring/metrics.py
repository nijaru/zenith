"""
Application metrics collection and monitoring utilities.

Provides simple metrics collection for monitoring application performance,
request rates, error rates, and custom business metrics.
"""

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock
from typing import Any


class MetricType(Enum):
    """Types of metrics that can be collected."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass(slots=True)
class MetricPoint:
    """A single metric data point."""

    name: str
    value: float
    timestamp: float
    labels: dict[str, str] = field(default_factory=dict)
    metric_type: MetricType = MetricType.GAUGE


class MetricsCollector:
    """
    Lightweight metrics collector for application monitoring.

    Collects counters, gauges, histograms, and timers with labels.
    Provides Prometheus-style metrics export.
    """

    def __init__(self, max_points_per_metric: int = 1000):
        """
        Initialize metrics collector.

        Args:
            max_points_per_metric: Maximum data points to keep per metric
        """
        self.max_points = max_points_per_metric
        self._metrics: dict[str, deque] = defaultdict(
            lambda: deque(maxlen=self.max_points)
        )
        self._counters: dict[str, float] = defaultdict(float)
        self._gauges: dict[str, float] = defaultdict(float)
        self._histograms: dict[str, list] = defaultdict(list)
        self._lock = Lock()

    def counter(
        self, name: str, value: float = 1.0, labels: dict[str, str] | None = None
    ) -> None:
        """
        Increment a counter metric.

        Args:
            name: Metric name
            value: Value to add (default 1.0)
            labels: Optional labels for the metric
        """
        labels = labels or {}
        metric_key = self._build_metric_key(name, labels)

        with self._lock:
            self._counters[metric_key] += value
            self._add_point(
                MetricPoint(
                    name=name,
                    value=self._counters[metric_key],
                    timestamp=time.time(),
                    labels=labels,
                    metric_type=MetricType.COUNTER,
                )
            )

    def gauge(
        self, name: str, value: float, labels: dict[str, str] | None = None
    ) -> None:
        """
        Set a gauge metric value.

        Args:
            name: Metric name
            value: Current value
            labels: Optional labels for the metric
        """
        labels = labels or {}
        metric_key = self._build_metric_key(name, labels)

        with self._lock:
            self._gauges[metric_key] = value
            self._add_point(
                MetricPoint(
                    name=name,
                    value=value,
                    timestamp=time.time(),
                    labels=labels,
                    metric_type=MetricType.GAUGE,
                )
            )

    def histogram(
        self, name: str, value: float, labels: dict[str, str] | None = None
    ) -> None:
        """
        Record a histogram observation.

        Args:
            name: Metric name
            value: Observed value
            labels: Optional labels for the metric
        """
        labels = labels or {}
        metric_key = self._build_metric_key(name, labels)

        with self._lock:
            self._histograms[metric_key].append(value)
            # Keep only recent values to prevent memory growth
            if len(self._histograms[metric_key]) > self.max_points:
                self._histograms[metric_key] = self._histograms[metric_key][
                    -self.max_points :
                ]

            self._add_point(
                MetricPoint(
                    name=name,
                    value=value,
                    timestamp=time.time(),
                    labels=labels,
                    metric_type=MetricType.HISTOGRAM,
                )
            )

    def timer(self, name: str, labels: dict[str, str] | None = None):
        """
        Context manager for timing operations.

        Args:
            name: Metric name
            labels: Optional labels for the metric

        Usage:
            with metrics.timer("operation_duration"):
                # ... operation to time
        """
        return TimerContext(self, name, labels or {})

    def timing(
        self, name: str, duration_seconds: float, labels: dict[str, str] | None = None
    ) -> None:
        """
        Record a timing metric.

        Args:
            name: Metric name
            duration_seconds: Duration in seconds
            labels: Optional labels for the metric
        """
        labels = labels or {}
        self.histogram(f"{name}_seconds", duration_seconds, labels)

    def _build_metric_key(self, name: str, labels: dict[str, str]) -> str:
        """Build a unique key for a metric with labels."""
        if not labels:
            return name

        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def _add_point(self, point: MetricPoint) -> None:
        """Add a metric point to the collection."""
        key = self._build_metric_key(point.name, point.labels)
        self._metrics[key].append(point)

    def get_current_values(self) -> dict[str, Any]:
        """Get current values for all metrics."""
        with self._lock:
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {k: list(v) for k, v in self._histograms.items()},
            }

    def get_histogram_stats(
        self, name: str, labels: dict[str, str] | None = None
    ) -> dict[str, float]:
        """Get statistics for a histogram metric."""
        labels = labels or {}
        metric_key = self._build_metric_key(name, labels)

        with self._lock:
            values = self._histograms.get(metric_key, [])

            if not values:
                return {"count": 0}

            sorted_values = sorted(values)
            count = len(sorted_values)

            return {
                "count": count,
                "sum": sum(sorted_values),
                "min": sorted_values[0],
                "max": sorted_values[-1],
                "mean": sum(sorted_values) / count,
                "p50": self._percentile(sorted_values, 0.5),
                "p90": self._percentile(sorted_values, 0.9),
                "p95": self._percentile(sorted_values, 0.95),
                "p99": self._percentile(sorted_values, 0.99),
            }

    def _percentile(self, sorted_values: list[float], p: float) -> float:
        """Calculate percentile from sorted values."""
        if not sorted_values:
            return 0.0

        index = int((len(sorted_values) - 1) * p)
        return sorted_values[index]

    def export_prometheus(self) -> str:
        """
        Export metrics in Prometheus format.

        Returns:
            String containing Prometheus-formatted metrics
        """
        lines = []
        current_values = self.get_current_values()

        # Export counters
        for metric_key, value in current_values["counters"].items():
            name, labels = self._parse_metric_key(metric_key)
            labels_str = self._format_prometheus_labels(labels)
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name}{labels_str} {value}")

        # Export gauges
        for metric_key, value in current_values["gauges"].items():
            name, labels = self._parse_metric_key(metric_key)
            labels_str = self._format_prometheus_labels(labels)
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name}{labels_str} {value}")

        # Export histograms
        for metric_key, values in current_values["histograms"].items():
            if values:
                name, labels = self._parse_metric_key(metric_key)
                stats = self.get_histogram_stats(name, labels)
                labels_str = self._format_prometheus_labels(labels)

                lines.append(f"# TYPE {name} histogram")
                lines.append(f"{name}_count{labels_str} {stats['count']}")
                lines.append(f"{name}_sum{labels_str} {stats['sum']}")

                # Add quantiles
                for q in [0.5, 0.9, 0.95, 0.99]:
                    quantile_labels = {**labels, "quantile": str(q)}
                    quantile_labels_str = self._format_prometheus_labels(
                        quantile_labels
                    )
                    percentile_key = f"p{int(q * 100)}"
                    lines.append(f"{name}{quantile_labels_str} {stats[percentile_key]}")

        return "\n".join(lines) + "\n"

    def _parse_metric_key(self, metric_key: str) -> tuple[str, dict[str, str]]:
        """Parse metric key back into name and labels."""
        if "{" not in metric_key:
            return metric_key, {}

        name, labels_str = metric_key.split("{", 1)
        labels_str = labels_str.rstrip("}")

        labels = {}
        if labels_str:
            for pair in labels_str.split(","):
                key, value = pair.split("=", 1)
                labels[key] = value

        return name, labels

    def _format_prometheus_labels(self, labels: dict[str, str]) -> str:
        """Format labels for Prometheus output."""
        if not labels:
            return ""

        label_pairs = [f'{k}="{v}"' for k, v in sorted(labels.items())]
        return "{" + ",".join(label_pairs) + "}"

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._metrics.clear()
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()


class TimerContext:
    """Context manager for timing operations."""

    def __init__(self, collector: MetricsCollector, name: str, labels: dict[str, str]):
        self.collector = collector
        self.name = name
        self.labels = labels
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration = time.time() - self.start_time
            self.collector.timing(self.name, duration, self.labels)


# Global metrics collector instance
metrics = MetricsCollector()


# Built-in HTTP metrics middleware integration
def record_request_metrics(
    method: str,
    path: str,
    status_code: int,
    duration_seconds: float,
    collector: MetricsCollector = None,
) -> None:
    """
    Record HTTP request metrics.

    Args:
        method: HTTP method
        path: Request path
        status_code: Response status code
        duration_seconds: Request duration
        collector: Metrics collector instance (defaults to global)
    """
    collector = collector or metrics

    labels = {
        "method": method,
        "path": path,
        "status": str(status_code),
    }

    # Request count
    collector.counter("http_requests_total", labels=labels)

    # Request duration
    collector.timing("http_request_duration", duration_seconds, labels)

    # Error rate
    if status_code >= 400:
        error_labels = {
            **labels,
            "error_type": "client" if status_code < 500 else "server",
        }
        collector.counter("http_errors_total", labels=error_labels)


# Route handler for metrics endpoint with time-based caching
_metrics_cache = {"data": "", "expires": 0}


async def metrics_endpoint() -> str:
    """Metrics endpoint handler returning Prometheus format with 5s caching."""
    current_time = time.time()

    # Use cached data if still valid (5 second cache)
    if current_time < _metrics_cache["expires"]:
        return _metrics_cache["data"]

    # Generate fresh metrics and cache
    _metrics_cache["data"] = metrics.export_prometheus()
    _metrics_cache["expires"] = current_time + 5.0  # 5 second TTL

    return _metrics_cache["data"]


def add_metrics_route(app, metrics_path: str = "/metrics") -> None:
    """
    Add metrics endpoint to a Zenith application.

    Args:
        app: Zenith application instance
        metrics_path: Path for the metrics endpoint
    """

    @app.get(metrics_path)
    async def app_metrics():
        return await metrics_endpoint()


# Custom metric creation functions for easy usage
class CustomCounter:
    """Simple counter metric for user-defined counters."""

    def __init__(self, name: str, description: str, collector: MetricsCollector = None):
        self.name = name
        self.description = description
        self.collector = collector or metrics
        self._value = 0

    def inc(self, amount: float = 1.0) -> None:
        """Increment the counter."""
        self._value += amount
        self.collector.counter(self.name, value=amount)


class CustomGauge:
    """Simple gauge metric for user-defined gauges."""

    def __init__(self, name: str, description: str, collector: MetricsCollector = None):
        self.name = name
        self.description = description
        self.collector = collector or metrics
        self._value = 0

    def set(self, value: float) -> None:
        """Set the gauge value."""
        self._value = value
        self.collector.gauge(self.name, value)

    def inc(self, amount: float = 1.0) -> None:
        """Increment the gauge."""
        self._value += amount
        self.collector.gauge(self.name, self._value)

    def dec(self, amount: float = 1.0) -> None:
        """Decrement the gauge."""
        self._value -= amount
        self.collector.gauge(self.name, self._value)


class CustomHistogram:
    """Simple histogram metric for user-defined histograms."""

    def __init__(self, name: str, description: str, collector: MetricsCollector = None):
        self.name = name
        self.description = description
        self.collector = collector or metrics
        self._observations = []
        self._count = 0
        self._sum = 0.0

    def observe(self, value: float) -> None:
        """Record an observation."""
        self._observations.append(value)
        self._count += 1
        self._sum += value
        self.collector.timing(self.name, value)


def counter_metric(name: str, description: str = "") -> CustomCounter:
    """Create a new counter metric.

    Args:
        name: Metric name
        description: Metric description

    Returns:
        CustomCounter instance
    """
    return CustomCounter(name, description)


def gauge_metric(name: str, description: str = "") -> CustomGauge:
    """Create a new gauge metric.

    Args:
        name: Metric name
        description: Metric description

    Returns:
        CustomGauge instance
    """
    return CustomGauge(name, description)


def histogram_metric(name: str, description: str = "") -> CustomHistogram:
    """Create a new histogram metric.

    Args:
        name: Metric name
        description: Metric description

    Returns:
        CustomHistogram instance
    """
    return CustomHistogram(name, description)
