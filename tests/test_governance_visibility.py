from server.services.governance import GovernanceService
from server.auth import ROLE_MATRIX

def test_governance_visibility_returns_role_matrix():
    """Governance service should expose role matrix for visibility"""
    service = GovernanceService()

    visibility = service.get_governance_visibility("tenant-a")

    assert "roles" in visibility
    assert "operator" in visibility["roles"]
    assert visibility["roles"]["operator"]["description"] == "Support operator: triage, replay, and handoff"
    assert visibility["roles"]["operator"]["capabilities"]["trigger_replay"] is True

def test_governance_visibility_shows_critical_actions():
    """Governance visibility should highlight critical actions"""
    service = GovernanceService()

    visibility = service.get_governance_visibility("tenant-a")

    critical_actions = visibility.get("critical_actions", [])
    assert len(critical_actions) > 0
    assert any(action["capability"] == "approve_action" for action in critical_actions)
    assert any(action["capability"] == "trigger_replay" for action in critical_actions)

def test_governance_visibility_maps_roles_to_actions():
    """Governance visibility should map which roles can perform each critical action"""
    service = GovernanceService()

    visibility = service.get_governance_visibility("tenant-a")

    critical_actions = visibility.get("critical_actions", [])
    approve_action = next((a for a in critical_actions if a["capability"] == "approve_action"), None)

    assert approve_action is not None
    assert "admin" in approve_action.get("allowed_roles", [])
    assert "guardian" in approve_action.get("allowed_roles", [])
    assert "operator" not in approve_action.get("allowed_roles", [])
