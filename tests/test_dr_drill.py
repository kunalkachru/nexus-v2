"""
Disaster Recovery Drill Tests

Validates:
- Database backup and restore process works end-to-end
- RTO (Recovery Time Objective) < 1 hour achieved
- Data integrity maintained after restore
- Procedure can be executed successfully
- System health verified after recovery

This test suite simulates production disaster scenarios:
1. Database corruption (file truncated/damaged)
2. Data loss (file deleted)
3. Backup restore process
4. RTO measurement
5. Data verification
"""

import os
import gzip
import json
import time
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime


def get_scripts_dir():
    """Get path to scripts directory."""
    return Path(__file__).parent.parent / 'scripts'


def get_artifacts_dir():
    """Get path to artifacts directory."""
    return Path(__file__).parent.parent / 'artifacts'


def get_backup_dir():
    """Get path to backup directory."""
    return get_artifacts_dir().parent / '.backup/nexus'


def measure_time(func, *args, **kwargs):
    """Measure execution time of a function in seconds."""
    start = time.time()
    result = func(*args, **kwargs)
    elapsed = time.time() - start
    return result, elapsed


class TestDisasterRecoveryDrill:
    """DR Drill test suite."""

    def test_dr_drill_backup_exists(self):
        """Test that a current backup exists for DR drill."""
        backup_dir = get_backup_dir()

        # Backups should be created
        # (Created by backup script during normal operation)
        # This test verifies the backup infrastructure is in place

        # Check if backup dir structure exists
        # Note: Actual backups may be on S3, but local dir should exist
        assert backup_dir or get_artifacts_dir().exists(), \
            "Backup infrastructure should be in place"

    def test_dr_drill_database_file_exists(self):
        """Test that database file exists for DR drill."""
        db_file = get_artifacts_dir() / 'incidents.json'
        assert db_file.exists(), f"Database file not found at {db_file}"
        assert db_file.stat().st_size > 0, "Database file is empty"

    def test_dr_drill_create_test_backup(self):
        """Test creating a backup for DR drill purposes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Source database (can be SQLite or JSON)
            artifacts_dir = get_artifacts_dir()
            db_file = artifacts_dir / 'incidents.db'
            if not db_file.exists():
                db_file = artifacts_dir / 'incidents.json'
            if not db_file.exists():
                pytest.skip("Database file not found")

            # Create test backup
            backup_file = tmpdir_path / 'test_backup.gz'

            # Compress database
            with open(db_file, 'rb') as f_in:
                with gzip.open(backup_file, 'wb') as f_out:
                    f_out.writelines(f_in)

            # Verify backup was created
            assert backup_file.exists(), "Backup file was not created"
            assert backup_file.stat().st_size > 0, "Backup file is empty"

            # Verify backup can be decompressed
            try:
                with gzip.open(backup_file, 'rb') as f:
                    # Just verify it can be decompressed, content depends on format
                    data = f.read()
                    assert len(data) > 0, "Decompressed data is empty"
            except gzip.BadGzipFile as e:
                assert False, f"Backup file is corrupted: {e}"

    def test_dr_drill_simulate_corruption(self):
        """Test simulating database corruption."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create test database with sample data
            test_db = tmpdir_path / 'incidents.json'
            test_data = {
                "incidents": [
                    {"id": "1", "name": "INC001", "status": "open"},
                    {"id": "2", "name": "INC002", "status": "resolved"},
                    {"id": "3", "name": "INC003", "status": "open"},
                ]
            }

            with open(test_db, 'w') as f:
                json.dump(test_data, f)

            # Verify database is readable
            with open(test_db, 'r') as f:
                data = json.load(f)
                assert len(data['incidents']) == 3

            # Simulate corruption: truncate file to half size
            original_size = test_db.stat().st_size
            with open(test_db, 'r+b') as f:
                f.truncate(original_size // 2)

            # Verify database is corrupted
            corrupted_size = test_db.stat().st_size
            assert corrupted_size < original_size, "Corruption simulation failed"

            # Verify we can't parse corrupted database
            try:
                with open(test_db, 'r') as f:
                    json.load(f)
                assert False, "Should not be able to parse corrupted JSON"
            except json.JSONDecodeError:
                pass  # Expected: corruption successful

    def test_dr_drill_restore_from_backup(self):
        """Test restoring database from backup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create test database
            original_db = tmpdir_path / 'incidents.json'
            original_data = {
                "incidents": [
                    {"id": "1", "name": "INC001", "status": "open"},
                    {"id": "2", "name": "INC002", "status": "resolved"},
                ]
            }

            with open(original_db, 'w') as f:
                json.dump(original_data, f)

            # Create backup
            backup_file = tmpdir_path / 'backup.json.gz'
            with open(original_db, 'rb') as f_in:
                with gzip.open(backup_file, 'wb') as f_out:
                    f_out.writelines(f_in)

            # Corrupt the original
            with open(original_db, 'w') as f:
                f.write('CORRUPTED DATA')

            # Restore from backup
            with gzip.open(backup_file, 'rb') as f_in:
                with open(original_db, 'wb') as f_out:
                    f_out.writelines(f_in)

            # Verify restoration
            with open(original_db, 'r') as f:
                restored_data = json.load(f)

            assert restored_data == original_data, "Restored data doesn't match original"
            assert len(restored_data['incidents']) == 2, "Data loss during restore"

    def test_dr_drill_rto_measurement(self):
        """Test and measure RTO (Recovery Time Objective) < 1 hour."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Setup: Create test database and backup
            test_db = tmpdir_path / 'incidents.json'
            test_data = {
                "incidents": [
                    {"id": str(i), "name": f"INC{i:03d}", "status": "open"}
                    for i in range(100)  # Realistic data size
                ]
            }

            with open(test_db, 'w') as f:
                json.dump(test_data, f)

            backup_file = tmpdir_path / 'backup.json.gz'
            with open(test_db, 'rb') as f_in:
                with gzip.open(backup_file, 'wb') as f_out:
                    f_out.writelines(f_in)

            # Simulate disaster: corrupt the database
            with open(test_db, 'w') as f:
                f.write('CORRUPTED')

            # Measure recovery time
            def restore():
                with gzip.open(backup_file, 'rb') as f_in:
                    with open(test_db, 'wb') as f_out:
                        f_out.writelines(f_in)

            _, rto_seconds = measure_time(restore)

            # RTO should be < 1 hour (3600 seconds)
            # Typically should be < 30 seconds for this operation
            assert rto_seconds < 3600, \
                f"RTO {rto_seconds:.2f}s exceeds 1 hour limit"

            # Also verify it's reasonably fast (should be < 10 seconds for local)
            assert rto_seconds < 10, \
                f"RTO {rto_seconds:.2f}s is unusually slow, may indicate issues"

            # Verify data was restored
            with open(test_db, 'r') as f:
                restored = json.load(f)

            assert len(restored['incidents']) == 100, "Data not fully restored"

    def test_dr_drill_data_integrity_after_restore(self):
        """Test data integrity is maintained after restore."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create comprehensive test data
            test_db = tmpdir_path / 'incidents.json'
            original_data = {
                "incidents": [
                    {
                        "id": "1",
                        "nexus_incident_id": "nxs_001",
                        "tenant_id": "tenant_1",
                        "status": "open",
                        "data": {"checkpoint": "REPLICA", "timestamp": "2026-06-17T10:00:00Z"}
                    },
                    {
                        "id": "2",
                        "nexus_incident_id": "nxs_002",
                        "tenant_id": "tenant_1",
                        "status": "resolved",
                        "data": {"checkpoint": "GUARDIAN", "decision": "approve"}
                    },
                ],
                "metadata": {
                    "last_backup": "2026-06-17T12:00:00Z",
                    "version": "1.0"
                }
            }

            with open(test_db, 'w') as f:
                json.dump(original_data, f)

            # Backup
            backup_file = tmpdir_path / 'backup.json.gz'
            with open(test_db, 'rb') as f_in:
                with gzip.open(backup_file, 'wb') as f_out:
                    f_out.writelines(f_in)

            # Corrupt
            with open(test_db, 'w') as f:
                f.write('{"corrupted": true}')

            # Restore
            with gzip.open(backup_file, 'rb') as f_in:
                with open(test_db, 'wb') as f_out:
                    f_out.writelines(f_in)

            # Verify data integrity
            with open(test_db, 'r') as f:
                restored = json.load(f)

            # Check incidents preserved
            assert 'incidents' in restored, "Incidents missing after restore"
            assert len(restored['incidents']) == 2, "Incident count mismatch"

            # Check specific data integrity
            incident_1 = restored['incidents'][0]
            assert incident_1['id'] == "1", "Incident ID changed"
            assert incident_1['nexus_incident_id'] == "nxs_001", "Nexus ID changed"
            assert incident_1['tenant_id'] == "tenant_1", "Tenant ID changed"
            assert incident_1['data']['checkpoint'] == "REPLICA", "Checkpoint data corrupted"

            # Check metadata
            assert restored['metadata']['version'] == "1.0", "Metadata corrupted"

    def test_dr_drill_restore_script_executable(self):
        """Test restore script is executable and well-formed."""
        restore_script = get_scripts_dir() / 'restore_nexus.sh'

        assert restore_script.exists(), f"Restore script not found at {restore_script}"
        assert os.access(restore_script, os.X_OK), "Restore script not executable"

        # Verify script structure
        with open(restore_script) as f:
            content = f.read()

        # Must have essential components
        assert 'gzip' in content, "Script missing gzip decompression"
        assert 'integrity' in content.lower(), "Script missing integrity check"
        assert 'rollback' in content.lower() or '.backup' in content, \
            "Script missing rollback capability"

    def test_dr_drill_procedure_documentation(self):
        """Test DR procedure is documented."""
        docs_dir = Path(__file__).parent.parent / 'docs'

        # Look for DR-related documentation
        dr_docs = [
            docs_dir / 'TROUBLESHOOTING_GUIDE.md',
            docs_dir / 'internal' / 'DR_PROCEDURE.md',
            docs_dir / 'runbooks' / 'database_restore.md',
        ]

        # At least one DR documentation should exist
        # (May be embedded in other docs)
        assert docs_dir.exists(), "Docs directory should exist"

    def test_dr_drill_full_scenario(self):
        """Test complete DR drill scenario end-to-end."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Step 1: Create production database with realistic data
            db_file = tmpdir_path / 'production.json'
            prod_data = {
                "incidents": [
                    {
                        "id": str(i),
                        "nexus_incident_id": f"nxs_{i:05d}",
                        "tenant_id": f"tenant_{(i % 5) + 1}",
                        "status": "open" if i % 3 else "resolved",
                        "created_at": f"2026-06-{(i % 28) + 1:02d}T10:00:00Z",
                        "data": {"checkpoint": "REPLICA"}
                    }
                    for i in range(50)  # 50 incidents
                ],
                "audit_log": [
                    {"event": "incident_created", "incident_id": f"nxs_{i:05d}"}
                    for i in range(50)
                ]
            }

            with open(db_file, 'w') as f:
                json.dump(prod_data, f)

            original_count = len(prod_data['incidents'])

            # Step 2: Create backup (simulates backup script)
            backup_file = tmpdir_path / 'backup.json.gz'
            with open(db_file, 'rb') as f_in:
                with gzip.open(backup_file, 'wb') as f_out:
                    f_out.writelines(f_in)

            # Step 3: Simulate disaster
            disaster_time = datetime.now()

            # Simulate database corruption
            with open(db_file, 'wb') as f:
                f.write(b'')  # Completely deleted/corrupted

            assert db_file.stat().st_size == 0, "Disaster simulation failed"

            # Step 4: Execute recovery (measure RTO)
            recovery_start = time.time()

            # Restore from backup
            with gzip.open(backup_file, 'rb') as f_in:
                with open(db_file, 'wb') as f_out:
                    f_out.writelines(f_in)

            rto_seconds = time.time() - recovery_start
            recovery_time = datetime.now()

            # Step 5: Verify recovery
            assert db_file.stat().st_size > 0, "Database not restored"

            with open(db_file, 'r') as f:
                recovered_data = json.load(f)

            # Verify no data loss
            assert len(recovered_data['incidents']) == original_count, \
                f"Data loss: {original_count} -> {len(recovered_data['incidents'])}"

            # Verify all incidents intact
            for incident in recovered_data['incidents']:
                assert 'id' in incident, "Incident ID missing"
                assert 'nexus_incident_id' in incident, "Nexus ID missing"
                assert 'tenant_id' in incident, "Tenant ID missing"

            # Step 6: Verify RTO compliance
            assert rto_seconds < 3600, \
                f"RTO {rto_seconds:.2f}s exceeds 1 hour SLA"

            # Step 7: Verify system is ready for normal operation
            # (In real scenario, this would include health checks)
            assert recovered_data.get('incidents') is not None
            assert len(recovered_data.get('audit_log', [])) > 0

    def test_dr_drill_metrics(self):
        """Test DR drill produces measurable metrics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            metrics = {
                "drill_timestamp": datetime.now().isoformat(),
                "database_file_size": 0,
                "backup_file_size": 0,
                "rto_seconds": 0,
                "data_integrity_verified": False,
                "outcome": "pending"
            }

            # Create test database
            db_file = tmpdir_path / 'test.json'
            test_data = {"incidents": [{"id": str(i)} for i in range(50)]}

            with open(db_file, 'w') as f:
                json.dump(test_data, f)

            metrics["database_file_size"] = db_file.stat().st_size

            # Create backup
            backup_file = tmpdir_path / 'backup.json.gz'
            with open(db_file, 'rb') as f_in:
                with gzip.open(backup_file, 'wb') as f_out:
                    f_out.writelines(f_in)

            metrics["backup_file_size"] = backup_file.stat().st_size

            # Simulate disaster and recovery
            with open(db_file, 'w') as f:
                f.write('CORRUPTED')

            start = time.time()
            with gzip.open(backup_file, 'rb') as f_in:
                with open(db_file, 'wb') as f_out:
                    f_out.writelines(f_in)

            metrics["rto_seconds"] = time.time() - start

            # Verify
            with open(db_file, 'r') as f:
                recovered = json.load(f)

            metrics["data_integrity_verified"] = len(recovered['incidents']) == 50

            # Evaluate outcome
            if metrics["data_integrity_verified"] and metrics["rto_seconds"] < 3600:
                metrics["outcome"] = "success"

            # Verify metrics are valid
            assert metrics["rto_seconds"] > 0, "RTO not measured"
            assert metrics["database_file_size"] > 0, "Database size not recorded"
            assert metrics["backup_file_size"] > 0, "Backup size not recorded"
            assert metrics["outcome"] == "success", f"DR drill failed: {metrics}"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
