from __future__ import annotations

import re

_PRIORITY_ALIAS_MAP = {
    "CRITICAL": "P1",
    "URGENT": "P1",
    "HIGH": "P2",
    "MEDIUM": "P3",
    "NORMAL": "P3",
    "LOW": "P4",
    "INFO": "P5",
}

_PRIORITY_RANK_MAP = {
    "P0": 0,
    "P1": 1,
    "P2": 2,
    "P3": 3,
    "P4": 4,
}


def normalize_priority_label(value: str | None, *, default: str = "P3") -> str:
    normalized = str(value or "").strip().upper()
    if not normalized:
        return default
    if re.fullmatch(r"P\d+", normalized):
        return normalized
    return _PRIORITY_ALIAS_MAP.get(normalized, normalized)


def priority_rank(value: str | None) -> int:
    normalized = normalize_priority_label(value)
    if re.fullmatch(r"P\d+", normalized):
        return int(normalized[1:])
    return _PRIORITY_RANK_MAP.get(normalized, 3)


def shift_priority_label(value: str | None, *, delta: int = 1, default: str = "P3") -> str:
    normalized = normalize_priority_label(value, default=default)
    match = re.fullmatch(r"P(\d+)", normalized)
    if match:
        return f"P{int(match.group(1)) + max(0, delta)}"
    return normalized


def priority_snapshot(value: str | None, *, default: str = "P3") -> dict[str, object]:
    normalized = normalize_priority_label(value, default=default)
    return {
        "raw_label": str(value or "").strip() or default,
        "normalized_label": normalized,
        "rank": priority_rank(normalized),
    }
