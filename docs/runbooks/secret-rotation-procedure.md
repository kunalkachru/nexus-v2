# Webhook Secret Rotation Procedure

**Document ID:** SR-001  
**Last Updated:** 2026-06-17  
**Audience:** DevOps, Security, Integration Partners  

---

## Overview

This document describes the zero-downtime webhook secret rotation procedure for NEXUS. The process allows you to rotate the `NEXUS_WEBHOOK_SIGNING_SECRET` without any service interruption or webhook rejections.

**Key Principle:** During rotation, NEXUS accepts webhooks signed with both the **current secret** and the **previous secret**, enabling customers to transition their webhook signing keys gracefully.

---

## Why Rotate Secrets?

Secret rotation is a security best practice that:
- Limits exposure window if a secret is compromised
- Reduces risk from accidental secret leaks
- Meets compliance requirements (SOC 2, HIPAA, etc.)
- Implements the principle of least privilege

**Recommended Rotation Schedule:** Every 90 days (or annually per your security policy)

---

## Prerequisites

Before starting rotation:

- [ ] Current `NEXUS_WEBHOOK_SIGNING_SECRET` is securely stored (e.g., in HashiCorp Vault, AWS Secrets Manager)
- [ ] You have access to deployment configuration (environment variables, config files)
- [ ] You can communicate the new secret to webhook customers
- [ ] You can monitor webhook delivery logs during rotation
- [ ] NEXUS version supports dual-secret verification (v2.0+)

---

## Rotation Process

### Day 1: Generate and Deploy New Secret

#### Step 1: Generate New Secret

Generate a cryptographically secure random secret:

```bash
# Option A: Using OpenSSL (recommended)
openssl rand -hex 32

# Option B: Using Python
python3 -c "import secrets; print(secrets.token_hex(32))"

# Option C: Using /dev/urandom
head -c 32 /dev/urandom | xxd -p -c 256
```

**Example Output:** `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0`

**Store this securely:**
- [ ] Saved in password manager (LastPass, 1Password, etc.)
- [ ] Saved in secret management system (Vault, AWS Secrets Manager, etc.)
- [ ] NOT checked into git or shared in plain text

#### Step 2: Update Configuration

Update NEXUS configuration to include both secrets:

**Option A: Environment Variables**

```bash
# Current secret (will be previous during next rotation)
export NEXUS_WEBHOOK_SIGNING_SECRET="a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0"

# Previous secret (allows old webhooks to still work)
export NEXUS_WEBHOOK_SIGNING_SECRET_PREVIOUS="<old_secret_from_previous_rotation>"
```

**Option B: Configuration File**

```yaml
# config.yaml or environment.yaml
webhook:
  signing_secret: "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0"  # new secret
  signing_secret_previous: "<old_secret>"  # previous secret (optional)
```

**Option C: Docker Environment**

```dockerfile
# In docker-compose.yml or Dockerfile
ENV NEXUS_WEBHOOK_SIGNING_SECRET="a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0"
ENV NEXUS_WEBHOOK_SIGNING_SECRET_PREVIOUS="<old_secret>"
```

#### Step 3: Deploy Code Change

Deploy the updated configuration:

```bash
# Option A: For systemd service
sudo systemctl restart nexus

# Option B: For Docker
docker-compose restart nexus-app

# Option C: For Kubernetes
kubectl set env deployment/nexus \
  NEXUS_WEBHOOK_SIGNING_SECRET="a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0" \
  NEXUS_WEBHOOK_SIGNING_SECRET_PREVIOUS="<old_secret>"
```

#### Step 4: Verify Deployment

```bash
# Health check
curl http://localhost:7860/health

# Verify webhook endpoint responds
curl -X POST http://localhost:7860/api/webhooks/test \
  -H "Content-Type: application/json" \
  -H "x-signature: sha256=..." \
  -d '{}'

# Check logs for rotation event
tail -20 /var/log/nexus.log | grep -i "webhook\|rotation"
```

- [ ] Service is running
- [ ] Health check passes
- [ ] Webhook endpoint responds
- [ ] No errors in logs

**Record Deployment Time:** ___:___ UTC

---

### Days 1-7: Grace Period

#### Verify Both Secrets Work

During the grace period, verify that:

1. **New Webhooks:** Customers can use the new secret

   ```bash
   # Test with new secret
   NEW_SECRET="a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0"
   BODY='{"test": "webhook"}'
   SIGNATURE=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "$NEW_SECRET" -hex | sed 's/(stdin)= /sha256=/')
   
   curl -X POST http://localhost:7860/api/webhooks \
     -H "Content-Type: application/json" \
     -H "x-signature: $SIGNATURE" \
     -d "$BODY"
   ```

   Expected: `200 OK`

2. **Old Webhooks:** Existing customers can still use the previous secret

   ```bash
   # Test with previous secret
   PREV_SECRET="<old_secret>"
   SIGNATURE=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "$PREV_SECRET" -hex | sed 's/(stdin)= /sha256=/')
   
   curl -X POST http://localhost:7860/api/webhooks \
     -H "Content-Type: application/json" \
     -H "x-signature: $SIGNATURE" \
     -d "$BODY"
   ```

   Expected: `200 OK` (with log note: "webhook_signature_verified_with_previous_secret")

3. **Invalid Secret:** Reject unknown secrets

   ```bash
   # Test with invalid secret
   INVALID_SECRET="invalid_secret_xxx"
   SIGNATURE=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "$INVALID_SECRET" -hex | sed 's/(stdin)= /sha256=/')
   
   curl -X POST http://localhost:7860/api/webhooks \
     -H "Content-Type: application/json" \
     -H "x-signature: $SIGNATURE" \
     -d "$BODY"
   ```

   Expected: `401 Unauthorized`

#### Monitor Webhook Logs

```bash
# Monitor for old secret usage
grep -i "webhook_signature_verified_with_previous_secret" /var/log/nexus.log

# Monitor for failures
grep -i "webhook_signature_mismatch" /var/log/nexus.log | tail -20

# Count by customer/tenant
grep "webhook_signature" /var/log/nexus.log | \
  grep -o '"tenant_id":"[^"]*"' | sort | uniq -c
```

- [ ] New secret accepted
- [ ] Previous secret accepted (grace period)
- [ ] Invalid secrets rejected
- [ ] No unexpected errors

#### Notify Customers

Send notification to webhook customers:

**Email Template:**

```
Subject: NEXUS Webhook Secret Rotation — Action Required

Dear Integration Partner,

We are rotating our webhook signing secret as part of our security hardening process.

**Timeline:**
- June 17, 2026 (Day 1): New secret deployed (old secret still accepted)
- June 24, 2026 (Day 7): Deadline to update your webhook signing logic
- June 25, 2026 (Day 8): Old secret deactivated

**Action Required:**
1. Update your webhook signature verification to use this new secret:
   NEW_SECRET: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0

2. Test your webhook integration in staging first
3. Deploy to production by June 24, 2026

**Support:**
If you have questions or issues, contact: support@nexus.example.com

**Backward Compatibility:**
The old secret will continue to work until June 25, 2026. You have a full week to transition.

Best regards,
NEXUS Security Team
```

- [ ] Email sent to all webhook customers
- [ ] Customers acknowledge receipt
- [ ] Customers confirm testing/update plan

---

### Day 8: Deactivate Previous Secret

#### Step 1: Remove Previous Secret

After all customers have rotated (typically 7+ days later):

```bash
# Update configuration to remove previous secret
export NEXUS_WEBHOOK_SIGNING_SECRET="a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0"
# Unset NEXUS_WEBHOOK_SIGNING_SECRET_PREVIOUS (or set to empty)
unset NEXUS_WEBHOOK_SIGNING_SECRET_PREVIOUS
```

#### Step 2: Deploy

```bash
# Option A: For systemd service
sudo systemctl restart nexus

# Option B: For Docker
docker-compose restart nexus-app

# Option C: For Kubernetes
kubectl set env deployment/nexus \
  NEXUS_WEBHOOK_SIGNING_SECRET="a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0"
```

#### Step 3: Verify

```bash
# Verify new secret still works
NEW_SECRET="a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0"
BODY='{"test": "webhook"}'
SIGNATURE=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "$NEW_SECRET" -hex | sed 's/(stdin)= /sha256=/')

curl -X POST http://localhost:7860/api/webhooks \
  -H "Content-Type: application/json" \
  -H "x-signature: $SIGNATURE" \
  -d "$BODY"
# Expected: 200 OK
```

#### Step 4: Archive Old Secret

```bash
# Archive old secret for audit purposes (keep for 30 days minimum)
# Option: Store in archive database or encrypted backup
echo "Old secret (valid until June 25, 2026): $(cat /secure/old_secret.txt)" >> /secure/archived_secrets.log

# Delete old secret from active systems
shred -vfz /secure/old_secret.txt

# Update audit log
echo "Secret rotation completed: $(date)" >> /var/log/nexus-security.log
```

- [ ] Configuration updated
- [ ] Service restarted
- [ ] New secret verified
- [ ] Old secret archived and destroyed

**Record Completion Time:** ___:___ UTC

---

## Rollback Procedure

If issues occur during rotation, you can rollback to the previous secret:

### Immediate Rollback (First 24 hours)

```bash
# Revert to previous configuration
export NEXUS_WEBHOOK_SIGNING_SECRET="<old_secret>"
unset NEXUS_WEBHOOK_SIGNING_SECRET_PREVIOUS

# Restart service
sudo systemctl restart nexus

# Verify rollback
curl http://localhost:7860/health
```

### Extended Rollback (After 1+ days)

If you need to rollback after removing the previous secret:

1. Restore the old secret value
2. Set it as current secret again
3. Follow notification process to inform customers of rollback

---

## Monitoring & Logging

### Webhook Signature Logs

The webhook verifier logs two key events:

```json
// Event 1: Current secret verification success
{
  "event": "webhook_signature_verified",
  "secret_type": "current",
  "timestamp": "2026-06-17T10:30:00Z"
}

// Event 2: Previous secret verification (rotation grace period)
{
  "event": "webhook_signature_verified_with_previous_secret",
  "rotation_in_progress": true,
  "timestamp": "2026-06-17T10:30:05Z"
}

// Event 3: Signature mismatch failure
{
  "event": "webhook_signature_mismatch",
  "path": "/api/webhooks",
  "timestamp": "2026-06-17T10:30:10Z"
}
```

### Dashboard Queries

Create Prometheus/Grafana queries to monitor rotation:

```promql
# Count successful verifications with current secret
rate(webhook_signature_verified_total{secret_type="current"}[5m])

# Count verifications with previous secret (should decrease over time)
rate(webhook_signature_verified_total{secret_type="previous"}[5m])

# Failed signature verifications (should remain low)
rate(webhook_signature_mismatch_total[5m])
```

### Alerts

Create alerts to catch rotation issues:

```yaml
- alert: WebhookSignatureMismatchSpike
  expr: rate(webhook_signature_mismatch_total[5m]) > 0.1
  for: 5m
  severity: high
  annotations:
    summary: "Webhook signature failures detected"
    action: "Check if customers have updated their secret"

- alert: PreviousSecretStillInUse
  expr: rate(webhook_signature_verified_total{secret_type="previous"}[24h]) > 0
  for: 24h
  severity: medium
  annotations:
    summary: "Previous secret still in use after grace period"
    action: "Contact customer to complete rotation"
```

---

## Checklist for Rotation

Use this checklist to ensure complete rotation:

### Pre-Rotation (1 week before)

- [ ] Review current webhook integrations
- [ ] Plan communication to customers
- [ ] Identify customers using webhooks
- [ ] Prepare new secret (generate and store securely)
- [ ] Update deployment configuration (test in staging first)

### Day 1: Deployment

- [ ] Generate new secret
- [ ] Update configuration with both old and new secrets
- [ ] Deploy code change
- [ ] Verify service is healthy
- [ ] Test webhook endpoints with both secrets
- [ ] Notify customers of rotation

### Days 1-7: Grace Period

- [ ] Monitor webhook logs for signature mismatches
- [ ] Confirm customers have received notification
- [ ] Track usage of previous secret (should decrease)
- [ ] Provide support for customer issues
- [ ] Document any customers still using old secret

### Day 8: Deactivate

- [ ] Confirm all identified customers have rotated
- [ ] Remove previous secret from configuration
- [ ] Deploy final configuration
- [ ] Verify only new secret is accepted
- [ ] Archive old secret
- [ ] Update audit log
- [ ] Send completion notification to customers

### Post-Rotation (Follow-up)

- [ ] Review webhook metrics and logs
- [ ] Document lessons learned
- [ ] Update next rotation date (calendar event)
- [ ] Communicate completion to security team

---

## Troubleshooting

### Issue: Webhooks Still Being Rejected After Rotation

**Symptoms:** Customers report 401 errors on webhook delivery

**Investigation:**
```bash
# Check logs for signature mismatches
grep "webhook_signature_mismatch" /var/log/nexus.log | tail -20

# Verify both secrets are configured
echo $NEXUS_WEBHOOK_SIGNING_SECRET
echo $NEXUS_WEBHOOK_SIGNING_SECRET_PREVIOUS

# Test webhook manually with customer's secret
SIGNATURE=$(echo -n '{"test":"data"}' | openssl dgst -sha256 -hmac "CUSTOMER_SECRET" -hex | sed 's/(stdin)= /sha256=/')
curl -X POST http://localhost:7860/api/webhooks/test \
  -H "x-signature: $SIGNATURE" \
  -d '{"test":"data"}'
```

**Resolution:**
1. Confirm customer is using the NEW secret (from notification email)
2. Verify customer's HMAC implementation matches ours (SHA256)
3. Check that customer is providing full request body in HMAC calculation
4. If needed, extend grace period and notify customer

### Issue: Old Webhooks Break When Previous Secret is Removed

**Symptoms:** Spikes in webhook failures after Day 8

**Prevention:**
- Track usage during grace period
- Extend grace period if customers still using old secret
- Send reminder emails on Day 5 and Day 7

**Recovery:**
```bash
# If customers still need old secret, restore it temporarily
export NEXUS_WEBHOOK_SIGNING_SECRET_PREVIOUS="<old_secret>"
systemctl restart nexus

# Send apology + extended deadline email
```

### Issue: Secret Leaked (Emergency Rotation)

If the current secret is compromised:

1. **Immediately** change the current secret:
   ```bash
   NEW_SECRET=$(openssl rand -hex 32)
   export NEXUS_WEBHOOK_SIGNING_SECRET="$NEW_SECRET"
   systemctl restart nexus
   ```

2. **Keep previous secret active** for the grace period

3. **Notify customers immediately** (not in 7 days):
   ```
   URGENT: Webhook secret was exposed. Rotate to new secret immediately.
   New Secret: [provided]
   Grace Period: 24 hours (shorter than normal due to security incident)
   ```

4. **Monitor closely** during emergency rotation

---

## Related Documentation

- [Webhook Integration Guide](../webhook-integration.md)
- [Auth Configuration](../auth-configuration.md)
- [Security Incident Response](./security-incident-response.md)
- [Production Operations Runbook](./production-operations.md)

---

**Document Owner:** Security Team  
**Review Frequency:** Annually  
**Last Reviewed:** 2026-06-17  
**Next Review:** 2027-06-17
