from server.models import AgentStubInfo, IncidentDefinition, SystemContext


def test_system_context_is_typed() -> None:
    context = SystemContext(
        service="payment-svc",
        language="Python/FastAPI",
        infra="AWS ECS Fargate",
        dependencies=["postgres-payments", "stripe-api"],
    )

    assert context.service == "payment-svc"
    assert context.dependencies == ["postgres-payments", "stripe-api"]


def test_incident_definition_wraps_context() -> None:
    incident = IncidentDefinition(
        id="INC001",
        name="Payment Service Timeout",
        severity="P2",
        difficulty="Easy",
        symptoms=["Payment API returning HTTP 504 after 30s"],
        system_context=SystemContext(
            service="payment-svc",
            language="Python/FastAPI",
            infra="AWS ECS Fargate",
            dependencies=["postgres-payments", "stripe-api"],
        ),
        root_cause="Third-party Stripe API degradation causing upstream timeout",
        fix="Increase timeout from 10s to 30s",
    )

    assert incident.system_context.service == "payment-svc"


def test_agent_stub_info_defaults_to_not_implemented() -> None:
    info = AgentStubInfo(name="sentinel")

    assert info.name == "sentinel"
    assert info.implemented is False
