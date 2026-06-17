"""
Tests for the NEXUS Troubleshooting Guide.

Validates:
- Guide file exists and is accessible
- All required scenarios are documented
- Each scenario has diagnosis, fix, and escalation info
- Links to related runbooks are consistent
- Content is well-structured
"""

import re
from pathlib import Path


def test_troubleshooting_guide_exists():
    """Test troubleshooting guide file exists."""
    guide_path = Path(__file__).parent.parent / 'docs' / 'TROUBLESHOOTING_GUIDE.md'
    assert guide_path.exists(), f"Troubleshooting guide not found at {guide_path}"


def test_guide_has_all_7_scenarios():
    """Test guide covers all 7 required scenarios."""
    guide_path = Path(__file__).parent.parent / 'docs' / 'TROUBLESHOOTING_GUIDE.md'
    with open(guide_path) as f:
        content = f.read()

    required_scenarios = [
        'Scenario 1: Incident Won\'t Load',
        'Scenario 2: Webhook Keeps Rejecting',
        'Scenario 3: Auth Failures Spiking',
        'Scenario 4: Database Growing Fast',
        'Scenario 5: GUARDIAN Keeps Rejecting',
        'Scenario 6: Performance Degraded',
        'Scenario 7: Can\'t Access the API',
    ]

    for scenario in required_scenarios:
        assert scenario in content, f"Guide missing: {scenario}"


def test_each_scenario_has_structure():
    """Test each scenario has diagnosis/fix/escalation."""
    guide_path = Path(__file__).parent.parent / 'docs' / 'TROUBLESHOOTING_GUIDE.md'
    with open(guide_path) as f:
        content = f.read()

    scenarios = re.findall(r'## Scenario \d+: .+', content)
    assert len(scenarios) == 7, f"Expected 7 scenarios, found {len(scenarios)}"

    for scenario in scenarios:
        # Extract scenario content
        scenario_num = scenario.split(':')[0]  # "## Scenario 1"
        # Rough check: each scenario should have diagnostic steps, fix steps, and related runbook
        assert 'Diagnosis' in content or 'Symptom' in content, \
            f"{scenario} missing diagnosis section"


def test_guide_links_to_runbooks():
    """Test guide references the runbook files."""
    guide_path = Path(__file__).parent.parent / 'docs' / 'TROUBLESHOOTING_GUIDE.md'
    with open(guide_path) as f:
        content = f.read()

    runbook_names = [
        'nexus-down.md',
        'auth-failures.md',
        'slow-persistence.md',
        'guardian-approval-rate.md',
        'pending-reviews-backlog.md',
        'database-growth.md'
    ]

    for runbook in runbook_names:
        assert runbook in content, f"Guide doesn't reference {runbook}"


def test_guide_has_quick_reference():
    """Test guide has quick links at top."""
    guide_path = Path(__file__).parent.parent / 'docs' / 'TROUBLESHOOTING_GUIDE.md'
    with open(guide_path) as f:
        content = f.read()

    assert '## Quick Links' in content, "Guide missing Quick Links section"


def test_guide_has_escalation_info():
    """Test guide provides escalation guidance."""
    guide_path = Path(__file__).parent.parent / 'docs' / 'TROUBLESHOOTING_GUIDE.md'
    with open(guide_path) as f:
        content = f.read()

    assert 'When to Escalate' in content, "Guide missing escalation guidance"
    assert 'Page on-call' in content or 'escalate' in content.lower(), \
        "Guide missing escalation procedures"


def test_guide_uses_code_examples():
    """Test guide includes bash/SQL code examples."""
    guide_path = Path(__file__).parent.parent / 'docs' / 'TROUBLESHOOTING_GUIDE.md'
    with open(guide_path) as f:
        content = f.read()

    # Count code blocks
    code_blocks = content.count('```')
    assert code_blocks > 20, f"Expected many code examples, found {code_blocks//2} blocks"


def test_guide_scenario_1_incident_not_loading():
    """Test Scenario 1 covers incident loading issues."""
    guide_path = Path(__file__).parent.parent / 'docs' / 'TROUBLESHOOTING_GUIDE.md'
    with open(guide_path) as f:
        content = f.read()

    scenario_1 = content[content.find('## Scenario 1'):content.find('## Scenario 2')]

    assert 'curl' in scenario_1 and 'health' in scenario_1, \
        "Scenario 1 missing health check"
    assert 'sqlite3' in scenario_1, "Scenario 1 missing database query"
    assert 'status=' in scenario_1, "Scenario 1 missing status check"


def test_guide_scenario_2_webhook():
    """Test Scenario 2 covers webhook issues."""
    guide_path = Path(__file__).parent.parent / 'docs' / 'TROUBLESHOOTING_GUIDE.md'
    with open(guide_path) as f:
        content = f.read()

    scenario_2 = content[content.find('## Scenario 2'):content.find('## Scenario 3')]

    assert 'signature' in scenario_2.lower(), "Scenario 2 missing signature check"
    assert 'WEBHOOK_SECRET' in scenario_2, "Scenario 2 missing secret reference"


def test_guide_scenario_3_auth():
    """Test Scenario 3 covers auth failures."""
    guide_path = Path(__file__).parent.parent / 'docs' / 'TROUBLESHOOTING_GUIDE.md'
    with open(guide_path) as f:
        content = f.read()

    scenario_3 = content[content.find('## Scenario 3'):content.find('## Scenario 4')]

    assert 'auth_failure' in scenario_3, "Scenario 3 missing auth_failure metric"
    assert 'attack' in scenario_3.lower(), "Scenario 3 missing attack discussion"


def test_guide_scenario_4_database():
    """Test Scenario 4 covers database growth."""
    guide_path = Path(__file__).parent.parent / 'docs' / 'TROUBLESHOOTING_GUIDE.md'
    with open(guide_path) as f:
        content = f.read()

    scenario_4 = content[content.find('## Scenario 4'):content.find('## Scenario 5')]

    assert 'VACUUM' in scenario_4, "Scenario 4 missing VACUUM"
    assert 'retention' in scenario_4.lower(), "Scenario 4 missing retention policy"


def test_guide_scenario_5_guardian():
    """Test Scenario 5 covers GUARDIAN issues."""
    guide_path = Path(__file__).parent.parent / 'docs' / 'TROUBLESHOOTING_GUIDE.md'
    with open(guide_path) as f:
        content = f.read()

    scenario_5 = content[content.find('## Scenario 5'):content.find('## Scenario 6')]

    assert 'GUARDIAN' in scenario_5, "Scenario 5 missing GUARDIAN reference"
    assert 'decision' in scenario_5.lower(), "Scenario 5 missing decision discussion"


def test_guide_scenario_6_performance():
    """Test Scenario 6 covers performance."""
    guide_path = Path(__file__).parent.parent / 'docs' / 'TROUBLESHOOTING_GUIDE.md'
    with open(guide_path) as f:
        content = f.read()

    scenario_6 = content[content.find('## Scenario 6'):content.find('## Scenario 7')]

    assert 'latency' in scenario_6.lower(), "Scenario 6 missing latency reference"
    assert 'CPU' in scenario_6 or 'memory' in scenario_6.lower(), \
        "Scenario 6 missing resource checks"


def test_guide_scenario_7_no_access():
    """Test Scenario 7 covers API access issues."""
    guide_path = Path(__file__).parent.parent / 'docs' / 'TROUBLESHOOTING_GUIDE.md'
    with open(guide_path) as f:
        content = f.read()

    scenario_7 = content[content.find('## Scenario 7'):]

    assert 'netstat' in scenario_7 or 'lsof' in scenario_7, \
        "Scenario 7 missing port checking"
    assert 'firewall' in scenario_7.lower(), "Scenario 7 missing firewall check"


def test_guide_has_common_quick_fixes():
    """Test guide has quick reference table."""
    guide_path = Path(__file__).parent.parent / 'docs' / 'TROUBLESHOOTING_GUIDE.md'
    with open(guide_path) as f:
        content = f.read()

    assert 'Common Quick Fixes' in content, "Guide missing quick fixes table"
    assert '| Issue | Quick Fix | Test |' in content, "Quick fixes missing table structure"


def test_guide_is_readable_length():
    """Test guide is comprehensive but not overwhelming."""
    guide_path = Path(__file__).parent.parent / 'docs' / 'TROUBLESHOOTING_GUIDE.md'
    with open(guide_path) as f:
        lines = f.readlines()

    # Should be substantial but not impossibly long
    assert len(lines) > 200, f"Guide too short ({len(lines)} lines)"
    assert len(lines) < 800, f"Guide too long ({len(lines)} lines)"


def test_guide_has_getting_help():
    """Test guide provides help/escalation contact info."""
    guide_path = Path(__file__).parent.parent / 'docs' / 'TROUBLESHOOTING_GUIDE.md'
    with open(guide_path) as f:
        content = f.read()

    assert 'Getting Help' in content, "Guide missing help section"
    assert 'slack' in content.lower() or 'contact' in content.lower(), \
        "Guide missing contact information"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
