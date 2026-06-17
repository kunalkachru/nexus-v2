# Runbook: Suspicious Auth Failures

**Alert:** `SuspiciousAuthFailures`  
**Severity:** HIGH  
**On-Call Owner:** Security Team + Backend Team  
**Estimated Resolution Time:** 10-20 minutes

---

## Symptoms

- Auth failure rate >0.2 failures/sec (12/min) sustained for >5 minutes
- Prometheus metric: `rate(nexus_auth_failures_total[5m]) > 0.2`
- Possible indicators:
  - Webhook signature verification failing repeatedly
  - HMAC validation errors in logs
  - Invalid or expired credentials from callers
  - Brute-force attack on API keys

---

## Immediate Actions (< 5 min)

1. **Check the type of failures**
   ```bash
   # Review audit logs for failure types
   tail -100 /var/log/nexus/audit.log | grep "auth_failure\|invalid_signature"
   
   # Or query database
   sqlite3 /path/to/nexus.db "SELECT failure_type, COUNT(*) FROM audit_logs 
     WHERE event_type='auth_failure' AND created_at > datetime('now','-5 minutes') 
     GROUP BY failure_type ORDER BY COUNT(*) DESC;"
   ```
   - Document which failure_type is dominant (invalid_signature, invalid_key, expired_token, etc.)

2. **Check if it's an attack or misconfiguration**
   - **Attack indicators:** Many different API keys or sources, random-looking data
   - **Misconfiguration indicators:** Same source/key repeatedly, specific pattern

3. **If attack suspected:**
   ```bash
   # Check IP addresses of failing requests
   grep "auth_failure" /var/log/nexus/access.log | awk '{print $1}' | sort | uniq -c | sort -rn | head -10
   
   # Block attacking IPs at firewall (if applicable)
   # iptables -I INPUT -s <IP> -j DROP
   ```

4. **If misconfiguration:**
   - Contact the webhook source owner
   - Verify their NEXUS_WEBHOOK_SECRET matches what's in our config
   - Check if secret was recently rotated: `grep -i "secret.*rotation" /var/log/nexus/audit.log`

5. **Check if credentials rotated without updating callers**
   ```bash
   # Last time secrets were rotated
   grep "secret_rotated\|secret_updated" /var/log/nexus/audit.log | tail -5
   
   # Send notification to webhook owners: "Secret rotated on [date], please update your credentials"
   ```

---

## If Immediate Actions Don't Work (5-15 min)

1. **Check if this is a legitimate spike (new feature deployed)**
   - Check deployment log: `git log --oneline -20 | head -10`
   - Did we deploy auth changes, webhook changes, or API changes?
   - If yes: review the diff, check for new validation rules

2. **Verify the secret/key configuration is correct**
   ```bash
   # Check environment variables
   echo $WEBHOOK_SECRET
   echo $RUNTIME_HOST_SECRET
   
   # Verify they're not empty or wrong
   # Check git history for recent changes
   git log -p --follow -S "WEBHOOK_SECRET" | head -50
   ```

3. **Check if callers have the right IP allowlist**
   - If NEXUS enforces IP allowlists: check if a caller is being rejected due to IP
   - Whitelist might be missing a new caller IP

4. **Temporarily increase logging to see details**
   ```bash
   # Set log level to DEBUG
   docker exec nexus-app /bin/sh -c "export LOG_LEVEL=DEBUG && restart"
   
   # Or restart with debug env var
   docker kill nexus-app
   docker run -e LOG_LEVEL=DEBUG -p 7860:7860 nexus:latest
   
   # Tail logs to see detailed auth failures
   tail -f /var/log/nexus/app.log | grep -i "auth\|webhook"
   ```

---

## If Still Spiking (15+ min)

1. **Escalation**
   - Slack: `@security-team`
   - If appears to be active attack: engage incident commander
   - Create security incident ticket

2. **Mitigation options**
   - **Temporary:** Disable webhook signature verification (NOT RECOMMENDED, security risk)
   - **Better:** Implement rate limiting per source IP
     ```bash
     # Check if rate limiting is enabled
     grep -i "rate_limit" /etc/nexus/config.yaml
     
     # If not, temporarily enable: add rate_limit_per_ip: 10/sec to config
     ```

3. **If attack is ongoing**
   - Coordinate with Platform/Security to block attacker IPs
   - Rotate WEBHOOK_SECRET to invalidate any compromised keys
   - Notify affected webhook owners

---

## Post-Incident

- [ ] Determine root cause (attack, misconfiguration, deployment issue)
- [ ] If attack: create security incident report
- [ ] If misconfiguration: document the change and notify team
- [ ] If deployment issue: revert or fix the code
- [ ] Add metrics dashboard to track auth failures over time
- [ ] Consider adding automatic rate limiting per API key
- [ ] Improve alerting: separate "legitimate misconfiguration" from "attack" alerts

---

## Prevention

- Require signature verification in ALL webhook calls
- Rotate secrets every 90 days
- Maintain an audit log of all failed auth attempts
- Alert on unusual patterns (same failure type, same source)
- Test webhooks in staging before enabling in production

---

## Contact & Escalation

- **Security Team:** Slack `#security`
- **Backend Team Lead:** See wiki
- **Incident Commander:** If appears to be active attack
