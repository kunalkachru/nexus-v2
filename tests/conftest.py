from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def auth_headers():
    def build_headers(*, user_id: str = "user-123", tenant_id: str = "tenant-a", roles: str = "operator") -> dict[str, str]:
        return {
            "x-user-id": user_id,
            "x-tenant-id": tenant_id,
            "x-roles": roles,
        }

    return build_headers
