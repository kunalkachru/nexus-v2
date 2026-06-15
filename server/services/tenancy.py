from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import HTTPException, Request
from pydantic import BaseModel


class TenantBootstrapConfig(BaseModel):
    tenant_id: str
    owners: dict[str, Any] = {}
    repos: dict[str, Any] = {}
    delivery_targets: dict[str, Any] = {}
    approval_policy: dict[str, Any] = {}
    enabled_packs: list[str] = []
    completed_at: str | None = None
    last_updated_at: str | None = None


class TenancyService:
    def __init__(self, config_dir: str = "artifacts"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        self.bootstrap_path = self.config_dir / "tenant_bootstrap.json"

    def resolve_webhook_tenant(self, request: Request) -> str:
        tenant_id = request.headers.get("x-tenant-id", "").strip()
        if not tenant_id:
            raise HTTPException(status_code=403, detail="tenant required")
        allowed_tenants = getattr(getattr(request.app.state, "config", None), "allowed_tenant_ids", ["tenant-a", "tenant-system"])
        if tenant_id not in allowed_tenants:
            raise HTTPException(status_code=403, detail="tenant not allowed")
        return tenant_id

    def _load_bootstrap_configs(self) -> dict[str, dict[str, Any]]:
        if not self.bootstrap_path.exists():
            return {}
        try:
            with open(self.bootstrap_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def _save_bootstrap_configs(self, configs: dict[str, dict[str, Any]]) -> None:
        with open(self.bootstrap_path, "w") as f:
            json.dump(configs, f, indent=2)

    def get_bootstrap_status(self, tenant_id: str) -> dict[str, Any]:
        from server.services.replica_runtime import runtime_host_supported_packs

        configs = self._load_bootstrap_configs()
        config = configs.get(tenant_id, {})

        # Build outage family coverage based on enabled packs
        enabled_packs = config.get("enabled_packs", [])
        all_packs = runtime_host_supported_packs()
        enabled_pack_set = set(enabled_packs) if isinstance(enabled_packs, list) else set()

        # Map incident classes to human-readable family names
        incident_family_map = {
            "timeout_retry_amplification": "INC001: Timeout/Retry Amplification",
            "checkout_timeout_cascade": "INC001: Timeout/Retry Amplification",
            "db_pool_exhaustion": "INC002: DB Pool Exhaustion",
            "session_leak": "INC002: DB Pool Exhaustion",
            "deploy_regression": "INC003: Deploy Regression / 5xx Spike",
            "query_null_pointer": "INC003: Deploy Regression / 5xx Spike",
            "auth_dependency_slowdown": "INC007: Auth Dependency Slowdown / Token Validation Failures",
            "token_validation_failures": "INC007: Auth Dependency Slowdown / Token Validation Failures",
            "queue_worker_backlog": "INC005: Queue / Worker Backlog",
            "worker_stall": "INC005: Queue / Worker Backlog",
        }

        supported_families = set()
        pack_coverage = {}
        for pack in all_packs:
            if pack.get("pack_id") in enabled_pack_set:
                pack_id = pack.get("pack_id")
                classes = pack.get("incident_classes", [])
                pack_coverage[pack_id] = {
                    "incident_classes": classes,
                    "stack": pack.get("stack", []),
                }
                for cls in classes:
                    if cls in incident_family_map:
                        supported_families.add(incident_family_map[cls])

        return {
            "tenant_id": tenant_id,
            "owners_configured": bool(config.get("owners")),
            "repos_configured": bool(config.get("repos")),
            "delivery_targets_configured": bool(config.get("delivery_targets")),
            "approval_policy_configured": bool(config.get("approval_policy")),
            "enabled_packs_configured": bool(config.get("enabled_packs")),
            "is_ready": all([
                config.get("owners"),
                config.get("repos"),
                config.get("delivery_targets"),
                config.get("approval_policy"),
                config.get("enabled_packs"),
            ]),
            "missing_fields": [
                field for field in ["owners", "repos", "delivery_targets", "approval_policy", "enabled_packs"]
                if not config.get(field)
            ],
            "supported_outage_families": sorted(list(supported_families)),
            "pack_coverage": pack_coverage,
            "last_updated_at": config.get("last_updated_at"),
        }

    def get_bootstrap_config(self, tenant_id: str) -> dict[str, Any]:
        configs = self._load_bootstrap_configs()
        config = configs.get(tenant_id, {})
        # Note: This endpoint returns unmasked configuration.
        # Admins should NOT store production secrets in bootstrap config.
        # Use environment variables for sensitive credentials instead.
        return config

    def update_bootstrap_config(self, tenant_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        from datetime import datetime, timezone

        configs = self._load_bootstrap_configs()
        current = configs.get(tenant_id, {})
        current.update(updates)
        current["tenant_id"] = tenant_id
        current["last_updated_at"] = datetime.now(timezone.utc).isoformat()
        configs[tenant_id] = current
        self._save_bootstrap_configs(configs)
        return current

    def get_incident_support_state(
        self,
        tenant_id: str,
        issue_family: str,
    ) -> dict[str, Any]:
        from server.services.replica_runtime import runtime_host_supported_packs

        configs = self._load_bootstrap_configs()
        config = configs.get(tenant_id, {})
        enabled_packs = config.get("enabled_packs", [])
        enabled_pack_set = set(enabled_packs) if isinstance(enabled_packs, list) else set()

        # Map issue families to incident classes
        family_to_classes = {
            "Timeout cascade / retry amplification": ["timeout_retry_amplification", "checkout_timeout_cascade"],
            "Database pool exhaustion / session leak": ["db_pool_exhaustion", "session_leak"],
            "Deploy regression / 5xx spike": ["deploy_regression", "query_null_pointer"],
            "Auth dependency slowdown / token validation failures": ["auth_dependency_slowdown", "token_validation_failures"],
            "Queue / worker backlog affecting transaction completion": ["queue_worker_backlog", "worker_stall"],
            "Certificate expiry / trust boundary outage": [],
            "Memory leak / runtime degradation": [],
            "Production incident investigation": [],
        }

        incident_classes = family_to_classes.get(issue_family, [])

        # Check if tenant has a pack that supports this incident
        all_packs = runtime_host_supported_packs()
        pack_supports_incident = False
        supporting_packs = []

        for pack in all_packs:
            pack_id = pack.get("pack_id")
            pack_classes = pack.get("incident_classes", [])

            # Check if this pack supports the incident
            has_match = any(ic in pack_classes for ic in incident_classes)
            if has_match:
                if pack_id in enabled_pack_set:
                    pack_supports_incident = True
                    supporting_packs.append(pack_id)

        if pack_supports_incident:
            support_state = "runtime-backed"
        elif incident_classes:  # Has known incident classes but no enabled pack
            support_state = "inference-first"
        else:  # Unknown incident family
            support_state = "unsupported"

        status = self.get_bootstrap_status(tenant_id)
        return {
            "support_state": support_state,
            "issue_family": issue_family,
            "tenant_id": tenant_id,
            "supported_packs": supporting_packs,
            "all_supported_families": status.get("supported_outage_families", []),
            "downgrade_guidance": self._downgrade_guidance_for_state(support_state, issue_family),
        }

    def _downgrade_guidance_for_state(self, support_state: str, issue_family: str) -> str:
        if support_state == "runtime-backed":
            return "This incident is fully supported with runtime-backed reproduction and validation."
        elif support_state == "inference-first":
            return (
                f"This incident family ('{issue_family}') can be triaged with inference, "
                "but runtime-backed validation is not yet available. "
                "Contact your administrator to enable the required runtime pack for full support."
            )
        else:
            return (
                f"This incident family ('{issue_family}') is not yet supported by NEXUS. "
                "NEXUS will provide triage guidance based on inference only. "
                "For production incidents outside the supported wedge, rely on your team's established runbooks. "
                "Contact your administrator or the NEXUS team to discuss adding support for this incident family."
            )
