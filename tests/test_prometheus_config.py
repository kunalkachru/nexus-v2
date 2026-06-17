"""
Tests for Prometheus configuration.

Validates:
- prometheus.yml syntax
- Required fields present
- Scrape endpoints correct
- Alert rules file referenced
"""

import pytest
import yaml
from pathlib import Path


@pytest.fixture
def prometheus_config():
    """Load prometheus.yml configuration."""
    config_path = Path(__file__).parent.parent / 'deployment' / 'prometheus.yml'
    with open(config_path) as f:
        return yaml.safe_load(f)


def test_prometheus_config_loads():
    """Test prometheus.yml can be loaded."""
    config_path = Path(__file__).parent.parent / 'deployment' / 'prometheus.yml'
    assert config_path.exists(), f"prometheus.yml not found at {config_path}"

    with open(config_path) as f:
        config = yaml.safe_load(f)

    assert config is not None, "Config is empty"


def test_global_config_present(prometheus_config):
    """Test global configuration section exists."""
    assert 'global' in prometheus_config
    global_config = prometheus_config['global']

    assert 'scrape_interval' in global_config
    assert 'evaluation_interval' in global_config
    assert global_config['scrape_interval'] == '15s'


def test_alert_rules_referenced(prometheus_config):
    """Test alert rules file is configured."""
    assert 'rule_files' in prometheus_config
    rule_files = prometheus_config['rule_files']

    assert len(rule_files) > 0
    assert 'alerts.yml' in rule_files[0]


def test_scrape_configs_present(prometheus_config):
    """Test scrape configurations exist."""
    assert 'scrape_configs' in prometheus_config
    scrape_configs = prometheus_config['scrape_configs']

    assert len(scrape_configs) > 0


def test_nexus_scrape_config(prometheus_config):
    """Test NEXUS service scrape config."""
    scrape_configs = prometheus_config['scrape_configs']

    nexus_config = None
    for config in scrape_configs:
        if config['job_name'] == 'nexus':
            nexus_config = config
            break

    assert nexus_config is not None, "NEXUS scrape config not found"
    assert nexus_config['metrics_path'] == '/metrics'
    assert 'localhost:7860' in str(nexus_config['static_configs'])


def test_storage_retention_configured(prometheus_config):
    """Test storage retention is configured."""
    assert 'storage' in prometheus_config
    storage = prometheus_config['storage']

    assert 'tsdb' in storage
    tsdb = storage['tsdb']

    assert 'retention' in tsdb
    retention = tsdb['retention']

    assert 'time' in retention
    assert '30d' in retention['time']


def test_docker_compose_file_exists():
    """Test docker-compose file exists."""
    compose_path = Path(__file__).parent.parent / 'deployment' / 'docker-compose.prometheus.yml'
    assert compose_path.exists(), f"docker-compose file not found at {compose_path}"


def test_docker_compose_prometheus_service():
    """Test docker-compose has prometheus service."""
    compose_path = Path(__file__).parent.parent / 'deployment' / 'docker-compose.prometheus.yml'

    with open(compose_path) as f:
        compose = yaml.safe_load(f)

    assert 'services' in compose
    assert 'prometheus' in compose['services']

    prometheus_service = compose['services']['prometheus']
    assert prometheus_service['image'] == 'prom/prometheus:latest'
    assert '9090:9090' in prometheus_service['ports']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
