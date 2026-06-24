from __future__ import annotations

import os

from server.config import AppConfig
from server.services.replica_runtime import (
    ReplicaExecutionResult,
    ReplicaRunner,
    build_execution_plan,
    build_hypothesis_packet,
    build_runtime_host_relay_status,
)


def extract_reproduced_symptoms(recent_logs: list[object]) -> list[str]:
    symptom_map = (
        ("timeout", "Customer-facing timeouts reproduced in the sandbox request path."),
        ("worker pool saturation", "Worker pool saturation reappeared under replayed load."),
        ("retry", "Retry amplification reappeared once the failing dependency slowed down."),
        ("circuit breaker", "Circuit breaker remained closed while upstream latency climbed."),
        ("5xx", "The replayed path produced elevated 5xx responses."),
        ("queuepool", "Connection pool exhaustion reproduced in the sandbox."),
        ("leaked session", "Session leakage reappeared across repeated checkout retries."),
        ("max_connections", "Database connection ceiling was reached under the replay."),
        ("certificate", "Public certificate validation failed in the active listener path."),
        ("tls", "TLS trust failure was reproduced at the edge entrypoint."),
    )
    text = " ".join(str(item).lower() for item in recent_logs)
    symptoms = [description for needle, description in symptom_map if needle in text]
    return symptoms[:4]


def default_reproduced_symptoms(issue_family: str, recent_logs: list[object]) -> list[str]:
    if "auth" in issue_family.lower() and "dependency" in issue_family.lower():
        return [
            "Authenticated API requests time out as token validation latency increases downstream.",
            "Token cache effectiveness degrades and validation throughput drops under replayed load.",
        ]
    if "queue" in issue_family.lower() and "backlog" in issue_family.lower():
        return [
            "Consumer lag grew as partition assignment changed and rebalancing did not recover.",
            "Worker throughput dropped when several partitions remained unassigned after the deployment.",
        ]
    if "retry amplification" in issue_family:
        return [
            "Customer-facing checkout requests stall after repeated upstream auth retries.",
            "Gateway workers remain occupied until the timeout budget is exhausted.",
        ]
    if "pool exhaustion" in issue_family or "session leak" in issue_family:
        return [
            "Checkout writes stall once the shared database pool reaches saturation.",
            "Retry traffic keeps leaked sessions open long enough to block new writes.",
        ]
    if "certificate expiry" in issue_family:
        return [
            "Public clients fail TLS handshakes against the active edge listener.",
            "The active certificate chain remains stale after rotation should have occurred.",
        ]
    if "memory leak" in issue_family:
        return [
            "Worker memory keeps climbing across repeated task replay cycles.",
            "Garbage-collection pauses stretch as retained buffers accumulate.",
        ]
    if "deploy regression" in issue_family or "5xx spike" in issue_family:
        return [
            "The replayed path produced elevated 5xx responses after the regression deploy.",
            "API latency spiked once the query optimization was applied to the search path.",
        ]
    return extract_reproduced_symptoms(recent_logs) or ["REPLICA did not find a reusable reproduction signature yet."]


def build_mitigation_checks(
    candidate_actions: list[str],
    *,
    fallback_checks: list[tuple[str, str, float]],
) -> list[dict[str, object]]:
    matched_checks: list[dict[str, object]] = []
    fallback_only_checks: list[dict[str, object]] = []
    for action, result, confidence_delta in fallback_checks:
        check = {
            "action": action,
            "result": result,
            "confidence_delta": confidence_delta,
            "outcome_class": "inferred_only",
        }
        if candidate_actions and not any(action.lower() in candidate.lower() or candidate.lower() in action.lower() for candidate in candidate_actions):
            fallback_only_checks.append(check)
            continue
        matched_checks.append(check)
    if matched_checks:
        return matched_checks + fallback_only_checks
    return [
        {
            "action": action,
            "result": result,
            "confidence_delta": confidence_delta,
            "outcome_class": "inferred_only",
        }
        for action, result, confidence_delta in fallback_checks
    ]


def _tokenize_text(value: str) -> set[str]:
    return {
        part
        for part in value.lower().replace("/", " ").replace("-", " ").replace("_", " ").split()
        if part and len(part) > 2
    }


def _action_overlap(left: str, right: str) -> float:
    left_tokens = _tokenize_text(left)
    right_tokens = _tokenize_text(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / max(1, len(left_tokens | right_tokens))


def _runtime_outcome_class(
    *,
    baseline_status: int | None,
    mitigation_status: int | None,
    baseline_duration: int | None,
    mitigation_duration: int | None,
) -> str:
    if mitigation_status is None:
        return "inferred_only"
    if baseline_status is None:
        return "validated"
    if baseline_status >= 500 and mitigation_status < 500:
        return "resolved"
    if mitigation_status < baseline_status:
        return "improved"
    if baseline_status == mitigation_status and baseline_duration and mitigation_duration:
        if mitigation_duration <= int(baseline_duration * 0.6):
            return "improved"
    return "unresolved"


def _runtime_outcome_score(
    outcome_class: str,
    *,
    baseline_duration: int | None,
    mitigation_duration: int | None,
) -> float:
    base = {
        "resolved": 0.97,
        "improved": 0.89,
        "validated": 0.8,
        "unresolved": 0.62,
        "inferred_only": 0.0,
    }.get(outcome_class, 0.0)
    if (
        outcome_class in {"resolved", "improved"}
        and baseline_duration
        and mitigation_duration
        and baseline_duration > 0
    ):
        gain = max(0.0, min(0.08, (baseline_duration - mitigation_duration) / baseline_duration * 0.12))
        return round(min(0.99, base + gain), 2)
    return round(base, 2)


def _runtime_delta_ms(baseline_duration: int | None, mitigation_duration: int | None) -> int | None:
    if baseline_duration is None or mitigation_duration is None:
        return None
    return baseline_duration - mitigation_duration


def _runtime_mitigation_sort_key(
    item: dict[str, object],
    *,
    baseline_duration: int | None,
) -> tuple[float, float]:
    duration = item.get("duration_ms")
    return (
        _runtime_outcome_score(
            str(item.get("outcome_class") or ""),
            baseline_duration=baseline_duration,
            mitigation_duration=duration if isinstance(duration, int) else None,
        ),
        float(item.get("confidence_delta", 0.0) or 0.0),
    )


def _rank_runtime_mitigations(
    runtime_mitigations: list[dict[str, object]] | None,
    *,
    baseline_duration: int | None,
) -> list[dict[str, object]]:
    return sorted(
        [item for item in (runtime_mitigations or []) if isinstance(item, dict)],
        key=lambda item: _runtime_mitigation_sort_key(item, baseline_duration=baseline_duration),
        reverse=True,
    )


def _mitigation_comparison_row(
    item: dict[str, object] | None,
    *,
    baseline_status: int | None,
    baseline_duration: int | None,
) -> dict[str, object] | None:
    if not isinstance(item, dict):
        return None
    status_code = item.get("status_code")
    duration_ms = item.get("duration_ms")
    delta_ms = item.get("delta_ms")
    if delta_ms is None and isinstance(duration_ms, int):
        delta_ms = _runtime_delta_ms(baseline_duration, duration_ms)
    outcome_class = str(item.get("outcome_class") or "")
    summary = (
        f"{item.get('action', 'Mitigation')} returned "
        f"{status_code if status_code is not None else 'no status'}"
        f"{f' at {duration_ms}ms' if duration_ms is not None else ''}"
        f" ({outcome_class.replace('_', ' ') if outcome_class else 'not classified'})."
    )
    if isinstance(delta_ms, int):
        if delta_ms > 0:
            summary = f"{summary} It improved runtime by {delta_ms}ms versus the baseline."
        elif delta_ms < 0:
            summary = f"{summary} It regressed runtime by {abs(delta_ms)}ms versus the baseline."
    return {
        "action": str(item.get("action") or ""),
        "status_code": int(status_code) if isinstance(status_code, (int, float)) else None,
        "duration_ms": int(duration_ms) if isinstance(duration_ms, (int, float)) else None,
        "delta_ms": int(delta_ms) if isinstance(delta_ms, (int, float)) else None,
        "outcome_class": outcome_class,
        "confidence_delta": float(item.get("confidence_delta", 0.0) or 0.0),
        "won": bool(item.get("won")),
        "summary": summary,
        "baseline_status_code": baseline_status,
        "baseline_duration_ms": baseline_duration,
    }


def _build_mitigation_comparison(
    runtime_result: object | None,
    runtime_mitigations: list[dict[str, object]] | None,
    *,
    baseline_outcome_class: str,
) -> dict[str, object]:
    baseline_status = getattr(runtime_result, "replay_status_code", None) if runtime_result else None
    baseline_duration = getattr(runtime_result, "replay_duration_ms", None) if runtime_result else None
    ranked = _rank_runtime_mitigations(runtime_mitigations, baseline_duration=baseline_duration)
    winner = _mitigation_comparison_row(
        ranked[0] if ranked else None,
        baseline_status=baseline_status,
        baseline_duration=baseline_duration,
    )
    runner_up = _mitigation_comparison_row(
        ranked[1] if len(ranked) > 1 else None,
        baseline_status=baseline_status,
        baseline_duration=baseline_duration,
    )
    verdict = ""
    if winner and runner_up:
        verdict = (
            f"{winner['action']} outranked {runner_up['action']} because it finished as "
            f"{str(winner.get('outcome_class') or 'not classified').replace('_', ' ')} while the runner-up remained "
            f"{str(runner_up.get('outcome_class') or 'not classified').replace('_', ' ')}."
        )
    elif winner:
        verdict = (
            f"{winner['action']} is the leading mitigation because it produced the strongest "
            f"{str(winner.get('outcome_class') or 'runtime').replace('_', ' ')} signal."
        )
    return {
        "baseline": {
            "status_code": int(baseline_status) if isinstance(baseline_status, (int, float)) else None,
            "duration_ms": int(baseline_duration) if isinstance(baseline_duration, (int, float)) else None,
            "outcome_class": baseline_outcome_class,
        },
        "winner": winner,
        "runner_up": runner_up,
        "verdict": verdict,
    }


def _build_mitigation_ladder(comparison: dict[str, object]) -> dict[str, object]:
    winner = comparison.get("winner") if isinstance(comparison, dict) else None
    runner_up = comparison.get("runner_up") if isinstance(comparison, dict) else None
    baseline = comparison.get("baseline") if isinstance(comparison, dict) else None

    primary_action = str((winner or {}).get("action") or "")
    primary_outcome = str((winner or {}).get("outcome_class") or "inferred_only")
    fallback_action = str((runner_up or {}).get("action") or "")
    fallback_outcome = str((runner_up or {}).get("outcome_class") or "inferred_only")
    baseline_outcome = str((baseline or {}).get("outcome_class") or "not_run")

    if primary_outcome == "resolved":
        stop_condition = "Stop after the primary mitigation once the bounded replay no longer returns the baseline 5xx failure and the customer path remains stable."
        operator_summary = (
            f"Run {primary_action or 'the primary mitigation'} first and stop there if the bounded replay stays resolved. "
            f"{f'Keep {fallback_action} as the bounded fallback only if the failure signature returns.' if fallback_action else 'Escalate with TRACE if the failure signature returns.'}"
        )
        guardian_summary = (
            f"Approve the primary step first. {f'Do not pre-authorize {fallback_action} unless the resolved signal regresses.' if fallback_action else 'Do not authorize broader changes unless the resolved signal regresses.'}"
        )
    elif primary_outcome == "improved":
        stop_condition = (
            f"If {primary_action or 'the primary mitigation'} only improves the runtime and the baseline failure signature remains active, move to "
            f"{fallback_action or 'manual escalation with TRACE'} next."
        )
        operator_summary = (
            f"Start with {primary_action or 'the primary mitigation'} because it improves the bounded replay first. "
            f"{f'If the incident is still not resolved, execute {fallback_action} as the bounded fallback.' if fallback_action else 'If the incident is still not resolved, stop and escalate with the TRACE packet.'}"
        )
        guardian_summary = (
            f"Approve the primary step as a bounded first move, but require another review before treating the incident as resolved. "
            f"{f'Fallback approval should point to {fallback_action} if the failure signature remains.' if fallback_action else 'Fallback should be manual engineering escalation if the failure signature remains.'}"
        )
    else:
        stop_condition = (
            f"If {primary_action or 'the primary mitigation'} does not materially improve the baseline {baseline_outcome.replace('_', ' ')}, stop automation and escalate with the TRACE packet."
        )
        operator_summary = (
            f"Primary move is {primary_action or 'the leading mitigation candidate'}, but it is not yet runtime-cleared. "
            f"{f'Use {fallback_action} only as the next bounded attempt under explicit review.' if fallback_action else 'Escalate directly instead of assuming the next step is safe.'}"
        )
        guardian_summary = (
            f"Do not treat the incident as resolved after the primary move alone. "
            f"{f'Fallback {fallback_action} still requires explicit approval.' if fallback_action else 'Further action requires explicit engineering review.'}"
        )

    steps = []
    if primary_action:
        steps.append(
            {
                "rank": 1,
                "role": "primary",
                "action": primary_action,
                "outcome_class": primary_outcome,
                "summary": str((winner or {}).get("summary") or ""),
            }
        )
    if fallback_action:
        steps.append(
            {
                "rank": 2,
                "role": "fallback",
                "action": fallback_action,
                "outcome_class": fallback_outcome,
                "summary": str((runner_up or {}).get("summary") or ""),
            }
        )

    return {
        "primary": steps[0] if steps else {},
        "fallback": steps[1] if len(steps) > 1 else {},
        "steps": steps,
        "stop_condition": stop_condition,
        "operator_summary": operator_summary,
        "guardian_summary": guardian_summary,
    }


def runtime_aligned_candidate_fixes(issue_family: str, service: str) -> list[dict[str, object]]:
    issue_family_text = issue_family.lower()
    if "auth" in issue_family_text and "dependency" in issue_family_text:
        return [
            {"action": "Reset circuit breaker and force token cache invalidation to restore auth throughput", "success_rate": 0.91},
            {"action": "Temporarily increase auth-svc timeout and cache TTL to smooth the validation latency", "success_rate": 0.87},
            {"action": "Roll back auth-svc to recover from enhanced validation overhead", "success_rate": 0.82},
        ]
    if "queue" in issue_family_text and "backlog" in issue_family_text:
        return [
            {"action": "Roll back consumer and force group rebalance", "success_rate": 0.93},
            {"action": "Re-enable rebalance feature flag in place", "success_rate": 0.88},
            {"action": "Increase partition count immediately", "success_rate": 0.24},
        ]
    if "retry amplification" in issue_family_text or ("timeout" in issue_family_text and "retry" in issue_family_text):
        return [
            {"action": "Enable auth-svc circuit breaker and cap retries to 1", "success_rate": 0.9},
            {"action": "Roll back auth-svc retry middleware", "success_rate": 0.87},
            {"action": "Drain hot gateway pods and scale replicas +2", "success_rate": 0.8},
        ]
    if "pool exhaustion" in issue_family_text or "session leak" in issue_family_text:
        return [
            {"action": "Terminate orphaned sessions and restart checkout pods", "success_rate": 0.89},
            {"action": "Roll back checkout retry patch", "success_rate": 0.86},
            {"action": "Increase pool size temporarily to 650", "success_rate": 0.78},
        ]
    if "certificate expiry" in issue_family_text or "trust boundary" in issue_family_text:
        return [
            {"action": "Rotate the expired certificate", "success_rate": 0.93},
            {"action": "Reload the active edge listener", "success_rate": 0.86},
        ]
    return [
        {"action": f"Validate {service or 'service'} ownership and confirm incident scope", "success_rate": 0.9},
        {"action": "Prepare rollback-safe mitigation and monitor audit trail", "success_rate": 0.82},
    ]


def _deployment_signal_summary(recent_deployments: list[object] | None) -> tuple[str, list[str]]:
    if not recent_deployments:
        return "", []
    text = " ".join(str(item).lower() for item in recent_deployments)
    supporting_conditions: list[str] = []
    if "retry" in text:
        supporting_conditions.append("recent retry-related deployment matches the reproduced failure path")
    if "middleware" in text:
        supporting_conditions.append("middleware change is present in the same incident window")
    if "telemetry" in text:
        supporting_conditions.append("telemetry-only change appears adjacent but not causal")
    if "certificate" in text or "rotation" in text:
        supporting_conditions.append("certificate rotation or listener deployment is part of the affected edge path")
    return text, supporting_conditions


def _runtime_enablement_hint(
    *,
    scaffold_ready: bool,
    runtime_executed: bool,
    runtime_mode: str,
    compose_config_valid: bool,
    docker_available: bool,
    runtime_capability_state: str = "",
) -> str:
    if runtime_capability_state == "relay_executed":
        return "A configured runtime host ran Docker-backed replay for this incident. REPLICA is showing measured baseline and mitigation outcomes from delegated execution."
    if runtime_capability_state == "relay_available":
        return "This incident maps to a bounded runtime scaffold and can delegate Docker-backed replay to the configured runtime host."
    if runtime_executed:
        return "Docker-backed replay ran for this incident. REPLICA is showing measured baseline and mitigation outcomes."
    if scaffold_ready and compose_config_valid and docker_available:
        return "Runtime scaffold is ready. Start NEXUS with NEXUS_ENABLE_REPLICA_RUNTIME=1 to execute Docker-backed replay instead of scaffold-only inference."
    if scaffold_ready and not docker_available:
        return "This incident maps to a bounded runtime scaffold, but the current app environment cannot execute Docker-backed replay. Run NEXUS on a Docker-capable host with NEXUS_ENABLE_REPLICA_RUNTIME=1 to execute replay."
    if scaffold_ready:
        return "This incident maps to a bounded runtime scaffold, but the compose contract still needs validation before replay can run."
    if runtime_mode == "inferred":
        return "This incident is using inferred reproduction logic because no bounded runtime scaffold matches yet."
    return "Runtime replay is not available for this incident yet."


def _runtime_host_capability(
    *,
    plan: object,
    runner_result: object,
    runtime_result: object,
) -> dict[str, object]:
    bounded_pack_available = bool(plan and runner_result and not getattr(runner_result, "missing_assets", ()))
    docker_available = bool(getattr(runner_result, "docker_available", False)) if runner_result else False
    compose_config_valid = bool(getattr(runner_result, "compose_config_valid", False)) if runner_result else False
    relay_configured = bool(build_runtime_host_relay_status(AppConfig()).get("configured"))

    if runtime_result:
        return {
            "state": "replay_executed",
            "label": "Replay executed",
            "host_label": "Current app host",
            "can_execute_replay": True,
            "bounded_pack_available": bounded_pack_available,
            "docker_available": docker_available,
            "compose_config_valid": compose_config_valid,
            "message": "This host executed Docker-backed replay for the bounded runtime pack.",
        }
    if bounded_pack_available and not docker_available and relay_configured:
        return {
            "state": "relay_available",
            "label": "Relay available",
            "host_label": "External runtime host",
            "can_execute_replay": True,
            "bounded_pack_available": True,
            "docker_available": False,
            "compose_config_valid": compose_config_valid,
            "message": "The current app host cannot run Docker-backed replay directly, but a configured runtime host can execute it on demand.",
        }
    if bounded_pack_available and docker_available and compose_config_valid:
        return {
            "state": "replay_available",
            "label": "Replay available",
            "host_label": "Current app host",
            "can_execute_replay": True,
            "bounded_pack_available": True,
            "docker_available": True,
            "compose_config_valid": True,
            "message": "This host can execute Docker-backed replay for the bounded runtime pack when replay is explicitly triggered.",
        }
    if bounded_pack_available and not docker_available:
        return {
            "state": "host_unavailable",
            "label": "Host unavailable",
            "host_label": "External Docker host required",
            "can_execute_replay": False,
            "bounded_pack_available": True,
            "docker_available": False,
            "compose_config_valid": False,
            "message": "The incident maps to a bounded runtime pack, but the current app environment cannot execute Docker-backed replay.",
        }
    if bounded_pack_available:
        return {
            "state": "pack_validation_required",
            "label": "Pack validation required",
            "host_label": "Current app host",
            "can_execute_replay": False,
            "bounded_pack_available": True,
            "docker_available": docker_available,
            "compose_config_valid": False,
            "message": "A bounded runtime pack exists for this incident, but the compose contract still needs validation before replay can run.",
        }
    return {
        "state": "no_pack",
        "label": "No bounded pack",
        "host_label": "Not applicable",
        "can_execute_replay": False,
        "bounded_pack_available": False,
        "docker_available": docker_available,
        "compose_config_valid": False,
        "message": "No bounded runtime pack matches this incident class yet.",
    }


def _runtime_provenance(
    *,
    runtime_mode: str,
    runtime_executed: bool,
    runtime_capability: dict[str, object],
) -> dict[str, object]:
    capability_state = str(runtime_capability.get("state") or "")
    if runtime_executed and runtime_mode == "relay_runtime_scaffold":
        return {
            "mode": "delegated_relay",
            "label": "Delegated runtime host replay",
            "summary": "A configured runtime host executed the bounded runtime pack on behalf of the packaged app.",
            "executed_by": "runtime_host",
        }
    if runtime_executed:
        return {
            "mode": "direct_runtime",
            "label": "Direct runtime replay",
            "summary": "The current app host executed the bounded runtime pack directly.",
            "executed_by": "current_app_host",
        }
    if capability_state == "relay_available":
        return {
            "mode": "relay_ready",
            "label": "Delegated runtime host ready",
            "summary": "The packaged app can delegate bounded replay to the configured runtime host when requested.",
            "executed_by": "runtime_host",
        }
    if capability_state == "replay_available":
        return {
            "mode": "direct_ready",
            "label": "Direct runtime ready",
            "summary": "The current app host can execute the bounded runtime pack directly when requested.",
            "executed_by": "current_app_host",
        }
    if capability_state == "host_unavailable":
        return {
            "mode": "runtime_unavailable",
            "label": "Direct runtime unavailable",
            "summary": "The current app environment cannot execute the bounded runtime pack directly.",
            "executed_by": "unavailable",
        }
    return {
        "mode": "inferred_only",
        "label": "Inferred only",
        "summary": "The current incident view is still using bounded inference rather than measured runtime replay.",
        "executed_by": "not_run",
    }


def build_replica_summary(
    *,
    incident_id: str,
    triage_summary: dict[str, object],
    root_cause: str,
    recent_logs: list[object] | None = None,
    recent_deployments: list[object] | None = None,
    candidate_fixes: list[object] | None = None,
    execute_runtime: bool | None = None,
    runtime_execution: ReplicaExecutionResult | None = None,
    runtime_capability_override: dict[str, object] | None = None,
    runtime_mode_override: str | None = None,
) -> dict[str, object]:
    issue_family = str(triage_summary.get("issue_family", "")).lower()
    logs_text = " ".join(str(item) for item in (recent_logs or [])).lower()
    service = str(triage_summary.get("likely_owner_service") or "")
    deployment_text, deployment_conditions = _deployment_signal_summary(recent_deployments)
    reproduced_symptoms = extract_reproduced_symptoms(recent_logs or [])
    candidate_actions = [str(item.get("action", "")).strip() for item in (candidate_fixes or []) if isinstance(item, dict)]
    plan = build_execution_plan(
        issue_family=str(triage_summary.get("issue_family", "")),
        service=service,
        recent_logs=recent_logs,
        recent_deployments=recent_deployments,
    )
    incident_class = str(plan.incident_class) if plan else ""
    runner_result = runtime_execution if runtime_execution is not None else (ReplicaRunner().inspect_plan(plan) if plan else None)
    execute_runtime = (
        os.environ.get("NEXUS_ENABLE_REPLICA_RUNTIME", "0") == "1"
        if execute_runtime is None
        else execute_runtime
    )
    runtime_result = runtime_execution or (
        ReplicaRunner().execute_scaffold(plan) if plan and execute_runtime and runner_result and runner_result.compose_config_valid and not runner_result.missing_assets else None
    )

    environment_pack_id = "generic-support-triage-pack-v1"
    reproduction_status = "not_run"
    hypothesis_supported = False
    confidence_delta = 0.0
    tested_mitigations: list[dict[str, object]] = []
    reasoning = "REPLICA has not run for this incident class yet."
    supporting_conditions: list[str] = []

    if plan is not None:
        environment_pack_id = plan.pack.pack_id
        if runner_result and not runner_result.missing_assets:
            supporting_conditions.append("pack scaffold is present on disk for the bounded runtime-backed replay path")
        if runner_result and runner_result.compose_config_valid and runner_result.services_seen:
            supporting_conditions.append(
                f"compose plan validates with services: {', '.join(runner_result.services_seen)}"
            )
        if runner_result and not runner_result.docker_available:
            supporting_conditions.append("docker binary is unavailable in the current app environment")
        if runtime_result and runtime_result.replay_output:
            supporting_conditions.append("runtime scaffold executed a replay hook successfully")

    if incident_class == "timeout_retry_amplification" or (
        not incident_class and ("retry amplification" in issue_family or ("retry" in logs_text and "timeout" in logs_text))
    ):
        reproduction_status = "reproduced"
        supporting_conditions = [
            "downstream auth latency above 5s",
            "retry middleware enabled",
            "gateway worker pool near saturation",
        ] + deployment_conditions
        hypothesis_supported = True
        confidence_delta = 0.14 if "middleware" in deployment_text else 0.12
        tested_mitigations = build_mitigation_checks(
            candidate_actions,
            fallback_checks=[
                ("Enable auth-svc circuit breaker and cap retries to 1", "latency improved and worker pressure eased once retries were capped at the auth boundary", 0.08),
                ("Roll back auth-svc retry middleware", "the timeout cascade no longer persisted after the retry refactor was removed", 0.06),
                ("Drain hot gateway pods and scale replicas +2", "worker pressure eased but the root retry pattern still remained visible", 0.03),
            ],
        )
        reasoning = (
            "The failure pattern reproduced only when the retry-heavy middleware path remained enabled under downstream auth degradation. "
            "The sandbox required both the retry middleware change and elevated downstream auth latency to sustain the timeout cascade."
        )
    elif incident_class == "db_pool_exhaustion" or (
        not incident_class and ("pool exhaustion" in issue_family or "session leak" in issue_family or "queuepool" in logs_text)
    ):
        reproduction_status = "reproduced"
        supporting_conditions = [
            "checkout retry patch enabled",
            "primary pool capped at production threshold",
            "session cleanup path disabled under retry failure",
        ] + deployment_conditions
        hypothesis_supported = True
        confidence_delta = 0.11 if "retry" in deployment_text else 0.1
        tested_mitigations = build_mitigation_checks(
            candidate_actions,
            fallback_checks=[
                ("Terminate orphaned sessions and restart checkout pods", "pool capacity recovered quickly and new checkout writes resumed", 0.06),
                ("Roll back checkout retry patch", "session growth stopped once the retry patch was removed from the write path", 0.05),
                ("Increase pool size temporarily to 650", "capacity improved briefly but the leak signature remained active", 0.01),
            ],
        )
        reasoning = (
            "The failure reproduced when the patched retry path leaked sessions long enough to exhaust the primary pool. "
            "Pool exhaustion did not persist once the retry patch was removed from the sandbox."
        )
    elif "certificate expiry" in issue_family or "tls" in root_cause.lower():
        environment_pack_id = "edge-nginx-acme-v1"
        reproduction_status = "reproduced"
        supporting_conditions = [
            "expired public certificate chain attached",
            "edge listener still serving stale cert",
        ] + deployment_conditions
        hypothesis_supported = True
        confidence_delta = 0.09
        tested_mitigations = build_mitigation_checks(
            candidate_actions,
            fallback_checks=[
                ("Rotate the expired certificate", "public trust restored", 0.09),
            ],
        )
        reasoning = "The failure reproduced when the edge listener served an expired public certificate chain."
    elif "memory leak" in issue_family or "heap" in logs_text:
        environment_pack_id = "worker-python-image-gc-v1"
        reproduction_status = "reproduced"
        supporting_conditions = [
            "retained frame buffers stay live after task completion",
            "gc pause time increases as replay batches accumulate",
        ] + deployment_conditions
        hypothesis_supported = True
        confidence_delta = 0.08
        tested_mitigations = build_mitigation_checks(
            candidate_actions,
            fallback_checks=[
                ("Recycle leaking worker pods", "memory pressure dropped but the retained-object pattern returned under load", 0.03),
                ("Disable the new frame-cache path", "heap growth stopped once the suspected buffer path was disabled", 0.05),
            ],
        )
        reasoning = "The failure reproduced when repeated image transform batches retained frame buffers beyond the expected cleanup path."
    elif incident_class == "auth_dependency_slowdown" or (
        not incident_class and "auth" in issue_family and "dependency" in issue_family
    ):
        environment_pack_id = "checkout-python-fastapi-auth-validation-v1"
        reproduction_status = "reproduced"
        supporting_conditions = [
            "auth-svc token validation latency above 500ms per request",
            "token cache hit rate dropped below 50%",
            "upstream identity provider latency is elevated",
        ] + deployment_conditions
        hypothesis_supported = True
        confidence_delta = 0.1
        tested_mitigations = build_mitigation_checks(
            candidate_actions,
            fallback_checks=[
                ("Reset circuit breaker and force token cache invalidation to restore auth throughput", "auth throughput recovered when cache was cleared and circuit breaker reset", 0.08),
                ("Temporarily increase auth-svc timeout and cache TTL to smooth the validation latency", "validation latency improved with increased timeout and cache TTL", 0.06),
                ("Roll back auth-svc to recover from enhanced validation overhead", "auth validation throughput returned to baseline after rollback", 0.05),
            ],
        )
        reasoning = "The failure reproduced when auth-svc token validation latency remained elevated and cache effectiveness degraded. Token validation timeouts and cache misses drove upstream timeouts in the checkout path."
    elif incident_class == "queue_backlog_surge" or (
        not incident_class and "queue" in issue_family and "backlog" in issue_family
    ):
        environment_pack_id = "worker-backlog-kafka-v1"
        reproduction_status = "reproduced"
        supporting_conditions = [
            "consumer group rebalancing has stalled",
            "partitions remain unassigned and idle",
            "consumer throughput dropped while lag grows",
        ] + deployment_conditions
        hypothesis_supported = True
        confidence_delta = 0.1
        tested_mitigations = build_mitigation_checks(
            candidate_actions,
            fallback_checks=[
                ("Roll back consumer and force group rebalance", "consumer lag recovered when rebalance was triggered", 0.08),
                ("Re-enable rebalance feature flag in place", "partition assignment resumed once rebalance flag was enabled", 0.06),
                ("Scale consumer group temporarily", "throughput improved but lag backfill remained slow", 0.03),
            ],
        )
        reasoning = "The failure reproduced when consumer group rebalancing stalled after the deployment and partitions remained unassigned. Consumer lag and partition assignment errors drove upstream transaction delays."

    if not reproduced_symptoms:
        reproduced_symptoms = default_reproduced_symptoms(issue_family, recent_logs or [])

    runtime_mitigations = _runtime_override_mitigations(
        runtime_result=runtime_result,
        default_checks=tested_mitigations,
    )
    runtime_comparison_summary = _runtime_comparison_summary(runtime_result, runtime_mitigations)
    best_mitigation = next((item for item in runtime_mitigations if item.get("won")), runtime_mitigations[0] if runtime_mitigations else {})
    best_outcome_class = str(best_mitigation.get("outcome_class") or "")
    best_status_code = best_mitigation.get("status_code")
    best_duration_ms = best_mitigation.get("duration_ms")
    baseline_outcome_class = (
        "reproduced"
        if (runtime_result and isinstance(runtime_result.replay_status_code, int) and runtime_result.replay_status_code >= 500)
        else (
            "reproduced"
            if reproduction_status == "reproduced" and not runtime_result
            else ("validated" if runtime_result and runtime_result.replay_status_code is not None else "not_run")
        )
    )
    mitigation_comparison = _build_mitigation_comparison(
        runtime_result,
        runtime_mitigations,
        baseline_outcome_class=baseline_outcome_class,
    )
    mitigation_ladder = _build_mitigation_ladder(mitigation_comparison)
    mitigation_verdict = str(mitigation_comparison.get("verdict") or "")
    runtime_mode = runtime_mode_override or ("runtime_scaffold" if runtime_result else ("pack_scaffold" if plan and runner_result and not runner_result.missing_assets else "inferred"))
    scaffold_ready = bool(plan and runner_result and not runner_result.missing_assets)
    runtime_capability = runtime_capability_override or _runtime_host_capability(
        plan=plan,
        runner_result=runner_result,
        runtime_result=runtime_result,
    )
    hypothesis_packet = build_hypothesis_packet(
        plan=plan,
        issue_family=str(triage_summary.get("issue_family", "")),
        service=service,
        deployment_conditions=deployment_conditions,
        tested_mitigations=runtime_mitigations,
        runtime_result=runtime_result,
    )
    runtime_provenance = _runtime_provenance(
        runtime_mode=runtime_mode,
        runtime_executed=bool(runtime_result),
        runtime_capability=runtime_capability,
    )

    return {
        "incident_id": incident_id,
        "environment_pack_id": environment_pack_id,
        "service": service,
        "reproduction_status": reproduction_status,
        "reproduced_symptoms": reproduced_symptoms,
        "hypothesis_supported": hypothesis_supported,
        "confidence_delta": confidence_delta,
        "scaffold_ready": scaffold_ready,
        "runtime_mode": runtime_mode,
        "runtime_executed": bool(runtime_result),
        "services_seen": list(runner_result.services_seen) if runner_result else [],
        "replay_output": runtime_result.replay_output if runtime_result else "",
        "replay_status_code": runtime_result.replay_status_code if runtime_result else None,
        "replay_duration_ms": runtime_result.replay_duration_ms if runtime_result else None,
        "mitigation_outputs": list(runtime_result.mitigation_outputs) if runtime_result else [],
        "mitigation_status_codes": list(runtime_result.mitigation_status_codes) if runtime_result else [],
        "mitigation_duration_ms": list(runtime_result.mitigation_duration_ms) if runtime_result else [],
        "runtime_comparison_summary": runtime_comparison_summary,
        "baseline_outcome_class": baseline_outcome_class,
        "best_mitigation_action": str(best_mitigation.get("action") or ""),
        "best_mitigation_outcome_class": best_outcome_class,
        "best_mitigation_status_code": int(best_status_code) if isinstance(best_status_code, (int, float)) else None,
        "best_mitigation_duration_ms": int(best_duration_ms) if isinstance(best_duration_ms, (int, float)) else None,
        "best_mitigation_summary": (
            (
                f"{best_mitigation.get('action', 'No mitigation validated')} "
                f"finished in state {best_outcome_class.replace('_', ' ') if best_outcome_class else 'not evaluated'}."
            )
            if best_mitigation and runtime_result
            else (
                f"{best_mitigation.get('action', 'No mitigation selected')} is the leading scaffold-only mitigation candidate."
                if best_mitigation
                else "No runtime-backed mitigation comparison is available yet."
            )
        ),
        "mitigation_comparison": mitigation_comparison,
        "mitigation_ladder": mitigation_ladder,
        "runtime_enablement_hint": _runtime_enablement_hint(
            scaffold_ready=scaffold_ready,
            runtime_executed=bool(runtime_result),
            runtime_mode=runtime_mode,
            compose_config_valid=bool(runner_result and runner_result.compose_config_valid),
            docker_available=bool(runner_result.docker_available) if runner_result else False,
            runtime_capability_state=str(runtime_capability.get("state") or ""),
        ),
        "hypothesis_packet": hypothesis_packet,
        "runtime_capability": runtime_capability,
        "runtime_provenance": runtime_provenance,
        "supporting_conditions": supporting_conditions + ([f"missing scaffold assets: {', '.join(runner_result.missing_assets)}"] if runner_result and runner_result.missing_assets else []),
        "tested_mitigations": runtime_mitigations,
        "reasoning": (
            f"{reasoning} "
            f"{'The bounded runtime scaffold was executed for this run.' if runtime_result and runtime_mode != 'relay_runtime_scaffold' else ('A configured runtime host executed the bounded runtime scaffold for this run.' if runtime_result and runtime_mode == 'relay_runtime_scaffold' else ('The bounded runtime scaffold is validated and ready for replay execution.' if runner_result and runner_result.compose_config_valid and not runner_result.missing_assets and str(runtime_capability.get('state') or '') != 'relay_available' else ('The bounded runtime scaffold can delegate replay to the configured runtime host.' if str(runtime_capability.get('state') or '') == 'relay_available' else ('The bounded runtime scaffold is mapped for this incident, but Docker-backed replay is unavailable in the current app environment.' if runner_result and not runner_result.missing_assets and not runner_result.docker_available else ('The bounded runtime scaffold is mapped for this incident, but the compose contract still needs validation.' if runner_result and not runner_result.missing_assets else 'The bounded runtime scaffold is not fully ready yet.')))))}"
            f"{f' {mitigation_verdict}' if mitigation_verdict else ''}"
        ).strip(),
    }


def _runtime_override_mitigations(
    *,
    runtime_result: object,
    default_checks: list[dict[str, object]],
) -> list[dict[str, object]]:
    if not runtime_result:
        return default_checks
    outputs = list(getattr(runtime_result, "mitigation_outputs", ()) or ())
    statuses = list(getattr(runtime_result, "mitigation_status_codes", ()) or ())
    durations = list(getattr(runtime_result, "mitigation_duration_ms", ()) or ())
    baseline_status = getattr(runtime_result, "replay_status_code", None)
    baseline_duration = getattr(runtime_result, "replay_duration_ms", None)
    if not outputs:
        return default_checks
    rewritten: list[dict[str, object]] = []
    default_iter = iter(default_checks)
    for index in range(0, len(outputs), 2):
        default = next(default_iter, {"action": f"Mitigation {index // 2 + 1}", "confidence_delta": 0.0})
        hook_output = outputs[index]
        replay_output = outputs[index + 1] if index + 1 < len(outputs) else ""
        status = statuses[index // 2] if index // 2 < len(statuses) else None
        duration = durations[index // 2] if index // 2 < len(durations) else None
        outcome_class = _runtime_outcome_class(
            baseline_status=baseline_status,
            mitigation_status=status,
            baseline_duration=baseline_duration,
            mitigation_duration=duration,
        )
        rewritten.append(
            {
                "action": default.get("action", f"Mitigation {index // 2 + 1}"),
                "result": (
                    f"{str(hook_output).splitlines()[0] if hook_output else 'Hook executed'}"
                    f"{f' -> replay status {status}' if status is not None else ''}"
                    f"{f' at {duration}ms' if duration is not None else ''}"
                    f"{f' | {str(replay_output).splitlines()[-1]}' if replay_output else ''}"
                ),
                "confidence_delta": default.get("confidence_delta", 0.0),
                "status_code": status,
                "duration_ms": duration,
                "delta_ms": _runtime_delta_ms(baseline_duration, duration),
                "outcome_class": outcome_class,
                "won": False,
            }
        )
    if not rewritten:
        return default_checks
    ranked = _rank_runtime_mitigations(rewritten, baseline_duration=baseline_duration)
    winner = ranked[0]
    for item in ranked:
        item["won"] = item is winner
    return ranked


def _runtime_comparison_summary(
    runtime_result: object | None,
    runtime_mitigations: list[dict[str, object]] | None = None,
) -> str:
    baseline_duration = getattr(runtime_result, "replay_duration_ms", None) if runtime_result else None
    ranked = _rank_runtime_mitigations(runtime_mitigations, baseline_duration=baseline_duration)
    if not runtime_result:
        if not ranked:
            return ""
        winner = ranked[0]
        runner_up = ranked[1] if len(ranked) > 1 else None
        if isinstance(winner, dict):
            best_action = str(winner.get("action") or "Selected mitigation")
            summary = (
                f"Scaffold-only mode ranked '{best_action}' as the leading mitigation candidate. "
                "Runtime replay has not validated this mitigation yet."
            )
            if runner_up:
                summary += f" Runner-up: '{str(runner_up.get('action') or 'Unknown mitigation')}'."
            return summary
        return ""
    baseline_status = getattr(runtime_result, "replay_status_code", None)
    if baseline_status is None:
        return ""
    winner = ranked[0] if ranked else None
    runner_up = ranked[1] if len(ranked) > 1 else None
    if isinstance(winner, dict):
        best_action = str(winner.get("action") or "Selected mitigation")
        best_status = winner.get("status_code")
        best_duration = winner.get("duration_ms")
        outcome = _runtime_outcome_class(
            baseline_status=baseline_status,
            mitigation_status=best_status,
            baseline_duration=baseline_duration,
            mitigation_duration=best_duration,
        ).replace("_", " ")
        summary = (
            f"Baseline replay returned {baseline_status}"
            f"{f' at {baseline_duration}ms' if baseline_duration is not None else ''}; "
            f"best mitigation {best_action} returned {best_status}"
            f"{f' at {best_duration}ms' if best_duration is not None else ''}"
            f" and the runtime outcome was {outcome}."
        )
        if isinstance(runner_up, dict):
            runner_action = str(runner_up.get("action") or "Runner-up mitigation")
            runner_status = runner_up.get("status_code")
            runner_duration = runner_up.get("duration_ms")
            runner_outcome = str(runner_up.get("outcome_class") or "").replace("_", " ")
            summary += (
                f" Runner-up {runner_action} returned {runner_status}"
                f"{f' at {runner_duration}ms' if runner_duration is not None else ''}"
                f" and remained {runner_outcome or 'not classified'}."
            )
        return summary
    return f"Baseline replay returned {baseline_status}{f' at {baseline_duration}ms' if baseline_duration is not None else ''}."


def _explain_evidence_weighting(
    *,
    action: str,
    base_success_rate: float,
    runtime_alignment: float,
    runtime_outcome: str,
    runtime_executed: bool,
    memory_weight: float = 0.0,
) -> dict[str, object]:
    if not runtime_executed:
        return {
            "primary_evidence": "inference",
            "evidence_posture": "inferred_only",
            "confidence_boost": 0.0,
            "weighting_summary": "This recommendation is based on historical incident patterns and memory (no runtime validation).",
            "residual_risk": "unvalidated" if base_success_rate < 0.85 else "moderate",
        }

    runtime_weight = _runtime_outcome_score(
        runtime_outcome,
        baseline_duration=None,
        mitigation_duration=None,
    ) * runtime_alignment

    if runtime_weight >= 0.6:
        primary = "runtime-backed"
        posture = "validated_runtime"
        risk = "low" if runtime_outcome == "resolved" else "moderate"
        boost = runtime_weight - base_success_rate
    elif runtime_alignment >= 0.25:
        primary = "runtime-informed"
        posture = "runtime_validated"
        risk = "moderate"
        boost = max(0.0, runtime_weight - base_success_rate)
    else:
        primary = "inference"
        posture = "inferred_only"
        risk = "unvalidated" if base_success_rate < 0.85 else "moderate"
        boost = 0.0

    weighting_parts = []
    if base_success_rate > 0:
        weighting_parts.append(f"inference ({round(base_success_rate * 100)}%)")
    if memory_weight > 0:
        weighting_parts.append(f"historical patterns ({round(memory_weight * 100)}%)")
    if runtime_weight > 0:
        weighting_parts.append(f"runtime validation ({round(runtime_weight * 100)}%)")

    return {
        "primary_evidence": primary,
        "evidence_posture": posture,
        "confidence_boost": round(boost, 2),
        "weighting_summary": (
            f"{action} is ranked based on {', '.join(weighting_parts) or 'multiple evidence sources'}. "
            f"Runtime validation {'confirmed' if runtime_outcome == 'resolved' else 'improved' if runtime_outcome == 'improved' else 'showed'} "
            f"the mitigation {'resolved the failure.' if runtime_outcome == 'resolved' else 'improved the failure.' if runtime_outcome == 'improved' else 'did not fully resolve it.'}"
        ),
        "residual_risk": risk,
    }


def rank_candidate_fixes_with_runtime(
    candidate_fixes: list[dict[str, object]] | None,
    *,
    replica_summary: dict[str, object],
) -> list[dict[str, object]]:
    ranked: list[dict[str, object]] = []
    best_action = str(replica_summary.get("best_mitigation_action") or "")
    best_outcome = str(replica_summary.get("best_mitigation_outcome_class") or "")
    best_duration = replica_summary.get("best_mitigation_duration_ms")
    baseline_duration = replica_summary.get("replay_duration_ms")
    runtime_executed = bool(replica_summary.get("runtime_executed", False))

    for item in candidate_fixes or []:
        if not isinstance(item, dict):
            continue
        action = str(item.get("action", "")).strip()
        base_success = float(item.get("success_rate", 0.0) or 0.0)
        overlap = _action_overlap(action, best_action) if best_action else 0.0
        runtime_score = _runtime_outcome_score(
            best_outcome,
            baseline_duration=baseline_duration if isinstance(baseline_duration, int) else None,
            mitigation_duration=best_duration if isinstance(best_duration, int) else None,
        ) * overlap

        weighting = _explain_evidence_weighting(
            action=action,
            base_success_rate=base_success,
            runtime_alignment=overlap,
            runtime_outcome=best_outcome,
            runtime_executed=runtime_executed and overlap >= 0.25,
            memory_weight=0.0,
        )

        ranked_item = dict(item)
        ranked_item["runtime_alignment"] = round(overlap, 2)
        ranked_item["runtime_score"] = round(runtime_score, 2)
        ranked_item["runtime_outcome_class"] = best_outcome if overlap >= 0.25 else ""
        ranked_item["success_rate"] = round(max(base_success, runtime_score), 2)
        ranked_item["evidence_posture"] = weighting["evidence_posture"]
        ranked_item["confidence_boost"] = weighting["confidence_boost"]
        ranked_item["weighting_summary"] = weighting["weighting_summary"]
        ranked_item["residual_risk"] = weighting["residual_risk"]
        ranked_item["why_action_won"] = _build_why_action_won(
            ranked_item=ranked_item,
            runtime_executed=runtime_executed,
            best_outcome=best_outcome,
        )
        ranked.append(ranked_item)
    ranked.sort(
        key=lambda item: (
            float(item.get("runtime_score", 0.0) or 0.0),
            float(item.get("success_rate", 0.0) or 0.0),
        ),
        reverse=True,
    )
    return ranked


def _build_why_action_won(
    *,
    ranked_item: dict[str, object],
    runtime_executed: bool,
    best_outcome: str,
) -> str:
    action = str(ranked_item.get("action", "")).strip()
    alignment = float(ranked_item.get("runtime_alignment", 0.0) or 0.0)

    if not runtime_executed or alignment < 0.25:
        return f"{action}: Selected based on historical success rate and current diagnosis pattern match."

    if best_outcome == "resolved":
        return f"{action}: Runtime validation in REPLICA showed this action fully resolved the failure condition."
    if best_outcome == "improved":
        return f"{action}: Runtime validation in REPLICA demonstrated this action improved performance without full resolution."
    return f"{action}: Ranked highest despite runtime validation not resolving the failure, due to mitigating risk vectors."


def enrich_memory_with_runtime(
    memory_hits: dict[str, list[dict[str, object]]] | None,
    *,
    replica_summary: dict[str, object],
) -> dict[str, list[dict[str, object]]]:
    payload = {
        "similar_incidents": [dict(item) for item in (memory_hits or {}).get("similar_incidents", [])],
        "runbooks": [dict(item) for item in (memory_hits or {}).get("runbooks", [])],
        "unresolved_items": [dict(item) for item in (memory_hits or {}).get("unresolved_items", [])],
        "recent_guardian_outcomes": [dict(item) for item in (memory_hits or {}).get("recent_guardian_outcomes", [])],
    }
    best_action = str(replica_summary.get("best_mitigation_action") or "")
    best_outcome = str(replica_summary.get("best_mitigation_outcome_class") or "").replace("_", " ")
    best_summary = str(replica_summary.get("best_mitigation_summary") or "")
    runtime_executed = bool(replica_summary.get("runtime_executed", False))
    if not best_action:
        return payload

    for item in payload["runbooks"]:
        overlap_sources = [str(item.get("runbook_summary", ""))]
        overlap_sources.extend(
            str(action).strip()
            for action in item.get("historical_actions", [])
            if str(action).strip()
        )
        overlap = max((_action_overlap(source, best_action) for source in overlap_sources), default=0.0)
        if overlap >= 0.2:
            item["success_rate"] = round(min(0.99, float(item.get("success_rate", 0.0) or 0.0) + 0.04), 2)
            if runtime_executed:
                note = f"Runtime alignment: {best_action} tested as {best_outcome} in REPLICA. Memory + runtime combination strengthens confidence."
            else:
                note = f"Action alignment: {best_action} aligns with the historical pattern from this runbook."
            item["why_now_fit"] = f"{str(item.get('why_now_fit', '')).strip()} {note}".strip()
            item["evidence_tier"] = "runtime_backed" if runtime_executed else "inference_grounded"
    payload["runbooks"].sort(key=lambda item: float(item.get("success_rate", 0.0) or 0.0), reverse=True)

    for item in payload["similar_incidents"]:
        overlap = _action_overlap(str(item.get("prior_action", "")), best_action)
        if overlap >= 0.2:
            item["similarity"] = round(min(0.99, float(item.get("similarity", 0.0) or 0.0) + 0.04), 2)
            if runtime_executed and best_outcome in ("resolved", "improved"):
                runtime_boost = 0.06
                item["similarity"] = round(min(0.99, item["similarity"] + runtime_boost), 2)
                item["match_reason"] = (
                    f"{str(item.get('match_reason', '')).strip()} "
                    f"Runtime alignment: the prior action aligns with tested mitigation ({best_outcome})."
                )
                item["evidence_tier"] = "runtime_confirmed"
            else:
                item["match_reason"] = (
                    f"{str(item.get('match_reason', '')).strip()} "
                    f"Action pattern match: the prior action aligns with inferred next step."
                )
                item["evidence_tier"] = "pattern_aligned"
    payload["similar_incidents"].sort(
        key=lambda item: (
            bool(item.get("service_match")),
            bool(item.get("severity_match")),
            float(item.get("similarity", 0.0) or 0.0),
            float(item.get("success_rate", 0.0) or 0.0),
        ),
        reverse=True,
    )

    for item in payload["unresolved_items"]:
        if runtime_executed:
            follow_reason = (
                f"{str(item.get('follow_up_reason', '')).strip()} "
                f"Current runtime outcome: {best_action} was {best_outcome} in REPLICA. "
                f"This informs next steps: {'incident resolution is confirmed' if best_outcome == 'resolved' else 'partial progress made' if best_outcome == 'improved' else 'further investigation needed'}."
            )
        else:
            follow_reason = (
                f"{str(item.get('follow_up_reason', '')).strip()} "
                f"Current inferred outcome: {best_summary or f'{best_action} is inferred as next step.'}"
            )
        item["follow_up_reason"] = follow_reason.strip()

    return payload
