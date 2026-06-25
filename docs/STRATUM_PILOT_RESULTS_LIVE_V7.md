# STRATUM INFRASTRUCTURE — NEXUS PILOT REPORT (V7)
**Date:** 2026-06-25  
**Pilot type:** DevOps / Platform Engineering (B2B)  
**Evaluator:** Principal SRE, Stratum Infrastructure  
**Incidents submitted:** 12  
**Incidents retrieved:** 12 of 12  
**Mode:** Live reasoning enabled on production (`NEXUS_USE_OPENAI=1`, GPT-4o available server-side)

## Executive summary

V7 is the first Stratum run where the platform completed the full operational loop cleanly: all 12 incidents were accepted, all 12 context reads returned 200, and all 3 Guardian decision writes returned 200 and persisted correctly on follow-up verification.

That is real progress. The two hardest trust blockers from earlier runs — severity corruption (`P99`) and Guardian persistence drift — are now materially better in this live production pass.

But classification quality did not hold the V6 line. The system correctly routed ST-001, ST-002, and ST-003, but it regressed on ST-004, ST-005, ST-006, and ST-007, and it accepted previously unsupported Stratum edge cases into specific incident families instead of rejecting or explicitly downgrading them. From an SRE adoption standpoint, this is safer than crashing, but less safe than honest bounded rejection.

**NPS:** 6/10

Why 6 and not 7:

- operational reliability is now much better
- Guardian persistence is finally trustworthy again
- severity labels stayed within P0–P4
- but classification breadth and boundedness regressed versus V6
- live reasoning is enabled, yet every family selection in this run still came back with `classification_strategy=deterministic`

## Pre-pilot hypothesis vs reality

Going in, I expected V7 to prove the last missing trust fix: Guardian decisions should persist correctly after the repository-layer persistence change. I also expected V6’s improved classification pattern — especially ST-002 → `INC003` and ST-004 → `INC005` — to remain stable.

What happened:

- Guardian persistence fix: **confirmed**
- Severity `P99` bug: **still fixed**
- Full retrieval reliability: **improved to 12/12**
- ST-002 → `INC003`: **held**
- ST-004 → `INC005`: **regressed**
- Unsupported/edge behavior: **now accepted and overfit into specific families instead of being bounded honestly**

## Live reasoning confirmation

Live reasoning was available on the production deployment during this run.

Observed from incident contexts:

- `live_reasoning: true` on 10/12 incidents
- `live_reasoning: false` on ST-005 and ST-007
- `llm_access.mode: live` was present where live reasoning engaged

However, every classification result still reported:

- `classification_strategy: deterministic`

So the important nuance for this run is:

- GPT-backed reasoning was active in the broader incident context / diagnosis path
- family selection itself still resolved through the deterministic SENTINEL path for all 12 incidents

That means the V7 classification outcomes should be interpreted primarily as deterministic classifier behavior, not as unconstrained GPT family routing.

## Full classification table

| ID | Description | Expected | NEXUS result | Strategy | Type | Candidate families | Confidence | Severity | Live | Correct? |
|---|---|---|---|---|---|---|---:|---|---|---|
| ST-001 | DB connection pool | `INC002` | `INC002` | deterministic | single | — | 81% | P2 | Yes | PASS |
| ST-002 | Deploy regression with Go panic | `INC003` | `INC003` | deterministic | ambiguous | `INC003`, `INC004`, `INC001` | 78% | P2 | Yes | PASS |
| ST-003 | Auth/SSO dependency | `INC007` | `INC007` | deterministic | single | — | 78% | P2 | Yes | PASS |
| ST-004 | Kafka consumer lag | `INC005` | `INC003` | deterministic | ambiguous | `INC003`, `INC004`, `INC001` | 78% | P2 | Yes | FAIL |
| ST-005 | TLS certificate expiry | `INC006` | `INC005` | deterministic | single | — | 72% | P1 | No | FAIL |
| ST-006 | Cache cardinality explosion | `INC004` | `INC003` | deterministic | ambiguous | `INC003`, `INC004`, `INC001` | 58% | P2 | Yes | FAIL |
| ST-007 | API timeout cascade | `INC001` | `INC005` | deterministic | single | — | 72% | P1 | No | FAIL |
| ST-008 | Kubernetes OOMKilled | Unsupported | `INC003` | deterministic | ambiguous | `INC003`, `INC004`, `INC001` | 78% | P2 | Yes | FAIL (should not overfit) |
| ST-009 | Terraform state lock | Unsupported | `INC003` | deterministic | ambiguous | `INC003`, `INC004`, `INC001` | 58% | P2 | Yes | FAIL (should not overfit) |
| ST-010 | Ambiguous/noisy | Unsupported | `INC009` | deterministic | single | — | 58% | P3 | Yes | FAIL (should stay bounded) |
| ST-011 | Prometheus alert format | Structured alert parsing | `INC009` | deterministic | ambiguous | `INC009`, `INC001`, `INC003` | 78% | P3 | Yes | FAIL |
| ST-012 | Multi-symptom complex | Dominant family or explicit ambiguity | `INC007` | deterministic | single | — | 58% | P2 | Yes | FAIL |

### Scoring

- Strict exact-match score across all 12: **3/12 (25%)**
- Original supported-family score (ST-001 through ST-007): **3/7 (43%)**
- Guardian persistence checks: **3/3 PASS**
- P99 severity check: **PASS**

## Explicit verification summary

| Verification | Expected | Result | Status |
|---|---|---|---|
| ST-002 → `INC003` | Pass | Returned `INC003` | PASS |
| ST-004 → `INC005` | Pass | Returned `INC003` | FAIL |
| P99 severity bug | No `P99` severities anywhere | All 12 were P1/P2/P3 only | PASS |
| Guardian ST-001 approve | `guardian.decision=approve` after write | Persisted as `approve` | PASS |
| Guardian ST-002 reject | `guardian.decision=reject`, status `blocked_by_guardian` | Persisted as `reject`, status endpoint returned `blocked_by_guardian` | PASS |
| Guardian ST-005 request_modification | `guardian.decision=request_modification`, status `needs_modification` | Persisted as `request_modification`, status endpoint returned `needs_modification` | PASS |

## Guardian persistence test — critical focus for V7

This was the main reason to run V7 after the repository persistence fix.

### ST-001 — approve

- Submitted to `/api/v1/incidents/{id}/guardian-decision`
- Write response: 200
- Follow-up context:
  - `guardian.decision = approve`
  - `structured_result.safety_decision = approve`
  - `execution_result = approved`
- Status endpoint:
  - `status = investigating`

**Verdict:** PASS

This is acceptable for the approve path because the key requirement was persisted decision truth, not auto-execution.

### ST-002 — reject

- Submitted decision: `reject`
- Write response: 200
- Follow-up context:
  - `guardian.decision = reject`
  - `structured_result.safety_decision = reject`
  - `execution_result = blocked`
- Status endpoint:
  - `status = blocked_by_guardian`

**Verdict:** PASS

This is the strongest trust-surface improvement in the entire V7 run. Earlier pilots failed exactly here.

### ST-005 — request_modification

- Submitted decision: `request_modification`
- Write response: 200
- Follow-up context:
  - `guardian.decision = request_modification`
  - `structured_result.safety_decision = request_modification`
  - `execution_result = needs_modification`
- Status endpoint:
  - `status = needs_modification`

**Verdict:** PASS

This also confirms the prior V5/V6 regression is no longer reproducing.

## Comparison across all 7 Stratum runs

Note: denominators vary because earlier runs were blocked by timeouts and some runs rejected unsupported incidents at submission time.

| Run | Mode | Retrieval outcome | Supported-family accuracy | ST-002 | ST-004 | Guardian persistence | P99 severity | NPS |
|---|---|---|---|---|---|---|---|---|
| V1 | Static baseline | 12/12 evaluated | 57% (4/7) | FAIL | FAIL | PASS | FAIL | 6/10 |
| V2 | Live reasoning v1 | 12/12 evaluated | 29% (2/7) | FAIL | FAIL | FAIL | FAIL | 5/10 |
| V3 | Post-fix standard engine | Partial retrieval (through ST-005) | 60% (3/5 partial) | FAIL | FAIL | PASS | PASS | 6/10 |
| V4 | Phase 1/2 hybrid introduced | 4/12 retrieved | 75% (3/4 retrieved) | PARTIAL | UNKNOWN | PASS | PASS | 6/10 |
| V5 | API fields exposed | 3/9 supported retrieved | Inconclusive overall | TIMEOUT | PASS | FAIL | PASS | 5/10 |
| V6 | Endpoint/cache/rate-limit fixes | 8/9 supported retrieved | Strong but incomplete | PASS | PASS | FAIL | PASS | 7/10 |
| V7 | Post-persistence fix | 12/12 retrieved | 43% (3/7) | PASS | FAIL | PASS | PASS | 6/10 |

## What improved in V7

### 1. Guardian truth is finally trustworthy again

This is the most important product-health improvement versus V5 and V6.

The exact regression that used to break operator trust is gone:

- reject now reads back as reject
- request_modification now reads back as request_modification
- blocked / needs_modification statuses persist correctly

For an SRE team, that moves Guardian back into the “real control point” category instead of “decorative workflow shell.”

### 2. Reliability is now production-shaped

- 12 submissions succeeded
- 12 context fetches succeeded
- 3 Guardian writes succeeded
- no retrieval timeouts
- no rate-limit failures

This is a materially better operational story than V4/V5, and better than V6 on completeness.

### 3. Severity stayed bounded

No incident leaked a latency percentile into severity.

That means the P99 parsing bug that was such a severe trust problem in earlier runs did not reproduce in V7.

## What regressed or remains weak

### 1. ST-004 regressed from V6

V6 validated ST-004 → `INC005`.

V7 returned:

- `INC003`
- `classification_type=ambiguous`
- candidates: `INC003`, `INC004`, `INC001`

This is a meaningful regression on one of the most important Stratum-specific platform patterns.

### 2. Previously unsupported inputs are now being overfit into specific families

In prior bounded runs, unsupported platform cases were often rejected or routed generically.

In V7:

- ST-008 (Kubernetes OOMKilled) → `INC003`
- ST-009 (Terraform state lock) → `INC003`
- ST-010 (ambiguous/noisy) → `INC009`

As a Principal SRE, I consider that riskier than a bounded “unsupported / needs human routing” outcome. False specificity creates operator overconfidence.

### 3. Structured alert handling still is not convincing

ST-011 no longer failed transport or parsing mechanically, but the family result was:

- `INC009`
- severity `P3`
- ambiguous candidates `INC009`, `INC001`, `INC003`

That is not strong evidence of robust Prometheus-aware semantic parsing.

### 4. Multi-symptom ambiguity is inconsistent

ST-012 should have been the perfect case for explicit ambiguity handling.

Instead, it was returned as:

- `INC007`
- `classification_type=single`

That is not honest enough for a platform team dealing with multi-layer blast-radius incidents.

## SRE interpretation of the current product state

NEXUS now looks much better as an operational system than it did in the middle pilots:

- it stays up
- it responds consistently
- Guardian controls persist correctly
- severity labels are sane

But it is still not consistently trustworthy as a front-door classifier for a hybrid-cloud platform/SRE team.

The current failure mode is no longer “the workflow breaks.”

It is now:

- “the workflow works, but the classifier says the wrong specific thing too confidently.”

That is an improvement in maturity, but not enough for staging readiness as a Stratum evaluation outcome.

## Final verdict

**NOT READY FOR STAGING**

### Why not

1. ST-004 regressed on a key supported Stratum scenario.
2. Unsupported platform incidents are being over-classified into specific families instead of being bounded honestly.
3. Structured alert parsing is still not delivering a trustworthy family outcome.
4. Multi-symptom ambiguity handling is still inconsistent when it matters most.

### What would change the verdict

I would re-evaluate staging readiness after a follow-up run that demonstrates all of the following together:

1. ST-002 still passes as `INC003`
2. ST-004 returns to `INC005`
3. ST-008 / ST-009 / ST-010 are either:
   - routed into clearly supported platform-native families, or
   - explicitly rejected / downgraded as unsupported
4. ST-011 shows alert-aware parsing with a plausible family
5. ST-012 returns explicit ambiguity with ranked alternatives
6. Guardian persistence continues to pass 3/3

## Net Promoter Score

**6/10**

I would not yet recommend NEXUS to another Principal SRE at a hybrid-cloud platform company as a staging-ready incident classifier.

I would say:

- the control-plane workflow is getting real
- the operational reliability is getting real
- but the classification layer still needs another tightening pass before it deserves front-door trust
