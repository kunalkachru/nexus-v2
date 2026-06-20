from datetime import datetime, timezone
from dataclasses import dataclass


@dataclass
class SubsystemHealth:
    """Health status of a subsystem."""
    status: str
    guidance: list[str]
    next_checks: list[str]
    summary: str = ""


class HealthService:
    """Service for computing platform health status."""

    def check_queue_health(self, queue_items: list) -> SubsystemHealth:
        """Check incident queue health based on queue depth."""
        queue_health = "healthy" if len(queue_items) < 100 else "degraded" if len(queue_items) < 500 else "unhealthy"
        queue_guidance = []
        queue_next_checks = []

        if queue_health == "degraded":
            queue_guidance.append("Queue depth is elevated. Review incident backlog and consider pausing intake.")
            queue_next_checks = [
                "Review the queue backlog and confirm intake is not spiking faster than operators can close cases.",
                "Pause non-critical manual intake if queue depth keeps rising.",
            ]
        elif queue_health == "unhealthy":
            queue_guidance.append("Queue is critically backlogged. Pause incident intake and investigate queue processing.")
            queue_next_checks = [
                "Pause new intake until the backlog returns to the bounded operating range.",
                "Check queue processing throughput and any database or worker contention behind the backlog.",
            ]

        return SubsystemHealth(
            status=queue_health,
            guidance=queue_guidance,
            next_checks=queue_next_checks,
            summary="Incident queue is outside the normal operating range." if queue_health != "healthy" else "Queue is operating within normal bounds.",
        )

    def check_memory_health(self, service) -> SubsystemHealth:
        """Check memory/knowledge base availability."""
        memory_health = "available"
        memory_guidance = []
        if not hasattr(service, 'memory') or service.memory is None:
            memory_health = "unavailable"
            memory_guidance.append("Memory service (knowledge base) is not available. Incidents will be triaged without historical context.")

        memory_next_checks = (
            [
                "Confirm the bounded memory layer is loaded before treating historical matches as available.",
                "Proceed with inference-first triage until memory becomes available again.",
            ]
            if memory_health != "available"
            else []
        )

        return SubsystemHealth(
            status=memory_health,
            guidance=memory_guidance,
            next_checks=memory_next_checks,
            summary="Historical memory is unavailable, so triage should stay inference-first." if memory_health != "available" else "Knowledge base is available.",
        )

    def check_delivery_health(self, deployment_readiness: dict) -> SubsystemHealth:
        """Check downstream delivery integration health."""
        delivery_health = "healthy"
        delivery_guidance = []
        delivery_next_checks = []
        deployment_readiness_str = deployment_readiness.get("readiness", "")

        if deployment_readiness_str == "partially_available":
            delivery_health = "degraded"
            delivery_guidance.append("Some downstream integrations are unavailable. Check GitHub and Slack connectivity.")
            delivery_next_checks = [
                "Check which delivery destinations are degraded before promising downstream handoff completion.",
                "Retry only the affected destination once connectivity or configuration is restored.",
            ]
        elif deployment_readiness_str != "fully_available":
            delivery_health = "unhealthy"
            delivery_guidance.append("Downstream delivery is blocked. Verify integration configuration and connectivity.")
            delivery_next_checks = [
                "Treat downstream export and send actions as blocked until integration readiness returns.",
                "Verify destination credentials, network reachability, and runtime-host dependent features before retrying.",
            ]

        return SubsystemHealth(
            status=delivery_health,
            guidance=delivery_guidance,
            next_checks=delivery_next_checks,
            summary="Downstream handoff destinations need operator review before promising delivery completion." if delivery_health != "healthy" else "Delivery integrations are healthy.",
        )

    def check_replay_health(self, execution_state, deployment_readiness: dict) -> SubsystemHealth:
        """Check replay/replay execution health."""
        execution_health = "idle" if execution_state.current_state == "idle" else "running"
        replay_health = execution_health
        replay_guidance = []
        replay_next_checks = []

        if execution_health == "running":
            replay_guidance.append("Replay is currently executing. Monitor the bounded pack progress.")
            replay_next_checks = [
                "Wait for the current bounded replay to finish before starting another replay for the same incident.",
            ]
        elif not deployment_readiness.get("docker", {}).get("available", False):
            replay_health = "unavailable"
            replay_guidance.append("Docker is not available. Bounded replay requires Docker to be installed and running.")
            replay_next_checks = [
                "Restore Docker or enable the runtime-host relay before claiming runtime-backed validation.",
                "Use inference-first triage and keep approval language bounded until replay is available again.",
            ]

        return SubsystemHealth(
            status=replay_health,
            guidance=replay_guidance,
            next_checks=replay_next_checks,
            summary="Replay is not currently available for runtime-backed validation." if replay_health not in ["idle", "running"] else "Replay is available.",
        )

    def check_runtime_queue_health(self, runtime_recovery: dict) -> SubsystemHealth:
        """Check runtime queue health."""
        runtime_queue_status = runtime_recovery.get("recovery_status") or "unknown"
        runtime_queue_guidance = []
        runtime_queue_next_checks = []

        if runtime_queue_status == "recovering":
            runtime_queue_guidance.append("Runtime queue recovered recent replay work after an interruption. Review recovered jobs before relaunching.")
            runtime_queue_next_checks = [
                "Review recovered runtime jobs before rerunning the same incident replay.",
                "Confirm the latest replay outcome was persisted before approving follow-on actions.",
            ]
        elif runtime_queue_status == "degraded":
            runtime_queue_guidance.append("Runtime queue has failed or stranded work that needs operator review.")
            runtime_queue_next_checks = [
                "Inspect failed or stranded runtime jobs before launching more replay work.",
                "Retry only jobs marked retryable and avoid duplicate launches for the same incident until state is clear.",
            ]

        return SubsystemHealth(
            status=runtime_queue_status,
            guidance=runtime_queue_guidance,
            next_checks=runtime_queue_next_checks,
        )
