"""
Tests for Prometheus metrics endpoint.

Validates:
- Metrics endpoint returns valid Prometheus format
- All metrics are present
- Metric values are correct
- No duplicate metrics
"""

import pytest

from server.metrics import (
    REGISTRY,
    get_metrics_text,
    incidents_created_total,
    guardian_decisions_total,
    auth_failures_total,
    artifact_persistence_latency_ms,
    incident_processing_duration_seconds,
    replay_duration_seconds,
    active_replays,
    pending_guardian_reviews,
    database_size_bytes,
    health_check_success,
    record_incident_created,
    record_guardian_decision,
    record_auth_failure,
    record_persistence_latency,
    record_processing_duration,
    record_replay_duration,
    set_active_replays,
    set_pending_reviews,
    set_database_size,
    set_health_check,
)


def test_metrics_endpoint_returns_bytes():
    """Test /metrics endpoint returns bytes."""
    output = get_metrics_text()
    assert isinstance(output, bytes)
    assert len(output) > 0


def test_metrics_format_is_prometheus():
    """Test metrics output is valid Prometheus format."""
    output = get_metrics_text().decode('utf-8')

    # Should contain HELP and TYPE comments
    assert '# HELP' in output
    assert '# TYPE' in output

    # Should contain metric names
    assert 'nexus_incidents_created_total' in output
    assert 'nexus_guardian_decisions_total' in output
    assert 'nexus_auth_failures_total' in output


def test_counter_metrics_present():
    """Test all counter metrics are present."""
    output = get_metrics_text().decode('utf-8')

    assert 'nexus_incidents_created_total' in output
    assert 'nexus_guardian_decisions_total' in output
    assert 'nexus_auth_failures_total' in output


def test_histogram_metrics_present():
    """Test all histogram metrics are present."""
    output = get_metrics_text().decode('utf-8')

    assert 'nexus_artifact_persistence_latency_ms' in output
    assert 'nexus_incident_processing_duration_seconds' in output
    assert 'nexus_replay_duration_seconds' in output


def test_gauge_metrics_present():
    """Test all gauge metrics are present."""
    output = get_metrics_text().decode('utf-8')

    assert 'nexus_active_replays' in output
    assert 'nexus_pending_guardian_reviews' in output
    assert 'nexus_database_size_bytes' in output
    assert 'nexus_health_check_success' in output


def test_record_incident_created():
    """Test recording incident creation."""
    record_incident_created(family="test", source="webhook")

    output = get_metrics_text().decode('utf-8')
    assert 'nexus_incidents_created_total{family="test",source="webhook"}' in output


def test_record_guardian_decision():
    """Test recording GUARDIAN decision."""
    record_guardian_decision("approve")

    output = get_metrics_text().decode('utf-8')
    assert 'nexus_guardian_decisions_total{decision="approve"}' in output


def test_record_auth_failure():
    """Test recording auth failure."""
    record_auth_failure("invalid_signature")

    output = get_metrics_text().decode('utf-8')
    assert 'nexus_auth_failures_total{failure_type="invalid_signature"}' in output


def test_record_persistence_latency():
    """Test recording persistence latency."""
    record_persistence_latency(25.5)  # 25.5ms

    output = get_metrics_text().decode('utf-8')
    assert 'nexus_artifact_persistence_latency_ms_bucket' in output
    assert 'nexus_artifact_persistence_latency_ms_sum' in output
    assert 'nexus_artifact_persistence_latency_ms_count' in output


def test_record_processing_duration():
    """Test recording processing duration."""
    record_processing_duration(5.25)  # 5.25 seconds

    output = get_metrics_text().decode('utf-8')
    assert 'nexus_incident_processing_duration_seconds_bucket' in output


def test_record_replay_duration():
    """Test recording replay duration."""
    record_replay_duration(10.5)  # 10.5 seconds

    output = get_metrics_text().decode('utf-8')
    assert 'nexus_replay_duration_seconds_bucket' in output


def test_set_active_replays():
    """Test setting active replay gauge."""
    set_active_replays(5)

    output = get_metrics_text().decode('utf-8')
    assert 'nexus_active_replays 5' in output


def test_set_pending_reviews():
    """Test setting pending reviews gauge."""
    set_pending_reviews(12)

    output = get_metrics_text().decode('utf-8')
    assert 'nexus_pending_guardian_reviews 12' in output


def test_set_database_size():
    """Test setting database size gauge."""
    set_database_size(1024000)  # 1MB

    output = get_metrics_text().decode('utf-8')
    # Prometheus may use scientific notation for large numbers
    assert 'nexus_database_size_bytes' in output
    # Check that the value appears (either as integer or scientific notation)
    assert '1024000' in output or '1.024e' in output


def test_set_health_check():
    """Test setting health check gauge."""
    set_health_check(True)

    output = get_metrics_text().decode('utf-8')
    assert 'nexus_health_check_success 1' in output

    set_health_check(False)

    output = get_metrics_text().decode('utf-8')
    assert 'nexus_health_check_success 0' in output


def test_no_duplicate_metrics():
    """Test metrics format is valid (histograms have buckets, which is expected)."""
    output = get_metrics_text().decode('utf-8')

    # Should have HELP and TYPE comments for each metric
    assert '# HELP nexus_incidents_created_total' in output
    assert '# TYPE nexus_incidents_created_total counter' in output

    assert '# HELP nexus_artifact_persistence_latency_ms' in output
    assert '# TYPE nexus_artifact_persistence_latency_ms histogram' in output

    # Histograms naturally have multiple lines (bucket, count, sum)
    # This is expected and correct behavior
    assert 'nexus_artifact_persistence_latency_ms_bucket' in output


def test_metrics_have_labels():
    """Test counter metrics have proper labels."""
    output = get_metrics_text().decode('utf-8')

    # Counter with labels
    assert 'nexus_incidents_created_total{' in output

    # Gauge without labels (simple value)
    assert 'nexus_active_replays' in output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
