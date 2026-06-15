import asyncio

from server.services.live_demo import build_demo_payload
from server.services.surface_payloads import build_incident_response
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
        orchestration = result.get("orchestration", {})
        task_board = (result.get("task_board") or {}).get("tasks", [])
        memory_hits = result.get("memory_hits", {})
        agent_metrics = result.get("agent_metrics", {})
        fallback_summary = result.get("fallback_summary", [])
        print("NEXUS v2 Judge Demo")
        print(f"Incident: {result['incident']['id']} - {result['incident']['name']}")
        print(f"Checkpoint: {result['checkpoint_path']}")
        print(f"Classification: {result['classification']}")
        print(f"Diagnosis: {result['diagnosis']}")
        print(f"Runbook: {result['runbook']}")
        print(f"Guardian: {result['guardian']}")
        print(f"Orchestration Story: {orchestration.get('active_story')}")
        print("Task Board:")
        for task in task_board:
            print(f"  - {task['owner']}: {task['title']} [{task['status']}] -> {task.get('handoff_to', '-')}")
            print(f"    {task['summary']}")
        print("Memory Hits:")
        print(
            "  "
            f"Similar incidents={len(memory_hits.get('similar_incidents', []))}, "
            f"Runbooks={len(memory_hits.get('runbooks', []))}, "
            f"Unresolved items={len(memory_hits.get('unresolved_items', []))}"
        )
        for item in memory_hits.get("similar_incidents", [])[:3]:
            print(f"    similar: {item['incident_id']} -> {item['summary']}")
        for item in memory_hits.get("unresolved_items", [])[:2]:
            print(f"    unresolved: {item['incident_id']} -> {item.get('title') or item.get('summary')}")
        print("Agent Metrics:")
        for name, metric in agent_metrics.items():
            print(
                f"  - {name}: confidence={metric.get('confidence')} "
                f"handoff={metric.get('handoff_to')} fallback={metric.get('fallback_used')}"
            )
        print(f"Fallback Summary: {fallback_summary or 'No fallback required'}")
        print(f"Execution Result: {result['execution_result']}")
        print(f"Final Reward: {result['final_reward']}")
        print(f"Execution Time Seconds: {result['execution_time_seconds']}")

    return result


def main() -> None:
    print("\n" + "="*70)
    print("NEXUS v3 End-to-End Demo: All 6 Workflow Stages")
    print("="*70)

    for incident_id in ["INC001", "INC002", "INC003"]:
        print(f"\n{'─'*70}")
        print(f"Incident: {incident_id}")
        print(f"{'─'*70}\n")

        response = build_incident_response(incident_id)
        incident = response["incident"]

        print(f"[SENTINEL] Classification")
        print(f"  ID: {incident['id']} — {incident['name']}")
        print(f"  Severity: {incident['severity']}")
        classification = response["classification"]
        print(f"  Reasoning: {classification['reasoning'][:100]}...")

        print(f"\n[PRISM] Diagnosis")
        diagnosis = response["diagnosis"]
        print(f"  Root cause: {diagnosis['root_cause']}")
        print(f"  Confidence: {diagnosis['confidence']}")
        print(f"  Reasoning: {diagnosis['reasoning'][:100]}...")

        print(f"\n[REPLICA] Runtime Evidence")
        replica = response["replica_summary"]
        print(f"  Status: {replica['reproduction_status']}")
        print(f"  Best mitigation: {replica['best_mitigation_action']}")
        print(f"  Outcome: {replica['best_mitigation_outcome_class']}")
        print(f"  Comparison: {replica['runtime_comparison_summary'][:100]}...")

        print(f"\n[TRACE] Investigation Depth")
        trace = response["trace_summary"]
        print(f"  Inspection point: {trace.get('inspection_point', 'N/A')[:100]}...")
        print(f"  Suspected modules: {trace.get('suspected_modules', [])}")
        print(f"  Anomalies: {len(trace.get('state_anomalies', []))} found")

        print(f"\n[FORGE] Runbook Selection")
        runbook = response["runbook"]
        print(f"  Proposed fix: {runbook['proposed_fix'][:60]}...")
        print(f"  Reasoning: {runbook['reasoning'][:120]}...")

        print(f"\n[GUARDIAN] Safety Posture")
        guardian = response["guardian"]
        print(f"  Decision: {guardian['decision'].upper()}")
        print(f"  Confidence: {guardian['confidence']}")
        print(f"  Reasoning: {guardian['reasoning'][:120]}...")

        print(f"\n[MEMORY] Historical Context")
        memory = response.get("memory_hits", {})
        print(f"  Similar incidents: {len(memory.get('similar_incidents', []))}")
        print(f"  Recommended runbooks: {len(memory.get('runbooks', []))}")
        if memory.get("runbooks"):
            for rb in memory.get("runbooks", [])[:1]:
                print(f"    • {rb.get('name')}: success_rate={rb.get('success_rate')}")
                if rb.get('why_now_fit'):
                    print(f"      Why now: {rb.get('why_now_fit')[:80]}...")

    print(f"\n{'─'*70}")
    print("Live graph demo (full agent orchestration for INC001):")
    print(f"{'─'*70}\n")
    run_demo(print_output=True)


if __name__ == "__main__":
    main()
