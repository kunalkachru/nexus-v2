# NEXUS Ops Team Training - Hands-On Lab

**Document Version:** 1.0  
**Last Updated:** 2026-06-17  
**Duration:** 2 hours (4 scenarios × 30 minutes each)  
**Prerequisites:** Completion of Modules 1-4 in training guide

---

## Lab Overview

This hands-on lab provides practical experience with NEXUS operations, troubleshooting, and disaster recovery. Each scenario simulates real-world situations the ops team may encounter.

**Learning Outcomes:**
- Execute all operational procedures hands-on
- Gain confidence troubleshooting NEXUS issues
- Practice disaster recovery under controlled conditions
- Understand incident processing workflow

**Lab Environment:** Staging or local development environment (NOT production)

---

## Pre-Lab Setup (10 minutes)

### Prerequisites

1. **Access Required:**
   - Shell access to NEXUS server/container
   - Grafana access (if monitoring dashboards available)
   - Text editor for editing configuration

2. **Files & Tools:**
   - `scripts/backup_nexus.sh` (backup script)
   - `scripts/restore_nexus.sh` (restore script)
   - `systemctl` or Docker CLI

3. **Environment Verification:**
   ```bash
   # Verify NEXUS runs
   systemctl status nexus
   
   # Verify health check works
   curl http://localhost:7860/health
   
   # Verify database exists
   ls -lh artifacts/incidents.json
   
   # Record incident count
   echo "Pre-lab incident count: $(python3 -c "import json; f=open('artifacts/incidents.json'); d=json.load(f); print(len(d.get('incidents', [])))")"
   ```

4. **Create Lab Log File:**
   ```bash
   LAB_LOG="lab-training-$(date +%Y%m%d_%H%M%S).log"
   echo "NEXUS Ops Training Lab - $(date)" > "$LAB_LOG"
   echo "Participant: $(whoami)" >> "$LAB_LOG"
   ```

---

## Scenario A: Service Startup & Health Check (30 minutes)

**Objective:** Verify NEXUS can be started cleanly and health checks pass  
**Real-World:** Daily operations, service recovery from outage

### A1. Verify Initial State (5 min)

```bash
# 1. Check current status
systemctl status nexus

# 2. Record output
echo "=== Pre-stop status ===" >> "$LAB_LOG"
systemctl status nexus >> "$LAB_LOG"

# 3. Verify health endpoint
curl -v http://localhost:7860/health

# 4. Check database accessibility
ls -lh artifacts/incidents.json
```

**Expected Result:**
- ✓ Service is active (running)
- ✓ Health endpoint returns 200 OK with `{"status": "ok"}`
- ✓ Database file exists and is readable

### A2. Graceful Stop (5 min)

```bash
# 1. Stop service gracefully
echo "Stopping NEXUS service..."
systemctl stop nexus

# 2. Wait for graceful shutdown
sleep 5

# 3. Verify stopped
systemctl status nexus

# 4. Verify port is released
curl http://localhost:7860/health 2>&1 | grep -i "refused\|connection"
# Should fail with: curl: (7) Failed to connect

echo "✓ Service stopped cleanly" >> "$LAB_LOG"
```

**Expected Result:**
- ✓ Service status shows "inactive (dead)"
- ✓ Health check fails with connection refused
- ✓ No lingering processes: `ps aux | grep nexus`

### A3. Start Service (10 min)

```bash
# 1. Start the service
echo "Starting NEXUS service..."
systemctl start nexus

# 2. Wait for startup
echo "Waiting for startup..."
sleep 10

# 3. Check status
systemctl status nexus

# 4. Test health endpoint repeatedly (verify not yet ready)
for i in {1..5}; do
  echo "Health check attempt $i..."
  curl -s http://localhost:7860/health && break
  sleep 2
done

# 5. Verify full startup
curl http://localhost:7860/health | jq .

echo "✓ Service started successfully" >> "$LAB_LOG"
```

**Expected Result:**
- ✓ Service status shows "active (running)"
- ✓ Health check passes with `{"status": "ok"}`
- ✓ Service took 5-15 seconds to start
- ✓ No errors in startup logs

### A4. Verify Resources (5 min)

```bash
# Check resource usage
echo "=== Resource Check ===" >> "$LAB_LOG"

# CPU and memory
PID=$(pgrep -f "python.*nexus" | head -1)
if [ -n "$PID" ]; then
  top -b -n 1 -p $PID >> "$LAB_LOG"
else
  echo "WARNING: Could not find NEXUS process" >> "$LAB_LOG"
fi

# Database size
du -h artifacts/incidents.json >> "$LAB_LOG"

# Disk space available
df -h . >> "$LAB_LOG"

echo "✓ Resources verified" >> "$LAB_LOG"
```

**Expected Result:**
- ✓ CPU < 50% (typically < 20%)
- ✓ Memory < 1 GB (typically 200-500 MB)
- ✓ Database size 1-5 MB
- ✓ Disk space > 1 GB available

### A5. Scenario Completion

```bash
echo "=== SCENARIO A COMPLETE ===" >> "$LAB_LOG"
echo "Participant signature: _______________" >> "$LAB_LOG"
echo "Date/Time: $(date)" >> "$LAB_LOG"
```

**Scenario A Checklist:**
- [ ] Initial state verified
- [ ] Service stopped cleanly
- [ ] Service started successfully
- [ ] Health check passed
- [ ] Resources verified
- [ ] No errors in logs

---

## Scenario B: Submit Incident & GUARDIAN Review (30 minutes)

**Objective:** Process incident from submission through GUARDIAN approval  
**Real-World:** Support team submitting incident for engineering analysis

### B1. Prepare Test Incident (5 min)

Create a sample incident log file with realistic data:

```bash
# Create test incident
cat > test_incident.json << 'EOF'
{
  "incident_family": "INC001",
  "raw_logs": "2026-06-17T14:30:00Z [ERROR] Checkout timeout after 30s retrying payment_service request. Customer: acme_corp. Attempts: 3. Error: deadline_exceeded. Stack: payment.go:234 -> auth.go:102 -> network.go:567.",
  "metadata": {
    "source": "customer_support_ticket_12345",
    "severity": "high",
    "affected_customers": ["acme_corp"],
    "time_to_failure": "2 minutes"
  }
}
EOF

# Verify file created
ls -lh test_incident.json
cat test_incident.json | jq .

echo "✓ Test incident prepared" >> "$LAB_LOG"
```

### B2. Submit Incident (10 min)

```bash
# Get authentication token (depends on your setup)
# For development: use test token or no auth
# For production: obtain from auth service

AUTH_TOKEN="test-token-12345"  # Replace with actual token

# Submit via API
echo "Submitting incident..."
RESPONSE=$(curl -X POST http://localhost:7860/api/incidents \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d @test_incident.json)

echo "Response: $RESPONSE" | tee -a "$LAB_LOG"

# Extract incident ID
INCIDENT_ID=$(echo "$RESPONSE" | jq -r '.id // .nexus_incident_id' 2>/dev/null)

if [ -z "$INCIDENT_ID" ] || [ "$INCIDENT_ID" == "null" ]; then
  echo "❌ ERROR: Could not extract incident ID from response"
  echo "$RESPONSE"
  exit 1
fi

echo "✓ Incident submitted: $INCIDENT_ID" >> "$LAB_LOG"
```

### B3. Verify Incident Processing (10 min)

```bash
# Query newly created incident
echo "Querying incident: $INCIDENT_ID"

curl -s -H "Authorization: Bearer $AUTH_TOKEN" \
  http://localhost:7860/api/incidents/$INCIDENT_ID | jq .

# Check incident status
STATUS=$(curl -s -H "Authorization: Bearer $AUTH_TOKEN" \
  http://localhost:7860/api/incidents/$INCIDENT_ID | jq -r '.status')

echo "Incident status: $STATUS"

# Verify status progression
if [ "$STATUS" == "pending_review" ] || [ "$STATUS" == "open" ]; then
  echo "✓ Incident in expected status: $STATUS"
else
  echo "⚠ Incident has unexpected status: $STATUS"
fi

echo "✓ Incident processing verified" >> "$LAB_LOG"
```

### B4. GUARDIAN Review (5 min)

If GUARDIAN functionality available in lab environment:

```bash
# Check for incidents pending review
curl -s -H "Authorization: Bearer $AUTH_TOKEN" \
  http://localhost:7860/api/incidents?status=pending_review | jq '.data | length'

# For each pending incident, simulate approval
# (This would typically be done via web UI)
echo "⚠ GUARDIAN review typically done via web UI"
echo "✓ Incident visible for GUARDIAN review" >> "$LAB_LOG"
```

**Expected Result:**
- ✓ Incident created successfully with unique ID
- ✓ Incident status is one of: pending_review, open, processing
- ✓ Incident data is retrievable via API
- ✓ All fields preserved (incident_family, metadata, etc.)

### B5. Scenario Completion

```bash
echo "=== SCENARIO B COMPLETE ===" >> "$LAB_LOG"
echo "Test incident ID: $INCIDENT_ID" >> "$LAB_LOG"
echo "Participant signature: _______________" >> "$LAB_LOG"
```

**Scenario B Checklist:**
- [ ] Test incident created
- [ ] Incident submitted successfully
- [ ] Incident ID obtained
- [ ] Incident retrievable via API
- [ ] Status verified correct
- [ ] No errors in submission process

---

## Scenario C: Monitoring & Troubleshooting (30 minutes)

**Objective:** Use monitoring tools to identify and resolve issues  
**Real-World:** Proactive monitoring and incident response

### C1. Access Grafana Dashboards (5 min)

```bash
# Navigate to Grafana
# http://localhost:3000
# Login: admin / admin

# Look for these dashboards:
# - NEXUS Health
# - NEXUS Performance
# - NEXUS Errors

echo "✓ Monitoring dashboards accessed" >> "$LAB_LOG"
```

### C2. Baseline Metrics (5 min)

```bash
# Query Prometheus metrics endpoint
curl -s http://localhost:7860/metrics | head -50

# Record baseline
echo "=== Baseline Metrics ===" >> "$LAB_LOG"
curl -s http://localhost:7860/metrics | grep -E "^nexus_" >> "$LAB_LOG"

# Specific metrics to note
curl -s http://localhost:7860/metrics | grep -E "incidents_created|guardian_decisions|auth_failures"
```

**Expected Baseline:**
- `incidents_created_total`: Growing (new incidents added)
- `guardian_decisions_total`: Stable
- `auth_failures_total`: < 1/hour
- `artifact_persistence_latency_ms`: < 100

### C3. Generate Load (10 min)

```bash
# Method 1: Create sample incidents in loop
echo "Generating load..."

for i in {1..10}; do
  curl -X POST http://localhost:7860/api/incidents \
    -H "Authorization: Bearer test-token" \
    -H "Content-Type: application/json" \
    -d "{\"incident_family\": \"INC001\", \"raw_logs\": \"Test log $i\"}" \
    2>/dev/null &
done

wait

echo "✓ Load generated" >> "$LAB_LOG"

# Method 2: If load test script available
# python tests/load_test.py --duration 60 --concurrency 10
```

### C4. Monitor During Load (5 min)

```bash
# Observe metrics during load
echo "Monitoring metrics during load..."

for i in {1..5}; do
  echo "Sample $i:"
  curl -s http://localhost:7860/metrics | grep nexus_requests_total
  sleep 2
done

# Check health under load
curl -s http://localhost:7860/health | jq .

echo "✓ Load test monitoring complete" >> "$LAB_LOG"
```

**Expected Result:**
- ✓ Metrics show increased request rate
- ✓ Latency increases but stays under 500ms
- ✓ Error rate remains < 1%
- ✓ Service stays healthy under load

### C5. Interpret Results (5 min)

```bash
# Record observations
cat >> "$LAB_LOG" << EOF

=== Load Test Observations ===
- Service remained stable: YES / NO
- Error rate increased: YES / NO
- Performance degradation: NONE / SLIGHT / SEVERE
- Recommendation: CONTINUE / INVESTIGATE / ESCALATE

Participant: ___________________
EOF
```

**Scenario C Checklist:**
- [ ] Grafana dashboards accessed
- [ ] Baseline metrics recorded
- [ ] Load successfully generated
- [ ] Metrics monitored during load
- [ ] Service remained stable
- [ ] Results documented

---

## Scenario D: Disaster Recovery Drill (30 minutes)

**Objective:** Execute full backup/restore cycle under simulated disaster  
**Real-World:** Database corruption, data loss recovery

### D1. Pre-Disaster Baseline (5 min)

```bash
# Record pre-disaster state
echo "=== DISASTER RECOVERY DRILL ===" >> "$LAB_LOG"
echo "Start time: $(date)" >> "$LAB_LOG"

# Backup current state
cp artifacts/incidents.json artifacts/incidents.json.pre-disaster

# Count incidents
INCIDENT_COUNT=$(python3 -c "import json; f=open('artifacts/incidents.json'); d=json.load(f); print(len(d.get('incidents', [])))")
echo "Pre-disaster incident count: $INCIDENT_COUNT" >> "$LAB_LOG"

# Verify database integrity
if python3 -m json.tool artifacts/incidents.json > /dev/null 2>&1; then
  echo "Pre-disaster database: VALID JSON" >> "$LAB_LOG"
else
  echo "Pre-disaster database: INVALID JSON" >> "$LAB_LOG"
  exit 1
fi

echo "✓ Baseline recorded" >> "$LAB_LOG"
```

### D2. Create Backup (5 min)

```bash
# Create backup manually (or verify recent backup exists)
echo "Creating backup..."

if [ -x "scripts/backup_nexus.sh" ]; then
  # Use backup script
  ./scripts/backup_nexus.sh
  BACKUP_FILE=$(ls -t .backup/nexus/*.gz 2>/dev/null | head -1)
else
  # Manual backup
  gzip -c artifacts/incidents.json > artifacts/incidents.json.backup.gz
  BACKUP_FILE="artifacts/incidents.json.backup.gz"
fi

echo "Backup file: $BACKUP_FILE"
ls -lh "$BACKUP_FILE"

# Verify backup
if gzip -t "$BACKUP_FILE" 2>/dev/null; then
  echo "✓ Backup integrity verified" >> "$LAB_LOG"
else
  echo "❌ Backup corrupted" >> "$LAB_LOG"
  exit 1
fi
```

### D3. Simulate Disaster (5 min)

Choose one disaster scenario:

```bash
echo "Simulating database corruption..."

# Option A: Truncate file (simulates incomplete write)
# > artifacts/incidents.json

# Option B: Overwrite with garbage
# echo "CORRUPTED DATA" > artifacts/incidents.json

# Option C: Delete file
rm artifacts/incidents.json

echo "✓ Disaster simulated" >> "$LAB_LOG"

# Verify disaster
if [ ! -f "artifacts/incidents.json" ]; then
  echo "✓ Database is gone (disaster confirmed)"
elif ! python3 -m json.tool artifacts/incidents.json > /dev/null 2>&1; then
  echo "✓ Database is corrupted (disaster confirmed)"
else
  echo "❌ Disaster simulation failed (database still valid)"
  exit 1
fi
```

### D4. Execute Restore (5 min)

```bash
echo "Executing restore procedure..."
RESTORE_START=$(date +%s)

# Use restore script
if [ -x "scripts/restore_nexus.sh" ]; then
  ./scripts/restore_nexus.sh "$BACKUP_FILE" 2>&1 | tee -a "$LAB_LOG"
else
  # Manual restore
  gunzip -c "$BACKUP_FILE" > artifacts/incidents.json
fi

RESTORE_END=$(date +%s)
RESTORE_TIME=$((RESTORE_END - RESTORE_START))

echo "Restore completed in ${RESTORE_TIME}s" >> "$LAB_LOG"

# Verify restore
if [ ! -f "artifacts/incidents.json" ]; then
  echo "❌ ERROR: Database file not restored"
  exit 1
fi

if ! python3 -m json.tool artifacts/incidents.json > /dev/null 2>&1; then
  echo "❌ ERROR: Restored database has invalid JSON"
  exit 1
fi

echo "✓ Restore completed successfully" >> "$LAB_LOG"
```

### D5. Verify Recovery (5 min)

```bash
# Verify data recovery
RESTORED_COUNT=$(python3 -c "import json; f=open('artifacts/incidents.json'); d=json.load(f); print(len(d.get('incidents', [])))")

echo "Restored incident count: $RESTORED_COUNT"
echo "Expected incident count: $INCIDENT_COUNT"

if [ "$RESTORED_COUNT" == "$INCIDENT_COUNT" ]; then
  echo "✓ All incidents recovered (data loss: 0)" >> "$LAB_LOG"
elif [ "$RESTORED_COUNT" -gt 0 ]; then
  LOSS=$((INCIDENT_COUNT - RESTORED_COUNT))
  echo "⚠ Partial recovery (data loss: $LOSS incidents)" >> "$LAB_LOG"
else
  echo "❌ ERROR: No incidents recovered" >> "$LAB_LOG"
  exit 1
fi

# Restart service (if not already running)
if ! curl -s http://localhost:7860/health > /dev/null 2>&1; then
  echo "Restarting service..."
  systemctl start nexus
  sleep 10
fi

# Health check
if curl -s http://localhost:7860/health | jq . > /dev/null 2>&1; then
  echo "✓ Service healthy after recovery" >> "$LAB_LOG"
else
  echo "❌ Service not responding after recovery" >> "$LAB_LOG"
  exit 1
fi

echo "=== DISASTER RECOVERY COMPLETE ===" >> "$LAB_LOG"
echo "RTO: ${RESTORE_TIME}s (Target: < 3600s)" >> "$LAB_LOG"
echo "Data recovered: $RESTORED_COUNT/$INCIDENT_COUNT incidents" >> "$LAB_LOG"
echo "End time: $(date)" >> "$LAB_LOG"
```

### D6. Cleanup

```bash
# Restore original data (if using pre-disaster backup)
if [ -f "artifacts/incidents.json.pre-disaster" ]; then
  echo "Restoring original data..."
  rm artifacts/incidents.json
  cp artifacts/incidents.json.pre-disaster artifacts/incidents.json
  
  systemctl restart nexus
  sleep 10
fi

# Remove temporary files
rm -f test_incident.json
rm -f artifacts/incidents.json.backup.gz

echo "✓ Lab cleanup complete" >> "$LAB_LOG"
```

**Scenario D Checklist:**
- [ ] Pre-disaster baseline recorded
- [ ] Backup created successfully
- [ ] Disaster simulated (data loss confirmed)
- [ ] Restore executed successfully
- [ ] Data recovery verified (100% or known loss)
- [ ] RTO < 1 hour achieved
- [ ] Service healthy after recovery
- [ ] Original data restored
- [ ] Cleanup complete

---

## Lab Completion

### Participant Final Checklist

After completing all 4 scenarios, verify:

```
SCENARIO A: Service Startup & Health Check
[ ] Service stopped cleanly
[ ] Service restarted successfully
[ ] Health check passed
[ ] Resources verified

SCENARIO B: Incident Submission & GUARDIAN Review
[ ] Test incident created
[ ] Incident submitted successfully
[ ] Incident retrievable via API
[ ] Status verified correct

SCENARIO C: Monitoring & Troubleshooting
[ ] Accessed Grafana dashboards
[ ] Recorded baseline metrics
[ ] Generated load successfully
[ ] Monitored metrics under load
[ ] Service remained stable

SCENARIO D: Disaster Recovery
[ ] Backup created successfully
[ ] Disaster simulated
[ ] Restore executed successfully
[ ] Data recovered
[ ] RTO < 1 hour achieved
[ ] Service healthy post-recovery

OVERALL
[ ] Completed all 4 scenarios
[ ] No critical errors encountered
[ ] Confident operating NEXUS
[ ] Ready for production support
```

### Lab Report

Save lab log and complete report:

```bash
# View complete lab log
cat "$LAB_LOG"

# Copy to permanent location
cp "$LAB_LOG" training-logs/

# Submit to trainer
echo "Lab completed by: $(whoami)"
echo "Lab log: $LAB_LOG"
echo "Date: $(date)"
```

### Trainer Sign-Off

**Participant Name:** _____________________  
**Participant Email:** _____________________  
**Completion Date:** _____________________  
**Scenarios Completed:** A [ ] B [ ] C [ ] D [ ]  
**Overall Outcome:** PASSED [ ] / CONDITIONAL [ ] / FAILED [ ]  
**Notes:** _________________________________  

**Trainer Name:** _____________________  
**Trainer Signature:** _____________________  
**Date:** _____________________  

---

## Support During Lab

If issues arise:

1. **Check logs immediately:**
   ```bash
   tail -50 /var/log/nexus.log
   journalctl -u nexus -30
   ```

2. **Verify service state:**
   ```bash
   systemctl status nexus
   curl http://localhost:7860/health
   ```

3. **Escalate if needed:**
   - Contact trainer or on-call engineer
   - Provide error messages and logs
   - Document issue in lab log

---

**Lab Document Owner:** DevOps Lead  
**Last Updated:** 2026-06-17  
**Next Review:** 2026-07-17
