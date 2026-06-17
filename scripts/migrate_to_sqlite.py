#!/usr/bin/env python3
"""
Migrate incidents from JSON file to SQLite database.

Usage:
    python scripts/migrate_to_sqlite.py [--json-path PATH] [--db-path PATH] [--dry-run]

Options:
    --json-path PATH    Path to JSON file (default: artifacts/incidents.json)
    --db-path PATH      Path to SQLite DB (default: artifacts/nexus.db)
    --dry-run          Don't commit changes, just validate
"""

import argparse
import asyncio
import json
import random
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.db import SQLiteDatabase


async def migrate_incidents(json_path: Path, db_path: Path, dry_run: bool = False) -> dict:
    """
    Migrate incidents from JSON to SQLite.

    Args:
        json_path: Path to JSON file
        db_path: Path to SQLite database
        dry_run: If True, validate without committing

    Returns:
        Migration report dict
    """
    report = {
        "status": "success",
        "json_path": str(json_path),
        "db_path": str(db_path),
        "dry_run": dry_run,
        "start_time": datetime.utcnow().isoformat(),
        "incidents_found": 0,
        "incidents_migrated": 0,
        "errors": [],
        "spot_checks": []
    }

    # Step 1: Load JSON file
    if not json_path.exists():
        report["status"] = "error"
        report["errors"].append(f"JSON file not found: {json_path}")
        return report

    try:
        json_data = json.loads(json_path.read_text())
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        report["status"] = "error"
        report["errors"].append(f"Failed to parse JSON: {e}")
        return report

    # Step 2: Extract incidents
    if not isinstance(json_data, dict):
        report["status"] = "error"
        report["errors"].append("JSON must be an object at root")
        return report

    incidents_data = json_data.get("incidents", {})
    if not isinstance(incidents_data, dict):
        report["status"] = "error"
        report["errors"].append("'incidents' field must be an object")
        return report

    incident_ids = list(incidents_data.keys())
    report["incidents_found"] = len(incident_ids)

    if report["incidents_found"] == 0:
        report["status"] = "warning"
        report["errors"].append("No incidents found in JSON file")
        return report

    print(f"Found {report['incidents_found']} incidents in JSON file")

    # Step 3: Migrate to SQLite (if not dry-run)
    if not dry_run:
        db = SQLiteDatabase(db_path)

        for incident_id in incident_ids:
            incident_data = incidents_data[incident_id]

            # Extract tenant_id (default to system tenant)
            tenant_id = incident_data.get("tenant_id", "tenant-system")

            try:
                await db.create_incident(
                    nexus_incident_id=incident_id,
                    tenant_id=tenant_id,
                    data=incident_data
                )
                report["incidents_migrated"] += 1
            except Exception as e:
                report["errors"].append(f"Failed to migrate {incident_id}: {e}")

    # Step 4: Spot-check random incidents
    if report["incidents_migrated"] > 0 and not dry_run:
        sample_size = min(10, report["incidents_migrated"])
        sample_ids = random.sample(incident_ids, sample_size)

        db = SQLiteDatabase(db_path)
        for sample_id in sample_ids:
            original = incidents_data[sample_id]
            tenant_id = original.get("tenant_id", "tenant-system")

            try:
                retrieved = await db.get_incident_for_tenant(sample_id, tenant_id)
                if retrieved is None:
                    report["errors"].append(f"Spot-check failed: {sample_id} not found")
                elif retrieved['data'] != original:
                    report["errors"].append(f"Spot-check failed: {sample_id} data mismatch")
                else:
                    report["spot_checks"].append({"incident_id": sample_id, "status": "ok"})
            except Exception as e:
                report["errors"].append(f"Spot-check error for {sample_id}: {e}")

    # Step 5: Summary
    report["end_time"] = datetime.utcnow().isoformat()
    report["success"] = len(report["errors"]) == 0

    return report


def print_report(report: dict) -> None:
    """Print migration report."""
    print("\n" + "=" * 70)
    print("MIGRATION REPORT")
    print("=" * 70)
    print(f"Status: {report['status'].upper()}")
    print(f"JSON File: {report['json_path']}")
    print(f"Database: {report['db_path']}")
    print(f"Dry Run: {report['dry_run']}")
    print()
    print(f"Incidents found:   {report['incidents_found']}")
    print(f"Incidents migrated: {report['incidents_migrated']}")
    print()

    if report["spot_checks"]:
        print(f"Spot-checks passed: {len(report['spot_checks'])}/{len(report['spot_checks'])}")
    else:
        print("Spot-checks: (none performed)")

    if report["errors"]:
        print()
        print("ERRORS:")
        for error in report["errors"]:
            print(f"  - {error}")
    else:
        print()
        print("✓ No errors")

    print()
    print(f"Start: {report['start_time']}")
    print(f"End:   {report['end_time']}")
    print("=" * 70)


async def main():
    """Parse arguments and run migration."""
    parser = argparse.ArgumentParser(description="Migrate incidents from JSON to SQLite")
    parser.add_argument(
        "--json-path",
        type=Path,
        default=Path("artifacts/incidents.json"),
        help="Path to JSON file"
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=Path("artifacts/nexus.db"),
        help="Path to SQLite database"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate without committing"
    )

    args = parser.parse_args()

    report = await migrate_incidents(
        json_path=args.json_path,
        db_path=args.db_path,
        dry_run=args.dry_run
    )

    print_report(report)

    # Exit with error code if failed
    sys.exit(0 if report["success"] else 1)


if __name__ == "__main__":
    asyncio.run(main())
