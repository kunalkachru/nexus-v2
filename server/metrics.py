"""
Prometheus metrics for NEXUS production readiness monitoring.

Exposes metrics on /metrics endpoint for Prometheus scraping.
"""

from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest

# Create registry
REGISTRY = CollectorRegistry()

# ============================================================================
# COUNTERS: Monotonically increasing events
# ============================================================================

incidents_created_total = Counter(
    'nexus_incidents_created_total',
    'Total incidents created',
    ['family', 'source'],
    registry=REGISTRY
)

guardian_decisions_total = Counter(
    'nexus_guardian_decisions_total',
    'Total GUARDIAN decisions made',
    ['decision'],  # approve, reject, request_modification
    registry=REGISTRY
)

auth_failures_total = Counter(
    'nexus_auth_failures_total',
    'Total authentication failures',
    ['failure_type'],  # missing_credentials, invalid_tenant, invalid_signature, etc.
    registry=REGISTRY
)

# ============================================================================
# HISTOGRAMS: Distribution of values (latencies, durations)
# ============================================================================

artifact_persistence_latency_ms = Histogram(
    'nexus_artifact_persistence_latency_ms',
    'Latency of artifact persistence in milliseconds',
    buckets=(10, 50, 100, 500, 1000, 5000),
    registry=REGISTRY
)

incident_processing_duration_seconds = Histogram(
    'nexus_incident_processing_duration_seconds',
    'Duration of incident processing in seconds',
    buckets=(1, 5, 10, 30, 60, 300),
    registry=REGISTRY
)

replay_duration_seconds = Histogram(
    'nexus_replay_duration_seconds',
    'Duration of incident replay in seconds',
    buckets=(1, 5, 10, 30, 60, 300),
    registry=REGISTRY
)

# ============================================================================
# GAUGES: Current point-in-time values
# ============================================================================

active_replays = Gauge(
    'nexus_active_replays',
    'Number of currently active replays',
    registry=REGISTRY
)

pending_guardian_reviews = Gauge(
    'nexus_pending_guardian_reviews',
    'Number of incidents pending GUARDIAN review',
    registry=REGISTRY
)

database_size_bytes = Gauge(
    'nexus_database_size_bytes',
    'Size of database in bytes',
    registry=REGISTRY
)

health_check_success = Gauge(
    'nexus_health_check_success',
    'Health check status (1 = success, 0 = failure)',
    registry=REGISTRY
)


def get_metrics_text() -> bytes:
    """
    Generate Prometheus-format metrics output.

    Returns:
        Bytes containing metrics in Prometheus text format
    """
    return generate_latest(REGISTRY)


def record_incident_created(family: str = "unknown", source: str = "unknown") -> None:
    """Record incident creation."""
    incidents_created_total.labels(family=family, source=source).inc()


def record_guardian_decision(decision: str) -> None:
    """Record GUARDIAN decision."""
    guardian_decisions_total.labels(decision=decision).inc()


def record_auth_failure(failure_type: str) -> None:
    """Record authentication failure."""
    auth_failures_total.labels(failure_type=failure_type).inc()


def record_persistence_latency(latency_ms: float) -> None:
    """Record artifact persistence latency."""
    artifact_persistence_latency_ms.observe(latency_ms)


def record_processing_duration(duration_seconds: float) -> None:
    """Record incident processing duration."""
    incident_processing_duration_seconds.observe(duration_seconds)


def record_replay_duration(duration_seconds: float) -> None:
    """Record replay duration."""
    replay_duration_seconds.observe(duration_seconds)


def set_active_replays(count: int) -> None:
    """Set current active replay count."""
    active_replays.set(count)


def set_pending_reviews(count: int) -> None:
    """Set pending GUARDIAN review count."""
    pending_guardian_reviews.set(count)


def set_database_size(size_bytes: int) -> None:
    """Set database size in bytes."""
    database_size_bytes.set(size_bytes)


def set_health_check(success: bool) -> None:
    """Set health check status."""
    health_check_success.set(1 if success else 0)
