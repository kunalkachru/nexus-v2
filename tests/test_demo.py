from demo import run_demo


def test_demo_runs_end_to_end_under_five_seconds() -> None:
    result = run_demo()

    assert result["execution_time_seconds"] < 5.0
    assert result["classification"]
    assert result["diagnosis"]
    assert result["runbook"]
    assert result["execution_result"] in {"executed", "blocked_by_guardian"}
    assert 0.0 <= result["final_reward"] <= 1.0


def test_demo_output_contains_judge_facing_sections(capsys) -> None:
    run_demo(print_output=True)

    captured = capsys.readouterr().out

    assert "Classification:" in captured
    assert "Diagnosis:" in captured
    assert "Runbook:" in captured
    assert "Execution Result:" in captured
    assert "Final Reward:" in captured
