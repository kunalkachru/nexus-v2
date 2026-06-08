from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


REPLICA_PACKS_ROOT = Path(__file__).resolve().parents[2] / "replica_packs"


@dataclass(frozen=True)
class ReplicaEnvironmentPack:
    pack_id: str
    incident_classes: tuple[str, ...]
    services: tuple[str, ...]
    stack: tuple[str, ...]
    compose_file: Path
    replay_profile: str
    mitigation_hooks: tuple[str, ...]
    trace_source_map: dict[str, tuple[str, ...]] = field(default_factory=dict)


@dataclass(frozen=True)
class ReplicaExecutionPlan:
    pack: ReplicaEnvironmentPack
    incident_class: str
    startup_timeout_seconds: int
    healthcheck_targets: tuple[str, ...]
    replay_entrypoint: str
    mitigation_sequence: tuple[str, ...]
    teardown_policy: str = "always"


@dataclass(frozen=True)
class ReplicaExecutionResult:
    pack_id: str
    compose_ready: bool
    replay_ready: bool
    mitigation_hooks_ready: bool
    missing_assets: tuple[str, ...]
    mode: str = "scaffold"


def registry() -> dict[str, ReplicaEnvironmentPack]:
    return {
        "checkout-python-fastapi-auth-redis-v1": ReplicaEnvironmentPack(
            pack_id="checkout-python-fastapi-auth-redis-v1",
            incident_classes=("timeout_retry_amplification", "checkout_timeout_cascade"),
            services=("api-gateway", "auth-svc", "checkout-api"),
            stack=("python", "fastapi", "redis"),
            compose_file=REPLICA_PACKS_ROOT / "checkout-python-fastapi-auth-redis-v1" / "docker-compose.yml",
            replay_profile="checkout_retry_replay_v1",
            mitigation_hooks=("cap_retries", "open_circuit_breaker", "disable_retry_middleware"),
            trace_source_map={
                "auth.middleware.retry": ("apply_retry_policy",),
                "gateway.timeout_guard": ("await_upstream_auth",),
                "auth.circuit_breaker": ("record_timeout_budget",),
            },
        ),
        "checkout-python-fastapi-postgres-v1": ReplicaEnvironmentPack(
            pack_id="checkout-python-fastapi-postgres-v1",
            incident_classes=("db_pool_exhaustion", "session_leak"),
            services=("checkout-svc", "postgres-orders"),
            stack=("python", "fastapi", "postgres"),
            compose_file=REPLICA_PACKS_ROOT / "checkout-python-fastapi-postgres-v1" / "docker-compose.yml",
            replay_profile="checkout_write_replay_v1",
            mitigation_hooks=("terminate_orphaned_sessions", "rollback_retry_patch", "restart_checkout_service"),
            trace_source_map={
                "checkout.db.session": ("checkout_session_scope",),
                "checkout.retry_patch": ("retry_checkout_write",),
                "checkout.transaction_flow": ("release_db_session",),
            },
        ),
    }


def select_environment_pack(
    *,
    issue_family: str,
    service: str,
    recent_logs: list[object] | None = None,
    recent_deployments: list[object] | None = None,
) -> ReplicaEnvironmentPack | None:
    issue_family_text = issue_family.lower()
    text = " ".join(
        [
            issue_family_text,
            service.lower(),
            " ".join(str(item).lower() for item in (recent_logs or [])),
            " ".join(str(item).lower() for item in (recent_deployments or [])),
        ]
    )
    packs = registry()
    if any(token in issue_family_text for token in ("pool exhaustion", "session leak", "database")) or any(
        token in text for token in ("queuepool", "pool exhaustion", "session leak", "max_connections", "leaked session")
    ):
        return packs["checkout-python-fastapi-postgres-v1"]
    if any(token in text for token in ("retry", "timeout", "worker saturation", "circuit breaker")):
        return packs["checkout-python-fastapi-auth-redis-v1"]
    return None


def build_execution_plan(
    *,
    issue_family: str,
    service: str,
    recent_logs: list[object] | None = None,
    recent_deployments: list[object] | None = None,
) -> ReplicaExecutionPlan | None:
    pack = select_environment_pack(
        issue_family=issue_family,
        service=service,
        recent_logs=recent_logs,
        recent_deployments=recent_deployments,
    )
    if pack is None:
        return None
    if pack.pack_id == "checkout-python-fastapi-auth-redis-v1":
        return ReplicaExecutionPlan(
            pack=pack,
            incident_class="timeout_retry_amplification",
            startup_timeout_seconds=45,
            healthcheck_targets=("gateway", "auth", "redis"),
            replay_entrypoint="scripts/replay_checkout_retry.sh",
            mitigation_sequence=pack.mitigation_hooks,
        )
    return ReplicaExecutionPlan(
        pack=pack,
        incident_class="db_pool_exhaustion",
        startup_timeout_seconds=45,
        healthcheck_targets=("checkout", "postgres"),
        replay_entrypoint="scripts/replay_checkout_pool.sh",
        mitigation_sequence=pack.mitigation_hooks,
    )


def trace_targets_for_plan(plan: ReplicaExecutionPlan | None) -> list[tuple[str, str]]:
    if plan is None:
        return []
    pairs: list[tuple[str, str]] = []
    for module_name, functions in plan.pack.trace_source_map.items():
        primary_function = functions[0] if functions else ""
        pairs.append((module_name, primary_function))
    return pairs


class ReplicaRunner:
    """Bounded execution contract for curated reproduction packs.

    This does not yet run Docker Compose. It verifies that the pack has enough
    on-disk structure for the next runtime slice to launch it safely.
    """

    def inspect_plan(self, plan: ReplicaExecutionPlan) -> ReplicaExecutionResult:
        pack_root = plan.pack.compose_file.parent
        replay_script = pack_root / plan.replay_entrypoint
        hooks_root = pack_root / "hooks"
        missing_assets: list[str] = []

        if not plan.pack.compose_file.exists():
            missing_assets.append(str(plan.pack.compose_file))
        if not replay_script.exists():
            missing_assets.append(str(replay_script))
        for hook_name in plan.mitigation_sequence:
            hook_path = hooks_root / f"{hook_name}.sh"
            if not hook_path.exists():
                missing_assets.append(str(hook_path))

        return ReplicaExecutionResult(
            pack_id=plan.pack.pack_id,
            compose_ready=plan.pack.compose_file.exists(),
            replay_ready=replay_script.exists(),
            mitigation_hooks_ready=all((hooks_root / f"{hook_name}.sh").exists() for hook_name in plan.mitigation_sequence),
            missing_assets=tuple(missing_assets),
        )
