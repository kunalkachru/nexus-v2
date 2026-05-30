from demo import run_demo


def test_demo_runs_end_to_end_under_five_seconds() -> None:
    result = run_demo()

    assert result["execution_time_seconds"] < 5.0
    assert result["classification"]
    assert result["diagnosis"]
    assert result["runbook"]
    assert result["execution_result"] in {"executed", "blocked_by_guardian", "needs_modification"}
    assert 0.0 <= result["final_reward"] <= 1.0


def test_demo_output_contains_judge_facing_sections(capsys) -> None:
    run_demo(print_output=True)

    captured = capsys.readouterr().out

    assert "Incident:" in captured
    assert "Classification:" in captured
    assert "Diagnosis:" in captured
    assert "Runbook:" in captured
    assert "Guardian:" in captured
    assert "Execution Result:" in captured
    assert "Final Reward:" in captured


def test_demo_exposes_rich_observability_and_reasoning() -> None:
    result = run_demo(incident_id="INC004")

    assert result["incident"]["id"] == "INC004"
    assert len(result["observability"]["recent_logs"]) == 20
    assert len(result["observability"]["metrics"]) == 4
    assert result["classification"]["confidence_breakdown"]
    assert result["diagnosis"]["supporting_logs"]
    assert result["runbook"]["candidate_fixes"]
    assert result["guardian"]["safety_checks"]
    assert result["guardian"]["policy_id"]
    assert result["structured_result"]["proposed_fix"]
    assert result["structured_result"]["raw_priority_label"]
    assert result["structured_result"]["normalized_priority_rank"] >= 0
    assert result["structured_result"]["guardian_policy_id"]
