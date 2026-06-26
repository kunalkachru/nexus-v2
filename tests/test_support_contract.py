from server.services.support_contract import (
    FAMILY_METADATA,
    RAW_TEXT_SUPPORTED_FAMILIES,
    current_raw_text_wedge_summary,
    guidance_for_incident_id,
    supported_family_display_lines,
    supported_family_message,
)


def test_raw_text_supported_families_match_current_contract() -> None:
    assert RAW_TEXT_SUPPORTED_FAMILIES == (
        "INC001",
        "INC002",
        "INC003",
        "INC005",
        "INC006",
        "INC007",
    )


def test_supported_family_display_lines_are_derived_from_contract() -> None:
    assert supported_family_display_lines() == [
        "Timeout/Retry Amplification (INC001)",
        "DB Pool Exhaustion (INC002)",
        "Deploy Regression / 5xx Spike (INC003)",
        "Queue / Worker Backlog (INC005)",
        "Expired TLS Certificate (INC006)",
        "Auth Dependency Slowdown (INC007)",
    ]
    assert "6 supported families" in supported_family_message()
    assert "Expired TLS Certificate (INC006)" in supported_family_message()


def test_family_metadata_owns_guidance_and_summary() -> None:
    assert "INC004" in FAMILY_METADATA
    guidance = guidance_for_incident_id("INC004")
    assert guidance["category"]
    assert guidance["steps"]
    assert current_raw_text_wedge_summary() == "6 bounded raw-text outage families remain the active pilot surface."
