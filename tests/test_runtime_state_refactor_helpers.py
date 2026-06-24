from server.services.runtime_state import normalize_pilot_health_status


def test_normalize_pilot_health_status_maps_healthy_states() -> None:
    assert (
        normalize_pilot_health_status(
            "READY",
            healthy_states=("ready", "healthy"),
        )
        == "healthy"
    )
