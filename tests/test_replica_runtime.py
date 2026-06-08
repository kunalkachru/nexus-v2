from server.services.replica_runtime import ReplicaRunner, build_execution_plan, registry, select_environment_pack, trace_targets_for_plan


def test_replica_registry_exposes_two_flagship_packs() -> None:
    packs = registry()

    assert "checkout-python-fastapi-auth-redis-v1" in packs
    assert "checkout-python-fastapi-postgres-v1" in packs
    assert packs["checkout-python-fastapi-auth-redis-v1"].replay_profile == "checkout_retry_replay_v1"
    assert packs["checkout-python-fastapi-postgres-v1"].replay_profile == "checkout_write_replay_v1"


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
