import json

from training.curriculum import CurriculumAdapter
from training.policy import AdamScalarOptimizer, ScalarPolicy
from training.runner import load_agent_policies, run_training


def test_grpo_update_increases_policy_likelihood_of_good_actions() -> None:
    policy = ScalarPolicy(name="sentinel", weight=-0.6)
    optimizer = AdamScalarOptimizer(lr=1e-4)
    before = policy.probability()

    optimizer.step(policy, gradient=-800.0)

    assert policy.probability() > before


def test_curriculum_advances_after_fifty_five_percent_threshold() -> None:
    curriculum = CurriculumAdapter()

    for reward in [0.56, 0.57, 0.60, 0.58, 0.59]:
        curriculum.observe_reward(reward)

    assert curriculum.current_difficulty == "Medium"
    assert curriculum.progression == ["Easy", "Medium"]


def test_training_is_reproducible_with_seed(tmp_path) -> None:
    save_one = tmp_path / "curve-one.json"
    save_two = tmp_path / "curve-two.json"

    first = run_training(num_episodes=10, seed=42, save_curve_path=save_one)
    second = run_training(num_episodes=10, seed=42, save_curve_path=save_two)

    assert first.reward_curve == second.reward_curve
    assert first.cost_curve == second.cost_curve
    assert first.final_difficulty == second.final_difficulty


def test_thirty_episode_training_shows_reward_improvement() -> None:
    summary = run_training(num_episodes=30, seed=7)

    assert summary.reward_curve[0] <= 0.35
    assert summary.reward_curve[-1] >= 0.65
    assert summary.reward_curve[-1] > summary.reward_curve[0]
    assert summary.final_difficulty in {"Medium", "Hard", "Nightmare", "Impossible"}


def test_training_saves_reward_curve_and_tracks_episode_costs(tmp_path) -> None:
    save_path = tmp_path / "metrics.json"

    summary = run_training(num_episodes=5, seed=3, save_curve_path=save_path)

    assert len(summary.episode_records) == 5
    assert all(record.cost_usd >= 0.0 for record in summary.episode_records)
    assert round(summary.total_cost_usd, 6) == round(sum(summary.cost_curve), 6)

    saved = json.loads(save_path.read_text())
    assert saved["reward_curve"] == summary.reward_curve
    assert saved["cost_curve"] == summary.cost_curve


def test_training_records_agent_trajectories_with_observation_digests() -> None:
    summary = run_training(num_episodes=3, seed=7)

    first_step = summary.episode_records[0].steps[0]

    assert first_step.agent_name == "sentinel"
    assert first_step.log_prob < 0.0
    assert first_step.observation_digest


def test_training_updates_policy_parameters_after_positive_advantage() -> None:
    policies = load_agent_policies()
    baseline = policies["sentinel"].weight

    run_training(num_episodes=5, seed=7, policies=policies)

    assert policies["sentinel"].weight != baseline


def test_training_metrics_include_dashboard_summary_fields(tmp_path) -> None:
    save_path = tmp_path / "metrics.json"

    run_training(num_episodes=30, seed=7, save_curve_path=save_path)

    saved = json.loads(save_path.read_text())

    assert saved["summary"]["baseline_reward"] == 0.28
    assert saved["summary"]["trained_reward"] >= 0.65
    assert saved["summary"]["episode_count"] == 30
    assert saved["summary"]["average_cost_per_episode"] > 0.0
    assert saved["summary"]["execution_target_seconds"] == 5.0
    assert saved["agent_accuracy"]["sentinel"] >= 0.9
    assert saved["agent_accuracy"]["prism"] >= 0.75
    assert "forge" in saved["agent_accuracy"]
    assert "guardian" in saved["agent_accuracy"]
    assert saved["training_evaluation"]["reward_curve_final"] >= 0.65
    assert saved["reward_evaluation"]["reward_curve_delta"] >= 0.0
    assert saved["rl_episode_contract"]["observation"]["incident_id"]
    assert saved["rl_episode_contract"]["guardian_decision"] in {"approve", "reject", "request_modification"}
    assert saved["rl_episode_contract"]["raw_priority_label"]
    assert saved["rl_episode_contract"]["solution_proposal"]
    assert saved["rl_episode_contract"]["live_reasoning"] is False
    assert saved["artifact_summary"]
    assert "learning_contracts" in saved["artifact_summary"]
    assert "sentinel" in saved["training_evaluation"]["policy_drift"]


def test_training_persists_artifacts_durably(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    summary = run_training(num_episodes=4, seed=11)

    artifact_path = tmp_path / "artifacts" / "platform_artifacts.json"
    assert artifact_path.exists()

    payload = json.loads(artifact_path.read_text())
    assert len(payload["training_snapshots"]) >= 1
    assert len(payload["learning_contracts"]) >= 1
    assert payload["training_snapshots"][-1]["reward_curve"] == summary.reward_curve
