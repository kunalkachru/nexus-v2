from pathlib import Path

from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    database_path: Path = Field(default=Path("artifacts/incidents.json"))
