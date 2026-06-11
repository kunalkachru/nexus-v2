from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from urllib.request import Request as UrlRequest, urlopen

from server.models import RuntimeHostReplayRequest, RuntimeHostReplayResponse


DEFAULT_REPLICA_PACKS_ROOT = Path(__file__).resolve().parents[2] / "replica_packs"


def replica_packs_root() -> Path:
    override = os.getenv("NEXUS_REPLICA_PACKS_ROOT", "").strip()
    return Path(override) if override else DEFAULT_REPLICA_PACKS_ROOT


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
    docker_available: bool = True
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
    packs_root = replica_packs_root()
    return {
        "checkout-python-fastapi-auth-redis-v1": ReplicaEnvironmentPack(
            pack_id="checkout-python-fastapi-auth-redis-v1",
            incident_classes=("timeout_retry_amplification", "checkout_timeout_cascade"),
            services=("api-gateway", "auth-svc", "checkout-api"),
            stack=("python", "fastapi", "redis"),
            compose_file=packs_root / "checkout-python-fastapi-auth-redis-v1" / "docker-compose.yml",
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
            compose_file=packs_root / "checkout-python-fastapi-postgres-v1" / "docker-compose.yml",
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

        docker_available = self._compose_base_command() is not None
        compose_config_valid = False
        services_seen: tuple[str, ...] = ()
        if plan.pack.compose_file.exists() and docker_available:
            compose_config_valid, services_seen = self._compose_config(plan)

        return ReplicaExecutionResult(
            pack_id=plan.pack.pack_id,
            compose_ready=plan.pack.compose_file.exists(),
            replay_ready=replay_script.exists(),
            mitigation_hooks_ready=all((hooks_root / f"{hook_name}.sh").exists() for hook_name in plan.mitigation_sequence),
            missing_assets=tuple(missing_assets),
            docker_available=docker_available,
            compose_config_valid=compose_config_valid,
            services_seen=services_seen,
        )

    def execute_scaffold(self, plan: ReplicaExecutionPlan, *, mitigation_limit: int | None = None) -> ReplicaExecutionResult:
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
            selected_hooks = plan.mitigation_sequence if mitigation_limit is None else plan.mitigation_sequence[:mitigation_limit]
            for hook_name in selected_hooks:
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
            docker_available=inspected.docker_available,
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
        compose_base = self._compose_base_command()
        if compose_base is None:
            return False, ()
        try:
            result = subprocess.run(
                [*compose_base, "-f", str(plan.pack.compose_file), "config", "--format", "json"],
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
        compose_base = self._compose_base_command()
        if compose_base is None:
            raise FileNotFoundError("docker compose is unavailable")
        subprocess.run(
            [*compose_base, "-f", str(plan.pack.compose_file), "down", "-v", "--remove-orphans"],
            cwd=str(plan.pack.compose_file.parent),
            capture_output=True,
            text=True,
            check=False,
        )
        subprocess.run(
            [*compose_base, "-f", str(plan.pack.compose_file), "up", "-d"],
            cwd=str(plan.pack.compose_file.parent),
            capture_output=True,
            text=True,
            check=True,
        )

    def _compose_down(self, plan: ReplicaExecutionPlan) -> None:
        compose_base = self._compose_base_command()
        if compose_base is None:
            return
        subprocess.run(
            [*compose_base, "-f", str(plan.pack.compose_file), "down", "-v"],
            cwd=str(plan.pack.compose_file.parent),
            capture_output=True,
            text=True,
            check=False,
        )

    def _run_script(self, script_path: Path) -> str:
        env = os.environ.copy()
        env.setdefault("NEXUS_RUNTIME_HTTP_HOST", self._runtime_http_host())
        result = subprocess.run(
            ["bash", str(script_path)],
            cwd=str(script_path.parent.parent),
            capture_output=True,
            text=True,
            check=True,
            env=env,
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
        runtime_host = self._runtime_http_host()
        if plan.pack.pack_id == "checkout-python-fastapi-auth-redis-v1":
            health_urls = [
                f"http://{runtime_host}:18080/health",
                f"http://{runtime_host}:18081/health",
            ]
        elif plan.pack.pack_id == "checkout-python-fastapi-postgres-v1":
            health_urls = [f"http://{runtime_host}:19080/health"]
        deadline = time.time() + plan.startup_timeout_seconds
        while time.time() < deadline:
            try:
                if all(urlopen(url, timeout=1).status == 200 for url in health_urls):
                    return
            except Exception:
                time.sleep(0.5)
                continue
        raise RuntimeError(f"Timed out waiting for runtime health for {plan.pack.pack_id}")

    def _compose_base_command(self) -> list[str] | None:
        if shutil.which("docker") is not None:
            try:
                result = subprocess.run(
                    ["docker", "compose", "version"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
            except FileNotFoundError:
                result = None
            if result is not None and result.returncode == 0:
                return ["docker", "compose"]
        if shutil.which("docker-compose") is not None:
            return ["docker-compose"]
        return None

    def _runtime_http_host(self) -> str:
        return os.getenv("NEXUS_RUNTIME_HTTP_HOST", "127.0.0.1").strip() or "127.0.0.1"


def build_runtime_host_relay_status(config: object | None) -> dict[str, object]:
    base_url = str(getattr(config, "runtime_host_base_url", "") or "").strip()
    token = str(getattr(config, "runtime_host_shared_token", "") or "").strip()
    configured = bool(base_url and token)
    return {
        "configured": configured,
        "base_url": base_url,
        "auth_configured": bool(token),
        "mode": "external_relay" if configured else "not_configured",
        "message": (
            "A runtime-host relay is configured for packaged replay delegation."
            if configured
            else "No external runtime-host relay is configured for packaged replay delegation yet."
        ),
    }


def _runtime_capability_for_host(
    *,
    plan: ReplicaExecutionPlan | None,
    inspected: ReplicaExecutionResult | None,
    executed: ReplicaExecutionResult | None,
) -> dict[str, object]:
    bounded_pack_available = bool(plan and inspected and not inspected.missing_assets)
    docker_available = bool(inspected.docker_available) if inspected else False
    compose_config_valid = bool(inspected.compose_config_valid) if inspected else False

    if executed and executed.replay_status_code is not None:
        return {
            "state": "replay_executed",
            "label": "Replay executed",
            "host_label": "Runtime host",
            "can_execute_replay": True,
            "bounded_pack_available": bounded_pack_available,
            "docker_available": docker_available,
            "compose_config_valid": compose_config_valid,
            "message": "The runtime host executed Docker-backed replay for the bounded runtime pack.",
        }
    if bounded_pack_available and docker_available and compose_config_valid:
        return {
            "state": "replay_available",
            "label": "Replay available",
            "host_label": "Runtime host",
            "can_execute_replay": True,
            "bounded_pack_available": True,
            "docker_available": True,
            "compose_config_valid": True,
            "message": "The runtime host can execute Docker-backed replay for the bounded runtime pack.",
        }
    if bounded_pack_available and not docker_available:
        return {
            "state": "host_unavailable",
            "label": "Host unavailable",
            "host_label": "Runtime host",
            "can_execute_replay": False,
            "bounded_pack_available": True,
            "docker_available": False,
            "compose_config_valid": False,
            "message": "The bounded runtime pack exists, but this runtime host cannot execute Docker-backed replay.",
        }
    if bounded_pack_available:
        return {
            "state": "pack_validation_required",
            "label": "Pack validation required",
            "host_label": "Runtime host",
            "can_execute_replay": False,
            "bounded_pack_available": True,
            "docker_available": docker_available,
            "compose_config_valid": False,
            "message": "A bounded runtime pack exists, but the compose contract still needs validation on the runtime host.",
        }
    return {
        "state": "no_pack",
        "label": "No bounded pack",
        "host_label": "Runtime host",
        "can_execute_replay": False,
        "bounded_pack_available": False,
        "docker_available": docker_available,
        "compose_config_valid": False,
        "message": "No bounded runtime pack matches this incident class on the runtime host.",
    }


def execute_runtime_host_replay(payload: RuntimeHostReplayRequest) -> RuntimeHostReplayResponse:
    plan = build_execution_plan(
        issue_family=payload.issue_family,
        service=payload.service,
        recent_logs=payload.recent_logs,
        recent_deployments=payload.recent_deployments,
    )
    if plan is None:
        capability = _runtime_capability_for_host(plan=None, inspected=None, executed=None)
        return RuntimeHostReplayResponse(
            status="unsupported",
            message=capability["message"],
            runtime_capability=capability,
            execution_plan={},
            execution_result={},
        )

    runner = ReplicaRunner()
    inspected = runner.inspect_plan(plan)
    executed = (
        runner.execute_scaffold(plan, mitigation_limit=payload.mitigation_limit)
        if payload.execute_runtime and inspected.compose_config_valid and not inspected.missing_assets and inspected.docker_available
        else None
    )
    capability = _runtime_capability_for_host(plan=plan, inspected=inspected, executed=executed)
    status = {
        "replay_executed": "replay_executed",
        "replay_available": "replay_available",
        "host_unavailable": "host_unavailable",
        "pack_validation_required": "pack_validation_required",
        "no_pack": "unsupported",
    }.get(str(capability.get("state") or "no_pack"), "unsupported")
    return RuntimeHostReplayResponse(
        status=status,
        message=str(capability.get("message") or "Runtime host replay state unavailable."),
        runtime_capability=capability,
        execution_plan={
            "pack_id": plan.pack.pack_id,
            "incident_class": plan.incident_class,
            "healthcheck_targets": list(plan.healthcheck_targets),
            "replay_entrypoint": plan.replay_entrypoint,
            "mitigation_sequence": list(plan.mitigation_sequence),
        },
        execution_result=asdict(executed or inspected),
    )


def invoke_runtime_host_relay(
    *,
    base_url: str,
    shared_token: str,
    payload: dict[str, object],
) -> dict[str, object]:
    request = UrlRequest(
        url=f"{base_url.rstrip('/')}/api/v1/internal/runtime-host/replica-replay",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "content-type": "application/json",
            "x-runtime-host-token": shared_token,
        },
        method="POST",
    )
    with urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))
