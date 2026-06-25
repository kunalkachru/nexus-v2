from typing import Any, Protocol

from fastapi import HTTPException

from server.models import SystemContext

SUPPORTED_RAW_TEXT_FAMILIES = {
    "INC001",
    "INC002",
    "INC003",
    "INC005",
    "INC006",
    "INC007",
}


class SupportsSentinel(Protocol):
    def classify(self, *, raw_symptoms: list[str], system_context: SystemContext) -> Any: ...


class SupportsParsedRawText(Protocol):
    service: str
    symptoms: list[str]


def investigation_guidance_for_keywords(raw_text: str) -> dict[str, object] | None:
    text_lower = raw_text.lower()

    if any(kw in text_lower for kw in ["cdn", "cache", "fastly", "cloudfront", "stale", "purge", "edge", "cache-control"]):
        return {
            "category": "CDN / Caching",
            "steps": [
                {"step": 1, "action": "Check CDN provider status page", "expected": "No active incidents reported", "if_fails": "Open ticket with CDN provider"},
                {"step": 2, "action": "Verify cache purge/invalidation was successful", "expected": "All edge nodes report cache miss after purge", "if_fails": "Check CDN API credentials and permissions"},
                {"step": 3, "action": "Check TTL settings and cache headers from origin", "expected": "Cache-Control headers match intended policy", "if_fails": "Update origin server cache headers or CDN config"},
                {"step": 4, "action": "Test from multiple geographic regions", "expected": "Fresh content appears consistently", "if_fails": "Check regional CDN configuration and propagation status"},
            ],
        }

    if any(kw in text_lower for kw in ["model", "ml", "recommendation", "prediction", "accuracy", "inference", "feature store", "generic output"]):
        return {
            "category": "ML / Model Degradation",
            "steps": [
                {"step": 1, "action": "Check model version in production", "expected": "Expected model version is deployed", "if_fails": "Verify model deployment pipeline"},
                {"step": 2, "action": "Compare current model outputs to baseline", "expected": "Quality metrics match or exceed baseline", "if_fails": "Consider rolling back to previous model version"},
                {"step": 3, "action": "Check feature pipeline health", "expected": "Feature store has recent data without gaps", "if_fails": "Investigate feature pipeline failures and data drift"},
                {"step": 4, "action": "Verify training data hasn't changed unexpectedly", "expected": "Training data distribution matches baseline", "if_fails": "Retrain model on current data or rollback"},
            ],
        }

    if any(kw in text_lower for kw in ["region", "geography", "country", "geo", "routing", "isp", "latency by region", "user location"]):
        return {
            "category": "Geographic / Routing",
            "steps": [
                {"step": 1, "action": "Identify affected geographic regions", "expected": "Clear pattern of affected vs unaffected regions", "if_fails": "Check if issue is truly geographic or service-wide"},
                {"step": 2, "action": "Check regional load balancer configuration", "expected": "All regions have healthy endpoints", "if_fails": "Update load balancer routing policies"},
                {"step": 3, "action": "Verify DNS propagation across regions", "expected": "DNS resolves to correct regional endpoints", "if_fails": "Check Route53 health checks or DNS configuration"},
                {"step": 4, "action": "Test latency and connectivity from affected region", "expected": "Network path is healthy and routes through proper endpoints", "if_fails": "Check ISP routing, BGP announcements, or Anycast configuration"},
            ],
        }

    if any(kw in text_lower for kw in ["database", "postgres", "mysql", "mongo", "sql"]):
        return {
            "category": "Database / Persistence",
            "steps": [
                {"step": 1, "action": "Check database connection pool status", "expected": "Available connections above threshold", "if_fails": "Identify connection leaks or excessive usage"},
                {"step": 2, "action": "Verify query performance", "expected": "Slow query logs show expected latencies", "if_fails": "Look for missing indexes or inefficient queries"},
                {"step": 3, "action": "Check database replication lag", "expected": "Replica lag is within acceptable bounds", "if_fails": "Investigate replication bottleneck or failover"},
                {"step": 4, "action": "Verify disk space and I/O metrics", "expected": "No resource exhaustion detected", "if_fails": "Scale database resources or clean up unused data"},
            ],
        }

    if any(kw in text_lower for kw in ["deploy", "release", "rollout", "version", "update"]):
        return {
            "category": "Deploy / Rollout",
            "steps": [
                {"step": 1, "action": "Identify recent deployment that correlates with incident", "expected": "Clear timeline match between deploy and error spike", "if_fails": "Look for other infrastructure changes"},
                {"step": 2, "action": "Review changes in the deployment", "expected": "Find potentially problematic code changes", "if_fails": "Check configuration changes or dependency updates"},
                {"step": 3, "action": "Consider rollback vs in-place fix", "expected": "Safe mitigation path identified", "if_fails": "Escalate to platform team for deployment safety review"},
                {"step": 4, "action": "Execute mitigation and verify recovery", "expected": "Error rate drops and metrics normalize", "if_fails": "Check if deployment change was actually the root cause"},
            ],
        }

    return {
        "category": "General Incident Investigation",
        "steps": [
            {"step": 1, "action": "Gather comprehensive symptoms and timeline", "expected": "Clear description of when issue started and what changed", "if_fails": "Review monitoring data and correlation with changes"},
            {"step": 2, "action": "Check all relevant service dependencies", "expected": "Identify which services are affected and healthy", "if_fails": "Expand search to infrastructure and external services"},
            {"step": 3, "action": "Review recent changes across all systems", "expected": "Identify candidate root causes", "if_fails": "Check for subtle configuration drifts or timing issues"},
            {"step": 4, "action": "Validate hypothesis with targeted testing", "expected": "Confirm root cause before implementing fix", "if_fails": "Refine hypothesis and test again"},
        ],
    }


def validate_supported_raw_text_classification(
    *,
    sentinel: SupportsSentinel,
    parsed: SupportsParsedRawText,
    raw_text: str,
) -> Any:
    system_context = SystemContext(
        service=parsed.service,
        language="Unknown",
        infra="Unknown",
        dependencies=[],
    )
    classification = sentinel.classify(
        raw_symptoms=parsed.symptoms,
        system_context=system_context,
    )
    if classification.incident_id in SUPPORTED_RAW_TEXT_FAMILIES:
        return classification

    raise HTTPException(
        status_code=400,
        detail={
            "error": "unsupported_incident_type",
            "message": (
                "This incident doesn't match any of the 6 supported families: "
                "1) Timeout/Retry Amplification (INC001), "
                "2) DB Pool Exhaustion (INC002), "
                "3) Deploy Regression / 5xx Spike (INC003), "
                "4) Queue / Worker Backlog (INC005), "
                "5) Expired TLS Certificate (INC006), "
                "6) Auth Dependency Slowdown (INC007). "
                "However, we've provided investigation guidance below to help you troubleshoot."
            ),
            "confidence": float(classification.confidence),
            "matched_family": classification.incident_name,
            "matched_id": classification.incident_id,
            "supported": False,
            "general_investigation": investigation_guidance_for_keywords(raw_text),
            "supported_families": [
                "Timeout/Retry Amplification",
                "DB Pool Exhaustion",
                "Deploy Regression / 5xx Spike",
                "Queue / Worker Backlog",
                "Expired TLS Certificate",
                "Auth Dependency Slowdown",
            ],
        },
    )
