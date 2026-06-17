import hashlib
import hmac

from server.auth import AuthenticatedContext, check_governance_capability, WebhookVerifier

def test_webhook_verifier_current_secret():
    """WebhookVerifier should accept signature from current secret"""
    current_secret = "current_secret_key"
    body = b'{"test": "webhook"}'

    verifier = WebhookVerifier(current_secret=current_secret)

    # Compute valid signature with current secret
    expected_digest = hmac.new(current_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    valid_signature = f"sha256={expected_digest}"

    assert verifier.verify(valid_signature, body) is True


def test_webhook_verifier_previous_secret():
    """WebhookVerifier should accept signature from previous secret during grace period"""
    current_secret = "new_secret_key"
    previous_secret = "old_secret_key"
    body = b'{"test": "webhook"}'

    verifier = WebhookVerifier(current_secret=current_secret, previous_secret=previous_secret)

    # Compute valid signature with previous secret
    expected_digest = hmac.new(previous_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    old_signature = f"sha256={expected_digest}"

    assert verifier.verify(old_signature, body) is True


def test_webhook_verifier_invalid_signature():
    """WebhookVerifier should reject invalid signatures"""
    current_secret = "secret_key"
    body = b'{"test": "webhook"}'

    verifier = WebhookVerifier(current_secret=current_secret)

    # Invalid signature (not matching either secret)
    invalid_signature = "sha256=0000000000000000000000000000000000000000000000000000000000000000"

    assert verifier.verify(invalid_signature, body) is False


def test_webhook_verifier_prefer_current_secret():
    """WebhookVerifier should accept current secret even if previous is set"""
    current_secret = "new_secret"
    previous_secret = "old_secret"
    body = b'{"test": "webhook"}'

    verifier = WebhookVerifier(current_secret=current_secret, previous_secret=previous_secret)

    # Compute valid signature with current secret
    expected_digest = hmac.new(current_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    new_signature = f"sha256={expected_digest}"

    assert verifier.verify(new_signature, body) is True


def test_webhook_verifier_no_previous_secret():
    """WebhookVerifier should reject old secrets when previous is not set"""
    current_secret = "new_secret"
    old_secret = "old_secret"
    body = b'{"test": "webhook"}'

    verifier = WebhookVerifier(current_secret=current_secret, previous_secret=None)

    # Compute signature with old secret
    expected_digest = hmac.new(old_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    old_signature = f"sha256={expected_digest}"

    # Should be rejected since previous_secret is None
    assert verifier.verify(old_signature, body) is False


def test_webhook_verifier_different_body():
    """WebhookVerifier should reject signature if body is different"""
    secret = "secret_key"
    original_body = b'{"test": "webhook"}'
    modified_body = b'{"test": "modified"}'

    verifier = WebhookVerifier(current_secret=secret)

    # Compute signature with original body
    expected_digest = hmac.new(secret.encode("utf-8"), original_body, hashlib.sha256).hexdigest()
    signature = f"sha256={expected_digest}"

    # Signature should be invalid for different body
    assert verifier.verify(signature, modified_body) is False


def test_guardian_can_approve_runbook():
    """Guardian role should have approve_action capability"""
    auth = AuthenticatedContext(
        user_id="user-alice",
        tenant_id="tenant-a",
        roles=["guardian"],
    )

    # Should not raise
    check_governance_capability(auth, "approve_action")

def test_operator_cannot_approve_runbook():
    """Operator role should not have approve_action capability"""
    auth = AuthenticatedContext(
        user_id="user-bob",
        tenant_id="tenant-a",
        roles=["operator"],
    )

    from fastapi import HTTPException
    import pytest

    with pytest.raises(HTTPException) as exc_info:
        check_governance_capability(auth, "approve_action")
    assert exc_info.value.status_code == 403

def test_admin_can_do_anything():
    """Admin role should have all capabilities"""
    auth = AuthenticatedContext(
        user_id="user-admin",
        tenant_id="tenant-a",
        roles=["admin"],
    )

    # All should pass
    check_governance_capability(auth, "approve_action")
    check_governance_capability(auth, "trigger_replay")
    check_governance_capability(auth, "send_handoff")
