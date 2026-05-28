from __future__ import annotations


def evaluate_training(summary) -> dict[str, object]:
    return {
        "reward_curve_final": round(summary.reward_curve[-1], 2) if summary.reward_curve else 0.0,
        "reward_curve_peak": round(max(summary.reward_curve), 2) if summary.reward_curve else 0.0,
        "policy_drift": dict(summary.policy_weights),
    }
