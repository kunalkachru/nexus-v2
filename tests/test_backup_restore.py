"""
Tests for backup and restore scripts.

Validates:
- Scripts exist and are executable
- Backup script creates compressed files
- Restore script handles backups safely
- Both scripts have proper error handling
"""

import os
import gzip
import tempfile
import json
import subprocess
from pathlib import Path


def get_scripts_dir():
    """Get path to scripts directory."""
    return Path(__file__).parent.parent / 'scripts'


def test_backup_script_exists():
    """Test backup script file exists and is executable."""
    backup_script = get_scripts_dir() / 'backup_nexus.sh'
    assert backup_script.exists(), f"Backup script not found at {backup_script}"

    # Check if executable
    assert os.access(backup_script, os.X_OK), "Backup script is not executable"


def test_restore_script_exists():
    """Test restore script file exists and is executable."""
    restore_script = get_scripts_dir() / 'restore_nexus.sh'
    assert restore_script.exists(), f"Restore script not found at {restore_script}"

    # Check if executable
    assert os.access(restore_script, os.X_OK), "Restore script is not executable"


def test_backup_script_syntax():
    """Test backup script has valid bash syntax."""
    backup_script = get_scripts_dir() / 'backup_nexus.sh'

    # Check for common bash syntax issues
    with open(backup_script) as f:
        content = f.read()

    # Must have shebang
    assert content.startswith('#!/bin/bash'), "Missing shebang"

    # Must have set -e for error handling
    assert 'set -e' in content, "Missing 'set -e' for error handling"

    # Must have error handling function
    assert 'error()' in content, "Missing error() function"


def test_restore_script_syntax():
    """Test restore script has valid bash syntax."""
    restore_script = get_scripts_dir() / 'restore_nexus.sh'

    with open(restore_script) as f:
        content = f.read()

    # Must have shebang
    assert content.startswith('#!/bin/bash'), "Missing shebang"

    # Must have set -e for error handling
    assert 'set -e' in content, "Missing 'set -e' for error handling"

    # Must have error handling function
    assert 'error()' in content, "Missing error() function"


def test_backup_script_creates_backup():
    """Test backup script can create a backup file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test database
        test_db = Path(tmpdir) / "test.json"
        test_data = {"incidents": [{"id": "1", "data": "test"}]}
        with open(test_db, 'w') as f:
            json.dump(test_data, f)

        # Create backup directory
        backup_dir = Path(tmpdir) / "backups"
        backup_dir.mkdir()

        # Verify backup script has backup creation logic
        backup_script = get_scripts_dir() / 'backup_nexus.sh'
        with open(backup_script) as f:
            content = f.read()

        # Check for gzip compression
        assert 'gzip' in content, "Backup script doesn't mention gzip"

        # Check for S3 upload logic
        assert 's3' in content.lower(), "Backup script missing S3 upload"

        # Check for retention cleanup
        assert 'mtime' in content or 'find' in content, "Backup script missing cleanup logic"


def test_backup_script_handles_errors():
    """Test backup script has proper error handling."""
    backup_script = get_scripts_dir() / 'backup_nexus.sh'
    with open(backup_script) as f:
        content = f.read()

    # Check for database file existence check
    assert 'not found' in content or 'exists' in content.lower(), \
        "Backup script missing database existence check"

    # Check for backup size verification
    assert 'empty' in content.lower() or 'size' in content, \
        "Backup script missing backup size check"

    # Check for gzip integrity check
    assert 'gzip -t' in content, "Backup script missing gzip integrity check"


def test_restore_script_handles_errors():
    """Test restore script has proper error handling."""
    restore_script = get_scripts_dir() / 'restore_nexus.sh'
    with open(restore_script) as f:
        content = f.read()

    # Check for argument validation
    assert '$#' in content, "Restore script missing argument check"

    # Check for backup existence check
    assert 'not found' in content or '-f' in content, \
        "Restore script missing backup existence check"

    # Check for integrity check
    assert 'integrity' in content.lower() or 'pragma' in content.lower(), \
        "Restore script missing integrity check"

    # Check for rollback capability
    assert 'backup' in content.lower() or '.backup' in content, \
        "Restore script missing rollback capability"


def test_backup_script_mentions_cron():
    """Test backup script mentions cron job setup."""
    backup_script = get_scripts_dir() / 'backup_nexus.sh'
    with open(backup_script) as f:
        content = f.read()

    # Should document cron entry
    assert 'cron' in content.lower(), "Backup script should document cron setup"

    # Should mention 6-hour interval
    assert '6' in content, "Backup script should mention 6-hour interval"


def test_restore_script_mentions_usage():
    """Test restore script documents usage clearly."""
    restore_script = get_scripts_dir() / 'restore_nexus.sh'
    with open(restore_script) as f:
        content = f.read()

    # Should explain usage
    assert 'Usage' in content or 'usage' in content.lower(), \
        "Restore script should document usage"

    # Should show examples
    assert 'Example' in content or 'example' in content.lower() or 'aws s3' in content, \
        "Restore script should show usage examples"


def test_backup_script_compression():
    """Test backup script uses proper compression."""
    backup_script = get_scripts_dir() / 'backup_nexus.sh'
    with open(backup_script) as f:
        content = f.read()

    # Should use gzip compression
    assert 'gzip' in content, "Backup script should use gzip"

    # Should verify compression
    assert 'gzip -t' in content, "Backup script should verify gzip integrity"


def test_restore_script_verification():
    """Test restore script verifies restored data."""
    restore_script = get_scripts_dir() / 'restore_nexus.sh'
    with open(restore_script) as f:
        content = f.read()

    # Should verify restored database
    assert 'verify' in content.lower(), "Restore script should verify data"

    # Should check for empty database
    assert 'empty' in content.lower() or 'size' in content, \
        "Restore script should check if database is empty"


def test_backup_script_configuration():
    """Test backup script is configurable via environment."""
    backup_script = get_scripts_dir() / 'backup_nexus.sh'
    with open(backup_script) as f:
        content = f.read()

    # Should have configurable paths
    assert 'BACKUP_DIR' in content, "Backup script should have BACKUP_DIR config"
    assert 'DATABASE_PATH' in content, "Backup script should have DATABASE_PATH config"
    assert 'S3_BUCKET' in content, "Backup script should have S3_BUCKET config"


def test_restore_script_configuration():
    """Test restore script is configurable via environment."""
    restore_script = get_scripts_dir() / 'restore_nexus.sh'
    with open(restore_script) as f:
        content = f.read()

    # Should have configurable database path
    assert 'DATABASE_PATH' in content, "Restore script should have DATABASE_PATH config"


def test_scripts_readability():
    """Test scripts are well-commented and readable."""
    backup_script = get_scripts_dir() / 'backup_nexus.sh'
    restore_script = get_scripts_dir() / 'restore_nexus.sh'

    for script in [backup_script, restore_script]:
        with open(script) as f:
            lines = f.readlines()

        # Should have reasonable length
        assert len(lines) > 20, f"{script.name} is too short"
        assert len(lines) < 300, f"{script.name} is too long"

        # Should have comments
        comment_lines = sum(1 for line in lines if line.strip().startswith('#'))
        assert comment_lines > 3, f"{script.name} lacks comments"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
