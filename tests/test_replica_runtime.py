import shutil
import subprocess
from pathlib import Path

from server.services.enterprise_runtime import build_replica_summary, enrich_memory_with_runtime, rank_candidate_fixes_with_runtime
from server.services.replica_runtime import ReplicaRunner, build_execution_plan, registry, select_environment_pack, trace_targets_for_plan


def test_replica_registry_exposes_two_flagship_packs() -> None:
    packs = registry()

    assert "checkout-python-fastapi-auth-redis-v1" in packs
    assert "checkout-python-fastapi-postgres-v1" in packs
    assert packs["checkout-python-fastapi-auth-redis-v1"].replay_profile == "checkout_retry_replay_v1"
    assert packs["checkout-python-fastapi-postgres-v1"].replay_profile == "checkout_write_replay_v1"


def test_replica_registry_respects_runtime_pack_root_override(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("NEXUS_REPLICA_PACKS_ROOT", str(tmp_path))

    packs = registry()

    assert packs["checkout-python-fastapi-auth-redis-v1"].compose_file == (
        tmp_path / "checkout-python-fastapi-auth-redis-v1" / "docker-compose.yml"
    )
    assert packs["checkout-python-fastapi-postgres-v1"].compose_file == (
        tmp_path / "checkout-python-fastapi-postgres-v1" / "docker-compose.yml"
    )


def test_select_environment_pack_prefers_retry_pack_for_timeout_cascade() -> None:
    pack = select_environment_pack(
        issue_family="Timeout cascade / retry amplification",
        service="auth-svc",
        recent_logs=["api-gateway retry budget exceeded", "auth-svc timeout after 5000ms"],
        recent_deployments=[{"service": "auth-svc", "change": "Retry middleware refactor"}],
    )

    assert pack is not None
    assert pack.pack_id == "checkout-python-fastapi-auth-redis-v1"


def test_select_environment_pack_prefers_postgres_pack_for_pool_exhaustion() -> None:
    pack = select_environment_pack(
        issue_family="Database pool exhaustion / session leak",
        service="checkout-svc",
        recent_logs=["SQLAlchemy QueuePool limit reached", "leaked session detected"],
        recent_deployments=[{"service": "checkout-svc", "change": "Retry-on-timeout patch"}],
    )

    assert pack is not None
    assert pack.pack_id == "checkout-python-fastapi-postgres-v1"


def test_build_execution_plan_returns_healthchecks_and_mitigation_sequence() -> None:
    plan = build_execution_plan(
        issue_family="Timeout cascade / retry amplification",
        service="auth-svc",
        recent_logs=["worker pool saturation", "circuit breaker still closed"],
        recent_deployments=[{"service": "auth-svc", "change": "Retry middleware refactor"}],
    )

    assert plan is not None
    assert plan.pack.pack_id == "checkout-python-fastapi-auth-redis-v1"
    assert "gateway" in plan.healthcheck_targets
    assert "cap_retries" in plan.mitigation_sequence


def test_replica_runner_inspects_pack_scaffold_assets() -> None:
    plan = build_execution_plan(
        issue_family="Database pool exhaustion / session leak",
        service="checkout-svc",
        recent_logs=["QueuePool limit reached", "session leak"],
        recent_deployments=[{"service": "checkout-svc", "change": "Retry-on-timeout patch"}],
    )

    assert plan is not None
    result = ReplicaRunner().inspect_plan(plan)
    assert result.pack_id == "checkout-python-fastapi-postgres-v1"
    assert result.compose_ready is True
    assert result.replay_ready is True
    assert result.mitigation_hooks_ready is True
    assert result.missing_assets == ()
    assert result.compose_config_valid is True
    assert "checkout" in result.services_seen
    assert "postgres" in result.services_seen


def test_trace_targets_follow_selected_pack_source_map() -> None:
    plan = build_execution_plan(
        issue_family="Timeout cascade / retry amplification",
        service="auth-svc",
        recent_logs=["retry budget exceeded", "worker saturation"],
        recent_deployments=[{"service": "auth-svc", "change": "Retry middleware refactor"}],
    )

    assert plan is not None
    targets = trace_targets_for_plan(plan)
    assert ("auth.middleware.retry", "apply_retry_policy") in targets
    assert ("gateway.timeout_guard", "await_upstream_auth") in targets


def test_replica_runner_executes_db_pool_pack() -> None:
    plan = build_execution_plan(
        issue_family="Database pool exhaustion / session leak",
        service="checkout-svc",
        recent_logs=["QueuePool limit reached", "session leak"],
        recent_deployments=[{"service": "checkout-svc", "change": "Retry-on-timeout patch"}],
    )

    assert plan is not None
    result = ReplicaRunner().execute_scaffold(plan)
    assert result.pack_id == "checkout-python-fastapi-postgres-v1"
    assert result.replay_status_code == 503
    assert result.mode == "runtime_scaffold"
    assert result.mitigation_status_codes
    assert len(result.mitigation_status_codes) == len(plan.mitigation_sequence)


def test_replica_runner_inspect_degrades_when_docker_binary_is_unavailable(monkeypatch) -> None:
    plan = build_execution_plan(
        issue_family="Timeout cascade / retry amplification",
        service="auth-svc",
        recent_logs=["retry budget exceeded", "worker saturation"],
        recent_deployments=[{"service": "auth-svc", "change": "Retry middleware refactor"}],
    )

    assert plan is not None

    monkeypatch.setattr(shutil, "which", lambda _: None)

    result = ReplicaRunner().inspect_plan(plan)
    assert result.docker_available is False
    assert result.compose_config_valid is False
    assert result.services_seen == ()


def test_replica_summary_keeps_pack_scaffold_when_docker_unavailable(monkeypatch) -> None:
    monkeypatch.delenv("NEXUS_RUNTIME_HOST_BASE_URL", raising=False)
    monkeypatch.delenv("NEXUS_RUNTIME_HOST_SHARED_TOKEN", raising=False)
    monkeypatch.setattr(shutil, "which", lambda _: None)

    summary = build_replica_summary(
        incident_id="INC001",
        triage_summary={
            "issue_family": "Timeout cascade / retry amplification",
            "likely_owner_service": "auth-svc",
        },
        root_cause="Runaway retry storm on downstream auth calls exhausted worker threads and drove API timeouts",
        recent_logs=[
            "09:05:12 WARN api-gateway retry budget exceeded for POST /payments after 4 upstream attempts",
            "09:05:34 ERROR auth-svc upstream timeout after 5000ms request_id=req-8e12",
            "09:06:01 WARN api-gateway worker pool saturation 93/96 workers busy",
        ],
        recent_deployments=[{"service": "auth-svc", "change": "Retry middleware refactor"}],
        candidate_fixes=[
            {"action": "Enable auth-svc circuit breaker and cap retries to 1", "success_rate": 0.91},
        ],
    )

    assert summary["runtime_mode"] == "pack_scaffold"
    assert summary["scaffold_ready"] is True
    assert summary["best_mitigation_outcome_class"] == "inferred_only"
    assert summary["mitigation_comparison"]["winner"]["action"] == "Enable auth-svc circuit breaker and cap retries to 1"
    assert summary["mitigation_comparison"]["runner_up"]["action"] == "Roll back auth-svc retry middleware"
    assert summary["runtime_capability"]["state"] == "host_unavailable"
    assert summary["runtime_capability"]["can_execute_replay"] is False
    assert "cannot execute Docker-backed replay" in summary["runtime_enablement_hint"]
    assert "Docker-backed replay is unavailable in the current app environment" in summary["reasoning"]


def test_replica_summary_reports_relay_available_when_runtime_host_configured(monkeypatch) -> None:
    monkeypatch.setenv("NEXUS_RUNTIME_HOST_BASE_URL", "http://runtime-host.internal")
    monkeypatch.setenv("NEXUS_RUNTIME_HOST_SHARED_TOKEN", "relay-secret")
    monkeypatch.setattr(shutil, "which", lambda _: None)

    summary = build_replica_summary(
        incident_id="INC001",
        triage_summary={
            "issue_family": "Timeout cascade / retry amplification",
            "likely_owner_service": "auth-svc",
        },
        root_cause="Runaway retry storm on downstream auth calls exhausted worker threads and drove API timeouts",
        recent_logs=[
            "09:05:12 WARN api-gateway retry budget exceeded for POST /payments after 4 upstream attempts",
            "09:05:34 ERROR auth-svc upstream timeout after 5000ms request_id=req-8e12",
        ],
        recent_deployments=[{"service": "auth-svc", "change": "Retry middleware refactor"}],
        candidate_fixes=[
            {"action": "Enable auth-svc circuit breaker and cap retries to 1", "success_rate": 0.91},
        ],
    )

    assert summary["runtime_capability"]["state"] == "relay_available"
    assert summary["runtime_capability"]["can_execute_replay"] is True
    assert summary["runtime_capability"]["host_label"] == "External runtime host"


def test_runtime_candidate_ranking_prefers_validated_mitigation() -> None:
    ranked = rank_candidate_fixes_with_runtime(
        [
            {"action": "Enable auth-svc circuit breaker and cap retries to 1", "success_rate": 0.84},
            {"action": "Drain hot gateway pods and scale replicas +2", "success_rate": 0.88},
        ],
        replica_summary={
            "best_mitigation_action": "Enable auth-svc circuit breaker and cap retries to 1",
            "best_mitigation_outcome_class": "resolved",
            "best_mitigation_duration_ms": 420,
            "replay_duration_ms": 1640,
        },
    )

    assert ranked[0]["action"] == "Enable auth-svc circuit breaker and cap retries to 1"
    assert ranked[0]["runtime_score"] >= ranked[1]["runtime_score"]


def test_runtime_memory_enrichment_links_validated_mitigation() -> None:
    memory_hits = enrich_memory_with_runtime(
        {
            "similar_incidents": [
                {
                    "incident_id": "INC-X",
                    "prior_action": "Enable auth-svc circuit breaker and cap retries to 1",
                    "similarity": 0.41,
                    "success_rate": 0.82,
                    "service_match": True,
                    "severity_match": True,
                    "match_reason": "Shared retry pattern.",
                }
            ],
            "runbooks": [
                {
                    "incident_id": "INC-X",
                    "runbook_summary": "Enable auth-svc circuit breaker and cap retries to 1",
                    "success_rate": 0.84,
                    "why_now_fit": "Historical mitigation favored reversible recovery.",
                }
            ],
            "unresolved_items": [{"incident_id": "INC-Y", "follow_up_reason": "Pending cleanup."}],
            "recent_guardian_outcomes": [],
        },
        replica_summary={
            "best_mitigation_action": "Enable auth-svc circuit breaker and cap retries to 1",
            "best_mitigation_outcome_class": "resolved",
            "best_mitigation_summary": "Enable auth-svc circuit breaker and cap retries to 1 finished in state resolved.",
        },
    )

    assert "Runtime overlap" in memory_hits["similar_incidents"][0]["match_reason"]
    assert "Runtime alignment" in memory_hits["runbooks"][0]["why_now_fit"]
    assert "Current runtime outcome" in memory_hits["unresolved_items"][0]["follow_up_reason"]
