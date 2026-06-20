from pathlib import Path
import sys

import pytest
from starlette.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from server.app import app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers():
    def build_headers(*, user_id: str = "user-123", tenant_id: str = "tenant-a", roles: str = "operator") -> dict[str, str]:
        return {
            "x-user-id": user_id,
            "x-tenant-id": tenant_id,
            "x-roles": roles,
        }

    return build_headers
