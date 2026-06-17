# Runbook: Artifact Persistence Latency Degradation

**Alert:** `ArtifactPersistenceSlow`  
**Severity:** HIGH  
**On-Call Owner:** Backend Team + Database Team  
**Estimated Resolution Time:** 20-45 minutes

---

## Symptoms

- p99 artifact persistence latency >1000ms (1 second)
- Prometheus metric: `histogram_quantile(0.99, nexus_artifact_persistence_latency_ms_bucket) > 1000`
- Users report slow incident submissions or delayed artifact storage
- Dashboard shows latency spike in "NEXUS Performance Metrics" dashboard

---

## Immediate Actions (< 5 min)

1. **Confirm the spike is real (not measurement error)**
   ```bash
   # Check raw latency metrics
   curl -s http://localhost:9090/api/v1/query?query='nexus_artifact_persistence_latency_ms_bucket' | jq '.'
   
   # Check if it's a specific percentile or all requests
   # If p99 > 1000ms but p50 < 100ms: some slow queries, not all
   # If p50 > 1000ms: systemic database issue
   ```

2. **Check database connection and resource usage**
   ```bash
   # SQLite file exists and is accessible
   ls -lah /path/to/nexus.db
   
   # Check disk I/O
   iostat -x 1 5  # Show I/O stats for 5 seconds
   
   # Check if database is locked
   lsof /path/to/nexus.db  # Should show only nexus process
   
   # Check if database file is corrupted
   sqlite3 /path/to/nexus.db "PRAGMA integrity_check;" # Should return "ok"
   ```

3. **Check application resource usage**
   ```bash
   # CPU usage
   top -b -n 1 | grep nexus-app
   
   # Memory usage
   docker stats nexus-app --no-stream
   
   # Open file descriptors
   lsof -p $(pgrep -f nexus-app) | wc -l
   ```
   - High CPU might indicate query scanning large dataset
   - High memory might indicate cache building
   - High FDs might indicate connection pool exhaustion

4. **Check if there's high concurrent load**
   ```bash
   # Count active requests
   grep "POST /incidents" /var/log/nexus/access.log | tail -100 | wc -l
   
   # Check query queue
   sqlite3 /path/to/nexus.db "SELECT COUNT(*) FROM pragma_locks"
   ```

---

## If Immediate Actions Don't Work (5-20 min)

1. **Profile the slow query**
   ```bash
   # Enable query logging
   sqlite3 /path/to/nexus.db ".mode line"
   
   # Find slow queries in logs
   grep "SLOW QUERY\|duration.*ms" /var/log/nexus/app.log | tail -20
   
   # Or enable SQLite EXPLAIN
   sqlite3 /path/to/nexus.db "EXPLAIN QUERY PLAN SELECT * FROM incidents WHERE tenant_id=? ORDER BY created_at DESC LIMIT 10;"
   ```

2. **Check if recent deployment changed query patterns**
   ```bash
   git log --oneline -10
   git diff HEAD~1 HEAD -- server/db.py  # Check for new queries or changed query logic
   ```

3. **Check database size and indexes**
   ```bash
   # Database size
   du -h /path/to/nexus.db
   
   # Check table sizes
   sqlite3 /path/to/nexus.db "SELECT name, page_count * page_size / (1024*1024) as size_mb FROM pragma_page_count(), (SELECT page_size FROM pragma_page_size()) CROSS JOIN sqlite_master WHERE type='table';"
   
   # Verify indexes exist
   sqlite3 /path/to/nexus.db ".indices incidents"
   ```
   - If `incidents` table is very large (>1GB) and no tenant_id index: queries will be slow
   - If database file is fragmented: run VACUUM

4. **Run index analysis and maintenance**
   ```bash
   # Analyze query performance
   sqlite3 /path/to/nexus.db "ANALYZE;"
   
   # Rebuild indexes if needed
   sqlite3 /path/to/nexus.db "REINDEX;"
   
   # Defragment database
   sqlite3 /path/to/nexus.db "VACUUM;"
   ```
   - These commands lock the database, do during low-traffic window if possible

---

## If Still Slow (20+ min)

1. **Check for database locks or deadlocks**
   ```bash
   # Check for processes holding locks
   lsof +D /path/to/  # Show all processes accessing the DB directory
   
   # Check SQLite WAL (Write-Ahead Log) status
   ls -lah /path/to/nexus.db-*
   
   # If WAL is large, it means many writes queued
   du -h /path/to/nexus.db-wal
   ```

2. **Temporary mitigation: increase timeout and cache**
   ```bash
   # In code or config, increase:
   # - Database connection timeout
   # - Query timeout
   # - Connection pool size
   
   docker exec nexus-app /bin/sh -c "export DB_TIMEOUT=30 DB_CACHE_SIZE=10000 && restart"
   ```

3. **If issue is write-heavy (many concurrent incidents)**
   - Check if there's a batch import or test spike
   - Evaluate: PostgreSQL migration (better concurrency than SQLite)
   - Temporary: implement request queuing/backpressure

4. **Escalation**
   - Slack: `@database-team`
   - Create ticket: "Evaluate SQLite scalability for [incident count] incidents"
   - Consider: migrate to PostgreSQL if load exceeds SQLite capacity

---

## Post-Incident

- [ ] Identify whether issue was resource, lock, or query-specific
- [ ] Add indexes if missing for common query patterns
- [ ] Run VACUUM and ANALYZE on schedule (nightly)
- [ ] Set up alerting for: database file size, query latency percentiles, lock wait time
- [ ] Evaluate: is SQLite sufficient or should we migrate to PostgreSQL?
- [ ] Document any workarounds applied
- [ ] Test with load testing to find breaking point

---

## Prevention

- Index all WHERE clause columns (tenant_id, created_at, etc.)
- Run ANALYZE weekly to keep query planner informed
- Monitor database file size growth
- Set query timeout to prevent runaway queries
- Plan for PostgreSQL migration as scale increases
- Use connection pooling to prevent exhaustion

---

## Performance Targets (SLA)

- p50 artifact persistence: <100ms
- p95 artifact persistence: <500ms
- p99 artifact persistence: <1000ms (alert threshold)

---

## Contact & Escalation

- **Database Team:** See wiki
- **Backend Team Lead:** Database performance questions
- **Infrastructure Team:** If migrating to PostgreSQL
