import math
from dataclasses import dataclass


@dataclass
class ScalarPolicy:
    """Lightweight scalar policy used for deterministic Day 6 training."""

    name: str
    weight: float = -0.0007
    scale: float = 1000.0

    def probability(self) -> float:
        """Return the action likelihood induced by the current scalar weight."""

        return 1.0 / (1.0 + math.exp(-(self.weight * self.scale)))

    def log_prob(self) -> float:
        """Return a stable log-probability for the chosen action."""

        return math.log(max(self.probability(), 1e-9))


@dataclass
class AdamScalarOptimizer:
    """Pure-Python Adam optimizer for a single scalar parameter."""

    lr: float = 1e-4
    beta1: float = 0.9
    beta2: float = 0.999
    eps: float = 1e-8
    m: float = 0.0
    v: float = 0.0
    t: int = 0

    def step(self, policy: ScalarPolicy, gradient: float) -> None:
        """Apply one Adam update step to the scalar policy weight."""

        self.t += 1
        self.m = self.beta1 * self.m + (1.0 - self.beta1) * gradient
        self.v = self.beta2 * self.v + (1.0 - self.beta2) * (gradient * gradient)
        m_hat = self.m / (1.0 - self.beta1**self.t)
        v_hat = self.v / (1.0 - self.beta2**self.t)
        policy.weight -= self.lr * m_hat / (math.sqrt(v_hat) + self.eps)


@dataclass
class TrainingStepRecord:
    """One agent action record used for on-policy GRPO-style updates."""

    agent_name: str
    action: str
    log_prob: float
    reward_contribution: float
    observation_digest: str
