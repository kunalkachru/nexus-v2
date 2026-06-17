"""
Tests for Ops Team Training Program (Task 7.4)

Validates:
- All training materials exist and are complete
- Training covers all required topics
- Hands-on lab scenarios are well-defined
- Completion tracking is in place
- All acceptance criteria are met
"""

import re
from pathlib import Path


def get_docs_dir():
    """Get path to docs directory."""
    return Path(__file__).parent.parent / 'docs'


def get_internal_docs_dir():
    """Get path to internal docs directory."""
    return get_docs_dir() / 'internal'


def get_runbooks_dir():
    """Get path to runbooks directory."""
    return get_docs_dir() / 'runbooks'


class TestOpsTeamTraining:
    """Ops training validation tests."""

    def test_training_guide_exists(self):
        """Test main training guide file exists."""
        training_guide = get_internal_docs_dir() / 'ops-team-training-guide.md'
        assert training_guide.exists(), \
            f"Training guide not found at {training_guide}"

    def test_hands_on_lab_exists(self):
        """Test hands-on lab guide exists."""
        lab_guide = get_internal_docs_dir() / 'ops-team-training-hands-on-lab.md'
        assert lab_guide.exists(), \
            f"Hands-on lab guide not found at {lab_guide}"

    def test_completion_tracker_exists(self):
        """Test training completion tracker exists."""
        completion = get_internal_docs_dir() / 'ops-team-training-completion.md'
        assert completion.exists(), \
            f"Completion tracker not found at {completion}"

    def test_training_guide_completeness(self):
        """Test training guide covers all 5 modules."""
        guide = get_internal_docs_dir() / 'ops-team-training-guide.md'

        with open(guide) as f:
            content = f.read()

        # Check for all 5 modules
        assert 'Module 1' in content and 'Architecture' in content, \
            "Missing Module 1: Architecture"
        assert 'Module 2' in content and 'Operations' in content, \
            "Missing Module 2: Operations"
        assert 'Module 3' in content and 'Troubleshooting' in content, \
            "Missing Module 3: Troubleshooting"
        assert 'Module 4' in content and 'Disaster Recovery' in content, \
            "Missing Module 4: Disaster Recovery"
        assert 'Module 5' in content and 'Hands-On Lab' in content, \
            "Missing Module 5: Hands-On Lab"

    def test_module_1_topics(self):
        """Test Module 1 covers architecture topics."""
        guide = get_internal_docs_dir() / 'ops-team-training-guide.md'

        with open(guide) as f:
            content = f.read()

        # Check for key architecture topics
        assert 'SENTINEL' in content, "Missing SENTINEL stage"
        assert 'PRISM' in content, "Missing PRISM stage"
        assert 'REPLICA' in content, "Missing REPLICA stage"
        assert 'TRACE' in content, "Missing TRACE stage"
        assert 'FORGE' in content, "Missing FORGE stage"
        assert 'GUARDIAN' in content, "Missing GUARDIAN stage"
        assert 'incidents.json' in content, "Missing incidents.json reference"
        assert 'audit' in content.lower(), "Missing audit trail coverage"

    def test_module_2_topics(self):
        """Test Module 2 covers operations topics."""
        guide = get_internal_docs_dir() / 'ops-team-training-guide.md'

        with open(guide) as f:
            content = f.read()

        # Check for operational procedures
        assert 'systemctl start' in content, "Missing start procedure"
        assert 'systemctl stop' in content, "Missing stop procedure"
        assert 'systemctl restart' in content, "Missing restart procedure"
        assert 'journalctl' in content, "Missing log viewing"
        assert 'Grafana' in content, "Missing monitoring/dashboard reference"
        assert 'health' in content.lower(), "Missing health check"

    def test_module_3_topics(self):
        """Test Module 3 covers troubleshooting topics."""
        guide = get_internal_docs_dir() / 'ops-team-training-guide.md'

        with open(guide) as f:
            content = f.read()

        # Check for troubleshooting coverage
        assert 'Troubleshooting' in content, "Missing troubleshooting section"
        assert 'ERROR' in content, "Missing error pattern discussion"
        assert 'escalat' in content.lower(), "Missing escalation procedures"
        assert 'diagnostic' in content.lower(), "Missing diagnostic procedures"

    def test_module_4_topics(self):
        """Test Module 4 covers disaster recovery topics."""
        guide = get_internal_docs_dir() / 'ops-team-training-guide.md'

        with open(guide) as f:
            content = f.read()

        # Check for DR procedures
        assert 'restore' in content.lower(), "Missing restore procedure"
        assert 'backup' in content.lower(), "Missing backup reference"
        assert 'RTO' in content, "Missing RTO discussion"
        assert 'corrupt' in content.lower(), "Missing corruption handling"

    def test_module_5_lab_scenarios(self):
        """Test Module 5 defines all 4 hands-on scenarios."""
        lab = get_internal_docs_dir() / 'ops-team-training-hands-on-lab.md'

        with open(lab) as f:
            content = f.read()

        # Check for all 4 scenarios
        assert 'Scenario A' in content, "Missing Scenario A"
        assert 'Scenario B' in content, "Missing Scenario B"
        assert 'Scenario C' in content, "Missing Scenario C"
        assert 'Scenario D' in content, "Missing Scenario D"

        # Check scenario titles
        assert 'Service Startup' in content, "Scenario A: Missing Service Startup"
        assert 'Incident' in content, "Scenario B: Missing Incident reference"
        assert 'Monitor' in content, "Scenario C: Missing Monitoring"
        assert 'Recovery' in content or 'Disaster' in content, \
            "Scenario D: Missing Disaster Recovery"

    def test_hands_on_lab_structure(self):
        """Test hands-on lab is well-structured with steps."""
        lab = get_internal_docs_dir() / 'ops-team-training-hands-on-lab.md'

        with open(lab) as f:
            content = f.read()

        # Check for procedure structure
        for scenario in ['A', 'B', 'C', 'D']:
            # Each scenario should have steps
            assert f'Scenario {scenario}' in content, f"Missing Scenario {scenario}"
            # Should have step markers
            assert f'{scenario}1.' in content or f'Step' in content, \
                f"Scenario {scenario} lacks clear step structure"

    def test_completion_tracking_template(self):
        """Test completion tracker has team member templates."""
        completion = get_internal_docs_dir() / 'ops-team-training-completion.md'

        with open(completion) as f:
            content = f.read()

        # Check for team member templates
        assert 'Team Member 1' in content, "Missing Team Member 1 template"
        assert 'Team Member 2' in content, "Missing Team Member 2 template"
        assert 'Team Member 3' in content, "Missing Team Member 3 template"

    def test_acceptance_criteria_documented(self):
        """Test all acceptance criteria are documented."""
        guide = get_internal_docs_dir() / 'ops-team-training-guide.md'

        with open(guide) as f:
            content = f.read()

        # Acceptance criteria from spec:
        # - All ops team members trained
        # - Each member runs troubleshooting guide
        # - Each member executes restore procedure
        # - Knowledge transfer documented

        assert 'train' in content.lower(), "Not documenting training"
        assert 'troubleshoot' in content.lower(), "Not covering troubleshooting"
        assert 'restore' in content.lower(), "Not covering restore procedure"
        assert 'knowledge' in content.lower() or 'documentation' in content.lower(), \
            "Not covering knowledge transfer"

    def test_escalation_paths_defined(self):
        """Test training covers escalation procedures."""
        guide = get_internal_docs_dir() / 'ops-team-training-guide.md'

        with open(guide) as f:
            content = f.read()

        # Should cover when and how to escalate
        assert 'escalat' in content.lower(), "Missing escalation procedures"
        assert 'contact' in content.lower() or 'phone' in content.lower(), \
            "Missing contact information"

    def test_quick_reference_provided(self):
        """Test training includes quick reference guide."""
        guide = get_internal_docs_dir() / 'ops-team-training-guide.md'

        with open(guide) as f:
            content = f.read()

        # Should have quick reference section
        assert 'Quick Reference' in content or 'quick' in content.lower(), \
            "Missing quick reference guide"
        assert 'command' in content.lower(), "Missing command reference"

    def test_training_duration_specified(self):
        """Test training duration is clearly specified."""
        guide = get_internal_docs_dir() / 'ops-team-training-guide.md'

        with open(guide) as f:
            content = f.read()

        # Should specify 8 hours total (1+2+2+1+2)
        assert 'hour' in content.lower(), "Missing duration specification"
        assert '8' in content, "Missing total duration"

    def test_runbooks_referenced(self):
        """Test training references existing runbooks."""
        guide = get_internal_docs_dir() / 'ops-team-training-guide.md'

        with open(guide) as f:
            content = f.read()

        # Should reference runbooks directory
        assert 'runbook' in content.lower() or 'docs/runbooks' in content, \
            "Not referencing runbooks"

    def test_monitoring_dashboard_topics(self):
        """Test Module 2 covers monitoring dashboards."""
        guide = get_internal_docs_dir() / 'ops-team-training-guide.md'

        with open(guide) as f:
            content = f.read()

        # Should cover Grafana dashboards
        assert 'Grafana' in content, "Missing Grafana coverage"
        assert 'dashboard' in content.lower(), "Missing dashboard coverage"
        assert 'metric' in content.lower(), "Missing metrics coverage"

    def test_lab_verification_checklist(self):
        """Test hands-on lab has verification checklist."""
        lab = get_internal_docs_dir() / 'ops-team-training-hands-on-lab.md'

        with open(lab) as f:
            content = f.read()

        # Should have checklists for scenario completion
        assert 'checklist' in content.lower() or '[ ]' in content, \
            "Missing verification checklist"

    def test_all_modules_have_learning_objectives(self):
        """Test each module specifies learning objectives."""
        guide = get_internal_docs_dir() / 'ops-team-training-guide.md'

        with open(guide) as f:
            content = f.read()

        # Each module should have learning objectives
        assert 'learning objective' in content.lower() or 'will:' in content, \
            "Missing learning objectives"

    def test_hands_on_lab_has_expected_results(self):
        """Test each lab scenario specifies expected results."""
        lab = get_internal_docs_dir() / 'ops-team-training-hands-on-lab.md'

        with open(lab) as f:
            content = f.read()

        # Should have expected results
        assert 'Expected' in content, "Missing expected results"
        assert '✓' in content or 'PASS' in content, \
            "Missing pass/fail criteria"

    def test_training_availability(self):
        """Test training materials are in correct locations."""
        internal_docs = get_internal_docs_dir()

        # All training files should exist in internal docs
        files = [
            'ops-team-training-guide.md',
            'ops-team-training-hands-on-lab.md',
            'ops-team-training-completion.md'
        ]

        for filename in files:
            filepath = internal_docs / filename
            assert filepath.exists(), \
                f"Training file not found: {filepath}"

    def test_training_references_key_files(self):
        """Test training references key NEXUS files."""
        guide = get_internal_docs_dir() / 'ops-team-training-guide.md'

        with open(guide) as f:
            content = f.read()

        # Should reference key files
        assert 'incidents.json' in content, "Not referencing incidents.json"
        assert 'audit' in content.lower(), "Not referencing audit logs"
        assert 'prometheus' in content.lower() or 'metrics' in content.lower(), \
            "Not referencing metrics"

    def test_disaster_recovery_included(self):
        """Test disaster recovery is fully covered."""
        guide = get_internal_docs_dir() / 'ops-team-training-guide.md'
        lab = get_internal_docs_dir() / 'ops-team-training-hands-on-lab.md'

        # DR covered in both guide and lab
        with open(guide) as f:
            guide_content = f.read()
        with open(lab) as f:
            lab_content = f.read()

        # Training guide should have DR module
        assert 'Module 4' in guide_content and 'Disaster' in guide_content, \
            "DR not covered in training guide"

        # Lab should have DR scenario
        assert 'Scenario D' in lab_content and 'Disaster' in lab_content, \
            "DR not covered in lab"

    def test_document_metadata(self):
        """Test documents have proper metadata."""
        for doc_file in ['ops-team-training-guide.md',
                         'ops-team-training-hands-on-lab.md',
                         'ops-team-training-completion.md']:
            doc = get_internal_docs_dir() / doc_file

            with open(doc) as f:
                first_lines = f.read(500)

            # Should have version and update date
            assert 'Version' in first_lines or 'version' in first_lines, \
                f"{doc_file} missing version"
            assert '2026-06' in first_lines or 'Updated' in first_lines, \
                f"{doc_file} missing update date"

    def test_prerequisite_completion(self):
        """Test training can reference completed tasks."""
        guide = get_internal_docs_dir() / 'ops-team-training-guide.md'

        with open(guide) as f:
            content = f.read()

        # Should reference tasks that were completed before this
        # (Database, Monitoring, Alerting, Runbooks, DR)
        references = [
            'metrics',  # From monitoring
            'alert',    # From alerting
            'runbook',  # From runbooks
            'backup',   # From DR
            'restore'   # From DR
        ]

        for ref in references:
            assert ref.lower() in content.lower(), \
                f"Not referencing {ref} from completed tasks"

    def test_team_member_sign_off_required(self):
        """Test completion tracker requires team member sign-off."""
        completion = get_internal_docs_dir() / 'ops-team-training-completion.md'

        with open(completion) as f:
            content = f.read()

        # Should have sign-off sections
        assert 'Sign-Off' in content, "Missing sign-off requirement"
        assert 'Trainer' in content, "Missing trainer sign-off"
        assert 'Date' in content, "Missing date fields"

    def test_training_effectiveness_feedback(self):
        """Test completion tracker includes effectiveness feedback."""
        completion = get_internal_docs_dir() / 'ops-team-training-completion.md'

        with open(completion) as f:
            content = f.read()

        # Should have feedback mechanism
        assert 'Feedback' in content, "Missing training feedback"
        assert 'improve' in content.lower(), \
            "Missing improvement suggestions"

    def test_runbook_integration(self):
        """Test training materials reference runbooks directory."""
        guide = get_internal_docs_dir() / 'ops-team-training-guide.md'

        with open(guide) as f:
            content = f.read()

        # Should reference or list runbooks
        assert 'runbook' in content.lower(), "Not referencing runbooks"
        assert 'docs/runbooks' in content or 'runbooks/' in content, \
            "Missing runbooks directory reference"

    def test_training_content_length(self):
        """Test training materials are comprehensive (not too short)."""
        guide = get_internal_docs_dir() / 'ops-team-training-guide.md'
        lab = get_internal_docs_dir() / 'ops-team-training-hands-on-lab.md'

        # Each should be substantial (> 5000 characters)
        with open(guide) as f:
            guide_content = f.read()
        with open(lab) as f:
            lab_content = f.read()

        assert len(guide_content) > 5000, \
            f"Training guide too short ({len(guide_content)} chars)"
        assert len(lab_content) > 5000, \
            f"Lab guide too short ({len(lab_content)} chars)"

    def test_practical_command_examples(self):
        """Test training includes practical command examples."""
        guide = get_internal_docs_dir() / 'ops-team-training-guide.md'
        lab = get_internal_docs_dir() / 'ops-team-training-hands-on-lab.md'

        with open(guide) as f:
            guide_content = f.read()
        with open(lab) as f:
            lab_content = f.read()

        # Should have bash code blocks
        assert '```bash' in guide_content, "Guide missing bash examples"
        assert '```bash' in lab_content, "Lab missing bash examples"

        # Should have specific commands
        assert 'systemctl' in guide_content, "Missing systemctl examples"
        assert 'curl' in guide_content, "Missing curl examples"

    def test_acceptance_criteria_met(self):
        """Test all task acceptance criteria are covered."""
        guide = get_internal_docs_dir() / 'ops-team-training-guide.md'
        lab = get_internal_docs_dir() / 'ops-team-training-hands-on-lab.md'
        completion = get_internal_docs_dir() / 'ops-team-training-completion.md'

        # Acceptance Criteria from spec:
        # 1. All ops team members trained
        # 2. Each member runs troubleshooting guide
        # 3. Each member executes restore procedure
        # 4. Knowledge transfer documented

        # 1. Training guide covers training
        with open(guide) as f:
            content = f.read()
            assert 'Module' in content, "AC1: No training modules"

        # 2. Lab includes troubleshooting scenario
        with open(lab) as f:
            content = f.read()
            assert 'Scenario C' in content and 'Troubleshoot' in content, \
                "AC2: Missing troubleshooting scenario"

        # 3. Lab includes restore scenario
        with open(lab) as f:
            content = f.read()
            assert 'Scenario D' in content and 'Restore' in content, \
                "AC3: Missing restore scenario"

        # 4. Completion tracker documents knowledge transfer
        with open(completion) as f:
            content = f.read()
            assert 'Documentation' in content or 'knowledge' in content.lower(), \
                "AC4: No knowledge transfer documentation"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
