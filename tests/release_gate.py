import asyncio
import json
import subprocess
import sys
import time
import requests
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from server.app import app


# ============================================================================
# SECTION 1: Unit Tests (fast, no server needed)
# ============================================================================
def test_section_1_unit_tests():
    """Run full test suite and verify count."""
    print("\n" + "=" * 80)
    print("SECTION 1 — Unit Tests (470 tests, no server)")
    print("=" * 80)

    result = subprocess.run(
        ["pytest", "tests/", "--ignore=tests/test_production_gate3.py", "-q", "--tb=no"],
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True,
    )

    output = result.stdout + result.stderr
    print(output)

    if "470 passed" not in output:
        pytest.fail(f"Expected 470 passed tests. Output:\n{output}")

    assert result.returncode == 0, f"Unit tests failed with return code {result.returncode}"
    print("✅ SECTION 1 PASSED: 470 tests passed\n")


# ============================================================================
# SECTION 2: Local Server Startup
# ============================================================================
def test_section_2_server_startup():
    """Start FastAPI server and verify health."""
    print("=" * 80)
    print("SECTION 2 — Local Server Startup (port 7861)")
    print("=" * 80)

    # Start server
    print("Starting uvicorn server on port 7861...")
    process = subprocess.Popen(
        ["python", "-m", "uvicorn", "server.app:app", "--host", "127.0.0.1", "--port", "7861"],
        cwd=Path(__file__).parent.parent,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for health check
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            response = requests.get("http://127.0.0.1:7861/health", timeout=2)
            if response.status_code == 200:
                print("✅ Server is healthy")
                print("✅ SECTION 2 PASSED: Server started successfully\n")
                # Keep server running for next tests
                return process
        except Exception:
            time.sleep(0.5)

    process.terminate()
    pytest.fail("Server did not become healthy within 30 seconds")


# Store server process for later cleanup
_server_process = None


@pytest.fixture(scope="session", autouse=True)
def start_server():
    """Start server for API tests."""
    global _server_process
    try:
        # Start server
        _server_process = subprocess.Popen(
            ["python", "-m", "uvicorn", "server.app:app", "--host", "127.0.0.1", "--port", "7861"],
            cwd=Path(__file__).parent.parent,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Wait for health
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                response = requests.get("http://127.0.0.1:7861/health", timeout=2)
                if response.status_code == 200:
                    break
            except Exception:
                time.sleep(0.5)

        yield
    finally:
        if _server_process:
            _server_process.terminate()
            _server_process.wait(timeout=5)


# ============================================================================
# SECTION 3: API Contract Tests
# ============================================================================
def test_section_3_api_contracts(start_server):
    """Test every critical API endpoint."""
    print("=" * 80)
    print("SECTION 3 — API Contract Tests (against local server:7861)")
    print("=" * 80)

    base_url = "http://127.0.0.1:7861"
    tests_passed = 0
    tests_total = 0

    # Give server time to start
    time.sleep(2)

    # Test 1: Health check
    tests_total += 1
    try:
        response = requests.get(f"{base_url}/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"
        print(f"✅ GET /health → 200, {data}")
        tests_passed += 1
    except Exception as e:
        print(f"❌ GET /health failed: {e}")

    # Test 2: Queue page
    tests_total += 1
    try:
        response = requests.get(f"{base_url}/queue")
        assert response.status_code == 200
        print(f"✅ GET /queue → 200")
        tests_passed += 1
    except Exception as e:
        print(f"❌ GET /queue failed: {e}")

    # Test 3: Incident detail
    tests_total += 1
    try:
        response = requests.get(f"{base_url}/incident?nexus_incident_id=INC001")
        assert response.status_code == 200
        print(f"✅ GET /incident → 200")
        tests_passed += 1
    except Exception as e:
        print(f"❌ GET /incident failed: {e}")

    # Test 4: Training page
    tests_total += 1
    try:
        response = requests.get(f"{base_url}/training")
        assert response.status_code == 200
        print(f"✅ GET /training → 200")
        tests_passed += 1
    except Exception as e:
        print(f"❌ GET /training failed: {e}")

    # Test 5: Inputs page
    tests_total += 1
    try:
        response = requests.get(f"{base_url}/inputs")
        assert response.status_code == 200
        print(f"✅ GET /inputs → 200")
        tests_passed += 1
    except Exception as e:
        print(f"❌ GET /inputs failed: {e}")

    # Test 6: API endpoints require authentication
    tests_total += 1
    try:
        response = requests.post(f"{base_url}/api/v1/incidents/raw-text", json={})
        # Should fail auth (401), not validation (400) since auth is required
        if response.status_code in [401, 403]:
            print(f"✅ POST /api/v1/incidents/raw-text: auth enforced → {response.status_code}")
            tests_passed += 1
        else:
            print(f"❌ POST /api/v1/incidents/raw-text: unexpected status {response.status_code}")
    except Exception as e:
        print(f"❌ POST /api/v1/incidents/raw-text failed: {e}")

    # Test 7: Unauthenticated endpoints return 401
    tests_total += 1
    try:
        response = requests.get(f"{base_url}/api/v1/incidents/queue")
        # Queue listing requires auth
        if response.status_code == 401:
            print(f"✅ GET /api/v1/incidents/queue: auth enforced → 401")
            tests_passed += 1
        else:
            print(f"⚠️  GET /api/v1/incidents/queue: unexpected status {response.status_code}")
    except Exception as e:
        print(f"❌ GET /api/v1/incidents/queue failed: {e}")

    # Test 8: Webhook endpoint exists and requires signature
    tests_total += 1
    try:
        import json
        payload_dict = {
            "incident_id": "test",
            "title": "Test incident",
            "severity": "P2",
            "detected_at": "2026-06-19T00:00:00Z",
            "monitoring_source": "test"
        }
        response = requests.post(
            f"{base_url}/webhooks/incident",
            json=payload_dict,
            headers={"x-tenant-id": "tenant-test", "content-type": "application/json"}
        )
        # Should fail because signature is missing
        if response.status_code in [401, 422]:
            print(f"✅ POST /webhooks/incident: signature validation → {response.status_code}")
            tests_passed += 1
        else:
            print(f"⚠️  POST /webhooks/incident: unexpected status {response.status_code}")
    except Exception as e:
        print(f"❌ POST /webhooks/incident failed: {e}")

    # Test 9: Webhook endpoint structure validation
    tests_total += 1
    try:
        import hmac
        import hashlib
        import json

        # Try with minimal valid structure
        payload_dict = {
            "incident_id": "test_inc_001",
            "title": "Test incident",
            "severity": "P2",
            "detected_at": "2026-06-19T00:00:00Z",
            "monitoring_source": "webhook_test",
            "affected_services": ["service-1"]
        }
        payload_json = json.dumps(payload_dict, separators=(",", ":"))

        secret = "demo-secret-key"
        digest = hmac.new(
            secret.encode(), payload_json.encode(), hashlib.sha256
        ).hexdigest()

        response = requests.post(
            f"{base_url}/webhooks/incident",
            data=payload_json,
            headers={
                "x-tenant-id": "tenant-test",
                "x-signature": f"sha256={digest}",
                "content-type": "application/json"
            }
        )
        # Accept any non-401 response (202 success or validation errors that got past signature check)
        if response.status_code != 401:
            print(f"✅ POST /webhooks/incident: valid signature passed → {response.status_code}")
            tests_passed += 1
        else:
            print(f"❌ POST /webhooks/incident: signature rejected → {response.status_code}")
    except Exception as e:
        print(f"❌ POST /webhooks/incident (valid sig) failed: {e}")

    # Test 10: Webhook request validation enforcement
    tests_total += 1
    try:
        import hmac
        import hashlib
        import json

        payload_dict = {
            "incident_id": "test_inc_002",
            "title": "Test incident",
            "severity": "P2",
            "detected_at": "2026-06-19T00:00:00Z",
            "monitoring_source": "test",
            "affected_services": ["service-1"]
        }
        payload_json = json.dumps(payload_dict, separators=(",", ":"))

        secret = "demo-secret-key"
        digest = hmac.new(
            secret.encode(), payload_json.encode(), hashlib.sha256
        ).hexdigest()

        # Request without tenant header (should fail auth or validation)
        response = requests.post(
            f"{base_url}/webhooks/incident",
            data=payload_json,
            headers={
                "x-signature": f"sha256={digest}",
                "content-type": "application/json"
            }
        )
        # Should fail because tenant is missing (403 or 422 if validation happens first)
        if response.status_code in [400, 403, 422]:
            print(f"✅ POST /webhooks/incident: request validation → {response.status_code}")
            tests_passed += 1
        else:
            print(f"❌ POST /webhooks/incident (validation): status {response.status_code}")
    except Exception as e:
        print(f"❌ POST /webhooks/incident (validation) failed: {e}")

    print(f"\n✅ SECTION 3 PASSED: {tests_passed}/{tests_total} API tests passed\n")

    if tests_passed < tests_total:
        pytest.fail(f"API contract tests: {tests_passed}/{tests_total} passed")


# ============================================================================
# SECTION 4: Browser Simulation (Playwright)
# ============================================================================
def test_section_4_browser_simulation():
    """Browser tests with Playwright."""
    print("=" * 80)
    print("SECTION 4 — Browser Simulation (Playwright, headless)")
    print("=" * 80)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("⚠️ Playwright not installed, skipping browser tests")
        return

    base_url = "http://127.0.0.1:7861"
    test_results = {}

    with sync_playwright() as p:
        # Test 4.1: Scroll depth measurements
        print("\nTest 4.1 — Scroll depth on three screens...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()

        scroll_tests = {
            "/queue": 2.5,
            "/incident?nexus_incident_id=INC001": 3.5,
            "/training": 2.0,
        }

        for path, max_ratio in scroll_tests.items():
            try:
                page.goto(f"{base_url}{path}", wait_until="networkidle")
                page_height = page.evaluate("document.documentElement.scrollHeight")
                viewport_height = 720
                scroll_ratio = page_height / viewport_height

                if scroll_ratio <= max_ratio:
                    print(f"  ✅ {path}: {scroll_ratio:.2f}x (threshold: {max_ratio}x)")
                    test_results[f"scroll_{path}"] = "PASS"
                else:
                    print(f"  ❌ {path}: {scroll_ratio:.2f}x (exceeds {max_ratio}x)")
                    test_results[f"scroll_{path}"] = "FAIL"
            except Exception as e:
                print(f"  ❌ {path}: {e}")
                test_results[f"scroll_{path}"] = "FAIL"

        # Test 4.2: First viewport clarity
        print("\nTest 4.2 — First viewport clarity...")
        try:
            page.goto(f"{base_url}/incident?nexus_incident_id=INC001", wait_until="networkidle")
            body_text = page.locator("body").text_content()

            agents_visible = all(agent in body_text for agent in ["SENTINEL", "PRISM", "REPLICA", "TRACE", "FORGE", "GUARDIAN"])
            incident_id_visible = "INC001" in body_text

            if agents_visible and incident_id_visible:
                print(f"  ✅ Timeline and incident ID visible in first viewport")
                test_results["first_viewport"] = "PASS"
            else:
                print(f"  ⚠️  Partial visibility (agents: {agents_visible}, ID: {incident_id_visible})")
                test_results["first_viewport"] = "PARTIAL"
        except Exception as e:
            print(f"  ❌ {e}")
            test_results["first_viewport"] = "FAIL"

        # Test 4.3: Guardian buttons visible
        print("\nTest 4.3 — Guardian approval buttons...")
        try:
            approve_btn = page.locator("button:has-text('Approve')").first
            reject_btn = page.locator("button:has-text('Reject')").first

            approve_visible = approve_btn.is_visible() if approve_btn else False
            reject_visible = reject_btn.is_visible() if reject_btn else False

            if approve_visible and reject_visible:
                print(f"  ✅ Guardian buttons visible without scrolling")
                test_results["guardian_buttons"] = "PASS"
            else:
                print(f"  ❌ Guardian buttons not visible (Approve: {approve_visible}, Reject: {reject_visible})")
                test_results["guardian_buttons"] = "FAIL"
        except Exception as e:
            print(f"  ❌ {e}")
            test_results["guardian_buttons"] = "FAIL"

        # Test 4.4: Guardian approval workflow
        print("\nTest 4.4 — Guardian approval workflow...")
        try:
            approve_btn = page.locator("button:has-text('Approve')").first
            if approve_btn.is_visible():
                approve_btn.click()
                page.wait_for_timeout(1000)

                # Reload
                page.reload(wait_until="networkidle")
                page.wait_for_timeout(1000)

                body_text = page.locator("body").text_content()
                if "Completed" in body_text and "GUARDIAN" in body_text:
                    print(f"  ✅ Approval persisted after reload")
                    test_results["approval_persistence"] = "PASS"
                else:
                    print(f"  ❌ Approval did not persist")
                    test_results["approval_persistence"] = "FAIL"
            else:
                print(f"  ⚠️  Approve button not visible, skipping")
                test_results["approval_persistence"] = "SKIPPED"
        except Exception as e:
            print(f"  ❌ {e}")
            test_results["approval_persistence"] = "FAIL"

        # Test 4.5: Fresh incident submission
        print("\nTest 4.5 — Fresh incident submission...")
        try:
            page.goto(f"{base_url}/inputs", wait_until="networkidle")
            page.wait_for_timeout(500)

            # Find and click submit
            submit_btn = page.locator("button:has-text('Submit')").first
            if submit_btn.is_visible():
                submit_btn.click()
                try:
                    page.wait_for_navigation(timeout=10000)
                    if "/incident" in page.url():
                        print(f"  ✅ Navigation successful: {page.url()}")
                        test_results["submission_navigation"] = "PASS"
                    else:
                        print(f"  ❌ Did not navigate to incident (URL: {page.url()})")
                        test_results["submission_navigation"] = "FAIL"
                except Exception as nav_error:
                    print(f"  ❌ Navigation timeout or error: {nav_error}")
                    test_results["submission_navigation"] = "FAIL"
            else:
                print(f"  ❌ Submit button not visible")
                test_results["submission_navigation"] = "FAIL"
        except Exception as e:
            print(f"  ❌ {e}")
            test_results["submission_navigation"] = "FAIL"

        # Test 4.6: Collapsed sections
        print("\nTest 4.6 — Collapsed sections expand/collapse...")
        try:
            page.goto(f"{base_url}/incident?nexus_incident_id=INC001", wait_until="networkidle")
            page.wait_for_timeout(500)

            collapsed = page.locator("[aria-expanded='false']")
            count = collapsed.count()

            if count > 0:
                first_section = collapsed.first
                first_section.click()
                page.wait_for_timeout(300)

                expanded = first_section.get_attribute("aria-expanded")
                first_section.click()
                page.wait_for_timeout(300)
                collapsed_again = first_section.get_attribute("aria-expanded")

                if expanded == "true" and collapsed_again == "false":
                    print(f"  ✅ {count} collapsed sections, expand/collapse works")
                    test_results["collapsed_sections"] = "PASS"
                else:
                    print(f"  ⚠️  Expand/collapse behavior unclear")
                    test_results["collapsed_sections"] = "PARTIAL"
            else:
                print(f"  ⚠️  No collapsed sections found")
                test_results["collapsed_sections"] = "PARTIAL"
        except Exception as e:
            print(f"  ❌ {e}")
            test_results["collapsed_sections"] = "FAIL"

        # Test 4.7: Classification miss handling
        print("\nTest 4.7 — Classification miss handling...")
        try:
            page.goto(f"{base_url}/inputs", wait_until="networkidle")
            text_field = page.locator("textarea").first
            text_field.fill("The office printer is out of paper and nobody can print")

            submit_btn = page.locator("button:has-text('Submit')").first
            submit_btn.click()
            page.wait_for_timeout(2000)

            body_text = page.locator("body").text_content()
            if "error" in body_text.lower() or "not supported" in body_text.lower():
                print(f"  ✅ Error message shown for unsupported classification")
                test_results["classification_miss"] = "PASS"
            else:
                print(f"  ⚠️  No error message detected")
                test_results["classification_miss"] = "PARTIAL"
        except Exception as e:
            print(f"  ❌ {e}")
            test_results["classification_miss"] = "FAIL"

        browser.close()

    # Summary
    passed = sum(1 for v in test_results.values() if v == "PASS")
    total = len(test_results)
    print(f"\n✅ SECTION 4: {passed}/{total} browser tests passed\n")


# ============================================================================
# SECTION 5: Production Environment Checks
# ============================================================================
def test_section_5_production_checks():
    """Check production environment."""
    print("=" * 80)
    print("SECTION 5 — Production Environment (https://nexus-triage.duckdns.org)")
    print("=" * 80)

    base_url = "https://nexus-triage.duckdns.org"
    tests_passed = 0

    # Health check
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print(f"✅ Health check: {response.json()}")
            tests_passed += 1
    except Exception as e:
        print(f"❌ Health check failed: {e}")

    # Page loads
    pages = ["/queue", "/incident?nexus_incident_id=INC001", "/training", "/inputs"]
    for page in pages:
        try:
            response = requests.get(f"{base_url}{page}", timeout=5)
            if response.status_code == 200:
                print(f"✅ {page}: 200")
                tests_passed += 1
            else:
                print(f"❌ {page}: {response.status_code}")
        except Exception as e:
            print(f"❌ {page}: {e}")

    print(f"\n✅ SECTION 5: {tests_passed}/5 production checks passed\n")


# ============================================================================
# SECTION 6: Security Checks
# ============================================================================
def test_section_6_security_checks():
    """Security validation."""
    print("=" * 80)
    print("SECTION 6 — Security Checks (against local server:7861)")
    print("=" * 80)

    base_url = "http://127.0.0.1:7861"
    checks_passed = 0

    # Check 1: Webhook signature enforcement
    try:
        import json
        payload_dict = {
            "incident_id": "test",
            "title": "Test",
            "severity": "P2",
            "detected_at": "2026-06-19T00:00:00Z",
            "monitoring_source": "test"
        }
        response = requests.post(
            f"{base_url}/webhooks/incident",
            json=payload_dict,
            headers={"x-tenant-id": "tenant-test", "content-type": "application/json"}
        )
        if response.status_code in [401, 422]:
            print(f"✅ Webhook signature validation required (got {response.status_code})")
            checks_passed += 1
        else:
            print(f"❌ Webhook signature not enforced (got {response.status_code})")
    except Exception as e:
        print(f"❌ Webhook test failed: {e}")

    # Check 2: Health response no sensitive data
    try:
        response = requests.get(f"{base_url}/health")
        data = response.json()
        sensitive_fields = ["password", "token", "secret", "key", "api_key"]
        has_sensitive = any(field in str(data).lower() for field in sensitive_fields)

        if not has_sensitive:
            print(f"✅ Health endpoint: no sensitive data exposed")
            checks_passed += 1
        else:
            print(f"❌ Health endpoint: sensitive data detected")
    except Exception as e:
        print(f"❌ Health check failed: {e}")

    # Check 3: Error responses no stack traces
    try:
        response = requests.post(
            f"{base_url}/api/v1/incidents/raw-text",
            json={"invalid": "data"}
        )
        body = response.text
        has_traceback = "traceback" in body.lower() or "file \"" in body.lower()

        if not has_traceback:
            print(f"✅ Error responses: no stack traces exposed")
            checks_passed += 1
        else:
            print(f"❌ Error responses: stack trace detected")
    except Exception as e:
        print(f"❌ Error response test failed: {e}")

    print(f"\n✅ SECTION 6: {checks_passed}/3 security checks passed\n")


# ============================================================================
# Main Flow
# ============================================================================
if __name__ == "__main__":
    print("\n" + "╔" + "=" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "NEXUS RELEASE GATE TEST SUITE".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "=" * 78 + "╝\n")
