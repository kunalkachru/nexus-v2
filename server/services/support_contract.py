from __future__ import annotations

from typing import Final

RAW_TEXT_SUPPORTED_FAMILIES: Final[tuple[str, ...]] = (
    "INC001",
    "INC002",
    "INC003",
    "INC005",
    "INC006",
    "INC007",
)

FAMILY_METADATA: Final[dict[str, dict[str, object]]] = {
    "INC001": {
        "name": "Timeout/Retry Amplification",
        "short_description": "API timeout cascade and retry amplification incidents.",
        "guidance": {
            "category": "Timeout / Retry",
            "steps": [
                {"step": 1, "action": "Identify the slow upstream dependency", "expected": "One dependency clearly dominates latency", "if_fails": "Inspect recent network, database, and external API changes"},
                {"step": 2, "action": "Confirm retry policy behavior under failure", "expected": "Retry volume stays within expected bounds", "if_fails": "Temporarily reduce retries or tighten circuit breaking"},
                {"step": 3, "action": "Check customer-facing saturation metrics", "expected": "Latency and error rate correlate with the same bottleneck", "if_fails": "Look for load balancer or worker pool exhaustion"},
                {"step": 4, "action": "Apply a reversible mitigation", "expected": "Traffic stabilizes without widening blast radius", "if_fails": "Escalate to incident command and prepare rollback"},
            ],
        },
    },
    "INC002": {
        "name": "DB Pool Exhaustion",
        "short_description": "Database pool exhaustion or leaked session path incidents.",
        "guidance": {
            "category": "Database / Persistence",
            "steps": [
                {"step": 1, "action": "Check database connection pool usage", "expected": "Available connections remain above safety threshold", "if_fails": "Identify leaking sessions or runaway traffic"},
                {"step": 2, "action": "Inspect recent query and transaction changes", "expected": "No new long-lived or unbounded transactions", "if_fails": "Roll back the leaking change or disable the new path"},
                {"step": 3, "action": "Verify database health and resource headroom", "expected": "CPU, I/O, and replication remain healthy", "if_fails": "Scale the database or fail over safely"},
                {"step": 4, "action": "Recover connection capacity", "expected": "Pool pressure drops and request success recovers", "if_fails": "Escalate to database operations"},
            ],
        },
    },
    "INC003": {
        "name": "Deploy Regression / 5xx Spike",
        "short_description": "Deploy-linked regression causing elevated 5xx or crash rates.",
        "guidance": {
            "category": "Deploy / Rollout",
            "steps": [
                {"step": 1, "action": "Correlate the incident with recent deployments", "expected": "A recent deploy lines up with the error spike", "if_fails": "Expand scope to configuration or dependency changes"},
                {"step": 2, "action": "Inspect the changed code path or rollout diff", "expected": "One risky code or config change stands out", "if_fails": "Check infrastructure or feature-flag drift"},
                {"step": 3, "action": "Choose rollback or forward-fix path", "expected": "One mitigation path is clearly safer", "if_fails": "Escalate to platform lead before executing"},
                {"step": 4, "action": "Verify recovery after mitigation", "expected": "5xx rate and crash signals return to baseline", "if_fails": "Re-open root-cause analysis and check hidden dependencies"},
            ],
        },
    },
    "INC004": {
        "name": "Cache Cardinality Explosion",
        "short_description": "Cache or metrics cardinality growth causing memory exhaustion.",
        "guidance": {
            "category": "Caching / Memory",
            "steps": [
                {"step": 1, "action": "Measure key or label cardinality growth", "expected": "A single dimension or key pattern explains the explosion", "if_fails": "Inspect recent metrics and cache schema changes"},
                {"step": 2, "action": "Check cache memory pressure and eviction rate", "expected": "Resource pressure matches the cardinality change", "if_fails": "Look for unrelated memory leaks or traffic anomalies"},
                {"step": 3, "action": "Disable or roll back the offending dimension expansion", "expected": "Cardinality growth stops quickly", "if_fails": "Purge hot keys or scale the cluster temporarily"},
                {"step": 4, "action": "Confirm API latency recovers", "expected": "Dependent APIs return to normal response times", "if_fails": "Inspect downstream dependencies and backlog effects"},
            ],
        },
    },
    "INC005": {
        "name": "Queue / Worker Backlog",
        "short_description": "Queue lag, worker backlog, or consumer throughput collapse.",
        "guidance": {
            "category": "Queue / Worker Backlog",
            "steps": [
                {"step": 1, "action": "Measure lag, backlog, and throughput together", "expected": "Lag growth correlates with a clear throughput drop", "if_fails": "Inspect producer spikes or partition imbalance"},
                {"step": 2, "action": "Check consumer health and partition ownership", "expected": "Consumers are healthy and correctly assigned", "if_fails": "Rebalance or restart unhealthy workers"},
                {"step": 3, "action": "Inspect downstream enrichment or dependency calls", "expected": "One slow dependency explains per-message slowdown", "if_fails": "Profile worker code path directly"},
                {"step": 4, "action": "Apply reversible throughput recovery", "expected": "Lag stops growing and begins draining", "if_fails": "Scale consumers and escalate to streaming platform on-call"},
            ],
        },
    },
    "INC006": {
        "name": "Expired TLS Certificate",
        "short_description": "Public trust-boundary outage caused by expired or invalid TLS.",
        "guidance": {
            "category": "Certificate / Trust Boundary",
            "steps": [
                {"step": 1, "action": "Confirm certificate expiry or trust failure", "expected": "Handshake or cert validation failure is reproducible", "if_fails": "Check DNS, load balancer, and client trust chain"},
                {"step": 2, "action": "Inspect renewal or cert-manager pipeline", "expected": "A failed renewal or challenge explains the outage", "if_fails": "Check manual certificate changes or secret drift"},
                {"step": 3, "action": "Restore a valid certificate safely", "expected": "Public endpoints present a valid renewed certificate", "if_fails": "Escalate to security/edge reliability immediately"},
                {"step": 4, "action": "Verify customer traffic recovers", "expected": "Handshake errors disappear and success rate returns", "if_fails": "Check cached old certs or regional propagation lag"},
            ],
        },
    },
    "INC007": {
        "name": "Auth Dependency Slowdown",
        "short_description": "Auth validation slowdown or token dependency latency incident.",
        "guidance": {
            "category": "Auth / Identity",
            "steps": [
                {"step": 1, "action": "Check auth dependency latency and timeout path", "expected": "One auth dependency clearly regressed", "if_fails": "Inspect local auth service CPU, cache, and network path"},
                {"step": 2, "action": "Compare new-logins vs existing-session behavior", "expected": "Failure pattern matches token-validation path", "if_fails": "Inspect unrelated routing or session store issues"},
                {"step": 3, "action": "Review recent auth configuration changes", "expected": "A recent claim, cert, or policy change explains the slowdown", "if_fails": "Check third-party identity provider drift"},
                {"step": 4, "action": "Apply reversible auth mitigation", "expected": "Login success rate improves without widening risk", "if_fails": "Escalate to identity platform incident command"},
            ],
        },
    },
    "INC008": {
        "name": "Message Queue Issue",
        "short_description": "Catalogued but not wired raw-text queue-transport issue.",
        "guidance": {
            "category": "Message Queue / Transport",
            "steps": [
                {"step": 1, "action": "Check broker health and partition leadership", "expected": "Cluster control-plane remains healthy", "if_fails": "Escalate to messaging platform on-call"},
                {"step": 2, "action": "Inspect producer and consumer error logs", "expected": "One side clearly shows transport or auth failures", "if_fails": "Check broker network path and ACL drift"},
                {"step": 3, "action": "Validate retention and quota posture", "expected": "No quota or retention breach is blocking traffic", "if_fails": "Adjust quotas or drain backlog safely"},
                {"step": 4, "action": "Confirm message flow resumes", "expected": "Ingress and egress rates return to baseline", "if_fails": "Escalate to incident command"},
            ],
        },
    },
    "INC009": {
        "name": "CDN / Cache Invalidation Failure",
        "short_description": "CDN edge, purge, or invalidation drift incident.",
        "guidance": {
            "category": "CDN / Caching",
            "steps": [
                {"step": 1, "action": "Check CDN provider and purge status", "expected": "Provider health and purge calls are visible", "if_fails": "Open vendor escalation and inspect credentials"},
                {"step": 2, "action": "Verify origin cache headers and TTLs", "expected": "Origin headers match intended cache policy", "if_fails": "Correct cache-control configuration"},
                {"step": 3, "action": "Test from multiple geographic edges", "expected": "Edge behavior is consistent after purge", "if_fails": "Investigate regional propagation drift"},
                {"step": 4, "action": "Confirm customers see fresh content", "expected": "Stale reads disappear across affected paths", "if_fails": "Inspect surrogate keys and edge overrides"},
            ],
        },
    },
    "INC010": {
        "name": "ML Model Degradation",
        "short_description": "Model output quality or inference-quality regression.",
        "guidance": {
            "category": "ML / Model Degradation",
            "steps": [
                {"step": 1, "action": "Check current model version and rollout", "expected": "Deployed model version is known and recent", "if_fails": "Inspect model deployment history"},
                {"step": 2, "action": "Compare output quality to baseline", "expected": "A measurable regression is visible", "if_fails": "Inspect upstream data and evaluation pipeline"},
                {"step": 3, "action": "Review feature freshness and drift signals", "expected": "Feature inputs are current and consistent", "if_fails": "Escalate to feature pipeline owners"},
                {"step": 4, "action": "Rollback or retrain on the safest path", "expected": "Quality returns without widening customer risk", "if_fails": "Freeze rollout and escalate to ML platform"},
            ],
        },
    },
    "INC011": {
        "name": "Geographic Routing Failure",
        "short_description": "Regional edge or geography-specific routing incident.",
        "guidance": {
            "category": "Geographic / Routing",
            "steps": [
                {"step": 1, "action": "Map affected regions and unaffected controls", "expected": "A clear geographic pattern appears", "if_fails": "Treat as broader service incident"},
                {"step": 2, "action": "Inspect DNS, GSLB, or load-balancer routing policy", "expected": "Regional routing targets are healthy", "if_fails": "Check health checks and traffic steering policy"},
                {"step": 3, "action": "Test latency and reachability from affected edges", "expected": "Network path explains the routing imbalance", "if_fails": "Escalate to networking team"},
                {"step": 4, "action": "Apply reversible traffic steering fix", "expected": "Regional success rates converge toward baseline", "if_fails": "Move to incident command with provider escalation"},
            ],
        },
    },
}


def supported_family_ids() -> tuple[str, ...]:
    return RAW_TEXT_SUPPORTED_FAMILIES


def supported_family_display_lines() -> list[str]:
    return [f"{FAMILY_METADATA[incident_id]['name']} ({incident_id})" for incident_id in RAW_TEXT_SUPPORTED_FAMILIES]


def supported_family_names() -> list[str]:
    return [str(FAMILY_METADATA[incident_id]["name"]) for incident_id in RAW_TEXT_SUPPORTED_FAMILIES]


def supported_family_message() -> str:
    supported_lines = supported_family_display_lines()
    enumerated = ", ".join(f"{index}) {line}" for index, line in enumerate(supported_lines, start=1))
    return (
        f"This incident doesn't match any of the {len(RAW_TEXT_SUPPORTED_FAMILIES)} supported families: "
        f"{enumerated}. However, we've provided investigation guidance below to help you troubleshoot."
    )


def current_raw_text_wedge_summary() -> str:
    return f"{len(RAW_TEXT_SUPPORTED_FAMILIES)} bounded raw-text outage families remain the active pilot surface."


def guidance_for_incident_id(incident_id: str) -> dict[str, object]:
    metadata = FAMILY_METADATA.get(incident_id)
    if metadata is None:
        metadata = FAMILY_METADATA["INC003"]
    guidance = metadata.get("guidance", {})
    return dict(guidance) if isinstance(guidance, dict) else {}
