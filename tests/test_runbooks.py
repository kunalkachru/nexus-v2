"""
Tests for operational runbooks.

Validates:
- Runbook files exist
- Markdown structure is valid
- Required sections present
- Links to related resources are consistent
"""

import re
from pathlib import Path


def get_runbooks_dir():
    """Get path to runbooks directory."""
    return Path(__file__).parent.parent / 'docs' / 'runbooks'


def test_runbooks_directory_exists():
    """Test runbooks directory exists."""
    runbooks_dir = get_runbooks_dir()
    assert runbooks_dir.exists(), f"Runbooks directory not found at {runbooks_dir}"


def test_all_required_runbooks_exist():
    """Test all 6 required runbooks exist."""
    runbooks_dir = get_runbooks_dir()
    required_runbooks = [
        'nexus-down.md',
        'auth-failures.md',
        'slow-persistence.md',
        'guardian-approval-rate.md',
        'pending-reviews-backlog.md',
        'database-growth.md'
    ]

    for runbook in required_runbooks:
        runbook_path = runbooks_dir / runbook
        assert runbook_path.exists(), f"Runbook not found: {runbook_path}"


def test_runbook_structure():
    """Test each runbook has required sections."""
    runbooks_dir = get_runbooks_dir()
    required_files = [
        'nexus-down.md',
        'auth-failures.md',
        'slow-persistence.md',
        'guardian-approval-rate.md',
        'pending-reviews-backlog.md',
        'database-growth.md'
    ]

    required_sections = [
        '## Symptoms',
        '## Immediate Actions',
        '## If ',  # catches "If Immediate...", "If Still...", etc.
        '## Post-Incident',
        '## Contact & Escalation'
    ]

    for runbook_file in required_files:
        runbook_path = runbooks_dir / runbook_file
        with open(runbook_path) as f:
            content = f.read()

        for section in required_sections:
            assert section in content, f"{runbook_file} missing section: {section}"


def test_runbook_has_metadata():
    """Test each runbook has alert name, severity, owner, ERT."""
    runbooks_dir = get_runbooks_dir()
    required_files = [
        'nexus-down.md',
        'auth-failures.md',
        'slow-persistence.md',
        'guardian-approval-rate.md',
        'pending-reviews-backlog.md',
        'database-growth.md'
    ]

    metadata_fields = [
        '**Alert:**',
        '**Severity:**',
        '**On-Call Owner:**',
        '**Estimated Resolution Time:**'
    ]

    for runbook_file in required_files:
        runbook_path = runbooks_dir / runbook_file
        with open(runbook_path) as f:
            content = f.read()

        for field in metadata_fields:
            assert field in content, f"{runbook_file} missing metadata: {field}"


def test_runbook_severity_valid():
    """Test runbook severity values are valid."""
    runbooks_dir = get_runbooks_dir()
    valid_severities = {'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'}

    for runbook_file in runbooks_dir.glob('*.md'):
        with open(runbook_file) as f:
            content = f.read()

        # Extract severity
        match = re.search(r'\*\*Severity:\*\*\s+(\w+)', content)
        if match:
            severity = match.group(1)
            assert severity in valid_severities, \
                f"{runbook_file.name} has invalid severity: {severity}"


def test_runbook_has_diagnostic_steps():
    """Test runbooks have diagnostic/investigation steps."""
    runbooks_dir = get_runbooks_dir()

    diagnostic_keywords = ['check', 'verify', 'confirm', 'diagnose', 'debug']

    for runbook_file in runbooks_dir.glob('*.md'):
        with open(runbook_file) as f:
            content = f.read().lower()

        # Check if any diagnostic keyword appears multiple times
        keyword_count = sum(content.count(kw) for kw in diagnostic_keywords)
        assert keyword_count > 5, \
            f"{runbook_file.name} lacks diagnostic steps (found {keyword_count} diagnostic keywords)"


def test_runbook_has_recovery_steps():
    """Test runbooks have recovery/mitigation steps."""
    runbooks_dir = get_runbooks_dir()

    recovery_keywords = ['restart', 'fix', 'restore', 'recover', 'escalate', 'mitigate', 'retry', 'reset']

    for runbook_file in runbooks_dir.glob('*.md'):
        with open(runbook_file) as f:
            content = f.read().lower()

        # Check for recovery sections and keywords
        has_recovery_section = 'if ' in content and 'actions' in content
        keyword_count = sum(content.count(kw) for kw in recovery_keywords)

        assert has_recovery_section or keyword_count > 0, \
            f"{runbook_file.name} lacks recovery steps"


def test_runbook_has_escalation_path():
    """Test runbooks specify escalation contacts."""
    runbooks_dir = get_runbooks_dir()

    for runbook_file in runbooks_dir.glob('*.md'):
        with open(runbook_file) as f:
            content = f.read()

        # Check for escalation contact info
        has_escalation = 'slack:' in content.lower() or 'contact' in content.lower() or 'escalat' in content.lower()
        assert has_escalation, f"{runbook_file.name} missing escalation information"


def test_nexus_down_runbook():
    """Test NexusDown runbook has specific content."""
    runbook_path = get_runbooks_dir() / 'nexus-down.md'
    with open(runbook_path) as f:
        content = f.read()

    assert 'NexusDown' in content
    assert 'docker logs' in content or 'systemctl' in content
    assert 'curl' in content  # health check
    assert 'CRITICAL' in content


def test_auth_failures_runbook():
    """Test auth failures runbook has security-specific content."""
    runbook_path = get_runbooks_dir() / 'auth-failures.md'
    with open(runbook_path) as f:
        content = f.read()

    assert 'SuspiciousAuthFailures' in content
    assert 'attack' in content.lower()
    assert 'signature' in content.lower() or 'secret' in content.lower()
    assert 'HIGH' in content  # severity


def test_slow_persistence_runbook():
    """Test slow persistence runbook has database-specific content."""
    runbook_path = get_runbooks_dir() / 'slow-persistence.md'
    with open(runbook_path) as f:
        content = f.read()

    assert 'ArtifactPersistenceSlow' in content
    assert 'sqlite3' in content or 'database' in content.lower()
    assert '1000ms' in content or '1 second' in content.lower()


def test_guardian_approval_runbook():
    """Test GUARDIAN approval rate runbook has specific content."""
    runbook_path = get_runbooks_dir() / 'guardian-approval-rate.md'
    with open(runbook_path) as f:
        content = f.read()

    assert 'GuardianApprovalRateLow' in content
    assert 'GUARDIAN' in content
    assert '50%' in content or '0.5' in content
    assert 'approval' in content.lower()


def test_pending_reviews_runbook():
    """Test pending reviews runbook has queue-specific content."""
    runbook_path = get_runbooks_dir() / 'pending-reviews-backlog.md'
    with open(runbook_path) as f:
        content = f.read()

    assert 'PendingGuardianReviewsHigh' in content
    assert 'queue' in content.lower() or 'backlog' in content.lower()
    assert '50' in content  # threshold


def test_database_growth_runbook():
    """Test database growth runbook has retention-specific content."""
    runbook_path = get_runbooks_dir() / 'database-growth.md'
    with open(runbook_path) as f:
        content = f.read()

    assert 'DatabaseGrowthFast' in content
    assert 'growth' in content.lower() or 'retention' in content.lower()
    assert '1GB' in content or '1000000000' in content


def test_runbooks_have_markdown_formatting():
    """Test runbooks are properly formatted Markdown."""
    runbooks_dir = get_runbooks_dir()

    for runbook_file in runbooks_dir.glob('*.md'):
        with open(runbook_file) as f:
            content = f.read()

        # Check for proper markdown headings
        assert re.search(r'^# ', content, re.MULTILINE), \
            f"{runbook_file.name} missing main heading"

        # Check for code blocks
        assert '```' in content, \
            f"{runbook_file.name} has no code examples"

        # Check for proper list formatting
        assert re.search(r'^\d+\.|\^-\s', content, re.MULTILINE), \
            f"{runbook_file.name} missing lists"


def test_runbook_readability():
    """Test runbooks are reasonably sized (not too long)."""
    runbooks_dir = get_runbooks_dir()

    for runbook_file in runbooks_dir.glob('*.md'):
        with open(runbook_file) as f:
            lines = f.readlines()

        # Should be detailed but not overwhelming
        # Expect 100-300 lines
        assert len(lines) > 50, \
            f"{runbook_file.name} is too short (only {len(lines)} lines)"

        assert len(lines) < 500, \
            f"{runbook_file.name} is too long ({len(lines)} lines, should be <500)"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
