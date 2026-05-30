from pathlib import Path

from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    database_path: Path = Field(default=Path("artifacts/incidents.json"))
    webhook_signing_secret: str = Field(default="nexus-demo-webhook-secret")
    allowed_tenant_ids: list[str] = Field(default_factory=lambda: ["tenant-a", "tenant-system"])
