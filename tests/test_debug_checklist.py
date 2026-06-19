"""Tests for debug checklist generation."""

import pytest

from server.models import DebugChecklist
from server.services.debug_checklist_generator import (
    generate_default_debug_checklist,
    generate_llm_debug_checklist,
)


def test_generate_default_checklist_for_timeout_amplification():
    """Verify default checklist generation for INC001."""
    checklist = generate_default_debug_checklist(
        incident_id="nxs_test_001",
        service="checkout-svc",
        issue_family="INC001",
    )

    assert isinstance(checklist, DebugChecklist)
    assert checklist.incident_id == "nxs_test_001"
    assert checklist.service == "checkout-svc"
    assert checklist.issue_family == "INC001"
    assert len(checklist.steps) == 3
    assert checklist.steps[0].step_number == 1
    assert "retry" in checklist.steps[0].description.lower()
    assert checklist.posture == "bounded_debugger"
    assert checklist.confidence > 0


def test_generate_default_checklist_for_db_pool():
    """Verify default checklist generation for INC002."""
    checklist = generate_default_debug_checklist(
        incident_id="nxs_test_002",
        service="payment-svc",
        issue_family="INC002",
    )

    assert checklist.issue_family == "INC002"
    assert len(checklist.steps) == 3
    assert "connection pool" in checklist.steps[0].description.lower()


def test_generate_default_checklist_for_deploy_regression():
    """Verify default checklist generation for INC003."""
    checklist = generate_default_debug_checklist(
        incident_id="nxs_test_003",
        service="api-svc",
        issue_family="INC003",
    )

    assert checklist.issue_family == "INC003"
    assert len(checklist.steps) == 3
    assert "code" in checklist.steps[0].description.lower()


def test_generate_default_checklist_for_queue_backlog():
    """Verify default checklist generation for INC005."""
    checklist = generate_default_debug_checklist(
        incident_id="nxs_test_005",
        service="worker-svc",
        issue_family="INC005",
    )

    assert checklist.issue_family == "INC005"
    assert len(checklist.steps) == 3
    assert "worker" in checklist.steps[0].description.lower()


def test_generate_default_checklist_for_auth_slowdown():
    """Verify default checklist generation for INC007."""
    checklist = generate_default_debug_checklist(
        incident_id="nxs_test_007",
        service="auth-svc",
        issue_family="INC007",
    )

    assert checklist.issue_family == "INC007"
    assert len(checklist.steps) == 3
    assert "auth" in checklist.steps[0].description.lower()


def test_generate_default_checklist_for_unknown_family():
    """Verify default checklist generation for unknown incident family."""
    checklist = generate_default_debug_checklist(
        incident_id="nxs_unknown",
        service="unknown-svc",
        issue_family="INC999",
    )

    assert checklist.issue_family == "INC999"
    assert len(checklist.steps) == 3
    assert checklist.posture == "bounded_debugger"


def test_checklist_steps_have_required_fields():
    """Verify all checklist steps have required fields."""
    checklist = generate_default_debug_checklist(
        incident_id="nxs_test_001",
        service="test-svc",
        issue_family="INC001",
    )

    for step in checklist.steps:
        assert step.step_number > 0
        assert len(step.description) > 0
        assert len(step.expected_outcome) > 0
        assert len(step.action_if_fails) > 0


def test_llm_checklist_without_client_falls_back_to_default():
    """Verify LLM checklist falls back to default without client."""
    checklist = generate_llm_debug_checklist(
        incident_id="nxs_llm_test",
        service="test-svc",
        issue_family="INC001",
        openai_client=None,
    )

    assert isinstance(checklist, DebugChecklist)
    assert len(checklist.steps) == 3
    assert checklist.posture == "bounded_debugger"


def test_llm_checklist_with_diagnosis_context():
    """Verify LLM checklist accepts diagnosis context."""
    diagnosis = "The checkout service is experiencing timeout issues due to retries."
    checklist = generate_llm_debug_checklist(
        incident_id="nxs_llm_test",
        service="checkout-svc",
        issue_family="INC001",
        diagnosis=diagnosis,
        openai_client=None,  # Will fall back to default
    )

    assert isinstance(checklist, DebugChecklist)
    assert checklist.issue_family == "INC001"
