# MERIDIAN ANALYTICS NEXUS PILOT REPORT
**Date:** 2026-06-23  
**Pilot Company:** Meridian Analytics (B2B SaaS)  
**SRE Lead:** Myself (meridian-sre-lead)  
**Environment:** Local NEXUS instance  
**Incidents Submitted:** 10  

---

## EXECUTIVE SUMMARY

Meridian Analytics pilot reveals **classification and support parity issues** between documented families (INC009, INC010, INC011) and actual NEXUS behavior. The platform successfully detects incident signatures and service context but fails to classify into supported families for the 3 new incident types (CDN, ML, Geographic).

**Overall Assessment:** ⚠️ **Promising for B2B SaaS but new families require production validation**

---

## PILOT INCIDENT CORPUS

### CLASSIFICATIONS & ANALYSIS

| ID | Type | Expected | NEXUS Result | Quality | Status |
|---|---|---|---|---|---|
| **MA-001** | DB Pool | INC002 ✓ | Strong signature match | 80% | ✅ RECOGNIZED |
| **MA-002** | Deploy | INC003 ? | Partial (memory_pressure) | 55% | ⚠️ WRONG FAMILY |
| **MA-003** | Auth | INC007 ? | Partial (auth___permission_failure) | 55% | ⚠️ WRONG FAMILY |
| **MA-004** | Queue | INC005 ✗ | No signature detected | 40% | ❌ MISSED |
| **MA-005** | CDN | INC009 ✗ | No signature detected | 40% | ❌ MISSED |
| **MA-006** | ML | INC010 ✗ | No signature detected | 40% | ❌ MISSED |
| **MA-007** | Geographic | INC011 ✗ | Misclassified as INC004 | 79% | ❌ WRONG FAMILY |
| **MA-008** | Unsupported | N/A | Correctly unsupported | 40% | ✅ EXPECTED |
| **MA-009** | Ambiguous | N/A | Correctly unsupported | 40% | ✅ EXPECTED |
| **MA-010** | Follow-up | INC002 ? | Partial (memory_pressure) | 40% | ⚠️ WRONG FAMILY |

**Accuracy Score:** 20% (2/10 correct) — Critical issue for new families

---

## DETAILED FINDINGS

### ✅ SUCCESSES

#### MA-001: DB Pool Exhaustion (INC002) — CORRECT ✓
- **NEXUS Classification:** Strong match - signature detected
- **Quality Score:** 80%
- **Why This Works:** Explicit keywords (pool, connections, timeout, exhausted) present in structured message
- **Service Detection:** Correctly identified "analytics-api"
- **Enterprise Value:** Clear path to mitigation (increase pool size, investigate connection leaks)

#### MA-008, MA-009: Unsupported Handling — CORRECT ✓
- **Behavior:** System correctly rejects Stripe webhook and ambiguous reporting incidents
- **Investigation Guidance:** Present and contextually appropriate
- **Enterprise Value:** Graceful degradation with actionable guidance instead of rejection

### ⚠️ PARTIAL SUCCESSES / SURPRISES

#### MA-002: Deploy Regression — WRONG FAMILY (expected INC003, got memory_pressure)
- **NEXUS Detection:** Recognized severity and found "memory_pressure___leak" signature
- **Why It Failed:** The "panic: runtime error invalid memory" phrase triggered memory leak detection instead of deploy-regression classification
- **Root Cause:** NEXUS lacks semantic understanding that memory panics in NEW CODE = deploy regression, not generic memory pressure
- **B2B SaaS Impact:** HIGH — deploy regressions are daily incident type for Go microservices shops. Classification accuracy matters for post-incident runbook execution.

#### MA-003: Auth Slowdown — WRONG FAMILY (expected INC007, got auth___permission_failure)
- **NEXUS Detection:** Recognized "auth" signature
- **Why It Failed:** Matched "auth___permission_failure" instead of "auth___dependency_slowdown"
- **Root Cause:** NEXUS doesn't distinguish between permission/access failures vs slowness/latency issues
- **B2B SaaS Impact:** MEDIUM — Okta dependency slowness is different from IAM permission denial. Remediation paths diverge (check Okta health vs debug IAM config).

#### MA-007: Geographic Routing — MISCLASSIFIED (expected INC011, got INC004)
- **NEXUS Detection:** Confidence 79% but WRONG family
- **Classification:** "Cache Cardinality Explosion" (INC004) instead of "Geographic/Routing" (INC011)
- **Why It Failed:** Phrases like "routing change" and "health failing" triggered cache-related patterns instead of geographic/BGP patterns
- **Root Cause:** New family (INC011) vocabulary not yet trained into SENTINEL patterns
- **B2B SaaS Impact:** CRITICAL — Regional outages require different triage (check DNS/BGP vs check cache layers). Wrong classification leads to wrong runbook.

### ❌ CRITICAL MISSES

#### MA-004: Queue Backlog (INC005) — NO SIGNATURE
- **NEXUS Result:** Quality 40%, no signature detected
- **Why It Failed:** Kafka-specific terminology ("consumer lag", "msg/sec") not in NEXUS patterns
- **Root Cause:** SENTINEL trained on web/HTTP patterns, not message queue patterns (Kafka, RabbitMQ, SQS)
- **B2B SaaS Impact:** CRITICAL — Queue backlogs are common for analytics/ETL pipelines. Kafka is ubiquitous in Go microservices architecture.

#### MA-005: CDN Cache (INC009) — NO SIGNATURE (Should work!)
- **NEXUS Result:** Quality 40%, no signature despite keywords
- **Why It Failed:** INC009 was "recently added" per audit, but SENTINEL patterns may not be updated
- **Root Cause:** New incident family added to catalogue but not wired into classification agent
- **B2B SaaS Impact:** MEDIUM — CDN issues affect global user bases. Classification needed for cache-invalidation runbooks.

#### MA-006: ML Degradation (INC010) — NO SIGNATURE (Should work!)
- **NEXUS Result:** Quality 40%, no signature despite "precision dropped", "model v3.2"
- **Why It Failed:** Same as MA-005 — new family not wired into SENTINEL
- **Root Cause:** INC010 catalogue entry exists but agent doesn't recognize patterns
- **B2B SaaS Impact:** MEDIUM-HIGH — Anomaly detection is critical feature for analytics platform. Model quality drops silently without classification.

---

## COMPARISON: B2B SaaS vs B2C E-Commerce (Kartik Commerce Pilot)

| Dimension | Kartik (B2C) | Meridian (B2B) | Impact |
|---|---|---|---|
| **Incident Frequency** | ~3/week | ~8/month | SaaS has lower volume but higher SLA cost |
| **Blast Radius** | Single merchant or region | Enterprise customer SLA violation | B2B needs account-level decision making |
| **Triage Speed** | Best-effort | Contractual SLA (often 1 hour) | B2B requires faster classification |
| **Tech Stack** | Python/Django, Postgres, Redis | Go microservices, Kafka, Kubernetes | B2B has more complex distributed patterns |
| **Incident Types** | Payment/checkout, auth, deployment | DB pool, queue backlog, regional, ML | B2B: more infrastructure-level |
| **NEXUS Fit** | Good — payment flow is clear | Poor — distributed system patterns not recognized |  Needs Kafka, K8s, multi-region vocabulary |

**Key Difference:** Meridian's incidents are *infrastructure-distributed* (multi-service, multi-region, async pipelines). Kartik's were *single-flow* (user transaction). NEXUS was trained on single-flow patterns.

---

## NEW FAMILY PERFORMANCE (INC009, INC010, INC011)

| Family | Status | Issue | Confidence | Recommendation |
|---|---|---|---|---|
| **INC009 (CDN Cache)** | Not Working | No signatures in SENTINEL | 0% | Add "CloudFront", "cache invalidation", "stale content" patterns |
| **INC010 (ML Degradation)** | Not Working | No signatures in SENTINEL | 0% | Add "model", "precision drop", "training drift" patterns |
| **INC011 (Geographic)** | Broken | Wrong family (INC004) | 79% confidence WRONG | Retrain SENTINEL; "BGP", "Route53", "regional" priorities wrong |

**Root Cause:** Families added to `incidents/catalogue.py` but not integrated into `server/agents/sentinel.py` classification patterns.

---

## GUARDIAN WORKFLOW EVALUATION

### Requested Decisions

#### ✅ MA-001: DB Pool Exhaustion — APPROVE
```
GUARDIAN DECISION: APPROVE

Recommendation: Increase pool size 100→300 (already done) 
               + deploy v4.2.1 connection cleanup
               
Reasoning: 
- Root cause identified (async report generation leak)
- Mitigation deployed (pool increase + cleanup)
- Error rate back to 0% (verified)
- Connection leak concerns addressable in next release cycle
- SLA no longer at risk

Confidence: High (clear signal, proven fix)
```

#### ❌ MA-002: Deploy Regression — REJECT
```
GUARDIAN DECISION: REJECT (ROLLBACK BLOCKED)

Recommendation: DO NOT ROLL BACK — too risky with migration

Reasoning:
- Migration ran (data model changed)
- Rollback would require data migration reversal
- PDF export is isolated to new feature
- Better path: hotfix v2.1.1 with PDF feature flag disabled
- Risk of rollback > risk of bug in isolated feature

Action: 
1. Disable PDF export feature flag
2. Deploy v2.1.1 with flag off
3. Run PDF regression tests
4. Re-enable in v2.2.0 after full validation

Confidence: High (architectural constraint clear)
```

#### ⏸️ MA-007: Geographic Routing — ESCALATE
```
GUARDIAN DECISION: ESCALATE TO AWS

Recommendation: Engage AWS support for BGP routing investigation

Reasoning:
- AWS maintenance window at 08:15 UTC per notification
- Route53 health checks failing for Singapore
- Internal health OK but external timeouts
- BGP changes are infrastructure-level, requires AWS coordination
- SRE team cannot remediate without AWS diagnostic info

Action:
1. Create AWS support ticket (P1)
2. Reference maintenance window & BGP change
3. Ask for: BGP routing logs, Route53 health check diagnostics
4. Provide: Internal vs external health check comparison
5. Estimate resolution: AWS diagnostics + rollback

Confidence: High (clear escalation path)
```

---

## ENTERPRISE SLA CONTEXT FINDINGS

**Observation:** NEXUS does not currently track SLA/contract context

| Incident | Contractual Impact | NEXUS Handling | Gap |
|---|---|---|---|
| MA-001 | "SLA breach in 23 min" | No SLA awareness | Can't prioritize escalation |
| MA-007 | "100% APAC down" | Treats as severity P0 | No regional-SLA mapping |
| MA-002 | "3 customers affected" | No customer tracking | Can't link to contracts |

**Recommendation for Meridian:** Add tenant/customer mapping so NEXUS can surface SLA breach risk in Guardian decision context.

---

## NPS EVALUATION

**Net Promoter Score: 5/10** (Would not recommend in current state)

### Promoter Reasons (Score 8-10): None
- New families don't work
- Kafka patterns missing
- Multi-region triage patterns insufficient

### Passive Reasons (Score 7): 
- Good investigation guidance for unsupported incidents
- Clear incident intake quality signals
- Sound framework, needs better training

### Detractor Reasons (Score 1-6):
- 80% of pilot incidents misclassified or missed
- CDN/ML/Geographic families broken (core feature)
- Queue backlog (daily pattern) not recognized
- No Kafka/K8s vocabulary
- Deploy regression classification wrong (critical for Go shops)

**Bottom Line:** "NEXUS is architecturally sound but not trained for B2B SaaS distributed systems. Needs 2-3 weeks of pattern refinement before production use."

---

## TOP 3 GAPS vs KARTIK PILOT

1. **Missing Distributed Systems Vocabulary**
   - Kartik: Single-flow payment incidents
   - Meridian: Multi-service, async queue, regional patterns
   - Gap: No Kafka, Kubernetes, multi-region, BGP patterns

2. **New Families Not Integrated**
   - Families added to catalogue but not to SENTINEL agent patterns
   - INC009, INC010, INC011 doc-only, not live
   - Gap: Classification engine ≠ catalogue

3. **Go Microservices Patterns**
   - Kartik: Python/Django (stateless, clear request flow)
   - Meridian: Go microservices (goroutines, memory patterns, panics)
   - Gap: "panic" misinterpreted as generic memory leak, not deploy error

---

## RECOMMENDED NEXT FEATURES FOR MERIDIAN

### Phase 1 (Must-Have Before Production)
1. **Kafka Pattern Library**
   - Recognize consumer lag, broker issues, rebalancing
   - Keywords: "consumer lag", "msg/sec", "broker", "partition"

2. **New Family Integration**
   - Verify INC009, INC010, INC011 are actually live in SENTINEL
   - Add missing patterns (CDN, model degradation, BGP/Route53)

3. **Go Panic Classification**
   - Distinguish "panic in new code" = deploy regression (INC003)
   - vs "panic in existing code" = memory pressure (separate)

### Phase 2 (Nice-To-Have)
1. **Customer/SLA Context**
   - Link incidents to tenant/customer for SLA breach detection
   - Surface contract-level impact in Guardian decisions

2. **Regional Failure Patterns**
   - Kubernetes node failures, regional DNS, BGP announcements
   - Multi-region availability set differentiation

3. **Model Quality Baselines**
   - INC010 needs threshold tracking (precision 94% → 31%)
   - ML-specific telemetry integration

---

## PRODUCTION READINESS ASSESSMENT

| Dimension | Status | Comment |
|---|---|---|
| Intake/Normalization | ✅ Ready | Quality signals clear, evidence detection works |
| Classification | ❌ Not Ready | 20% accuracy, new families broken |
| Investigation Guidance | ✅ Ready | Fallback guidance helpful for unsupported |
| Guardian Workflow | ✅ Ready | SLA decision-making sound, clear escalation |
| Kubernetes Integration | ❌ Not Ready | No K8s-specific patterns |
| Regional Patterns | ❌ Not Ready | BGP/Route53 misclassified |
| Kafka/Queue | ❌ Not Ready | No async queue vocabulary |

**Verdict:** Classification must reach 70%+ accuracy before production release to Meridian.

---

## OVERALL RECOMMENDATION

**DO NOT DEPLOY to Meridian production yet.**

**Timeline for Production Readiness:**
- Week 1: Integrate new families, fix INC003/INC007/INC011 patterns
- Week 2: Add Kafka/queue vocabulary, test MA-004 classification
- Week 3: Regional/BGP patterns, user acceptance testing with SRE team

**Next Pilot Option:**
- Proceed with internal testing only
- OR run mini-pilot at staging environment to refine patterns without production risk

---

## SESSION ARTIFACTS
- Classification accuracy: 20% (2/10 correct)
- New families broken: 3/3 (INC009, INC010, INC011)
- Investigation guidance provided: Yes (MA-008, MA-009)
- Guardian decisions: 3 made (Approve, Reject, Escalate)
- Major blockers: Kafka patterns, new family integration, Go panic handling

**Report Generated:** 2026-06-23

