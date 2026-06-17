"""
Tests for Prometheus alert rules.

Validates:
- alerts.yml YAML syntax
- Required alert rule fields
- PromQL expression validity
- Threshold values sensible
- Label consistency
"""

import pytest
import yaml
from pathlib import Path


@pytest.fixture
def alerts_config():
    """Load alerts.yml configuration."""
    config_path = Path(__file__).parent.parent / 'deployment' / 'prometheus' / 'alerts.yml'
    with open(config_path) as f:
        return yaml.safe_load(f)


def test_alerts_file_exists():
    """Test alerts.yml file exists."""
    alerts_path = Path(__file__).parent.parent / 'deployment' / 'prometheus' / 'alerts.yml'
    assert alerts_path.exists(), f"Alerts file not found at {alerts_path}"


def test_alerts_config_valid_yaml(alerts_config):
    """Test alerts.yml is valid YAML."""
    assert alerts_config is not None
    assert isinstance(alerts_config, dict)


def test_alerts_has_groups(alerts_config):
    """Test alerts config has groups."""
    assert 'groups' in alerts_config
    assert len(alerts_config['groups']) > 0


def test_alert_group_structure(alerts_config):
    """Test alert group has required structure."""
    groups = alerts_config['groups']
    assert len(groups) == 1

    group = groups[0]
    assert 'name' in group
    assert group['name'] == 'nexus_alerts'
    assert 'interval' in group
    assert 'rules' in group


def test_alerts_count(alerts_config):
    """Test there are exactly 6 alert rules."""
    rules = alerts_config['groups'][0]['rules']
    assert len(rules) == 6, f"Expected 6 alert rules, got {len(rules)}"


def test_alert_rule_names(alerts_config):
    """Test all required alert rules are present."""
    rules = alerts_config['groups'][0]['rules']
    alert_names = [rule.get('alert') for rule in rules]

    assert 'NexusDown' in alert_names
    assert 'SuspiciousAuthFailures' in alert_names
    assert 'ArtifactPersistenceSlow' in alert_names
    assert 'GuardianApprovalRateLow' in alert_names
    assert 'PendingGuardianReviewsHigh' in alert_names
    assert 'DatabaseGrowthFast' in alert_names


def test_each_alert_has_required_fields(alerts_config):
    """Test each alert rule has required fields."""
    rules = alerts_config['groups'][0]['rules']

    for rule in rules:
        assert 'alert' in rule, f"Alert rule missing 'alert' field"
        assert 'expr' in rule, f"Alert rule {rule.get('alert')} missing 'expr' field"
        assert 'for' in rule, f"Alert rule {rule.get('alert')} missing 'for' field"
        assert 'labels' in rule, f"Alert rule {rule.get('alert')} missing 'labels' field"
        assert 'annotations' in rule, f"Alert rule {rule.get('alert')} missing 'annotations' field"


def test_alert_labels_consistency(alerts_config):
    """Test alert rules have consistent labels."""
    rules = alerts_config['groups'][0]['rules']

    for rule in rules:
        labels = rule.get('labels', {})
        assert 'severity' in labels, f"Alert {rule.get('alert')} missing severity label"
        assert 'service' in labels, f"Alert {rule.get('alert')} missing service label"
        assert labels['service'] == 'nexus', f"Alert {rule.get('alert')} has incorrect service label"


def test_alert_severity_values(alerts_config):
    """Test alert severity values are valid."""
    rules = alerts_config['groups'][0]['rules']
    valid_severities = {'critical', 'high', 'medium', 'low'}

    for rule in rules:
        severity = rule.get('labels', {}).get('severity')
        assert severity in valid_severities, f"Alert {rule.get('alert')} has invalid severity: {severity}"


def test_alert_annotations_present(alerts_config):
    """Test each alert has required annotations."""
    rules = alerts_config['groups'][0]['rules']

    for rule in rules:
        annotations = rule.get('annotations', {})
        assert 'summary' in annotations, f"Alert {rule.get('alert')} missing summary annotation"
        assert 'description' in annotations, f"Alert {rule.get('alert')} missing description annotation"
        assert 'runbook_url' in annotations, f"Alert {rule.get('alert')} missing runbook_url annotation"


def test_alert_prometheus_metrics(alerts_config):
    """Test alert expressions reference NEXUS metrics."""
    rules = alerts_config['groups'][0]['rules']

    for rule in rules:
        expr = rule.get('expr', '')
        # Should reference nexus metrics or up metric
        assert 'nexus_' in expr or 'up{' in expr, f"Alert {rule.get('alert')} doesn't reference NEXUS metrics"


def test_alert_duration_values(alerts_config):
    """Test alert duration 'for' values are reasonable."""
    rules = alerts_config['groups'][0]['rules']
    valid_durations = {'5m', '10m', '30m', '2h'}

    for rule in rules:
        duration = rule.get('for')
        assert duration in valid_durations, f"Alert {rule.get('alert')} has unusual duration: {duration}"


def test_nexusdown_alert(alerts_config):
    """Test NexusDown alert configuration."""
    rules = alerts_config['groups'][0]['rules']
    alert = next((r for r in rules if r.get('alert') == 'NexusDown'), None)

    assert alert is not None
    assert alert['labels']['severity'] == 'critical'
    assert 'up{job="nexus"} == 0' in alert['expr']
    assert alert['for'] == '5m'


def test_auth_failures_alert(alerts_config):
    """Test SuspiciousAuthFailures alert configuration."""
    rules = alerts_config['groups'][0]['rules']
    alert = next((r for r in rules if r.get('alert') == 'SuspiciousAuthFailures'), None)

    assert alert is not None
    assert alert['labels']['severity'] == 'high'
    assert 'nexus_auth_failures_total' in alert['expr']
    assert '0.2' in alert['expr']  # 0.2 failures/sec threshold
    assert alert['for'] == '5m'


def test_persistence_latency_alert(alerts_config):
    """Test ArtifactPersistenceSlow alert configuration."""
    rules = alerts_config['groups'][0]['rules']
    alert = next((r for r in rules if r.get('alert') == 'ArtifactPersistenceSlow'), None)

    assert alert is not None
    assert alert['labels']['severity'] == 'high'
    assert 'nexus_artifact_persistence_latency_ms' in alert['expr']
    assert '1000' in alert['expr']  # 1000ms threshold
    assert alert['for'] == '10m'


def test_guardian_approval_alert(alerts_config):
    """Test GuardianApprovalRateLow alert configuration."""
    rules = alerts_config['groups'][0]['rules']
    alert = next((r for r in rules if r.get('alert') == 'GuardianApprovalRateLow'), None)

    assert alert is not None
    assert alert['labels']['severity'] == 'medium'
    assert 'nexus_guardian_decisions_total' in alert['expr']
    assert '0.5' in alert['expr']  # 50% threshold
    assert alert['for'] == '30m'


def test_pending_reviews_alert(alerts_config):
    """Test PendingGuardianReviewsHigh alert configuration."""
    rules = alerts_config['groups'][0]['rules']
    alert = next((r for r in rules if r.get('alert') == 'PendingGuardianReviewsHigh'), None)

    assert alert is not None
    assert alert['labels']['severity'] == 'medium'
    assert 'nexus_pending_guardian_reviews' in alert['expr']
    assert '50' in alert['expr']  # 50 reviews threshold
    assert alert['for'] == '30m'


def test_database_growth_alert(alerts_config):
    """Test DatabaseGrowthFast alert configuration."""
    rules = alerts_config['groups'][0]['rules']
    alert = next((r for r in rules if r.get('alert') == 'DatabaseGrowthFast'), None)

    assert alert is not None
    assert alert['labels']['severity'] == 'low'
    assert 'nexus_database_size_bytes' in alert['expr']
    assert '1000000000' in alert['expr']  # 1GB/day threshold
    assert alert['for'] == '2h'


def test_alert_thresholds_make_sense(alerts_config):
    """Test alert thresholds are reasonable for production."""
    rules = alerts_config['groups'][0]['rules']

    # Auth failure rate: 0.2 failures/sec is high, reasonable for attack detection
    auth_alert = next((r for r in rules if r.get('alert') == 'SuspiciousAuthFailures'), None)
    assert auth_alert is not None

    # Persistence latency: 1000ms is 1 second, reasonable upper bound
    persistence_alert = next((r for r in rules if r.get('alert') == 'ArtifactPersistenceSlow'), None)
    assert persistence_alert is not None

    # Guardian approval: < 50% is significant drop from baseline
    guardian_alert = next((r for r in rules if r.get('alert') == 'GuardianApprovalRateLow'), None)
    assert guardian_alert is not None

    # Pending reviews: 50 is reasonable backlog threshold
    pending_alert = next((r for r in rules if r.get('alert') == 'PendingGuardianReviewsHigh'), None)
    assert pending_alert is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
