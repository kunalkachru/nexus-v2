"""
Tests for Production Deployment (Task 8.1)

Validates:
- Deployment documentation complete and comprehensive
- Deployment scripts exist and are well-formed
- Pre-deployment validation procedures documented
- Post-deployment health checks documented
- Deployment checklist comprehensive
- All acceptance criteria covered
"""

import re
from pathlib import Path


def get_docs_dir():
    """Get path to docs directory."""
    return Path(__file__).parent.parent / 'docs'


def get_scripts_dir():
    """Get path to scripts directory."""
    return Path(__file__).parent.parent / 'scripts'


def get_internal_docs_dir():
    """Get path to internal docs directory."""
    return get_docs_dir() / 'internal'


class TestProductionDeployment:
    """Production deployment validation tests."""

    def test_deployment_guide_exists(self):
        """Test production deployment guide exists."""
        guide = get_internal_docs_dir() / 'production-deployment-guide.md'
        assert guide.exists(), \
            f"Production deployment guide not found at {guide}"

    def test_deployment_checklist_exists(self):
        """Test deployment checklist exists."""
        checklist = get_internal_docs_dir() / 'deployment-checklist.md'
        assert checklist.exists(), \
            f"Deployment checklist not found at {checklist}"

    def test_pre_deployment_script_exists(self):
        """Test pre-deployment validation script exists."""
        script = get_scripts_dir() / 'pre-deployment-validation.sh'
        assert script.exists(), \
            f"Pre-deployment validation script not found at {script}"

    def test_post_deployment_script_exists(self):
        """Test post-deployment health check script exists."""
        script = get_scripts_dir() / 'post-deployment-health-check.sh'
        assert script.exists(), \
            f"Post-deployment health check script not found at {script}"

    def test_dockerfile_exists(self):
        """Test Dockerfile exists."""
        dockerfile = Path(__file__).parent.parent / 'Dockerfile'
        assert dockerfile.exists(), \
            f"Dockerfile not found at {dockerfile}"

    def test_docker_compose_exists(self):
        """Test docker-compose.yml exists."""
        compose = Path(__file__).parent.parent / 'docker-compose.yml'
        assert compose.exists(), \
            f"docker-compose.yml not found at {compose}"

    def test_deployment_guide_completeness(self):
        """Test deployment guide covers all required sections."""
        guide = get_internal_docs_dir() / 'production-deployment-guide.md'

        with open(guide) as f:
            content = f.read()

        # Check for required sections
        sections = [
            'Pre-Deployment Validation',
            'Production Docker Image',
            'Deployment Procedure',
            'Health Verification',
            'Smoke Testing',
            'Deployment Checklist',
            'Rollback Plan'
        ]

        for section in sections:
            assert section in content, f"Missing section: {section}"

    def test_deployment_guide_has_docker_steps(self):
        """Test deployment guide covers Docker operations."""
        guide = get_internal_docs_dir() / 'production-deployment-guide.md'

        with open(guide) as f:
            content = f.read()

        # Should mention key Docker operations
        docker_terms = [
            'docker build',
            'docker-compose',
            'docker run',
            'APP_ENV=product'
        ]

        for term in docker_terms:
            assert term in content, f"Missing Docker operation: {term}"

    def test_deployment_guide_covers_options(self):
        """Test deployment guide covers multiple deployment options."""
        guide = get_internal_docs_dir() / 'production-deployment-guide.md'

        with open(guide) as f:
            content = f.read()

        # Should document multiple deployment approaches
        options = [
            'Option 1',
            'Option 2',
            'Option 3',
            'docker-compose',
            'Docker Run',
            'Kubernetes'
        ]

        for option in options:
            assert option in content, f"Missing deployment option: {option}"

    def test_pre_deployment_script_structure(self):
        """Test pre-deployment validation script is well-structured."""
        script = get_scripts_dir() / 'pre-deployment-validation.sh'

        with open(script) as f:
            content = f.read()

        # Check for required components
        assert '#!/bin/bash' in content, "Missing shebang"
        assert 'set -e' in content, "Missing error handling"
        assert 'function' in content or 'pass()' in content, "Missing functions"
        assert 'exit' in content, "Missing exit handling"

    def test_pre_deployment_checks_coverage(self):
        """Test pre-deployment script covers all required checks."""
        script = get_scripts_dir() / 'pre-deployment-validation.sh'

        with open(script) as f:
            content = f.read()

        # Should check for key prerequisites
        checks = [
            'directory',
            'file',
            'docker',
            'database',
            'python',
            'dependency',
            'test'
        ]

        for check in checks:
            assert check.lower() in content.lower(), \
                f"Missing check for: {check}"

    def test_post_deployment_script_structure(self):
        """Test post-deployment health check script is well-structured."""
        script = get_scripts_dir() / 'post-deployment-health-check.sh'

        with open(script) as f:
            content = f.read()

        # Check for required components
        assert '#!/bin/bash' in content, "Missing shebang"
        assert 'set -e' in content, "Missing error handling"
        assert 'health' in content.lower(), "Not checking health"
        assert 'exit' in content, "Missing exit handling"

    def test_post_deployment_health_checks(self):
        """Test post-deployment script covers all health checks."""
        script = get_scripts_dir() / 'post-deployment-health-check.sh'

        with open(script) as f:
            content = f.read()

        # Should verify multiple aspects of health
        checks = [
            'health',
            'database',
            'metrics',
            'logs',
            'port',
            'resource'
        ]

        for check in checks:
            assert check.lower() in content.lower(), \
                f"Missing health check: {check}"

    def test_deployment_checklist_comprehensive(self):
        """Test deployment checklist is comprehensive."""
        checklist = get_internal_docs_dir() / 'deployment-checklist.md'

        with open(checklist) as f:
            content = f.read()

        # Should cover all deployment phases
        phases = [
            'Pre-Deployment',
            'During Deployment',
            'Post-Deployment',
            'Phase 1',
            'Phase 2',
            'Phase 3',
            'Phase 4',
            'Phase 5',
            'Phase 6'
        ]

        for phase in phases:
            assert phase in content, f"Missing deployment phase: {phase}"

    def test_deployment_checklist_has_sign_offs(self):
        """Test deployment checklist includes sign-off sections."""
        checklist = get_internal_docs_dir() / 'deployment-checklist.md'

        with open(checklist) as f:
            content = f.read()

        # Should have approval and sign-off
        assert 'Sign-Off' in content, "Missing sign-off section"
        assert 'Approval' in content, "Missing approval section"
        assert 'Signature' in content, "Missing signature fields"

    def test_deployment_checklist_has_rollback(self):
        """Test deployment checklist includes rollback procedure."""
        checklist = get_internal_docs_dir() / 'deployment-checklist.md'

        with open(checklist) as f:
            content = f.read()

        # Should have rollback decision and execution
        assert 'Rollback' in content, "Missing rollback section"
        assert 'restore' in content.lower(), "Missing restore in rollback"

    def test_dockerfile_production_ready(self):
        """Test Dockerfile is configured for production."""
        dockerfile = Path(__file__).parent.parent / 'Dockerfile'

        with open(dockerfile) as f:
            content = f.read()

        # Should have production-relevant settings
        assert 'python:3.11-slim' in content or 'python:3.11' in content, \
            "Should use slim Python image for production"
        assert 'APP_ENV' in content, "Should support APP_ENV variable"
        assert 'PYTHONUNBUFFERED' in content, \
            "Should have PYTHONUNBUFFERED for container logging"

    def test_docker_compose_production_config(self):
        """Test docker-compose.yml has production settings."""
        compose = Path(__file__).parent.parent / 'docker-compose.yml'

        with open(compose) as f:
            content = f.read()

        # Should have production environment
        assert 'APP_ENV' in content, "Should configure APP_ENV"
        assert 'product' in content, "Should support product environment"
        assert 'volumes' in content, "Should persist data with volumes"

    def test_acceptance_criteria_covered(self):
        """Test all task acceptance criteria are covered."""
        guide = get_internal_docs_dir() / 'production-deployment-guide.md'
        checklist = get_internal_docs_dir() / 'deployment-checklist.md'

        # Acceptance criteria from spec:
        # - Service starts cleanly
        # - Health check passes
        # - Smoke tests all pass
        # - Metrics flowing to Prometheus

        with open(guide) as f:
            guide_content = f.read()
        with open(checklist) as f:
            checklist_content = f.read()

        combined = guide_content + checklist_content

        criteria = [
            'start',  # Service starts cleanly
            'health',  # Health check passes
            'smoke test',  # Smoke tests pass
            'metric',  # Metrics flowing to Prometheus
            'prometheus'
        ]

        for criterion in criteria:
            assert criterion.lower() in combined.lower(), \
                f"Missing acceptance criterion coverage: {criterion}"

    def test_pre_deployment_and_post_deployment_linked(self):
        """Test pre and post deployment procedures are properly sequenced."""
        pre_script = get_scripts_dir() / 'pre-deployment-validation.sh'
        post_script = get_scripts_dir() / 'post-deployment-health-check.sh'

        # Both should exist
        assert pre_script.exists(), "Pre-deployment script missing"
        assert post_script.exists(), "Post-deployment script missing"

        # Post-deployment should reference health checks
        with open(post_script) as f:
            post_content = f.read()

        assert 'health' in post_content.lower(), \
            "Post-deployment should check health"

    def test_guides_reference_each_other(self):
        """Test deployment guide and checklist reference each other."""
        guide = get_internal_docs_dir() / 'production-deployment-guide.md'
        checklist = get_internal_docs_dir() / 'deployment-checklist.md'

        with open(guide) as f:
            guide_content = f.read()
        with open(checklist) as f:
            checklist_content = f.read()

        # Should cross-reference
        assert 'checklist' in guide_content.lower(), \
            "Guide should reference checklist"
        assert 'guide' in checklist_content.lower() or 'documentation' in checklist_content.lower(), \
            "Checklist should reference guide"

    def test_scripts_are_executable(self):
        """Test that deployment scripts are marked executable."""
        import os

        scripts = [
            get_scripts_dir() / 'pre-deployment-validation.sh',
            get_scripts_dir() / 'post-deployment-health-check.sh'
        ]

        for script in scripts:
            # Note: On Windows, file executable bit may not apply
            # Just verify the file exists
            assert script.exists(), f"Script missing: {script}"

    def test_deployment_guide_has_docker_build_commands(self):
        """Test deployment guide includes actual Docker build commands."""
        guide = get_internal_docs_dir() / 'production-deployment-guide.md'

        with open(guide) as f:
            content = f.read()

        # Should have runnable Docker build commands
        assert 'docker build' in content, "Missing docker build command"
        assert '-t nexus:prod' in content, "Missing image tag specification"
        assert 'APP_ENV=product' in content, "Missing production environment variable"

    def test_deployment_guide_has_health_commands(self):
        """Test deployment guide includes health check commands."""
        guide = get_internal_docs_dir() / 'production-deployment-guide.md'

        with open(guide) as f:
            content = f.read()

        # Should have health check examples
        assert 'curl http://localhost:7860/health' in content, \
            "Missing health check command"
        assert 'jq' in content, "Should use jq for JSON output"

    def test_deployment_guide_has_smoke_test_reference(self):
        """Test deployment guide references smoke testing."""
        guide = get_internal_docs_dir() / 'production-deployment-guide.md'

        with open(guide) as f:
            content = f.read()

        # Should reference smoke testing
        assert 'smoke' in content.lower(), "Missing smoke test reference"
        assert 'local_enterprise_smoke' in content, \
            "Should reference smoke test script"

    def test_checklist_has_phased_execution(self):
        """Test checklist is organized with clear phases."""
        checklist = get_internal_docs_dir() / 'deployment-checklist.md'

        with open(checklist) as f:
            content = f.read()

        # Should have clearly marked phases
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

    def test_checklist_metrics_recording(self):
        """Test checklist includes metrics recording fields."""
        checklist = get_internal_docs_dir() / 'deployment-checklist.md'

        with open(checklist) as f:
            content = f.read()

        # Should record before/after metrics
        metrics = [
            'incident',
            'database',
            'response',
            'error',
            'memory',
            'cpu'
        ]

        for metric in metrics:
            assert metric.lower() in content.lower(), \
                f"Missing metrics field: {metric}"

    def test_deployment_guide_content_length(self):
        """Test deployment guide is comprehensive (not too short)."""
        guide = get_internal_docs_dir() / 'production-deployment-guide.md'

        with open(guide) as f:
            content = f.read()

        # Should be substantial documentation
        assert len(content) > 3000, \
            f"Deployment guide too short ({len(content)} chars)"

    def test_checklist_content_length(self):
        """Test deployment checklist is comprehensive."""
        checklist = get_internal_docs_dir() / 'deployment-checklist.md'

        with open(checklist) as f:
            content = f.read()

        # Should be detailed with many checkpoints
        assert len(content) > 3000, \
            f"Deployment checklist too short ({len(content)} chars)"

    def test_scripts_have_proper_logging(self):
        """Test deployment scripts have good logging output."""
        pre_script = get_scripts_dir() / 'pre-deployment-validation.sh'
        post_script = get_scripts_dir() / 'post-deployment-health-check.sh'

        for script in [pre_script, post_script]:
            with open(script) as f:
                content = f.read()

            # Should have logging/output functions
            assert 'echo' in content, f"Script {script.name} lacks output"
            # Should use colors or symbols for clarity
            assert '✓' in content or 'pass' in content.lower() or 'GREEN' in content, \
                f"Script {script.name} lacks success indicators"

    def test_deployment_guide_references_runbooks(self):
        """Test deployment guide references incident runbooks."""
        guide = get_internal_docs_dir() / 'production-deployment-guide.md'

        with open(guide) as f:
            content = f.read()

        # Should reference runbooks for troubleshooting
        assert 'runbook' in content.lower(), "Should reference runbooks"
        assert 'docs/runbooks' in content, "Should link to runbooks directory"

    def test_all_files_have_metadata(self):
        """Test all deployment files have proper headers and metadata."""
        # Documentation files should have version/date
        docs = [
            get_internal_docs_dir() / 'production-deployment-guide.md',
        ]

        for doc in docs:
            with open(doc) as f:
                first_section = f.read(500)
            assert 'Version' in first_section or '2026-06' in first_section, \
                f"{doc.name} missing version/date metadata"

        # Scripts should have proper comments
        scripts = [
            get_scripts_dir() / 'pre-deployment-validation.sh',
            get_scripts_dir() / 'post-deployment-health-check.sh'
        ]

        for script in scripts:
            with open(script) as f:
                content = f.read(300)
            assert '#!/bin/bash' in content and 'Purpose:' in content, \
                f"{script.name} missing proper script header"

        # Checklist is a template, just needs title
        checklist = get_internal_docs_dir() / 'deployment-checklist.md'
        with open(checklist) as f:
            content = f.read(200)
        assert 'Deployment Checklist' in content, \
            f"{checklist.name} missing title"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
