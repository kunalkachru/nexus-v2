"""
Tests for Monitoring & Handoff (Tasks 8.2 & 8.3)

Validates:
- 24-hour monitoring procedures comprehensive
- Alert response procedures complete for all 8 alerts
- Ops handoff procedures thorough and clear
- All acceptance criteria covered
- Documentation quality and completeness
"""

from pathlib import Path


def get_docs_dir():
    """Get path to docs directory."""
    return Path(__file__).parent.parent / 'docs'


def get_internal_docs_dir():
    """Get path to internal docs directory."""
    return get_docs_dir() / 'internal'


class TestMonitoringAndHandoff:
    """Monitoring and handoff validation tests."""

    # ========== TASK 8.2 TESTS ==========

    def test_monitoring_playbook_exists(self):
        """Test 24-hour monitoring playbook exists."""
        playbook = get_internal_docs_dir() / 'monitoring-playbook-24hr.md'
        assert playbook.exists(), \
            f"Monitoring playbook not found at {playbook}"

    def test_alert_response_procedures_exist(self):
        """Test alert response procedures exist."""
        procedures = get_internal_docs_dir() / 'alert-response-procedures.md'
        assert procedures.exists(), \
            f"Alert response procedures not found at {procedures}"

    def test_monitoring_playbook_covers_8_metrics(self):
        """Test monitoring playbook covers all 8 monitored metrics."""
        playbook = get_internal_docs_dir() / 'monitoring-playbook-24hr.md'

        with open(playbook) as f:
            content = f.read()

        # Should define all 8 metrics
        metrics = [
            'Health Check Status',
            'Metrics Collection',
            'Auth Failure Rate',
            'Incident Processing Latency',
            'GUARDIAN Approval Rate',
            'Artifact Persistence Latency',
            'Unexpected Errors in Logs',
            'Backup Running Successfully'
        ]

        for metric in metrics:
            assert metric in content, f"Missing metric: {metric}"

    def test_monitoring_playbook_has_hourly_schedule(self):
        """Test monitoring playbook includes hour-by-hour schedule."""
        playbook = get_internal_docs_dir() / 'monitoring-playbook-24hr.md'

        with open(playbook) as f:
            content = f.read()

        # Should have hourly monitoring schedule
        assert 'Hour-by-Hour' in content or 'hour' in content.lower()
        assert 'Hour 0' in content or 'Hour 1' in content

    def test_alert_response_covers_all_8_alerts(self):
        """Test alert response procedures cover all 8 alert types."""
        procedures = get_internal_docs_dir() / 'alert-response-procedures.md'

        with open(procedures) as f:
            content = f.read()

        # Should have procedures for all 8 alerts
        alerts = [
            'Alert #1',
            'Alert #2',
            'Alert #3',
            'Alert #4',
            'Alert #5',
            'Alert #6',
            'Alert #7',
            'Alert #8'
        ]

        for alert in alerts:
            assert alert in content, f"Missing {alert}"

    def test_alert_responses_have_step_by_step(self):
        """Test alert responses include step-by-step procedures."""
        procedures = get_internal_docs_dir() / 'alert-response-procedures.md'

        with open(procedures) as f:
            content = f.read()

        # Each alert should have diagnosis and resolution steps
        assert 'Diagnosis' in content, "Missing diagnosis section"
        assert 'Resolution' in content, "Missing resolution section"
        assert 'Step' in content, "Missing step-by-step procedures"

    def test_alert_responses_include_escalation(self):
        """Test alert response procedures include escalation criteria."""
        procedures = get_internal_docs_dir() / 'alert-response-procedures.md'

        with open(procedures) as f:
            content = f.read()

        # Should define when to escalate
        assert 'Escalat' in content, "Missing escalation guidance"
        assert 'Backend Lead' in content or 'escalate' in content.lower()

    def test_monitoring_playbook_includes_issue_log_template(self):
        """Test monitoring playbook includes issue logging template."""
        playbook = get_internal_docs_dir() / 'monitoring-playbook-24hr.md'

        with open(playbook) as f:
            content = f.read()

        # Should have template for documenting issues
        assert 'Issue' in content and ('Log' in content or 'Template' in content)
        assert 'ISSUE #' in content or 'Issue #' in content

    def test_monitoring_playbook_defines_baseline_metrics(self):
        """Test monitoring playbook defines baseline metrics."""
        playbook = get_internal_docs_dir() / 'monitoring-playbook-24hr.md'

        with open(playbook) as f:
            content = f.read()

        # Should have baseline metric recording
        assert 'Baseline' in content, "Missing baseline section"
        assert 'pre-production' in content.lower() or 'baseline' in content.lower()

    def test_monitoring_playbook_includes_success_criteria(self):
        """Test monitoring playbook defines success criteria."""
        playbook = get_internal_docs_dir() / 'monitoring-playbook-24hr.md'

        with open(playbook) as f:
            content = f.read()

        # Should define what success looks like
        assert 'Success' in content, "Missing success criteria"
        assert '24 hours' in content, "Missing 24-hour timeframe"

    # ========== TASK 8.3 TESTS ==========

    def test_ops_handoff_procedures_exist(self):
        """Test ops handoff procedures exist."""
        procedures = get_internal_docs_dir() / 'ops-handoff-procedures.md'
        assert procedures.exists(), \
            f"Ops handoff procedures not found at {procedures}"

    def test_handoff_procedures_cover_6_phases(self):
        """Test handoff procedures include all 6 phases."""
        procedures = get_internal_docs_dir() / 'ops-handoff-procedures.md'

        with open(procedures) as f:
            content = f.read()

        # Should have 6 phases
        phases = [
            'Phase 1',
            'Phase 2',
            'Phase 3',
            'Phase 4',
            'Phase 5',
            'Phase 6'
        ]

        for phase in phases:
            assert phase in content, f"Missing {phase}"

    def test_handoff_phase_1_covers_kickoff(self):
        """Test Phase 1 covers kickoff and context."""
        procedures = get_internal_docs_dir() / 'ops-handoff-procedures.md'

        with open(procedures) as f:
            content = f.read()

        # Phase 1 should cover kickoff
        assert 'Kickoff' in content or 'Phase 1' in content
        assert 'Context' in content or 'Objectives' in content

    def test_handoff_phase_2_covers_operations(self):
        """Test Phase 2 covers operations procedures."""
        procedures = get_internal_docs_dir() / 'ops-handoff-procedures.md'

        with open(procedures) as f:
            content = f.read()

        # Phase 2 should cover: start, stop, logs, dashboards, alerts
        operations_topics = [
            'start',
            'stop',
            'logs',
            'dashboard',
            'alert'
        ]

        for topic in operations_topics:
            assert topic.lower() in content.lower(), f"Missing {topic}"

    def test_handoff_phase_3_covers_incident_response(self):
        """Test Phase 3 covers incident response procedures."""
        procedures = get_internal_docs_dir() / 'ops-handoff-procedures.md'

        with open(procedures) as f:
            content = f.read()

        # Phase 3 should cover incident response and runbooks
        assert 'Incident' in content or 'runbook' in content.lower()
        assert '6' in content  # 6 runbooks

    def test_handoff_phase_4_covers_escalation(self):
        """Test Phase 4 covers escalation and on-call."""
        procedures = get_internal_docs_dir() / 'ops-handoff-procedures.md'

        with open(procedures) as f:
            content = f.read()

        # Phase 4 should cover escalation chain and on-call
        assert 'Escalat' in content, "Missing escalation"
        assert 'on-call' in content.lower() or 'on call' in content.lower()

    def test_handoff_phase_5_covers_documentation(self):
        """Test Phase 5 covers documentation handoff."""
        procedures = get_internal_docs_dir() / 'ops-handoff-procedures.md'

        with open(procedures) as f:
            content = f.read()

        # Phase 5 should reference key documentation
        docs = [
            'Master Operator Guide',
            'Runbook',
            'Monitoring',
            'Deployment'
        ]

        for doc in docs:
            assert doc in content, f"Missing {doc} documentation reference"

    def test_handoff_phase_6_covers_first_shift(self):
        """Test Phase 6 covers first on-call shift."""
        procedures = get_internal_docs_dir() / 'ops-handoff-procedures.md'

        with open(procedures) as f:
            content = f.read()

        # Phase 6 should cover first shift execution
        assert 'First' in content and ('Shift' in content or 'on-call' in content.lower())
        assert 'Scenario' in content  # Should have practice scenarios

    def test_handoff_includes_sign_off_forms(self):
        """Test handoff procedures include sign-off forms."""
        procedures = get_internal_docs_dir() / 'ops-handoff-procedures.md'

        with open(procedures) as f:
            content = f.read()

        # Should have sign-off sections for completion verification
        assert 'Sign' in content and 'Off' in content
        assert 'Confirm' in content or 'verification' in content.lower()

    def test_handoff_includes_escalation_contacts(self):
        """Test handoff defines escalation contacts."""
        procedures = get_internal_docs_dir() / 'ops-handoff-procedures.md'

        with open(procedures) as f:
            content = f.read()

        # Should define who to contact for different issues
        contacts = [
            'Backend Lead',
            'DevOps Lead',
            'Engineering Manager'
        ]

        for contact in contacts:
            assert contact in content, f"Missing {contact}"

    def test_handoff_includes_on_call_rotation(self):
        """Test handoff covers on-call rotation setup."""
        procedures = get_internal_docs_dir() / 'ops-handoff-procedures.md'

        with open(procedures) as f:
            content = f.read()

        # Should explain on-call rotation
        assert 'rotation' in content.lower() or 'schedule' in content.lower()
        assert 'week' in content.lower()  # Weekly shifts typical

    def test_handoff_includes_weekly_syncs(self):
        """Test handoff schedules weekly sync meetings."""
        procedures = get_internal_docs_dir() / 'ops-handoff-procedures.md'

        with open(procedures) as f:
            content = f.read()

        # Should schedule weekly syncs
        assert 'weekly' in content.lower() or 'sync' in content.lower()

    # ========== COMBINED TESTS ==========

    def test_acceptance_criteria_all_tasks(self):
        """Test all acceptance criteria from spec are covered."""
        playbook = get_internal_docs_dir() / 'monitoring-playbook-24hr.md'
        procedures = get_internal_docs_dir() / 'alert-response-procedures.md'
        handoff = get_internal_docs_dir() / 'ops-handoff-procedures.md'

        with open(playbook) as f:
            pb_content = f.read()
        with open(procedures) as f:
            ap_content = f.read()
        with open(handoff) as f:
            ho_content = f.read()

        combined = pb_content + ap_content + ho_content

        # Task 8.2 Acceptance Criteria
        # - 24 hours monitoring documented
        assert '24' in combined or 'hour' in combined.lower()
        # - All metrics stable documented
        assert 'metric' in combined.lower() and 'stable' in combined.lower()
        # - Customer satisfied documented
        assert 'customer' in combined.lower()

        # Task 8.3 Acceptance Criteria
        # - Ops team confirms understanding
        assert 'understand' in combined.lower()
        # - Documentation handed over
        assert 'documentation' in combined.lower()
        # - Escalation chain confirmed
        assert 'escalat' in combined.lower()

    def test_procedures_reference_each_other(self):
        """Test procedures reference each other appropriately."""
        playbook = get_internal_docs_dir() / 'monitoring-playbook-24hr.md'
        procedures = get_internal_docs_dir() / 'alert-response-procedures.md'

        with open(playbook) as f:
            pb_content = f.read()
        with open(procedures) as f:
            ap_content = f.read()

        # Playbook should reference alert procedures
        assert 'alert' in pb_content.lower(), \
            "Playbook should reference alert procedures"

        # Alert procedures should reference playbook
        assert 'Metric' in ap_content or 'baseline' in ap_content.lower(), \
            "Alert procedures should reference metrics from playbook"

    def test_documentation_completeness(self):
        """Test all documentation files are substantial and complete."""
        files = [
            get_internal_docs_dir() / 'monitoring-playbook-24hr.md',
            get_internal_docs_dir() / 'alert-response-procedures.md',
            get_internal_docs_dir() / 'ops-handoff-procedures.md'
        ]

        for file in files:
            with open(file) as f:
                content = f.read()

            # Each file should be substantial (> 2000 chars)
            assert len(content) > 2000, \
                f"{file.name} is too short ({len(content)} chars)"

    def test_procedures_have_practical_examples(self):
        """Test procedures include practical examples/scenarios."""
        procedures = get_internal_docs_dir() / 'alert-response-procedures.md'

        with open(procedures) as f:
            content = f.read()

        # Should have runnable commands or examples
        assert 'curl' in content or 'docker' in content or 'example' in content.lower()

    def test_handoff_practicality(self):
        """Test handoff procedures are practical and executable."""
        handoff = get_internal_docs_dir() / 'ops-handoff-procedures.md'

        with open(handoff) as f:
            content = f.read()

        # Should have time estimates
        assert 'minutes' in content.lower() or 'hours' in content.lower()
        # Should be organized with clear sections
        assert 'Phase' in content
        # Should have practice scenarios
        assert 'Scenario' in content or 'practice' in content.lower()

    def test_all_files_have_purpose_and_version(self):
        """Test all files have clear purpose and version."""
        files = [
            get_internal_docs_dir() / 'monitoring-playbook-24hr.md',
            get_internal_docs_dir() / 'alert-response-procedures.md',
            get_internal_docs_dir() / 'ops-handoff-procedures.md'
        ]

        for file in files:
            with open(file) as f:
                first_500 = f.read(500)

            # Should have version
            assert 'Version' in first_500 or '1.0' in first_500, \
                f"{file.name} missing version"
            # Should have purpose
            assert 'Purpose' in first_500 or 'Objective' in first_500, \
                f"{file.name} missing purpose"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
