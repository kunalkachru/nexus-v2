from __future__ import annotations

import hashlib
import hmac
import logging

from fastapi import HTTPException, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AuthenticatedContext(BaseModel):
    user_id: str
    tenant_id: str
    roles: list[str] = Field(default_factory=list)


ROLE_MATRIX = {
    "operator": {
        "description": "Support operator: triage, replay, and handoff",
        "capabilities": {
            "read_incidents": True,
            "create_incident": True,
            "trigger_replay": True,
            "send_handoff": True,
            "view_settings": True,
            "update_bootstrap": False,
            "approve_action": False,
            "review_action": False,
        },
    },
    "incident_manager": {
        "description": "Incident manager: operator + incident management controls",
        "capabilities": {
            "read_incidents": True,
            "create_incident": True,
            "trigger_replay": True,
            "send_handoff": True,
            "view_settings": True,
            "update_bootstrap": False,
            "approve_action": False,
            "review_action": True,
        },
    },
    "guardian": {
        "description": "Guardian reviewer: approves and executes suggested actions",
        "capabilities": {
            "read_incidents": True,
            "create_incident": False,
            "trigger_replay": False,
            "send_handoff": False,
            "view_settings": True,
            "update_bootstrap": False,
            "approve_action": True,
            "review_action": True,
        },
    },
    "admin": {
        "description": "Administrator: full system access including bootstrap configuration",
        "capabilities": {
            "read_incidents": True,
            "create_incident": True,
            "trigger_replay": True,
            "send_handoff": True,
            "view_settings": True,
            "update_bootstrap": True,
            "approve_action": True,
            "review_action": True,
        },
    },
}


def get_user_capabilities(roles: list[str]) -> dict[str, bool]:
    capabilities = {
        "read_incidents": False,
        "create_incident": False,
        "trigger_replay": False,
        "send_handoff": False,
        "view_settings": False,
        "update_bootstrap": False,
        "approve_action": False,
        "review_action": False,
    }

    for role in roles:
        role_data = ROLE_MATRIX.get(role, {})
        for capability, allowed in role_data.get("capabilities", {}).items():
            if allowed:
                capabilities[capability] = True

    return capabilities


def require_role(auth: AuthenticatedContext, *allowed_roles: str) -> None:
    if not allowed_roles:
        return
    if not auth.roles:
        raise HTTPException(status_code=403, detail="role required")
    allowed = {role.strip() for role in allowed_roles if role.strip()}
    if not allowed.intersection(set(auth.roles)):
        raise HTTPException(status_code=403, detail="role not allowed")


def check_governance_capability(auth: AuthenticatedContext, capability: str) -> None:
    """Check if user has required capability for a governance action."""
    capabilities = get_user_capabilities(auth.roles)
    if not capabilities.get(capability, False):
        raise HTTPException(
            status_code=403,
            detail=f"governance action '{capability}' not allowed for roles: {', '.join(auth.roles)}",
        )


async def require_auth(request: Request) -> AuthenticatedContext:
    user_id = request.headers.get("x-user-id", "").strip()
    tenant_id = request.headers.get("x-tenant-id", "").strip()
    roles_header = request.headers.get("x-roles", "")
    roles = [role.strip() for role in roles_header.split(",") if role.strip()]

    if not user_id or not tenant_id:
        logger.warning(
            "auth_failed_missing_credentials",
            extra={
                "path": request.url.path,
                "has_user_id": bool(user_id),
                "has_tenant_id": bool(tenant_id),
                "method": request.method,
            }
        )
        raise HTTPException(status_code=401, detail="authentication required")

    allowed_tenants = getattr(getattr(request.app.state, "config", None), "allowed_tenant_ids", ["tenant-a", "tenant-system"])
    if tenant_id not in allowed_tenants:
        logger.warning(
            "auth_failed_invalid_tenant",
            extra={
                "tenant_id": tenant_id,
                "user_id": user_id,
                "path": request.url.path,
                "method": request.method,
            }
        )
        raise HTTPException(status_code=403, detail="tenant not allowed")

    return AuthenticatedContext(user_id=user_id, tenant_id=tenant_id, roles=roles)


class WebhookVerifier:
    """Verifies webhook signatures with support for zero-downtime secret rotation.

    During secret rotation, accepts both current and previous secret for a grace period.
    This allows customers to rotate their secret without service interruption.
    """

    def __init__(self, current_secret: str, previous_secret: str | None = None):
        self.current_secret = current_secret
        self.previous_secret = previous_secret

    def verify(self, signature: str, body: bytes) -> bool:
        """Verify signature against current or previous secret.

        Returns True if signature matches either the current or previous secret.
        This enables zero-downtime rotation: customer can rotate their key while
        we accept both old and new signatures.
        """
        # Compute expected signature with current secret
        expected_current = self._compute_signature(body, self.current_secret)

        # Compute expected signature with previous secret (if rotation in progress)
        expected_previous = None
        if self.previous_secret:
            expected_previous = self._compute_signature(body, self.previous_secret)

        # Accept signature if it matches current secret
        if hmac.compare_digest(signature, expected_current):
            return True

        # Accept signature if it matches previous secret (during rotation grace period)
        if expected_previous and hmac.compare_digest(signature, expected_previous):
            logger.info(
                "webhook_signature_verified_with_previous_secret",
                extra={"rotation_in_progress": True}
            )
            return True

        return False

    @staticmethod
    def _compute_signature(body: bytes, secret: str) -> str:
        """Compute HMAC-SHA256 signature."""
        digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        return f"sha256={digest}"


async def verify_webhook_signature(request: Request) -> None:
    provided = request.headers.get("x-signature", "").strip()
    if not provided.startswith("sha256="):
        logger.warning(
            "webhook_signature_invalid_format",
            extra={"path": request.url.path}
        )
        raise HTTPException(status_code=401, detail="invalid webhook signature")

    raw_body = await request.body()
    config = getattr(request.app.state, "config", None)
    current_secret = getattr(config, "webhook_signing_secret", "")
    previous_secret = getattr(config, "webhook_signing_secret_previous", None)

    verifier = WebhookVerifier(current_secret=current_secret, previous_secret=previous_secret)
    if not verifier.verify(provided, raw_body):
        logger.warning(
            "webhook_signature_mismatch",
            extra={"path": request.url.path}
        )
        raise HTTPException(status_code=401, detail="invalid webhook signature")


async def require_runtime_host_auth(request: Request) -> None:
    configured = getattr(getattr(request.app.state, "config", None), "runtime_host_shared_token", "").strip()
    if not configured:
        logger.warning("runtime_host_token_not_configured", extra={"path": request.url.path})
        raise HTTPException(status_code=503, detail="runtime host token not configured")
    provided = request.headers.get("x-runtime-host-token", "").strip()
    if not provided or not hmac.compare_digest(provided, configured):
        logger.warning(
            "runtime_host_auth_failed",
            extra={"path": request.url.path, "has_token": bool(provided)}
        )
        raise HTTPException(status_code=401, detail="invalid runtime host token")
