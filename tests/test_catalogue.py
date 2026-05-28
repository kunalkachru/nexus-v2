from incidents.catalogue import load_incident_types
from server.models import IncidentDefinition


def test_load_incident_types_returns_eight_incidents() -> None:
    incidents = load_incident_types()

    assert len(incidents) == 8
    assert all(isinstance(incident, IncidentDefinition) for incident in incidents)
    assert incidents[0].id == "INC001"
    assert incidents[-1].id == "INC008"


def test_incident_catalogue_ids_are_unique() -> None:
    incidents = load_incident_types()

    assert len({incident.id for incident in incidents}) == len(incidents)
