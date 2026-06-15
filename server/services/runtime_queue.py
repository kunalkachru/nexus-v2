from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from server.artifacts import record_runtime_queue_job, update_runtime_queue_job, get_runtime_queue_jobs


JobState = Literal["queued", "running", "retrying", "recovered", "failed", "abandoned", "completed"]


@dataclass(frozen=True)
class RuntimeQueueJob:
    job_id: str
    incident_id: str
    state: JobState
    requested_at: str
    started_at: str | None = None
    finished_at: str | None = None
    recovery_outcome: str | None = None
    retry_count: int = 0
    error_message: str | None = None
    host_label: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "job_id": self.job_id,
            "incident_id": self.incident_id,
            "state": self.state,
            "requested_at": self.requested_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "recovery_outcome": self.recovery_outcome,
            "retry_count": self.retry_count,
            "error_message": self.error_message,
            "host_label": self.host_label,
        }


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class RuntimeQueueManager:
    @staticmethod
    async def queue_replay_job(
        *,
        incident_id: str,
        host_label: str | None = None,
    ) -> str:
        job_id = f"job_{uuid4().hex[:12]}"
        job = RuntimeQueueJob(
            job_id=job_id,
            incident_id=incident_id,
            state="queued",
            requested_at=_utc_now_iso(),
            host_label=host_label,
        )
        await record_runtime_queue_job(job.to_dict())
        return job_id

    @staticmethod
    async def start_job(job_id: str) -> None:
        await update_runtime_queue_job(
            job_id,
            {
                "state": "running",
                "started_at": _utc_now_iso(),
            },
        )

    @staticmethod
    async def complete_job(job_id: str) -> None:
        await update_runtime_queue_job(
            job_id,
            {
                "state": "completed",
                "finished_at": _utc_now_iso(),
            },
        )

    @staticmethod
    async def retry_job(job_id: str, error: str | None = None) -> None:
        jobs = get_runtime_queue_jobs()
        job_data = next((j for j in jobs if j.get("job_id") == job_id), None)
        if job_data:
            retry_count = int(job_data.get("retry_count", 0)) + 1
            await update_runtime_queue_job(
                job_id,
                {
                    "state": "retrying",
                    "retry_count": retry_count,
                    "error_message": error,
                },
            )

    @staticmethod
    async def recover_job(job_id: str, outcome: str) -> None:
        await update_runtime_queue_job(
            job_id,
            {
                "state": "recovered",
                "recovery_outcome": outcome,
                "finished_at": _utc_now_iso(),
            },
        )

    @staticmethod
    async def fail_job(job_id: str, error: str) -> None:
        await update_runtime_queue_job(
            job_id,
            {
                "state": "failed",
                "error_message": error,
                "finished_at": _utc_now_iso(),
            },
        )

    @staticmethod
    async def abandon_job(job_id: str) -> None:
        await update_runtime_queue_job(
            job_id,
            {
                "state": "abandoned",
                "finished_at": _utc_now_iso(),
            },
        )

    @staticmethod
    def get_jobs_for_incident(incident_id: str) -> list[RuntimeQueueJob]:
        jobs = get_runtime_queue_jobs()
        return [
            RuntimeQueueJob(**{k: v for k, v in job.items() if k in RuntimeQueueJob.__dataclass_fields__})
            for job in jobs
            if isinstance(job, dict) and job.get("incident_id") == incident_id
        ]

    @staticmethod
    def get_runtime_recovery_posture() -> dict[str, object]:
        jobs = get_runtime_queue_jobs()
        active_jobs = [j for j in jobs if isinstance(j, dict) and j.get("state") not in {"completed", "failed", "abandoned"}]
        recovered_jobs = [j for j in jobs if isinstance(j, dict) and j.get("state") == "recovered"]
        failed_jobs = [j for j in jobs if isinstance(j, dict) and j.get("state") == "failed"]

        recovery_status = "healthy" if not active_jobs else "recovering" if recovered_jobs else "degraded"
        return {
            "recovery_status": recovery_status,
            "active_jobs": len(active_jobs),
            "recovered_jobs": len(recovered_jobs),
            "failed_jobs": len(failed_jobs),
            "total_jobs": len(jobs),
            "has_active_work": len(active_jobs) > 0,
            "recovery_needed": len(failed_jobs) > 0 or (len(active_jobs) > 0 and len(recovered_jobs) > 0),
            "message": _recovery_posture_message(recovery_status, len(active_jobs), len(recovered_jobs)),
        }

    @staticmethod
    def get_incident_queue_state(incident_id: str) -> dict[str, object]:
        incident_jobs = RuntimeQueueManager.get_jobs_for_incident(incident_id)
        if not incident_jobs:
            return {
                "has_queue_history": False,
                "current_state": "no_queue_history",
                "message": "No runtime queue history for this incident.",
            }

        latest = incident_jobs[0] if incident_jobs else None
        if not latest:
            return {
                "has_queue_history": False,
                "current_state": "no_queue_history",
                "message": "No runtime queue history for this incident.",
            }

        return {
            "has_queue_history": True,
            "current_state": latest.state,
            "latest_job_id": latest.job_id,
            "latest_started_at": latest.started_at,
            "latest_finished_at": latest.finished_at,
            "retry_count": latest.retry_count,
            "error_message": latest.error_message,
            "recovery_outcome": latest.recovery_outcome,
            "total_attempts": len(incident_jobs),
            "message": _incident_queue_state_message(latest),
        }


def _recovery_posture_message(status: str, active: int, recovered: int) -> str:
    if status == "healthy":
        return "Runtime queue is healthy with no active jobs."
    elif status == "recovering":
        return f"Runtime queue is recovering: {active} active job(s), {recovered} successfully recovered."
    else:
        return f"Runtime queue is degraded: {active} active job(s) need attention."


def _incident_queue_state_message(job: RuntimeQueueJob) -> str:
    if job.state == "queued":
        return "Replay job is queued and waiting to run."
    elif job.state == "running":
        return f"Replay job is running (started {job.started_at})."
    elif job.state == "retrying":
        return f"Replay job failed and is retrying (attempt {job.retry_count + 1}). Error: {job.error_message}"
    elif job.state == "recovered":
        return f"Replay job recovered successfully. Outcome: {job.recovery_outcome}"
    elif job.state == "completed":
        return "Replay job completed."
    elif job.state == "failed":
        return f"Replay job failed permanently. Error: {job.error_message}"
    else:  # abandoned
        return "Replay job was abandoned."
