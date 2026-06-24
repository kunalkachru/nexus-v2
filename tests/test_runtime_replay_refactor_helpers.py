from server.services.replay import runtime_aligned_candidate_fixes


def test_runtime_aligned_candidate_fixes_keeps_auth_dependency_actions() -> None:
    fixes = runtime_aligned_candidate_fixes(
        "Auth dependency slowdown / token validation failures",
        "auth-svc",
    )

    assert fixes[0]["action"] == "Reset circuit breaker and force token cache invalidation to restore auth throughput"
    assert len(fixes) == 3
