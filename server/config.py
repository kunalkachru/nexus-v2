import os
from pathlib import Path

from pydantic import BaseModel, Field


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _env_list(name: str, default: list[str]) -> list[str]:
    raw = os.environ.get(name)
    if not raw:
        return default
    return [item.strip() for item in raw.split(",") if item.strip()]


class AppConfig(BaseModel):
    database_path: Path = Field(default_factory=lambda: Path(_env("NEXUS_DATABASE_PATH", "artifacts/incidents.json")))
    webhook_signing_secret: str = Field(default_factory=lambda: _get_webhook_secret())
    allowed_tenant_ids: list[str] = Field(default_factory=lambda: _env_list("NEXUS_ALLOWED_TENANT_IDS", ["tenant-a", "tenant-system"]))
    forge_model_name: str = Field(default_factory=lambda: _env("NEXUS_FORGE_MODEL_NAME", "gpt-4o"))
    use_live_llm: bool = Field(default_factory=lambda: _env("NEXUS_USE_OPENAI", "0") == "1")
    runtime_host_base_url: str = Field(default_factory=lambda: _env("NEXUS_RUNTIME_HOST_BASE_URL", "").strip())
    runtime_host_shared_token: str = Field(default_factory=lambda: _env("NEXUS_RUNTIME_HOST_SHARED_TOKEN", "").strip())


def _get_webhook_secret() -> str:
    import logging
    secret = _env("NEXUS_WEBHOOK_SIGNING_SECRET", "").strip()
    if not secret:
        logger = logging.getLogger(__name__)
        logger.warning("NEXUS_WEBHOOK_SIGNING_SECRET not set. Using default demo secret. For production, set this to a random value: python -c 'import secrets; print(secrets.token_hex(32))'")
        return "nexus-demo-webhook-secret"
    return secret
