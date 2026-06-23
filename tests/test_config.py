import os
import pytest

from server.config import AppConfig


@pytest.fixture(autouse=True)
def cleanup_env():
    """Cleanup environment variables after each test."""
    original_app_env = os.environ.get("APP_ENV")
    original_tenant_ids = os.environ.get("NEXUS_ALLOWED_TENANT_IDS")

    yield

    # Restore original values
    if original_app_env is None:
        os.environ.pop("APP_ENV", None)
    else:
        os.environ["APP_ENV"] = original_app_env

    if original_tenant_ids is None:
        os.environ.pop("NEXUS_ALLOWED_TENANT_IDS", None)
    else:
        os.environ["NEXUS_ALLOWED_TENANT_IDS"] = original_tenant_ids


def test_app_env_defaults_to_demo():
    """Verify APP_ENV defaults to demo when not set."""
    os.environ.pop("APP_ENV", None)
    os.environ.pop("NEXUS_ALLOWED_TENANT_IDS", None)

    config = AppConfig()
    assert config.app_env == "demo"
    assert config.allowed_tenant_ids == ["tenant-a", "tenant-system"]


def test_app_env_demo_allows_default_tenants():
    """Verify demo mode accepts default tenant IDs."""
    os.environ["APP_ENV"] = "demo"
    os.environ.pop("NEXUS_ALLOWED_TENANT_IDS", None)

    config = AppConfig()
    assert config.app_env == "demo"
    assert config.allowed_tenant_ids == ["tenant-a", "tenant-system"]


def test_app_env_development_allows_default_tenants():
    """Verify development mode accepts default tenant IDs."""
    os.environ["APP_ENV"] = "development"
    os.environ.pop("NEXUS_ALLOWED_TENANT_IDS", None)

    config = AppConfig()
    assert config.app_env == "development"
    assert config.allowed_tenant_ids == ["tenant-a", "tenant-system"]


def test_app_env_production_requires_tenant_ids():
    """Verify production mode raises error if NEXUS_ALLOWED_TENANT_IDS not set."""
    os.environ["APP_ENV"] = "production"
    os.environ.pop("NEXUS_ALLOWED_TENANT_IDS", None)

    with pytest.raises(ValueError, match="NEXUS_ALLOWED_TENANT_IDS must be set in production mode"):
        AppConfig()


def test_app_env_production_accepts_configured_tenant_ids():
    """Verify production mode accepts configured tenant IDs."""
    os.environ["APP_ENV"] = "production"
    os.environ["NEXUS_ALLOWED_TENANT_IDS"] = "tenant-prod-a,tenant-prod-b"

    config = AppConfig()
    assert config.app_env == "production"
    assert config.allowed_tenant_ids == ["tenant-prod-a", "tenant-prod-b"]


def test_app_env_product_alias_maps_to_production():
    """Verify legacy product alias is normalized to production."""
    os.environ["APP_ENV"] = "product"
    os.environ["NEXUS_ALLOWED_TENANT_IDS"] = "tenant-prod-a,tenant-prod-b"

    config = AppConfig()
    assert config.app_env == "production"
    assert config.allowed_tenant_ids == ["tenant-prod-a", "tenant-prod-b"]


def test_custom_tenant_ids_in_demo():
    """Verify custom tenant IDs work in demo mode."""
    os.environ["APP_ENV"] = "demo"
    os.environ["NEXUS_ALLOWED_TENANT_IDS"] = "custom-tenant-1,custom-tenant-2"

    config = AppConfig()
    assert config.allowed_tenant_ids == ["custom-tenant-1", "custom-tenant-2"]
