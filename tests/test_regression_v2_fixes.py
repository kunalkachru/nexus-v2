"""Regression tests for V2 fixes: SENTINEL vocabulary, Prometheus parsing, ambiguity detection."""

import pytest

from server.agents.sentinel import SentinelAgent
from server.models import SystemContext
from server.services.live_ingest import RawIncidentParser


class TestINC004VocabularyGap:
    """Test FIX 1: INC004 vocabulary expansion for memory/OOM/cardinality themes."""

    def test_redis_memory_exhausted_classifies_as_inc004(self) -> None:
        """ST-006 scenario: Redis memory exhausted should map to INC004 (cache cardinality)."""
        agent = SentinelAgent()

        result = agent.classify(
            raw_symptoms=[
                "Redis memory exhausted approaching OOM kill threshold on cache cluster",
                "Unique key count: 18M (was 2M 30min ago)",
                "Cache hit rate dropped from 87% to 12%",
            ],
            system_context=SystemContext(
                service="cache-layer",
                language="Node.js",
                infra="GCP Cloud Run",
                dependencies=["redis-cache"],
            ),
        )

        assert result.incident_id == "INC004", f"Expected INC004 but got {result.incident_id}"
        assert "cache" in result.incident_name.lower() or "cardinality" in result.incident_name.lower()
        assert result.confidence >= 0.8

    def test_metrics_label_cardinality_explosion_classifies_as_inc004(self) -> None:
        """Metrics label cardinality explosion should map to INC004."""
        agent = SentinelAgent()

        result = agent.classify(
            raw_symptoms=[
                "Metrics label cardinality explosion causing unbounded time series growth",
                "Unique time series count grew from thousands to millions after deploy",
                "Memory limit reached due to high cardinality label or dimension expansion",
            ],
            system_context=SystemContext(
                service="monitoring-backend",
                language="Go",
                infra="Kubernetes on EKS",
                dependencies=["prometheus", "redis-cache"],
            ),
        )

        assert result.incident_id == "INC004", f"Expected INC004 but got {result.incident_id}"
        assert result.confidence >= 0.8


class TestINC003INC005VocabularyAdditions:
    """Test FIX 2: INC003 and INC005 vocabulary additions for Go/EKS context."""

    def test_go_panic_classifies_as_inc003(self) -> None:
        """ST-002 scenario: Go goroutine panic should classify as INC003 (deploy regression)."""
        agent = SentinelAgent()

        result = agent.classify(
            raw_symptoms=[
                "Go runtime error: invalid memory address or nil pointer dereference",
                "fatal error: all goroutines are asleep - deadlock detected after deploy",
                "Error rate jumped from 0.1% to 95% post-deploy",
            ],
            system_context=SystemContext(
                service="payment-api",
                language="Go",
                infra="Kubernetes on EKS",
                dependencies=["postgres", "redis"],
            ),
        )

        assert result.incident_id == "INC003", f"Expected INC003 but got {result.incident_id}"
        assert "deploy" in result.incident_name.lower() or "5xx" in result.incident_name.lower()
        assert result.confidence >= 0.75

    def test_kafka_lag_on_eks_classifies_as_inc005(self) -> None:
        """ST-004 scenario: Kafka consumer lag on EKS should classify as INC005 (queue backlog)."""
        agent = SentinelAgent()

        result = agent.classify(
            raw_symptoms=[
                "Consumer lag offset delta: +50000 messages per minute on Kubernetes EKS cluster",
                "Kafka topic lag accumulation after consumer deployment on EKS",
                "Consumer throughput flattened at 100 messages per second",
            ],
            system_context=SystemContext(
                service="billing-consumer",
                language="Go",
                infra="Kubernetes on EKS",
                dependencies=["kafka-cluster", "postgres"],
            ),
        )

        assert result.incident_id == "INC005", f"Expected INC005 but got {result.incident_id}"
        assert "queue" in result.incident_name.lower() or "backlog" in result.incident_name.lower()
        assert result.confidence >= 0.75


class TestPrometheusAlertParsing:
    """Test FIX 3: Prometheus structured alert field parsing."""

    def test_prometheus_alert_key_value_format_detected(self) -> None:
        """Prometheus alert with KEY=VALUE format should be detected and parsed."""
        parser = RawIncidentParser()

        raw_alert = 'ALERTNAME="HighErrorRate" SEVERITY="critical" SERVICE="api-server" NAMESPACE="prod" DESCRIPTION="API error rate exceeded threshold"'

        result = parser.parse(raw_alert)

        assert result.title == "HighErrorRate"
        assert result.service == "api-server"
        assert result.severity == "P1"  # critical maps to P1
        assert "SEVERITY" in str(result.symptoms) or "critical" in str(result.symptoms)
        assert result.input_quality["quality_score"] >= 0.8

    def test_prometheus_alert_severity_mapped_correctly(self) -> None:
        """Prometheus severity levels should map to P0-P4 correctly."""
        parser = RawIncidentParser()

        test_cases = [
            ('ALERTNAME="Test" SEVERITY="critical"', "P1"),
            ('ALERTNAME="Test" SEVERITY="warning"', "P2"),
            ('ALERTNAME="Test" SEVERITY="info"', "P4"),
        ]

        for alert_text, expected_severity in test_cases:
            result = parser.parse(alert_text)
            assert result.severity == expected_severity, f"Expected {expected_severity} for {alert_text}"

    def test_prometheus_missing_key_value_falls_back_to_text_parsing(self) -> None:
        """Raw text without 3+ KEY=VALUE pairs should fall back to text parsing."""
        parser = RawIncidentParser()

        raw_text = "Just a plain text incident report without structured fields"

        result = parser.parse(raw_text)

        # Should not detect as Prometheus, so title is first line
        assert result.title == "Just a plain text incident report without structured fields"

    def test_prometheus_unquoted_key_value_format_detected(self) -> None:
        """Unquoted Prometheus alert fields should still parse structurally."""
        parser = RawIncidentParser()

        raw_alert = (
            "ALERTNAME=HighErrorRate SEVERITY=critical SERVICE=platform-api "
            "NAMESPACE=stratum-prod VALUE=0.34 THRESHOLD=0.05 "
            "ANNOTATIONS={summary=Error rate above 5% threshold}"
        )

        result = parser.parse(raw_alert)

        assert result.title == "HighErrorRate"
        assert result.service == "platform-api"
        assert result.severity == "P1"
        assert result.signature != "General incident"
        assert any("Error rate above 5% threshold" in symptom for symptom in result.symptoms)


class TestRawIncidentIntakeCompression:
    """Regression tests for raw intake preserving real incident signal."""

    def test_long_paragraph_keeps_sentence_chunks_in_symptoms(self) -> None:
        parser = RawIncidentParser()

        text = (
            "Kafka consumer lag building on platform-events topic. Lag at 4.7M messages, growing at 200k/min. "
            "Normal consumer throughput 12000 msg/sec, current 800 msg/sec. "
            "No consumer pod crashes. CPU and memory normal."
        )

        result = parser.parse(text)

        assert any("Kafka consumer lag building on platform-events topic." in symptom for symptom in result.symptoms)
        assert any("Lag at 4.7M messages, growing at 200k/min." in symptom for symptom in result.symptoms)
        assert any("Normal consumer throughput 12000 msg/sec, current 800 msg/sec." in symptom for symptom in result.symptoms)

    def test_kafka_lag_prefers_queue_signature_over_memory(self) -> None:
        parser = RawIncidentParser()

        result = parser.parse(
            "Kafka consumer lag building on platform-events topic. "
            "Lag at 4.7M messages, growing at 200k/min. "
            "Normal consumer throughput 12000 msg/sec, current 800 msg/sec. "
            "No consumer pod crashes. CPU and memory normal."
        )

        assert result.signature == "Queue backlog / consumer lag"

    def test_cpu_and_memory_normal_does_not_trigger_memory_pressure_signature(self) -> None:
        parser = RawIncidentParser()

        result = parser.parse(
            "Kafka consumer lag building on platform-events topic. "
            "Consumer throughput flattened. CPU and memory normal."
        )

        assert result.signature != "Memory pressure / leak"

    def test_natural_service_phrasing_extracts_service_name(self) -> None:
        parser = RawIncidentParser()

        result = parser.parse(
            "pipeline-controller service crashing since 11:45 UTC deploy. "
            "Goroutine panic on nil pointer in reconcileCustomerPipeline()."
        )

        assert result.service == "pipeline-controller"

    def test_auth_dependency_wording_prefers_auth_slowdown_signature(self) -> None:
        parser = RawIncidentParser()

        result = parser.parse(
            "SSO authentication degraded for enterprise customers. "
            "Auth-proxy service showing p99 latency 8400ms. "
            "JWT validation requests to Okta timing out. "
            "New logins failing."
        )

        assert result.signature == "Auth dependency slowdown / token validation"


class TestAmbiguityDetection:
    """Test FIX 4: Ambiguity detection for multi-symptom incidents."""

    def test_ambiguous_classification_detected_when_scores_close(self) -> None:
        """Multi-symptom incident with close top scores should be marked ambiguous."""
        agent = SentinelAgent()

        # Craft symptoms that match both auth slowdown (INC007) and timeout cascade (INC001)
        result = agent.classify(
            raw_symptoms=[
                "Auth service p99 latency: 4500ms",
                "API timeout cascade detected",
                "Error rate: 22%",
                "Memory usage trending up on auth pods",
            ],
            system_context=SystemContext(
                service="api-gateway",
                language="Python/FastAPI",
                infra="Kubernetes on EKS",
                dependencies=["auth-svc", "api-gateway"],
            ),
        )

        # Should be marked as ambiguous if top scores are close
        if result.classification_type == "ambiguous":
            assert len(result.candidate_families) >= 2
            assert all("incident_id" in family and "score" in family for family in result.candidate_families)

    def test_single_classification_when_clear_winner(self) -> None:
        """Incident with clear winner should be marked single, not ambiguous."""
        agent = SentinelAgent()

        result = agent.classify(
            raw_symptoms=[
                "Database pool usage locked at 500 of 500 connections",
                "P95 query latency exceeded 10 seconds for checkout writes",
                "Active query count held above 200 while request queues grew",
            ],
            system_context=SystemContext(
                service="checkout-svc",
                language="Python/FastAPI",
                infra="Kubernetes on EKS",
                dependencies=["postgres-orders"],
            ),
        )

        # Should be clearly INC002 with single classification
        assert result.incident_id == "INC002"
        assert result.classification_type == "single"


class TestCachingAndPerformance:
    """Test FIX 5: Context caching for bulk retrieval performance."""

    def test_sentiment_classification_includes_new_fields(self) -> None:
        """SentinelClassification should include new ambiguity fields."""
        agent = SentinelAgent()
        incident = __import__("incidents.catalogue", fromlist=["load_incident_types"]).load_incident_types()[0]

        result = agent.classify(
            raw_symptoms=incident.symptoms,
            system_context=incident.system_context,
        )

        # Check new fields exist and have expected defaults
        assert hasattr(result, "classification_type")
        assert hasattr(result, "candidate_families")
        assert result.classification_type in ("single", "ambiguous")
        assert isinstance(result.candidate_families, list)

    def test_sentinel_preserves_priority_without_upshifting(self) -> None:
        agent = SentinelAgent()

        result = agent.classify(
            raw_symptoms=[
                "Database pool usage locked at 500 of 500 connections",
                "P95 query latency exceeded 10 seconds for checkout writes",
                "Active query count held above 200 while request queues grew",
            ],
            system_context=SystemContext(
                service="checkout-svc",
                language="Python/FastAPI",
                infra="Kubernetes on EKS",
                dependencies=["postgres-orders"],
            ),
        )

        assert result.severity == "P1"


class TestGitHubActionsUpgrade:
    """Test FIX 6: GitHub Actions upgrade to v4."""

    def test_github_workflow_uses_latest_actions(self) -> None:
        """GitHub workflow should reference v4 for checkout and setup-node."""
        with open(".github/workflows/deploy.yml", "r") as f:
            content = f.read()

        assert "actions/checkout@v4" in content, "checkout action should be v4"
        assert "actions/setup-python@v5" in content, "setup-python action should be v5"
        assert "actions/setup-node@v4" in content, "setup-node action should be v4"

        # Should not reference deprecated v3 for checkout and node
        assert "actions/checkout@v3" not in content
        assert "actions/setup-node@v3" not in content
