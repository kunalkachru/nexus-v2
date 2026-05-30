from __future__ import annotations


def evaluate_training(summary) -> dict[str, object]:
    reward_curve = summary.reward_curve or []
    reward_delta = round(reward_curve[-1] - reward_curve[0], 2) if len(reward_curve) > 1 else 0.0
    return {
        "reward_curve_final": round(reward_curve[-1], 2) if reward_curve else 0.0,
        "reward_curve_peak": round(max(reward_curve), 2) if reward_curve else 0.0,
        "reward_curve_delta": reward_delta,
        "reward_curve_mean": round(sum(reward_curve) / len(reward_curve), 2) if reward_curve else 0.0,
        "policy_drift": dict(summary.policy_weights),
    }
