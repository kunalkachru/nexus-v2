"""
Tests for Grafana dashboards.

Validates:
- Dashboard JSON structure and validity
- Required panels present
- Prometheus query validity
- Metric references correct
"""

import json
import pytest
from pathlib import Path


@pytest.fixture
def dashboards_dir():
    """Get path to dashboards directory."""
    return Path(__file__).parent.parent / 'deployment' / 'grafana'


@pytest.fixture
def system_health_dashboard(dashboards_dir):
    """Load system health dashboard."""
    with open(dashboards_dir / 'dashboard-system-health.json') as f:
        return json.load(f)


@pytest.fixture
def performance_dashboard(dashboards_dir):
    """Load performance dashboard."""
    with open(dashboards_dir / 'dashboard-performance.json') as f:
        return json.load(f)


@pytest.fixture
def error_analysis_dashboard(dashboards_dir):
    """Load error analysis dashboard."""
    with open(dashboards_dir / 'dashboard-errors.json') as f:
        return json.load(f)


def test_dashboards_directory_exists(dashboards_dir):
    """Test dashboards directory exists."""
    assert dashboards_dir.exists(), f"Dashboards directory not found at {dashboards_dir}"


def test_system_health_dashboard_exists(dashboards_dir):
    """Test system health dashboard file exists."""
    dashboard_path = dashboards_dir / 'dashboard-system-health.json'
    assert dashboard_path.exists(), f"Dashboard not found at {dashboard_path}"


def test_performance_dashboard_exists(dashboards_dir):
    """Test performance dashboard file exists."""
    dashboard_path = dashboards_dir / 'dashboard-performance.json'
    assert dashboard_path.exists(), f"Dashboard not found at {dashboard_path}"


def test_error_analysis_dashboard_exists(dashboards_dir):
    """Test error analysis dashboard file exists."""
    dashboard_path = dashboards_dir / 'dashboard-errors.json'
    assert dashboard_path.exists(), f"Dashboard not found at {dashboard_path}"


def test_system_health_dashboard_valid_json(system_health_dashboard):
    """Test system health dashboard is valid JSON."""
    assert system_health_dashboard is not None
    assert isinstance(system_health_dashboard, dict)


def test_performance_dashboard_valid_json(performance_dashboard):
    """Test performance dashboard is valid JSON."""
    assert performance_dashboard is not None
    assert isinstance(performance_dashboard, dict)


def test_error_analysis_dashboard_valid_json(error_analysis_dashboard):
    """Test error analysis dashboard is valid JSON."""
    assert error_analysis_dashboard is not None
    assert isinstance(error_analysis_dashboard, dict)


def test_system_health_dashboard_structure(system_health_dashboard):
    """Test system health dashboard has required structure."""
    assert 'title' in system_health_dashboard
    assert system_health_dashboard['title'] == 'NEXUS System Health'
    assert 'panels' in system_health_dashboard
    assert len(system_health_dashboard['panels']) == 4


def test_performance_dashboard_structure(performance_dashboard):
    """Test performance dashboard has required structure."""
    assert 'title' in performance_dashboard
    assert performance_dashboard['title'] == 'NEXUS Performance Metrics'
    assert 'panels' in performance_dashboard
    assert len(performance_dashboard['panels']) == 4


def test_error_analysis_dashboard_structure(error_analysis_dashboard):
    """Test error analysis dashboard has required structure."""
    assert 'title' in error_analysis_dashboard
    assert error_analysis_dashboard['title'] == 'NEXUS Error Analysis'
    assert 'panels' in error_analysis_dashboard
    assert len(error_analysis_dashboard['panels']) == 4


def test_system_health_panel_titles(system_health_dashboard):
    """Test system health dashboard has required panel titles."""
    titles = [p.get('title') for p in system_health_dashboard['panels']]

    assert 'Uptime (Health Check Success Rate)' in titles
    assert 'Incident Submission Rate (incidents/hour)' in titles
    assert 'GUARDIAN Approval Rate (%)' in titles
    assert 'Auth Failure Rate (failures/hour)' in titles


def test_performance_panel_titles(performance_dashboard):
    """Test performance dashboard has required panel titles."""
    titles = [p.get('title') for p in performance_dashboard['panels']]

    assert 'Artifact Persistence Latency (p50, p95, p99)' in titles
    assert 'Incident Processing Duration (p50, p95, p99)' in titles
    assert 'REPLICA Replay Duration (p50, p95, p99)' in titles
    assert 'Active Replays (Gauge)' in titles


def test_error_analysis_panel_titles(error_analysis_dashboard):
    """Test error analysis dashboard has required panel titles."""
    titles = [p.get('title') for p in error_analysis_dashboard['panels']]

    assert 'Auth Failures by Type (Pie Chart)' in titles
    assert 'Incidents Awaiting GUARDIAN Review (Time Series)' in titles
    assert 'Failed Artifact Persists (Counter)' in titles
    assert 'Database Size Over Time (Trend)' in titles


def test_system_health_prometheus_targets(system_health_dashboard):
    """Test system health dashboard has valid Prometheus queries."""
    for panel in system_health_dashboard['panels']:
        targets = panel.get('targets', [])
        assert len(targets) > 0, f"Panel {panel.get('title')} has no targets"

        for target in targets:
            assert 'expr' in target, f"Target in {panel.get('title')} has no expr"
            expr = target['expr']
            # Verify prometheus metric names
            assert 'nexus_' in expr, f"Invalid metric in {expr}"


def test_performance_prometheus_targets(performance_dashboard):
    """Test performance dashboard has valid Prometheus queries."""
    for panel in performance_dashboard['panels']:
        targets = panel.get('targets', [])
        assert len(targets) > 0, f"Panel {panel.get('title')} has no targets"

        for target in targets:
            assert 'expr' in target, f"Target in {panel.get('title')} has no expr"
            expr = target['expr']
            # Verify prometheus metric names
            assert 'nexus_' in expr, f"Invalid metric in {expr}"


def test_error_analysis_prometheus_targets(error_analysis_dashboard):
    """Test error analysis dashboard has valid Prometheus queries."""
    for panel in error_analysis_dashboard['panels']:
        targets = panel.get('targets', [])
        assert len(targets) > 0, f"Panel {panel.get('title')} has no targets"

        for target in targets:
            assert 'expr' in target, f"Target in {panel.get('title')} has no expr"
            expr = target['expr']
            # Verify prometheus metric names
            assert 'nexus_' in expr, f"Invalid metric in {expr}"


def test_system_health_specific_metrics(system_health_dashboard):
    """Test system health dashboard references correct metrics."""
    all_exprs = []
    for panel in system_health_dashboard['panels']:
        for target in panel.get('targets', []):
            all_exprs.append(target.get('expr', ''))

    combined = ' '.join(all_exprs)
    assert 'nexus_health_check_success' in combined
    assert 'nexus_incidents_created_total' in combined
    assert 'nexus_guardian_decisions_total' in combined
    assert 'nexus_auth_failures_total' in combined


def test_performance_specific_metrics(performance_dashboard):
    """Test performance dashboard references correct metrics."""
    all_exprs = []
    for panel in performance_dashboard['panels']:
        for target in panel.get('targets', []):
            all_exprs.append(target.get('expr', ''))

    combined = ' '.join(all_exprs)
    assert 'nexus_artifact_persistence_latency_ms' in combined
    assert 'nexus_incident_processing_duration_seconds' in combined
    assert 'nexus_replay_duration_seconds' in combined
    assert 'nexus_active_replays' in combined


def test_error_analysis_specific_metrics(error_analysis_dashboard):
    """Test error analysis dashboard references correct metrics."""
    all_exprs = []
    for panel in error_analysis_dashboard['panels']:
        for target in panel.get('targets', []):
            all_exprs.append(target.get('expr', ''))

    combined = ' '.join(all_exprs)
    assert 'nexus_auth_failures_total' in combined
    assert 'nexus_pending_guardian_reviews' in combined
    assert 'nexus_incidents_created_total' in combined
    assert 'nexus_database_size_bytes' in combined


def test_dashboards_have_refresh_configured(system_health_dashboard, performance_dashboard, error_analysis_dashboard):
    """Test dashboards have refresh interval configured."""
    assert system_health_dashboard.get('refresh') == '30s'
    assert performance_dashboard.get('refresh') == '30s'
    assert error_analysis_dashboard.get('refresh') == '30s'


def test_dashboards_have_time_range(system_health_dashboard, performance_dashboard, error_analysis_dashboard):
    """Test dashboards have time range configured."""
    for dashboard in [system_health_dashboard, performance_dashboard, error_analysis_dashboard]:
        assert 'time' in dashboard
        assert 'from' in dashboard['time']
        assert 'to' in dashboard['time']
        assert dashboard['time']['from'] == 'now-6h'
        assert dashboard['time']['to'] == 'now'


def test_dashboards_have_tags(system_health_dashboard, performance_dashboard, error_analysis_dashboard):
    """Test dashboards have NEXUS tag."""
    for dashboard in [system_health_dashboard, performance_dashboard, error_analysis_dashboard]:
        assert 'tags' in dashboard
        assert 'NEXUS' in dashboard['tags']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
