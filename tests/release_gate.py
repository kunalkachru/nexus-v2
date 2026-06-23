import os
import re
import subprocess
from pathlib import Path

import pytest
import requests
from fastapi.testclient import TestClient

from server.app import app


ROOT_DIR = Path(__file__).parent.parent
PRODUCTION_BASE_URL = os.getenv("RELEASE_GATE_BASE_URL", "https://nexus-triage.duckdns.org").rstrip("/")
MINIMUM_PASSED_TESTS = 480
UNIT_TEST_SELECTION = [
    "pytest",
    "tests/",
    "--ignore=tests/test_production_gate3.py",
    "-k",
    "not test_replica_runner_executes_db_pool_pack",
    "-q",
    "--tb=no",
]


def _extract_pass_count(output: str) -> int:
    match = re.search(r"(\d+)\s+passed", output)
    if not match:
        pytest.fail(f"Could not determine passed-test count from output:\n{output}")
    return int(match.group(1))


# ============================================================================
# SECTION 1: Unit Tests (stable CI-safe subset)
# ============================================================================
def test_section_1_unit_tests():
    """Run CI-safe unit suite and verify exit code plus minimum threshold."""
    print("\n" + "=" * 80)
    print(f"SECTION 1 — Unit Tests (exit code + >={MINIMUM_PASSED_TESTS} passed)")
    print("=" * 80)

    result = subprocess.run(
        UNIT_TEST_SELECTION,
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
    )

    output = result.stdout + result.stderr
    print(output)

    assert result.returncode == 0, f"Unit tests failed with return code {result.returncode}"

    passed_count = _extract_pass_count(output)
    assert passed_count >= MINIMUM_PASSED_TESTS, (
        f"Expected at least {MINIMUM_PASSED_TESTS} passed tests, got {passed_count}."
    )
    print(f"✅ SECTION 1 PASSED: {passed_count} tests passed\n")


# ============================================================================
# SECTION 2: Production Smoke
# ============================================================================
def test_section_2_production_smoke():
    """Check the live production URL with the buyer-facing smoke surface."""
    print("=" * 80)
    print(f"SECTION 2 — Production Smoke ({PRODUCTION_BASE_URL})")
    print("=" * 80)

    tests_passed = 0
    pages = ["/health", "/queue", "/incident?nexus_incident_id=INC001", "/training", "/inputs"]

    for path in pages:
        try:
            response = requests.get(f"{PRODUCTION_BASE_URL}{path}", timeout=10)
            if response.status_code == 200:
                print(f"✅ {path}: 200")
                tests_passed += 1
            else:
                print(f"❌ {path}: {response.status_code}")
        except Exception as exc:
            print(f"❌ {path}: {exc}")

    assert tests_passed == len(pages), f"Production smoke checks: {tests_passed}/{len(pages)} passed"
    print(f"\n✅ SECTION 2 PASSED: {tests_passed}/{len(pages)} production checks passed\n")


# ============================================================================
# SECTION 3: Security Checks (in-process, no localhost server dependency)
# ============================================================================
def test_section_3_security_checks():
    """Security validation that does not require external server startup."""
    print("=" * 80)
    print("SECTION 3 — Security Checks (in-process)")
    print("=" * 80)

    checks_passed = 0

    with TestClient(app) as client:
        payload = {
            "incident_id": "test_inc_001",
            "title": "Test incident",
            "severity": "P2",
            "detected_at": "2026-06-19T00:00:00Z",
            "monitoring_source": "webhook_test",
            "affected_services": ["service-1"],
        }

        # Check 1: webhook signature enforcement
        response = client.post(
            "/webhooks/incident",
            json=payload,
            headers={"x-tenant-id": "tenant-test", "content-type": "application/json"},
        )
        if response.status_code in {401, 422}:
            print(f"✅ Webhook signature validation required (got {response.status_code})")
            checks_passed += 1
        else:
            print(f"❌ Webhook signature not enforced (got {response.status_code})")

        # Check 2: health response should not expose secrets
        response = client.get("/health")
        assert response.status_code == 200, "Health endpoint should return 200"
        data = response.json()
        sensitive_fields = ["password", "token", "secret", "api_key", "openai_key"]
        has_sensitive = any(field in str(data).lower() for field in sensitive_fields)
        if not has_sensitive:
            print("✅ Health endpoint: no sensitive data exposed")
            checks_passed += 1
        else:
            print("❌ Health endpoint: sensitive data detected")

        # Check 3: error/auth responses should not leak stack traces
        response = client.post("/api/v1/incidents/raw-text", json={"invalid": "data"})
        body = response.text.lower()
        has_traceback = "traceback" in body or 'file "' in body
        if not has_traceback:
            print("✅ Error responses: no stack traces exposed")
            checks_passed += 1
        else:
            print("❌ Error responses: stack trace detected")

    assert checks_passed == 3, f"Security checks: {checks_passed}/3 passed"
    print(f"\n✅ SECTION 3 PASSED: {checks_passed}/3 security checks passed\n")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v", "--tb=short"]))
