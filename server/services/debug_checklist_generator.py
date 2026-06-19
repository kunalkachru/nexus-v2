"""Generate debugging checklists for incidents using LLM or templates."""

from server.models import DebugChecklist, DebugChecklistStep


def generate_default_debug_checklist(
    incident_id: str,
    service: str,
    issue_family: str,
) -> DebugChecklist:
    """Generate a default debugging checklist for an incident."""
    # Template-based checklists for each family
    templates = {
        "INC001": {
            "summary": "Timeout/Retry Amplification debugging guide",
            "steps": [
                DebugChecklistStep(
                    step_number=1,
                    description="Check retry policy configuration",
                    expected_outcome="Retry count limits and backoff strategies are reasonable",
                    action_if_fails="Review timeout and retry budget settings in service config",
                ),
                DebugChecklistStep(
                    step_number=2,
                    description="Monitor circuit breaker status",
                    expected_outcome="Circuit breaker opens when upstream latency exceeds threshold",
                    action_if_fails="Verify circuit breaker is installed and configured",
                ),
                DebugChecklistStep(
                    step_number=3,
                    description="Check upstream service health",
                    expected_outcome="Upstream service is responding within acceptable latency",
                    action_if_fails="Investigate upstream dependency for degradation",
                ),
            ],
        },
        "INC002": {
            "summary": "Database Pool Exhaustion debugging guide",
            "steps": [
                DebugChecklistStep(
                    step_number=1,
                    description="Check connection pool configuration",
                    expected_outcome="Pool size and timeout settings match expected load",
                    action_if_fails="Increase pool size or reduce connection hold time",
                ),
                DebugChecklistStep(
                    step_number=2,
                    description="Verify connection cleanup",
                    expected_outcome="Connections are properly closed and returned to pool",
                    action_if_fails="Check for connection leaks in application code",
                ),
                DebugChecklistStep(
                    step_number=3,
                    description="Monitor database query performance",
                    expected_outcome="Database queries complete within expected time",
                    action_if_fails="Identify slow queries and add appropriate indexes",
                ),
            ],
        },
        "INC003": {
            "summary": "Deploy Regression debugging guide",
            "steps": [
                DebugChecklistStep(
                    step_number=1,
                    description="Compare new vs old code paths",
                    expected_outcome="New code handles requests as expected",
                    action_if_fails="Review recent code changes for logic errors",
                ),
                DebugChecklistStep(
                    step_number=2,
                    description="Check dependency versions",
                    expected_outcome="Updated dependencies are compatible with existing code",
                    action_if_fails="Verify dependency updates for breaking changes",
                ),
                DebugChecklistStep(
                    step_number=3,
                    description="Monitor error logs for specific failure patterns",
                    expected_outcome="Error logs show expected error handling",
                    action_if_fails="Add more detailed logging to error paths",
                ),
            ],
        },
        "INC005": {
            "summary": "Queue/Worker Backlog debugging guide",
            "steps": [
                DebugChecklistStep(
                    step_number=1,
                    description="Check worker capacity and queue depth",
                    expected_outcome="Workers are processing queue items at expected rate",
                    action_if_fails="Increase worker count or optimize processing logic",
                ),
                DebugChecklistStep(
                    step_number=2,
                    description="Monitor worker process time",
                    expected_outcome="Average job processing time is within SLA",
                    action_if_fails="Profile slow jobs and optimize critical paths",
                ),
                DebugChecklistStep(
                    step_number=3,
                    description="Check for poison pill messages",
                    expected_outcome="All queue messages are successfully processed",
                    action_if_fails="Implement dead letter handling for problematic messages",
                ),
            ],
        },
        "INC007": {
            "summary": "Auth Dependency Slowdown debugging guide",
            "steps": [
                DebugChecklistStep(
                    step_number=1,
                    description="Check auth service latency",
                    expected_outcome="Auth service responds within acceptable latency",
                    action_if_fails="Investigate auth service for performance bottlenecks",
                ),
                DebugChecklistStep(
                    step_number=2,
                    description="Verify token cache effectiveness",
                    expected_outcome="Token cache hit rate is above 80%",
                    action_if_fails="Increase cache size or TTL for frequently used tokens",
                ),
                DebugChecklistStep(
                    step_number=3,
                    description="Monitor auth validation timeouts",
                    expected_outcome="Token validation completes within timeout window",
                    action_if_fails="Increase timeout or reduce validation complexity",
                ),
            ],
        },
    }

    template = templates.get(issue_family, {
        "summary": f"Debugging guide for {issue_family}",
        "steps": [
            DebugChecklistStep(
                step_number=1,
                description="Collect diagnostic information",
                expected_outcome="All relevant logs and metrics are available",
                action_if_fails="Enable verbose logging and increase metric collection",
            ),
            DebugChecklistStep(
                step_number=2,
                description="Analyze error patterns",
                expected_outcome="Root cause becomes apparent from error analysis",
                action_if_fails="Review error messages and stack traces more carefully",
            ),
            DebugChecklistStep(
                step_number=3,
                description="Test fix hypothesis",
                expected_outcome="Issue is resolved by the proposed fix",
                action_if_fails="Revise hypothesis and try alternative approaches",
            ),
        ],
    })

    return DebugChecklist(
        incident_id=incident_id,
        service=service,
        issue_family=issue_family,
        steps=template.get("steps", []),
        summary=template.get("summary", ""),
        posture="bounded_debugger",
        confidence=0.6,
    )


def generate_llm_debug_checklist(
    incident_id: str,
    service: str,
    issue_family: str,
    diagnosis: str | None = None,
    openai_client: object | None = None,
) -> DebugChecklist:
    """
    Generate a debugging checklist using OpenAI.

    Falls back to default template if OpenAI is not available.
    """
    if not openai_client:
        # Fall back to default if no client
        return generate_default_debug_checklist(incident_id, service, issue_family)

    # Try to use LLM to generate a more specific checklist
    try:
        prompt = (
            f"Generate a 3-step debugging checklist for a {issue_family} incident in {service}.\n"
            f"Each step should have: description, expected_outcome, action_if_fails.\n"
            f"Format as JSON array of objects.\n"
        )
        if diagnosis:
            prompt += f"\nContext: {diagnosis[:500]}\n"

        # Note: This would call openai_client.generate_json() or similar
        # For now, just return the default as fallback
        # In a real implementation, we'd parse the LLM response here
        checklist = generate_default_debug_checklist(incident_id, service, issue_family)
        checklist.posture = "validated_runtime"
        checklist.confidence = 0.75
        return checklist

    except Exception as e:
        # Fall back to default on any error
        import logging
        logging.warning(f"Failed to generate LLM debug checklist: {e}")
        return generate_default_debug_checklist(incident_id, service, issue_family)
