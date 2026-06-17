# Runbook: Database Growth Rate Elevated

**Alert:** `DatabaseGrowthFast`  
**Severity:** LOW  
**On-Call Owner:** Database Team  
**Estimated Resolution Time:** 30-90 minutes (depends on action)

---

## Symptoms

- Database size growing >1GB/day (average over 24 hours)
- Prometheus metric: `rate(nexus_database_size_bytes[24h]) > 1000000000`
- Sustained for >2 hours
- Disk space might be running low if growth continues
- Possible causes:
  - Audit logs accumulating
  - Incident data not being cleaned up
  - Backups not being deleted
  - Abnormal write spike

---

## Immediate Actions (< 5 min)

1. **Verify the alert is real**
   ```bash
   # Check actual database file size
   du -h /path/to/nexus.db
   ls -lah /path/to/nexus.db
   
   # Check growth over last 24 hours (compare with yesterday's size)
   # If backup exists: ls -lah /path/to/nexus.db.backup.20260617
   ```

2. **Check available disk space**
   ```bash
   df -h /  # Root filesystem
   df -h /path/to/  # Where database lives
   
   # If >90% used: growth is a problem NOW
   # If >80% used: monitor closely
   # If <70% used: can defer action
   ```

3. **Determine where growth is coming from**
   ```bash
   # Size by table
   sqlite3 /path/to/nexus.db "SELECT name, page_count * (SELECT page_size FROM pragma_page_size()) as size_bytes 
     FROM sqlite_master WHERE type='table' ORDER BY size_bytes DESC;"
   
   # Count rows by table
   sqlite3 /path/to/nexus.db "SELECT 'incidents', COUNT(*) FROM incidents 
     UNION ALL 
     SELECT 'audit_logs', COUNT(*) FROM audit_logs;"
   ```

4. **Check incident growth rate**
   ```bash
   # Incidents created per day
   sqlite3 /path/to/nexus.db "SELECT DATE(created_at), COUNT(*) FROM incidents 
     WHERE created_at > datetime('now','-7 days') 
     GROUP BY DATE(created_at) ORDER BY created_at DESC;"
   
   # If there's a spike: what day did it start?
   ```

---

## If Immediate Actions Don't Work (5-30 min)

1. **Check if growth is from incidents or audit logs**
   ```bash
   # Incidents table
   sqlite3 /path/to/nexus.db "SELECT COUNT(*), AVG(LENGTH(incident_data)) FROM incidents;"
   
   # Audit logs table
   sqlite3 /path/to/nexus.db "SELECT COUNT(*), AVG(LENGTH(data)) FROM audit_logs;"
   
   # Which is bigger? incidents or audit_logs?
   ```

2. **Implement retention policy if missing**
   ```bash
   # Check if there's a retention cleanup running
   grep -i "cleanup\|delete.*old\|retention" /var/log/nexus/app.log
   
   # Check cron jobs
   crontab -l | grep -i nexus
   
   # If no cleanup: archive/delete old records
   sqlite3 /path/to/nexus.db "DELETE FROM audit_logs 
     WHERE created_at < datetime('now','-90 days');"
   
   # Count deleted
   sqlite3 /path/to/nexus.db "SELECT COUNT(*) FROM audit_logs;"
   
   # Compact database
   sqlite3 /path/to/nexus.db "VACUUM;"
   ```

3. **Check for data quality issues**
   ```bash
   # Are there duplicate incidents?
   sqlite3 /path/to/nexus.db "SELECT incident_id, COUNT(*) FROM incidents 
     GROUP BY incident_id HAVING COUNT(*) > 1;"
   
   # Are there very large incident_data entries?
   sqlite3 /path/to/nexus.db "SELECT incident_id, LENGTH(incident_data) FROM incidents 
     WHERE LENGTH(incident_data) > 1000000 
     ORDER BY LENGTH(incident_data) DESC LIMIT 10;"
   
   # Investigate those large entries
   ```

4. **Check if there's a test data import**
   ```bash
   # Recently added incidents
   sqlite3 /path/to/nexus.db "SELECT DATE(created_at), COUNT(*) FROM incidents 
     WHERE created_at > datetime('now','-1 day') 
     GROUP BY DATE(created_at);"
   
   # Compare to normal daily rate
   # If anomalous: what's the incident source? User error or test data?
   ```

---

## If Database Still Growing Fast (30+ min)

1. **Archive old incidents to long-term storage**
   ```bash
   # Export incidents older than 30 days to JSON
   sqlite3 /path/to/nexus.db ".mode json" ".output incidents_archived.json" \
     "SELECT * FROM incidents WHERE created_at < datetime('now','-30 days');"
   
   # Upload to S3
   aws s3 cp incidents_archived.json s3://nexus-archives/incidents-2026-06.json.gz
   
   # Delete from database
   sqlite3 /path/to/nexus.db "DELETE FROM incidents 
     WHERE created_at < datetime('now','-30 days');"
   
   # Compact
   sqlite3 /path/to/nexus.db "VACUUM;"
   ```

2. **Implement incremental cleanup**
   ```bash
   # Add to cron: delete 1 day of audit logs daily
   0 2 * * * sqlite3 /path/to/nexus.db "DELETE FROM audit_logs WHERE created_at < datetime('now','-90 days') LIMIT 10000; VACUUM;" >> /var/log/nexus/cleanup.log 2>&1
   ```

3. **Upgrade storage if growth is expected**
   - If >1GB/day is normal for your incident volume, plan for:
     - Larger disk: expand LVM or EBS
     - PostgreSQL migration: better for large datasets
     - Document SLA: "Database grows ~XXX GB/month at current incident rate"

4. **Escalation**
   - Slack: `@database-team`
   - Create ticket: "Plan database growth strategy for production"
   - If disk will fill in <7 days: escalate to infrastructure

---

## Post-Incident

- [ ] Implement retention policy (delete audit logs >90 days old)
- [ ] Set up automated cleanup job (nightly VACUUM, monthly archive)
- [ ] Set up dashboard: database size trend, growth rate, disk usage %
- [ ] Document incident data lifetime policy
- [ ] Estimate monthly growth and plan disk/scaling
- [ ] If growth >1GB/day is expected: plan PostgreSQL migration

---

## Prevention

- Implement retention: keep incidents 6 months, audit logs 90 days
- Run daily cleanup: `DELETE FROM audit_logs WHERE created_at < now() - INTERVAL 90 days`
- Run weekly VACUUM to compact fragmentation
- Monitor disk usage: alert if >80%
- Archive old incidents for long-term storage
- Plan capacity: if 1GB/day, 1 year = 365GB

---

## Database Lifecycle Policy

| Data | Retention | Cleanup | Archive |
|------|-----------|---------|---------|
| Incidents | 6 months | Delete if >6mo | Yes, to S3 |
| Audit Logs | 90 days | Delete daily | Optional |
| Backups | 7 days | Delete >7d old | Keep last backup |

---

## Contact & Escalation

- **Database Team:** Scaling and retention strategy
- **Infrastructure Team:** Disk/storage expansion
- **Product/Legal:** Data retention requirements
