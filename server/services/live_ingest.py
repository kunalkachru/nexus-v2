from __future__ import annotations

import re
from dataclasses import dataclass

from server.services.priority import normalize_priority_label


@dataclass(slots=True)
class RawIncidentParseResult:
    title: str
    service: str
    severity: str
    symptoms: list[str]
    signature: str
    evidence: list[str]


class RawIncidentParser:
    def parse(self, raw_text: str, *, severity_hint: str | None = None) -> RawIncidentParseResult:
        text = raw_text.strip()
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        joined = " ".join(lines).lower()

        service = self._infer_service(text) or "unknown-service"
        severity = self._infer_severity(text, severity_hint)
        signature = self._infer_signature(joined)
        symptoms = self._infer_symptoms(lines, service, severity, signature)
        evidence = self._build_evidence(lines, service, severity, signature)
        title = lines[0][:96] if lines else f"{service} incident"

        return RawIncidentParseResult(
            title=title,
            service=service,
            severity=severity,
            symptoms=symptoms,
            signature=signature,
            evidence=evidence,
        )

    def _infer_service(self, raw_text: str) -> str:
        patterns = [
            r"(?:service|svc|app)\s*[:=]\s*([a-z0-9._-]+)",
            r"\b([a-z0-9._-]+-api|[a-z0-9._-]+-worker|[a-z0-9._-]+-svc)\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, raw_text, re.IGNORECASE)
            if match:
                return match.group(1)
        return ""

    def _infer_severity(self, raw_text: str, severity_hint: str | None) -> str:
        if severity_hint:
            return normalize_priority_label(severity_hint)
        severity_match = re.search(r"\b(P\d+)\b", raw_text, re.IGNORECASE)
        if severity_match:
            return normalize_priority_label(severity_match.group(1))
        for label, normalized in (
            ("critical", "P1"),
            ("urgent", "P1"),
            ("high", "P2"),
            ("medium", "P3"),
            ("normal", "P3"),
            ("low", "P4"),
        ):
            if label in raw_text.lower():
                return normalized
        if any(token in raw_text.lower() for token in ("panic", "outage", "customer impact", "down")):
            return "P1"
        return "P2"

    def _infer_signature(self, joined: str) -> str:
        if "timeout" in joined:
            return "Timeout / queue pressure"
        if any(token in joined for token in ("sql", "postgres", "mysql", "database")):
            return "Database / connection pool pressure"
        if any(token in joined for token in ("memory", "rss", "oom")):
            return "Memory pressure / leak"
        if any(token in joined for token in ("auth", "unauthorized", "permission")):
            return "Auth / permission failure"
        if any(token in joined for token in ("exception", "traceback", "panic")):
            return "Unhandled exception"
        return "General incident"

    def _infer_symptoms(self, lines: list[str], service: str, severity: str, signature: str) -> list[str]:
        symptoms = [signature]
        for line in lines[:4]:
            if len(line) < 180:
                symptoms.append(line)
        symptoms.append(f"service={service}")
        symptoms.append(f"severity={severity}")
        return list(dict.fromkeys(symptoms))

    def _build_evidence(self, lines: list[str], service: str, severity: str, signature: str) -> list[str]:
        evidence = [
            f"Detected service: {service}",
            f"Severity hint: {severity}",
            f"Signature: {signature}",
        ]
        evidence.extend(lines[:3])
        return evidence
