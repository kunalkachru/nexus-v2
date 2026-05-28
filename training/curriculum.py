from collections import deque


class CurriculumAdapter:
    """Tracks difficulty progression for the deterministic Day 6 trainer."""

    LEVELS = ("Easy", "Medium", "Hard", "Nightmare", "Impossible")

    def __init__(self) -> None:
        self._index = 0
        self._recent_rewards: deque[float] = deque(maxlen=5)
        self.progression = [self.current_difficulty]

    @property
    def current_difficulty(self) -> str:
        """Return the current curriculum level."""

        return self.LEVELS[self._index]

    def observe_reward(self, reward: float) -> None:
        """Record a reward and advance if the last five average reaches 55%."""

        self._recent_rewards.append(reward)
        if (
            len(self._recent_rewards) == self._recent_rewards.maxlen
            and sum(self._recent_rewards) / len(self._recent_rewards) >= 0.55
            and self._index < len(self.LEVELS) - 1
        ):
            self._index += 1
            self.progression.append(self.current_difficulty)
            self._recent_rewards.clear()
