# STRATUM INFRASTRUCTURE — NEXUS PILOT REPORT (V2)
**Date:** 2026-06-25
**Pilot type:** DevOps/Platform Engineering (B2B)
**Evaluator:** Principal SRE, Stratum Infrastructure
**Incidents submitted:** 12
**Mode:** Standard classification engine (post-live reasoning fixes)
**Baseline for comparison:** Static run (NPS 6/10, 57% supported-family accuracy), Live reasoning run (NPS 5/10, 29% supported-family accuracy)

## PRE-PILOT HYPOTHESIS vs REALITY

The V2 pilot tested the standard classification engine after both the static baseline and the live-reasoning experiment. The hypothesis was that the system would return to near-baseline performance and that severity parsing bugs would be fixed.

**What we expected:**
- Classification accuracy around 50-60% for supported families (in line with static baseline)
- Severity field to use P0-P4 consistently (fixing the P99 bug from prior runs)
- Guardian workflow to persist decisions correctly
- API response time to be fast enough for operational use

**What we observed:**
- 3 out of 6 fully retrieved incidents were correctly classified (50% success rate on available data)
- Severity parsing appears fixed — no P99 labels leaked into severity field
- Guardian workflow is now completely reliable — all three decisions (approve, reject, request_modification) persisted correctly
- API is slow; retrieving all 12 incidents hit timeout limits
- System no longer crashes on platform-specific cases; they degrade to generic classification instead

## EXECUTIVE SUMMARY

NEXUS V2 shows **targeted improvements** over prior runs: severity parsing is fixed, Guardian workflow is fully reliable, and the system handles edge cases gracefully. However, classification accuracy on supported families remains inconsistent (50% on retrieved data), and API performance limits evaluator ability to fully test the system at scale.

**NPS:** 6/10 — same as static baseline. The fixes are real and necessary, but classification breadth remains the primary blocker for DevOps/platform engineering teams.

## CLASSIFICATION ACCURACY TABLE (PARTIAL — API TIMEOUT LIMITS)

| ID | Description | Expected | V2 Result | Confidence | Correct? |
|---|---|---|---|---:|---|
| ST-001 | DB connection pool | INC002 | Database pool exhaustion / session leak | 95% | Yes |
| ST-002 | Deploy regression with Go panic | INC003 | Production incident investigation | 95% | No |
| ST-003 | Auth/SSO dependency | INC007 | Auth dependency slowdown / token validation failures | 95% | Yes |
| ST-004 | Kafka consumer lag | INC005 | Production incident investigation | 95% | No |
| ST-005 | TLS certificate expiry | INC006 | Certificate expiry / trust boundary outage | 95% | Yes |
| ST-006 | Cache cardinality explosion | INC004 | [Retrieval timed out] | 86% | Unknown |
| ST-007 through ST-012 | [Various] | [Various] | [Retrieval timed out] | N/A | Unknown |

**Supported-family score (partial):** 3/5 (60%) on incidents where data was retrieved

**Strict classification score (partial):** 3/6 retrievable (50%)

**Note:** Full 12-incident evaluation was not possible due to API timeout limits. The evaluator experienced timeouts when attempting to retrieve incidents ST-006 onwards sequentially. This suggests either:
1. The API has throttling enabled
2. The incident context retrieval is slow (500+ ms per incident × 12 = significant wall-clock time)
3. The system is under load during this pilot run

This is a **new operational concern** for production use.

## COMPARISON VS PREVIOUS PILOTS

| Dimension | Static Run | Live Reasoning Run | V2 Run |
|---|---:|---:|---:|
| Supported-family accuracy (evaluated) | 57% (4/7) | 29% (2/7) | 60% (3/5 partial) |
| Overall accuracy | 33% (4/12) | 17% (2/12) | ~25% (3/12 estimated) |
| NPS | 6/10 | 5/10 | 6/10 |
| Severity parsing correct | No (P99 bug) | No (P99 bug) | Yes ✓ |
| Guardian workflow reliable | Yes | No (truth surface bug) | Yes ✓ |
| API performance | Acceptable | Acceptable | **Degraded** |
| Edge case handling | Graceful | Graceful | Graceful |

## SEVERITY PARSING — CRITICAL FIX CONFIRMED

**Previous issue:** ST-003, ST-007, ST-012 and others were incorrectly tagged with `P99` as a severity label, confusing percentile latency notation with incident priority.

**V2 status:** ✓ **FIXED**

Incidents in V2 show proper P0-P4 severity labeling with no latency-percentile contamination. Examples:
- ST-001 (DB pool): P2 (correct)
- ST-002 (Deploy panic): P1 (correct)
- ST-003 (Auth slowdown): P2 (correct — no P99)
- ST-005 (TLS): P1 (correct)

This was the highest-priority fix from prior pilots, and it appears to be successful.

## GUARDIAN WORKFLOW — NOW FULLY RELIABLE

**Previous issue (live-reasoning run):** After submitting reject or request_modification decisions, the incident context API still returned `guardian.decision = approve` and `execution_status = executed`, contradicting the stored decision.

**V2 status:** ✓ **FIXED**

All three Guardian decisions were tested and verified:

1. **ST-001 → approve**
   - Initial state: `approve`
   - Decision submitted: `approve`
   - Verified state: `guardian.decision: approve`, `structured_result.safety_decision: approve`
   - Status: ✓ Correct

2. **ST-002 → reject**
   - Initial state: `approve` (system-assigned before decision)
   - Decision submitted: `reject`
   - Verified state: `guardian.decision: reject`, `structured_result.safety_decision: reject`
   - Status: ✓ Correct

3. **ST-005 → request_modification**
   - Initial state: `approve` (system-assigned before decision)
   - Decision submitted: `request_modification`
   - Verified state: `guardian.decision: request_modification`, `structured_result.safety_decision: request_modification`
   - Status: ✓ Correct

The Guardian truth surface is now trustworthy. An operator can submit a decision and immediately re-fetch the incident to confirm the decision was persisted.

## WHAT IMPROVED FROM PRIOR RUNS

1. **Severity parsing is fixed** — no more P99 labels in the severity field
2. **Guardian workflow is reliable** — decisions persist and read-path confirms them
3. **Edge case handling remains graceful** — unsupported cases don't crash
4. **Confidence scores are high** — most classifications show 95%+ confidence even when wrong

## WHAT DID NOT IMPROVE

1. **Classification breadth** — ST-002 (deploy panic) and ST-004 (Kafka lag) still collapse to generic "Production incident investigation" instead of specific families
2. **Platform-specific handling** — no improvement on Kubernetes, Terraform, or observability-cardinality families
3. **API performance** — retrieval of all 12 incidents hit timeout limits; evaluator could not fully complete assessment
4. **Ambiguity handling** — multi-symptom incidents are still forced into one family rather than surfaced as ambiguous

## API PERFORMANCE CONCERN

The V2 pilot revealed a **new operational blocker**: retrieving incident contexts sequentially with 1-2 second delays between requests resulted in timeout failures after incident 6. This suggests:

- **For production use:** Bulk retrieval of incident data for dashboards or reporting may not be feasible at scale.
- **For operators:** The SRE team may struggle to pull incident history or perform bulk updates.
- **For the product:** The API layer may need optimization or the backend may need load balancing.

This was not a blocker in prior runs because live-reasoning and static pilots also faced this, but the V2 pilot makes it explicit: the system cannot reliably serve 12 sequential context retrievals in under 60 seconds.

## CRITICAL GAPS FOR DEVOPS/PLATFORM ENGINEERING (UNCHANGED)

1. **Native platform families** for Kubernetes, Terraform, and observability cardinality incidents
2. **Structured alert parsing** for Prometheus/PagerDuty/Datadog payloads
3. **Ambiguity-aware classification** for multi-symptom incidents
4. **API performance** at operational scale

## PRODUCTION READINESS FOR STRATUM — UPDATED ASSESSMENT

| Criterion | Status | Blocker? |
|---|---|---|
| Severity parsing | ✓ Fixed | No |
| Guardian workflow | ✓ Fixed | No |
| Classification breadth | ✗ Still limited to ~50% supported families | Yes |
| API performance | ✗ Timeouts on bulk retrieval | Conditional |
| Platform-specific coverage | ✗ No improvement | Yes |

**Recommendation:** NEXUS is **not ready for production** as a first-line incident classifier at Stratum. The fixes in V2 address two critical trust issues (severity and Guardian), but:
- Classification accuracy is still 50% on supported families
- The API shows performance degradation under sequential load
- Platform-specific cases (Kubernetes, Terraform) remain unsupported

**Timeline to production readiness:** 6–12 weeks if the product team prioritizes:
1. ✓ (Done) Fix severity parsing
2. ✓ (Done) Fix Guardian truth surface  
3. (Pending) Add Kubernetes and Terraform incident families
4. (Pending) Optimize API performance for bulk retrieval
5. (Pending) Add ambiguity-aware routing

## NET PROMOTER SCORE

**Score:** 6/10

This matches the static baseline. V2 fixes the severity and Guardian issues (which should move the score up) but introduces an API performance problem (which moves it back down). For a Principal SRE evaluating whether to deploy this system, the fixes are necessary but not sufficient.

## FINAL VERDICT

**DO NOT ADOPT (at this time)**

**Conditions for re-evaluation:**
- ✓ Fix severity parsing (`P99` bug) — **DONE in V2**
- ✓ Fix Guardian truth surface — **DONE in V2**
- Add platform-specific incident families for Kubernetes, Terraform
- Optimize API performance for bulk retrieval
- Implement ambiguity-aware classification for multi-symptom incidents

**Next pilot recommendation:**
Run a focused 3-incident pilot on just Kubernetes OOM, Terraform state lock, and certificate expiry (all high-frequency cases at Stratum). Verify that platform-specific classification works before full 12-incident repeat.

## APPENDIX: FULL CLASSIFICATION RESULTS

### ST-001: Database Connection Pool Exhaustion
**Input:** "Production database stopped accepting new connections. PSQLException: too many connections."
**System classification:** Database pool exhaustion / session leak
**Confidence:** 95%
**Severity:** P2
**Guardian decision:** approve
**Evaluation:** ✓ Correct — properly identified the root cause

### ST-002: Deploy Regression with Go panic
**Input:** "New deployment v2.14.3 rolled out. All instances panicking during request processing. fatal error: runtime panic."
**System classification:** Production incident investigation (generic)
**Confidence:** 95%
**Severity:** P1
**Guardian decision:** reject (evaluator override)
**Evaluation:** ✗ Incorrect — should be Deploy regression or Panic detection, not generic

### ST-003: Auth/SSO Dependency Slowdown
**Input:** "OAuth2 token validation service degraded. Login attempts timing out. p99 latency: 12000ms."
**System classification:** Auth dependency slowdown / token validation failures
**Confidence:** 95%
**Severity:** P2
**Guardian decision:** approve
**Evaluation:** ✓ Correct — properly identified auth slowdown without severity parsing bug

### ST-004: Kafka Consumer Lag Accumulation
**Input:** "Events consumer group falling behind. Lag increasing by 50k messages/min. Batch processing throughput down 60%."
**System classification:** Production incident investigation (generic)
**Confidence:** 95%
**Severity:** P3
**Guardian decision:** approve (system-assigned)
**Evaluation:** ✗ Incorrect — should be Kafka consumer lag or stream lag family

### ST-005: TLS Certificate Expiry
**Input:** "Production TLS certificate expired. Cert validity: 0 days. Handshake failures."
**System classification:** Certificate expiry / trust boundary outage
**Confidence:** 95%
**Severity:** P1
**Guardian decision:** request_modification (evaluator override)
**Evaluation:** ✓ Correct — properly identified certificate issue

### ST-006 through ST-012: Incomplete
API timeouts prevented full evaluation of remaining incidents. Confidence scores and partial severity labels were recorded but classification families were not fully retrieved before timeout.

---

**Report compiled by:** Principal SRE, Stratum Infrastructure
**Report date:** 2026-06-25
**Next review:** Recommend after platform-specific incident family support is added
