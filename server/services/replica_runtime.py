from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request as UrlRequest, urlopen

from server.models import RuntimeHostReplayRequest, RuntimeHostReplayResponse


DEFAULT_REPLICA_PACKS_ROOT = Path(__file__).resolve().parents[2] / "replica_packs"


class EvidencePosture:
    """Shared evidence-posture vocabulary across seeded/live/exports/UI.

    Evidence tiers define the level of validation backing a claim:
    - validated_runtime: replay executed and produced measurable signals
    - runtime_ready: replay available but not executed
    - inferred_only: scaffold-only inference, no runtime backing
    - bounded_debugger: debugger packet produced for specific pack
    """

    VALIDATED_RUNTIME = "validated_runtime"
    RUNTIME_READY = "runtime_ready"
    INFERRED_ONLY = "inferred_only"
    BOUNDED_DEBUGGER = "bounded_debugger"

    @staticmethod
    def validated_clause(
        *,
        runtime_executed: bool,
        best_outcome_class: str | None = None,
        replay_status_code: int | None = None,
    ) -> str:
        """Build a consistent validated/inferred clause for all surfaces."""
        if not runtime_executed:
            return "Current signals are inferred-only: no bounded runtime replay has executed."

        outcome = str(best_outcome_class or "").replace("_", " ").strip() or "analyzed"
        if outcome == "resolved":
            return "Validated runtime signals: bounded REPLICA reproduced the failure and the proposed mitigation resolved it."
        elif outcome == "improved":
            return "Validated runtime signals: bounded REPLICA reproduced the failure and the proposed mitigation improved it without fully resolving."
        else:
            return f"Validated runtime signals: bounded REPLICA reproduced the failure with HTTP {replay_status_code or 'unknown'} but tested mitigations did not resolve."

    @staticmethod
    def evidence_tier_for_context(
        *,
        runtime_executed: bool,
        debugger_available: bool = False,
    ) -> str:
        """Determine the evidence tier for a context."""
        if debugger_available:
            return EvidencePosture.BOUNDED_DEBUGGER
        if runtime_executed:
            return EvidencePosture.VALIDATED_RUNTIME
        return EvidencePosture.INFERRED_ONLY


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
    hypothesis_summary: str = ""
    expected_baseline_status: int | None = None
    triggering_conditions: tuple[str, ...] = field(default_factory=tuple)
    expected_failure_signature: tuple[str, ...] = field(default_factory=tuple)
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
    reconciliation: dict[str, str] = field(default_factory=dict)
    reset_confirmed: bool = False
    repeatability_status: str = "unknown"


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
            hypothesis_summary=(
                "Prove that checkout timeouts persist only when downstream auth latency stays elevated while the retry-heavy auth path remains enabled."
            ),
            expected_baseline_status=504,
            triggering_conditions=(
                "Downstream auth latency is held above the checkout timeout budget.",
                "Retry middleware remains enabled on the auth boundary.",
                "Gateway worker pressure stays high enough for retry amplification to cascade.",
            ),
            expected_failure_signature=(
                "Baseline replay returns HTTP 504 on the checkout path.",
                "Retry budget exceeded and upstream auth timeout anchors appear together.",
                "Runtime improves only when retries are capped or the retry-heavy middleware path is removed.",
            ),
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
            hypothesis_summary=(
                "Prove that the checkout retry patch leaks database sessions until the bounded pool is exhausted and checkout writes start failing."
            ),
            expected_baseline_status=503,
            triggering_conditions=(
                "The checkout retry patch stays active on the write path.",
                "The bounded Postgres pool is capped at the production threshold.",
                "Session cleanup does not complete after retry failure.",
            ),
            expected_failure_signature=(
                "Baseline replay returns HTTP 503 once the pool saturates.",
                "QueuePool or session-leak anchors appear before checkout writes recover.",
                "Runtime clears only after leaked sessions are terminated or the retry patch is rolled back.",
            ),
            trace_source_map={
                "checkout.db.session": ("checkout_session_scope",),
                "checkout.retry_patch": ("retry_checkout_write",),
                "checkout.transaction_flow": ("release_db_session",),
            },
        ),
        "api-python-fastapi-catalog-v1": ReplicaEnvironmentPack(
            pack_id="api-python-fastapi-catalog-v1",
            incident_classes=("deploy_regression", "query_null_pointer"),
            services=("api-service", "catalog-db"),
            stack=("python", "fastapi", "postgres"),
            compose_file=packs_root / "api-python-fastapi-catalog-v1" / "docker-compose.yml",
            replay_profile="api_catalog_replay_v1",
            mitigation_hooks=("rollback_catalog_optimization", "deploy_null_check_hotfix"),
            hypothesis_summary=(
                "Prove that the catalog query optimization deployment introduces a null-pointer bug in the filter logic causing 5xx errors until the optimization is rolled back or the hotfix is deployed."
            ),
            expected_baseline_status=500,
            triggering_conditions=(
                "The catalog query optimization is enabled on the API service.",
                "Search queries hit the optimized filter path with the null-pointer regression.",
                "API returns 5xx errors until optimization is disabled or hotfixed.",
            ),
            expected_failure_signature=(
                "Baseline replay returns HTTP 500 due to null-pointer in query filter.",
                "Query optimization feature correlates with 5xx spike in logs.",
                "Runtime clears when optimization is rolled back or null-check hotfix is deployed.",
            ),
            trace_source_map={
                "api.catalog.query": ("_apply_optimized_filter",),
                "api.search.endpoint": ("search_products",),
                "api.filter.logic": ("_apply_optimized_filter",),
            },
        ),
    }


def runtime_host_supported_packs() -> list[dict[str, object]]:
    packs: list[dict[str, object]] = []
    for pack in registry().values():
        packs.append(
            {
                "pack_id": pack.pack_id,
                "incident_classes": list(pack.incident_classes),
                "services": list(pack.services),
                "stack": list(pack.stack),
            }
        )
    return packs


def validate_pack(pack: ReplicaEnvironmentPack) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []

    if not pack.pack_id or not isinstance(pack.pack_id, str):
        errors.append("pack_id: must be a non-empty string")

    if not pack.incident_classes or len(pack.incident_classes) == 0:
        errors.append("incident_classes: must contain at least one incident class")

    if not pack.services or len(pack.services) == 0:
        errors.append("services: must list at least one service in the pack")

    if not pack.stack or len(pack.stack) == 0:
        errors.append("stack: must specify the technology stack (e.g., python, fastapi, redis)")

    if not pack.compose_file:
        errors.append("compose_file: must be specified")
    elif not pack.compose_file.exists():
        errors.append(f"compose_file: file not found at {pack.compose_file}")

    if not pack.replay_profile or not isinstance(pack.replay_profile, str):
        errors.append("replay_profile: must be a non-empty string naming the replay hook")

    if not pack.mitigation_hooks or len(pack.mitigation_hooks) == 0:
        warnings.append("mitigation_hooks: should define at least one mitigation hook")

    if pack.compose_file and pack.compose_file.exists():
        hooks_dir = pack.compose_file.parent / "hooks"
        if pack.mitigation_hooks:
            for hook_name in pack.mitigation_hooks:
                hook_file = hooks_dir / f"{hook_name}.sh"
                if not hook_file.exists():
                    errors.append(f"mitigation_hook '{hook_name}': script not found at {hook_file}")

        replay_hook = pack.compose_file.parent / f"{pack.replay_profile}.sh"
        if not replay_hook.exists():
            errors.append(f"replay_profile '{pack.replay_profile}': script not found at {replay_hook}")

    if not pack.hypothesis_summary or not isinstance(pack.hypothesis_summary, str):
        warnings.append("hypothesis_summary: should contain a clear hypothesis for this pack")

    if pack.expected_baseline_status is None:
        warnings.append("expected_baseline_status: should specify the expected HTTP status for baseline failure")

    if not pack.trace_source_map or len(pack.trace_source_map) == 0:
        warnings.append("trace_source_map: should map code paths for TRACE debugging")

    is_valid = len(errors) == 0
    return {
        "pack_id": pack.pack_id,
        "is_valid": is_valid,
        "errors": errors,
        "warnings": warnings,
        "status": "ready" if is_valid and len(warnings) == 0 else ("valid_with_warnings" if is_valid else "invalid"),
    }


def validate_all_packs() -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for pack in registry().values():
        results.append(validate_pack(pack))
    return results


def probe_runtime_host(base_url: str) -> dict[str, object]:
    if not base_url:
        return {
            "reachable": False,
            "healthy": False,
            "health_status": "not_configured",
            "health_message": "No runtime host relay URL is configured.",
        }

    health_url = f"{base_url.rstrip('/')}/health"
    try:
        request = UrlRequest(health_url, method="GET")
        with urlopen(request, timeout=2) as response:
            healthy = response.status == 200
            return {
                "reachable": healthy,
                "healthy": healthy,
                "health_status": "healthy" if healthy else "unhealthy",
                "health_message": (
                    "The packaged app can reach the runtime host relay and its health check is passing."
                    if healthy
                    else "The runtime host relay responded, but it did not report a healthy status."
                ),
            }
    except URLError as error:
        reason = getattr(error, "reason", None)
        reason_text = str(reason or error).strip() or "connection failed"
    except Exception as error:  # pragma: no cover - defensive path for packaged networking differences
        reason_text = str(error).strip() or "connection failed"

    return {
        "reachable": False,
        "healthy": False,
        "health_status": "unreachable",
        "health_message": f"The packaged app cannot currently reach the runtime host relay: {reason_text}.",
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
    if any(token in issue_family_text for token in ("deploy regression", "5xx spike")) or any(
        token in text for token in ("api-service", "query optimization", "null pointer")
    ):
        return packs.get("api-python-fastapi-catalog-v1")
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
    if pack.pack_id == "api-python-fastapi-catalog-v1":
        return ReplicaExecutionPlan(
            pack=pack,
            incident_class="deploy_regression",
            startup_timeout_seconds=45,
            healthcheck_targets=("api", "catalog-db"),
            replay_entrypoint="scripts/api_catalog_replay_v1.sh",
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


def build_hypothesis_packet(
    *,
    plan: ReplicaExecutionPlan | None,
    issue_family: str,
    service: str,
    deployment_conditions: list[str] | None = None,
    tested_mitigations: list[dict[str, object]] | None = None,
    runtime_result: ReplicaExecutionResult | None = None,
) -> dict[str, object]:
    if plan is None:
        return {
            "supported": False,
            "summary": "No bounded REPLICA hypothesis packet is available for this incident class yet.",
            "scope": "unmapped_incident_class",
            "triggering_conditions": [],
            "expected_failure_signature": [],
            "mitigation_checkpoints": [],
            "mapping_basis": "",
            "validation_state": "not_supported",
        }

    deployment_conditions = [str(item).strip() for item in (deployment_conditions or []) if str(item).strip()]
    mitigation_checkpoints: list[dict[str, object]] = []
    for index, mitigation in enumerate(tested_mitigations or [], start=1):
        action = str(mitigation.get("action") or "").strip()
        if not action:
            continue
        mitigation_checkpoints.append(
            {
                "step": index,
                "action": action,
                "expected_signal": str(mitigation.get("result") or "").strip(),
                "outcome_class": str(mitigation.get("outcome_class") or "inferred_only"),
            }
        )

    expected_failure_signature = list(plan.pack.expected_failure_signature)
    if runtime_result and runtime_result.replay_status_code is not None:
        expected_failure_signature.insert(
            0,
            f"Validated baseline replay returned HTTP {runtime_result.replay_status_code} in {runtime_result.replay_duration_ms or 'unknown'}ms.",
        )
    elif plan.pack.expected_baseline_status is not None:
        expected_failure_signature.insert(
            0,
            f"Baseline replay is expected to return HTTP {plan.pack.expected_baseline_status} for the bounded failure path.",
        )

    mapping_basis_parts = [
        f"Issue family mapped to {plan.incident_class.replace('_', ' ')}.",
        f"Primary service boundary: {service or 'unknown service'}.",
    ]
    if issue_family:
        mapping_basis_parts.insert(0, f"Observed issue family: {issue_family}.")
    if deployment_conditions:
        mapping_basis_parts.append(f"Deployment clues carried into the hypothesis: {'; '.join(deployment_conditions)}.")

    return {
        "supported": True,
        "summary": plan.pack.hypothesis_summary,
        "scope": "curated_flagship_pack",
        "incident_class": plan.incident_class,
        "pack_id": plan.pack.pack_id,
        "service": service,
        "triggering_conditions": [*plan.pack.triggering_conditions, *deployment_conditions],
        "expected_failure_signature": expected_failure_signature,
        "mitigation_checkpoints": mitigation_checkpoints,
        "mapping_basis": " ".join(mapping_basis_parts),
        "validation_state": "executed" if runtime_result else "staged",
    }


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
            reset_confirmed=True,
            repeatability_status="deterministic" if replay_status_code is not None else "uncertain",
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
    health = probe_runtime_host(base_url) if configured else probe_runtime_host("")
    supported_packs = runtime_host_supported_packs()
    state = "healthy" if health["healthy"] else "configured" if configured else "not_configured"
    if configured and not health["reachable"]:
        state = "configured_unreachable"
    return {
        "configured": configured,
        "base_url": base_url,
        "auth_configured": bool(token),
        "reachable": bool(health["reachable"]),
        "healthy": bool(health["healthy"]),
        "state": state,
        "status_label": (
            "Healthy relay"
            if state == "healthy"
            else "Configured but unreachable"
            if state == "configured_unreachable"
            else "Configured relay"
            if state == "configured"
            else "Not configured"
        ),
        "mode": "external_relay" if configured else "not_configured",
        "health_status": str(health["health_status"]),
        "health_message": str(health["health_message"]),
        "supported_packs": supported_packs,
        "supported_pack_ids": [str(pack["pack_id"]) for pack in supported_packs],
        "supported_incident_classes": sorted(
            {
                incident_class
                for pack in supported_packs
                for incident_class in pack.get("incident_classes", [])
            }
        ),
        "pack_count": len(supported_packs),
        "message": (
            "A runtime-host relay is configured for packaged replay delegation and is reachable from the packaged app."
            if configured and health["healthy"]
            else "A runtime-host relay is configured for packaged replay delegation, but the packaged app cannot currently reach it."
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


def build_runtime_trust_packet(
    *,
    runtime_capability: dict[str, object],
    execution_result: ReplicaExecutionResult | None,
    execution_mode: str,
    pack_id: str = "",
) -> dict[str, object]:
    capability_state = str(runtime_capability.get("state") or "no_pack")
    host_label = str(runtime_capability.get("host_label") or "Runtime host")
    limiting_factor = {
        "host_unavailable": "docker_unavailable",
        "pack_validation_required": "pack_validation_required",
        "no_pack": "no_bounded_pack",
    }.get(capability_state, "")
    decision = (
        "executed"
        if capability_state in {"replay_executed", "relay_executed"}
        else "allowed"
        if capability_state in {"replay_available", "relay_available"}
        else "denied"
    )
    evidence_tier = (
        "validated_runtime"
        if decision == "executed"
        else "runtime_ready"
        if decision == "allowed"
        else "inferred_only"
    )
    status_code = execution_result.replay_status_code if execution_result else None
    duration_ms = execution_result.replay_duration_ms if execution_result else None

    reconciliation_source = (
        "runtime_host_relay" if execution_mode == "delegated_relay"
        else "packaged_app" if execution_mode == "direct_runtime"
        else "inferred_scaffold"
    )
    reconciliation_reason = {
        "replay_executed": "replay executed successfully on packaged app",
        "replay_available": "replay execution available but not executed on packaged app",
        "relay_executed": "replay delegated and executed on external runtime host",
        "relay_available": "replay delegation available but not executed on external runtime host",
        "host_unavailable": "external runtime host unavailable or unreachable",
        "pack_validation_required": "pack validation required on runtime host",
        "no_pack": "no bounded pack available for this incident class",
    }.get(capability_state, "unknown")

    repeatability_note = ""
    if execution_result:
        if execution_result.repeatability_status == "deterministic":
            repeatability_note = "Pack reset confirmed clean; replay is repeatable across consecutive runs."
        elif execution_result.repeatability_status == "uncertain":
            repeatability_note = "Pack state reset uncertain; results may be influenced by prior execution."

    return {
        "decision": decision,
        "execution_mode": execution_mode,
        "executor": host_label,
        "evidence_tier": evidence_tier,
        "pack_id": pack_id,
        "bounded_scope": "curated_flagship_packs_only",
        "limiting_factor": limiting_factor,
        "status_code": status_code,
        "duration_ms": duration_ms,
        "policy_basis": "Only curated bounded runtime packs can be replayed through the runtime host path.",
        "operator_summary": str(runtime_capability.get("message") or ""),
        "repeatability_status": execution_result.repeatability_status if execution_result else "unknown",
        "repeatability_note": repeatability_note,
        "reconciliation": {
            "source": reconciliation_source,
            "reason": reconciliation_reason,
            "timestamp": None,
        },
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
            trust_packet=build_runtime_trust_packet(
                runtime_capability=capability,
                execution_result=None,
                execution_mode="inferred_only",
            ),
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
        trust_packet=build_runtime_trust_packet(
            runtime_capability=capability,
            execution_result=executed,
            execution_mode="runtime_host",
            pack_id=plan.pack.pack_id,
        ),
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
