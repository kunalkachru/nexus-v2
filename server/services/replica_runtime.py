from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.request import urlopen


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
    compose_config_valid: bool = False
    services_seen: tuple[str, ...] = ()
    replay_output: str = ""
    replay_status_code: int | None = None
    replay_duration_ms: int | None = None
    mitigation_outputs: tuple[str, ...] = ()
    mitigation_status_codes: tuple[int | None, ...] = ()
    mitigation_duration_ms: tuple[int | None, ...] = ()
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

    This runner is intentionally bounded to curated packs. It can validate the
    compose file, boot the pack, run the replay hook, optionally run mitigation
    hooks, and tear everything down again.
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

        compose_config_valid = False
        services_seen: tuple[str, ...] = ()
        if plan.pack.compose_file.exists():
            compose_config_valid, services_seen = self._compose_config(plan)

        return ReplicaExecutionResult(
            pack_id=plan.pack.pack_id,
            compose_ready=plan.pack.compose_file.exists(),
            replay_ready=replay_script.exists(),
            mitigation_hooks_ready=all((hooks_root / f"{hook_name}.sh").exists() for hook_name in plan.mitigation_sequence),
            missing_assets=tuple(missing_assets),
            compose_config_valid=compose_config_valid,
            services_seen=services_seen,
        )

    def execute_scaffold(self, plan: ReplicaExecutionPlan, *, mitigation_limit: int = 1) -> ReplicaExecutionResult:
        inspected = self.inspect_plan(plan)
        if inspected.missing_assets or not inspected.compose_config_valid:
            return inspected

        replay_output = ""
        replay_status_code: int | None = None
        replay_duration_ms: int | None = None
        mitigation_outputs: list[str] = []
        mitigation_status_codes: list[int | None] = []
        mitigation_duration_ms: list[int | None] = []
        try:
            self._reset_runtime_state(plan)
            self._compose_up(plan)
            self._wait_for_runtime(plan)
            replay_output = self._run_script(plan.pack.compose_file.parent / plan.replay_entrypoint)
            replay_status_code, replay_duration_ms = self._extract_replay_signal(replay_output)
            hooks_root = plan.pack.compose_file.parent / "hooks"
            for hook_name in plan.mitigation_sequence[:mitigation_limit]:
                mitigation_outputs.append(self._run_script(hooks_root / f"{hook_name}.sh"))
                rerun_output = self._run_script(plan.pack.compose_file.parent / plan.replay_entrypoint)
                mitigation_outputs.append(rerun_output)
                rerun_status_code, rerun_duration = self._extract_replay_signal(rerun_output)
                mitigation_status_codes.append(rerun_status_code)
                mitigation_duration_ms.append(rerun_duration)
        finally:
            self._compose_down(plan)

        return ReplicaExecutionResult(
            pack_id=inspected.pack_id,
            compose_ready=inspected.compose_ready,
            replay_ready=inspected.replay_ready,
            mitigation_hooks_ready=inspected.mitigation_hooks_ready,
            missing_assets=inspected.missing_assets,
            compose_config_valid=inspected.compose_config_valid,
            services_seen=inspected.services_seen,
            replay_output=replay_output.strip(),
            replay_status_code=replay_status_code,
            replay_duration_ms=replay_duration_ms,
            mitigation_outputs=tuple(output.strip() for output in mitigation_outputs),
            mitigation_status_codes=tuple(mitigation_status_codes),
            mitigation_duration_ms=tuple(mitigation_duration_ms),
            mode="runtime_scaffold",
        )

    def _compose_config(self, plan: ReplicaExecutionPlan) -> tuple[bool, tuple[str, ...]]:
        try:
            result = subprocess.run(
                ["docker", "compose", "-f", str(plan.pack.compose_file), "config", "--format", "json"],
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError:
            return False, ()
        if result.returncode != 0:
            return False, ()
        try:
            payload = json.loads(result.stdout or "{}")
        except json.JSONDecodeError:
            return False, ()
        services = tuple(sorted((payload.get("services") or {}).keys()))
        return True, services

    def _compose_up(self, plan: ReplicaExecutionPlan) -> None:
        subprocess.run(
            ["docker", "compose", "-f", str(plan.pack.compose_file), "down", "-v", "--remove-orphans"],
            cwd=str(plan.pack.compose_file.parent),
            capture_output=True,
            text=True,
            check=False,
        )
        subprocess.run(
            ["docker", "compose", "-f", str(plan.pack.compose_file), "up", "-d"],
            cwd=str(plan.pack.compose_file.parent),
            capture_output=True,
            text=True,
            check=True,
        )

    def _compose_down(self, plan: ReplicaExecutionPlan) -> None:
        subprocess.run(
            ["docker", "compose", "-f", str(plan.pack.compose_file), "down", "-v"],
            cwd=str(plan.pack.compose_file.parent),
            capture_output=True,
            text=True,
            check=False,
        )

    def _run_script(self, script_path: Path) -> str:
        result = subprocess.run(
            ["bash", str(script_path)],
            cwd=str(script_path.parent.parent),
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout

    def _extract_replay_signal(self, output: str) -> tuple[int | None, int | None]:
        for line in output.splitlines():
            line = line.strip()
            if not line or not line.startswith("{"):
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            status = payload.get("status_code")
            duration = payload.get("duration_ms")
            return (int(status) if isinstance(status, (int, float)) else None, int(duration) if isinstance(duration, (int, float)) else None)
        return None, None

    def _reset_runtime_state(self, plan: ReplicaExecutionPlan) -> None:
        runtime_dir = plan.pack.compose_file.parent / "runtime"
        runtime_dir.mkdir(exist_ok=True)
        defaults: dict[str, str] = {}
        if plan.pack.pack_id == "checkout-python-fastapi-auth-redis-v1":
            defaults = {
                "auth_delay_ms.txt": "1200\n",
                "auth_timeout_ms.txt": "400\n",
                "retries.txt": "4\n",
                "retry_middleware_enabled.txt": "1\n",
                "circuit_breaker.txt": "closed\n",
            }
        elif plan.pack.pack_id == "checkout-python-fastapi-postgres-v1":
            defaults = {
                "pool_limit.txt": "500\n",
                "session_leak_enabled.txt": "1\n",
                "pool_exhausted.txt": "1\n",
            }
        for name, value in defaults.items():
            (runtime_dir / name).write_text(value)

    def _wait_for_runtime(self, plan: ReplicaExecutionPlan) -> None:
        health_urls: list[str] = []
        if plan.pack.pack_id == "checkout-python-fastapi-auth-redis-v1":
            health_urls = ["http://127.0.0.1:18080/health", "http://127.0.0.1:18081/health"]
        elif plan.pack.pack_id == "checkout-python-fastapi-postgres-v1":
            health_urls = ["http://127.0.0.1:19080/health"]
        deadline = time.time() + plan.startup_timeout_seconds
        while time.time() < deadline:
            try:
                if all(urlopen(url, timeout=1).status == 200 for url in health_urls):
                    return
            except Exception:
                time.sleep(0.5)
                continue
        raise RuntimeError(f"Timed out waiting for runtime health for {plan.pack.pack_id}")
