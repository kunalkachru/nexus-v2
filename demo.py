import asyncio

from server.services.live_demo import build_demo_payload
from training.reporting import CHECKPOINT_PATH, METRICS_PATH, ensure_metrics_payload, load_checkpoint


def run_demo(*, incident_id: str = "INC001", print_output: bool = False) -> dict[str, object]:
    metrics = ensure_metrics_payload()
    checkpoint = load_checkpoint()
    result = asyncio.run(build_demo_payload(incident_id))

    result.update({
        "checkpoint_path": str(CHECKPOINT_PATH),
        "metrics_path": str(METRICS_PATH),
        "checkpoint_final_difficulty": checkpoint["final_difficulty"],
        "trained_reward": checkpoint["reward_curve"][-1],
        "final_reward": round(result["reward"], 4),
        "execution_time_seconds": round(result["execution_time_ms"] / 1000, 4),
        "reward_curve_target": metrics["summary"]["trained_reward"],
    })

    if print_output:
        print("NEXUS v2 Judge Demo")
        print(f"Incident: {result['incident']['id']} - {result['incident']['name']}")
        print(f"Checkpoint: {result['checkpoint_path']}")
        print(f"Classification: {result['classification']}")
        print(f"Diagnosis: {result['diagnosis']}")
        print(f"Runbook: {result['runbook']}")
        print(f"Guardian: {result['guardian']}")
        print(f"Execution Result: {result['execution_result']}")
        print(f"Final Reward: {result['final_reward']}")
        print(f"Execution Time Seconds: {result['execution_time_seconds']}")

    return result


def main() -> None:
    run_demo(print_output=True)


if __name__ == "__main__":
    main()
