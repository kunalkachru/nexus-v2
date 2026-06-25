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
    input_quality: dict[str, object]


class RawIncidentParser:
    def parse(
        self,
        raw_text: str,
        *,
        severity_hint: str | None = None,
        tenant_service_hints: list[str] | None = None,
    ) -> RawIncidentParseResult:
        text = raw_text.strip()
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        joined = " ".join(lines).lower()

        service, service_source, tenant_matches = self._infer_service(
            text,
            tenant_service_hints=tenant_service_hints or [],
        )
        severity, severity_source = self._infer_severity(text, severity_hint)
        signature = self._infer_signature(joined)
        symptoms = self._infer_symptoms(lines, service, severity, signature)
        evidence = self._build_evidence(lines, service, severity, signature)
        title = lines[0][:96] if lines else f"{service} incident"
        input_quality = self._build_input_quality(
            text=text,
            lines=lines,
            service=service,
            severity=severity,
            signature=signature,
            service_source=service_source,
            severity_source=severity_source,
            tenant_matches=tenant_matches,
        )

        return RawIncidentParseResult(
            title=title,
            service=service,
            severity=severity,
            symptoms=symptoms,
            signature=signature,
            evidence=evidence,
            input_quality=input_quality,
        )

    def _infer_service(
        self,
        raw_text: str,
        *,
        tenant_service_hints: list[str],
    ) -> tuple[str, str, list[str]]:
        patterns = [
            r"(?:service|svc|app)\s*[:=]\s*([a-z0-9._-]+)",
            r"\b([a-z0-9._-]+-api|[a-z0-9._-]+-worker|[a-z0-9._-]+-svc)\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, raw_text, re.IGNORECASE)
            if match:
                return match.group(1), "explicit", []
        tenant_matches = self._match_tenant_service_hints(raw_text, tenant_service_hints)
        if tenant_matches:
            return tenant_matches[0], "tenant_hint", tenant_matches
        return "unknown-service", "defaulted", []

    def _infer_severity(self, raw_text: str, severity_hint: str | None) -> tuple[str, str]:
        if severity_hint:
            return normalize_priority_label(severity_hint), "hint"
        severity_match = re.search(
            r"\b(?:severity|priority)\s*[:=]\s*(P\d)\b",
            raw_text,
            re.IGNORECASE,
        )
        if severity_match:
            return normalize_priority_label(severity_match.group(1)), "explicit"
        severity_match = re.search(r"\b(P\d)\b", raw_text, re.IGNORECASE)
        if severity_match:
            return normalize_priority_label(severity_match.group(1)), "explicit"
        for label, normalized in (
            ("critical", "P1"),
            ("urgent", "P1"),
            ("high", "P2"),
            ("medium", "P3"),
            ("normal", "P3"),
            ("low", "P4"),
        ):
            if label in raw_text.lower():
                return normalized, "keyword"
        if any(token in raw_text.lower() for token in ("panic", "outage", "customer impact", "down")):
            return "P1", "keyword"
        return "P2", "default"

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

    def _match_tenant_service_hints(self, raw_text: str, tenant_service_hints: list[str]) -> list[str]:
        lowered = raw_text.lower()
        matches: list[str] = []
        for hint in tenant_service_hints:
            normalized_hint = str(hint or "").strip().lower()
            if not normalized_hint:
                continue
            if re.search(rf"(?<![a-z0-9._-]){re.escape(normalized_hint)}(?![a-z0-9._-])", lowered):
                matches.append(str(hint).strip())
        return list(dict.fromkeys(matches))

    def _build_input_quality(
        self,
        *,
        text: str,
        lines: list[str],
        service: str,
        severity: str,
        signature: str,
        service_source: str,
        severity_source: str,
        tenant_matches: list[str],
    ) -> dict[str, object]:
        missing_signals: list[str] = []
        weak_signals: list[str] = []
        detected_markers: list[str] = []

        if service_source == "defaulted":
            missing_signals.append("service")
            weak_signals.append("No explicit or tenant-mapped service token was found in the pasted evidence.")
        else:
            detected_markers.append(f"service:{service_source}")

        if severity_source == "default":
            missing_signals.append("severity")
            weak_signals.append("No explicit severity was provided; the intake fell back to a default priority.")
        else:
            detected_markers.append(f"severity:{severity_source}")

        if signature == "General incident":
            weak_signals.append("The error signature stayed general, so family matching is still provisional.")
        else:
            detected_markers.append(f"signature:{signature.lower().replace(' ', '_').replace('/', '_')}")

        if len(lines) < 2:
            weak_signals.append("Add at least two concrete log or stack lines so the crew can frame the incident more reliably.")
        else:
            detected_markers.append("evidence:multi_line")

        if tenant_matches:
            detected_markers.append("tenant_hint:matched")

        score = 0.2 if lines else 0.0
        if len(lines) >= 2:
            score += 0.15
        if service_source != "defaulted":
            score += 0.25
        if severity_source != "default":
            score += 0.2
        if signature != "General incident":
            score += 0.15
        if tenant_matches:
            score += 0.05
        if re.search(r"\d{4}-\d{2}-\d{2}T", text):
            score += 0.05
            detected_markers.append("timestamp:present")
        score = round(min(score, 0.99), 2)

        if score >= 0.8 and not missing_signals:
            posture = "strong"
            operator_guidance = (
                "The intake is strong enough for bounded triage. Proceed to the incident console and use runtime replay where pack coverage exists."
            )
        elif score >= 0.45:
            posture = "partial"
            operator_guidance = (
                "Proceed with triage, but confirm the missing signals before approving execution or sending the engineering handoff."
            )
        else:
            posture = "weak"
            operator_guidance = (
                "Ask for the affected service, an explicit severity, and 2-3 concrete log lines before treating the investigation packet as decision-ready."
            )

        return {
            "normalization_posture": posture,
            "quality_score": score,
            "service_source": service_source,
            "severity_source": severity_source,
            "tenant_hints_applied": tenant_matches,
            "missing_signals": missing_signals,
            "weak_signals": weak_signals,
            "detected_markers": detected_markers,
            "evidence_line_count": len(lines),
            "operator_guidance": operator_guidance,
            "detected_service": service,
            "detected_severity": severity,
        }
