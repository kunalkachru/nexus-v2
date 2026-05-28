from server.integrations.models import IncomingIncidentWebhook
from server.models import NormalizedAlertEnvelope


class DatadogAlertNormalizer:
    def normalize(self, payload: IncomingIncidentWebhook) -> NormalizedAlertEnvelope:
        return NormalizedAlertEnvelope(
            source="datadog",
            external_id=payload.incident_id,
            title=payload.title,
            severity=payload.severity,
            service=str(payload.metrics.get("service", "")),
            detected_at=payload.detected_at,
            observed_values=payload.metrics,
        )


class PrometheusAlertNormalizer:
    def normalize(self, payload: IncomingIncidentWebhook) -> NormalizedAlertEnvelope:
        service_name = str(payload.metrics.get("service") or payload.metrics.get("job") or "")
        return NormalizedAlertEnvelope(
            source="prometheus",
            external_id=payload.incident_id,
            title=payload.title,
            severity=payload.severity,
            service=service_name,
            detected_at=payload.detected_at,
            observed_values=payload.metrics,
        )


class AlertNormalizer:
    def __init__(self) -> None:
        self._datadog = DatadogAlertNormalizer()
        self._prometheus = PrometheusAlertNormalizer()

    def normalize(self, payload: IncomingIncidentWebhook) -> NormalizedAlertEnvelope:
        if payload.monitoring_source == "datadog":
            return self._datadog.normalize(payload)
        return self._prometheus.normalize(payload)
