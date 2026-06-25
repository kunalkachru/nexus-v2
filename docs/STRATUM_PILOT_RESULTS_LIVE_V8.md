# STRATUM INFRASTRUCTURE — NEXUS PILOT REPORT (V8)
**Date:** 2026-06-26  
**Pilot type:** DevOps / Platform Engineering (B2B)  
**Evaluator:** Principal SRE, Stratum Infrastructure  
**Incidents submitted:** 12  
**Submission outcome:** 6 accepted, 6 rejected at intake  
**Incidents retrieved:** 6 of 6 accepted incidents  
**Mode:** Live reasoning enabled on production (`NEXUS_USE_OPENAI=1`, GPT-4o available server-side)  
**Code baseline under test:** commit `592e99e`

## Executive summary

V8 is a better bounded-system run than V7.

The six-fix hardening clearly changed behavior in the right direction on three fronts:

- ST-004 now correctly maps to `INC005`
- ST-005 now correctly maps to `INC006`
- unsupported/noisy cases are being rejected at intake instead of silently overfit into random supported families

Guardian persistence remains solid: approve, reject, and request-modification decisions all wrote successfully and stayed consistent on follow-up reads.

But this is still not staging-ready for a Stratum-style SRE workflow. Two core supported-family cases still fail badly (`ST-001`, `ST-003`), `ST-007` still collapses into deploy-regression instead of timeout-cascade, Prometheus-style structured input is still rejected, and severity drift is not fully gone because the `classification.severity` field still upshifts on multiple incidents even though `P99` contamination is fixed.

**NPS:** 6/10

Why 6/10:

- boundedness is materially better than V7
- Guardian truth surfaces are now trustworthy
- Kafka and TLS classification improved in exactly the places we hoped
- but DB pool, auth, timeout-cascade, Prometheus parsing, and severity consistency are still not reliable enough for staging

## What changed versus V7

The V8 fixes produced real movement:

- `ST-004` improved from FAIL → PASS (`INC003` → `INC005`)
- `ST-005` improved from FAIL → PASS (`INC005` → `INC006`)
- `ST-008`, `ST-009`, and `ST-010` improved from dangerous overfit acceptance → bounded rejection
- `classification_strategy=hybrid_escalated` now appears on real incidents (`ST-007`, `ST-012`)

But new or remaining problems are still visible:

- `ST-001` regressed from correct DB-pool behavior to `INC003`
- `ST-003` was rejected as unsupported and mis-matched to `INC010`
- `ST-007` still fails and lands on `INC003`
- `ST-011` still cannot handle Prometheus-style structured alert input
- `classification.severity` still upshifts on `ST-004`, `ST-005`, and `ST-012`

## Full classification table

| ID | Description | Expected | Submission result | NEXUS result | Strategy | Type | Candidate families | Confidence | Severity | Status |
|---|---|---|---|---|---|---|---|---:|---|---|
| ST-001 | DB connection pool | `INC002` | Accepted | `INC003` | `deterministic` | `single` | — | 86% | incident `P1`, classification `P1` | FAIL |
| ST-002 | Deploy regression / Go panic | `INC003` | Accepted | `INC003` | `deterministic` | `single` | — | 87% | incident `P1`, classification `P1` | PASS |
| ST-003 | Auth / SSO dependency | `INC007` | Rejected | Unsupported, matched `INC010` | intake rejection | n/a | n/a | 80.9% | submission `P3` | FAIL |
| ST-004 | Kafka consumer lag | `INC005` | Accepted | `INC005` | `deterministic` | `single` | — | 78% | incident `P3`, classification `P1` | PASS* |
| ST-005 | TLS certificate expiry | `INC006` | Accepted | `INC006` | `deterministic` | `single` | — | 78% | incident `P1`, classification `P0` | PASS* |
| ST-006 | Redis cardinality / cache explosion | `INC004` | Rejected | Unsupported, matched `INC004` | intake rejection | n/a | n/a | 88.7% | submission `P2` | FAIL |
| ST-007 | API timeout cascade | `INC001` | Accepted | `INC003` | `hybrid_escalated` | `single` | — | 95% | incident `P1`, classification `P1` | FAIL |
| ST-008 | Kubernetes OOMKilled | Unsupported | Rejected | Unsupported, matched `INC004` | intake rejection | n/a | n/a | 84.2% | submission `P2` | PASS |
| ST-009 | Terraform state lock | Unsupported | Rejected | Unsupported, matched `INC004` | intake rejection | n/a | n/a | 80.9% | submission `P2` | PASS |
| ST-010 | Ambiguous / noisy intake | Unsupported | Rejected | Unsupported, matched `INC009` | intake rejection | n/a | n/a | 84.6% | submission `P3` | PASS |
| ST-011 | Prometheus-style structured alert | Structured alert should parse usefully | Rejected | Unsupported, matched `INC004` | intake rejection | n/a | n/a | 81.5% | submission `P1` | FAIL |
| ST-012 | Multi-symptom complex incident | Dominant family or explicit ambiguity | Accepted | `INC003` | `hybrid_escalated` | `single` | — | 58% | incident `P2`, classification `P1` | FAIL |

\* Classification family is correct, but severity consistency is not.

## Explicit verification summary

| Verification | Expected | Actual | Status |
|---|---|---|---|
| ST-001 → `INC002` | Must hold | Returned `INC003` | FAIL |
| ST-002 → `INC003` | Must hold | Returned `INC003` | PASS |
| ST-003 → `INC007` | Must hold | Rejected as unsupported, matched `INC010` | FAIL |
| ST-004 → `INC005` | Key regression fix | Returned `INC005` | PASS |
| ST-005 → `INC006` | TLS fix | Returned `INC006` | PASS |
| ST-006 → `INC004` | Cache-cardinality expectation | Rejected as unsupported `INC004` | FAIL |
| ST-007 → `INC001` | Timeout-cascade fix | Returned `INC003` | FAIL |
| ST-008 / ST-009 / ST-010 not accepted into specific families | Must stay bounded | All 3 rejected at intake | PASS |
| ST-011 Prometheus parsing | Should classify or gracefully parse usefully | Rejected as unsupported, matched `INC004` | FAIL |
| ST-012 ambiguity detection | Should choose dominant family or stay explicitly ambiguous | Returned `INC003`, `classification_type=single`, 58% confidence | FAIL |
| `classification_strategy` shows hybrid escalation | Should appear where deterministic path is weak | Present on `ST-007` and `ST-012` | PASS |
| No `P99` severities | Must hold | No `P99` observed | PASS |
| No artificial severity upshift | Must hold | `P3→P1` (`ST-004`), `P1→P0` (`ST-005`), `P2→P1` (`ST-012`) | FAIL |

## Guardian persistence — critical V8 test

All three decision-persistence checks passed cleanly.

| Incident | Submitted decision | Refetched `guardian.decision` | Refetched status | Verdict |
|---|---|---|---|---|
| ST-001 | `approve` | `approve` | `investigating` | PASS |
| ST-002 | `reject` | `reject` | `blocked_by_guardian` | PASS |
| ST-005 | `request_modification` | `request_modification` | `needs_modification` | PASS |

This is now one of the strongest operational surfaces in the product. The system is no longer contradicting itself after a Guardian write, which was a major trust blocker in earlier live runs.

## Supported-family scoring

There are two honest ways to score V8 because the raw-text contract was intentionally tightened before this run.

### 1. Prompt-expectation score (same Stratum expectations as prior runs)

- Supported-family exact-match score on `ST-001` through `ST-007`: **3/7 (43%)**
- Exact-match score across all 12 verification targets above: **6/12 (50%)**

### 2. Current six-family raw-text contract score

Under the currently shipped raw-text contract, `INC004` is intentionally outside supported intake, so `ST-006` is not a contract miss in the same way it was in earlier pilots.

- Current-contract supported-family score (`ST-001`, `ST-002`, `ST-003`, `ST-004`, `ST-005`, `ST-007`): **3/6 (50%)**

This is better-bounded than V7, but still below Stratum’s adoption threshold.

## Live reasoning / strategy observations

V8 finally shows mixed strategy behavior instead of “deterministic everywhere.”

Observed:

- `deterministic`: `ST-001`, `ST-002`, `ST-004`, `ST-005`
- `hybrid_escalated`: `ST-007`, `ST-012`
- intake rejection before context generation: `ST-003`, `ST-006`, `ST-008`, `ST-009`, `ST-010`, `ST-011`

One nuance worth calling out:

- `ST-001` returned `live_reasoning=false` with `degraded_mode=deterministic_fallback` even though the server key was available
- the other accepted contexts (`ST-002`, `ST-004`, `ST-005`, `ST-007`, `ST-012`) showed live reasoning active in the broader context payload

So V8 is closer to the intended hybrid path, but still not completely consistent incident-to-incident.

## Unsupported handling

This area improved meaningfully.

In V7, unsupported or weakly described platform incidents were often accepted and forced into specific families. In V8:

- `ST-008` (Kubernetes OOMKilled) was rejected
- `ST-009` (Terraform state lock) was rejected
- `ST-010` (ambiguous/noisy) was rejected

That is safer behavior for a bounded incident product.

But the rejection payloads still are not trustworthy enough for expert use because the fallback “matched family” and “general investigation” categories drift:

- `ST-008` matched `INC004` but returned deploy-style guidance
- `ST-006` matched `INC004` but returned CDN / caching guidance
- `ST-011` matched `INC004` but returned only generic investigation steps

So bounded rejection improved, but unsupported guidance quality is still inconsistent.

## Prometheus / structured alert handling

This remains a gap.

`ST-011` was rejected at intake instead of being classified into a supported operational family. For a platform team that routes Prometheus or PagerDuty-style alerts directly into triage, this is still below the bar.

Result:

- submission status: `400`
- matched unsupported family: `INC004`
- no useful structured parsing into timeout/deploy/queue/auth/TLS buckets

**Verdict:** FAIL

## Severity behavior

There are two separate findings here:

1. **The old `P99` bug remains fixed.**  
   No severity field surfaced as `P99`, `P95`, etc.

2. **Severity consistency is still not fixed end-to-end.**  
   The classification object still shifts severity upward on several incidents:

- `ST-004`: incident `P3` → classification `P1`
- `ST-005`: incident `P1` → classification `P0`
- `ST-012`: incident `P2` → classification `P1`

So if the requirement is “no percentile leakage,” V8 passes.  
If the requirement is “no artificial severity upshift,” V8 still fails.

## Comparison across all 8 Stratum runs

| Run | Mode | Retrieval / acceptance outcome | Supported-family accuracy | ST-002 | ST-004 | Guardian persistence | Severity state | NPS |
|---|---|---|---|---|---|---|---|---|
| V1 | Static baseline | 12/12 evaluated | 57% (4/7) | FAIL | FAIL | PASS | FAIL (`P99`) | 6/10 |
| V2 | Live reasoning v1 | 12/12 evaluated | 29% (2/7) | FAIL | FAIL | FAIL | FAIL (`P99`) | 5/10 |
| V3 | Post-fix standard engine | Partial retrieval | 60% (3/5 partial) | FAIL | FAIL | PASS | PASS | 6/10 |
| V4 | Phase 1/2 hybrid introduced | 4/12 retrieved | 75% (3/4 retrieved) | PARTIAL | UNKNOWN | PASS | PASS | 6/10 |
| V5 | API fields exposed | Partial supported retrieval | Inconclusive overall | TIMEOUT | PASS | FAIL | PASS | 5/10 |
| V6 | Endpoint/cache/rate-limit fixes | 8/9 supported retrieved | Strong but incomplete | PASS | PASS | FAIL | PASS | 7/10 |
| V7 | Post-persistence fix | 12/12 retrieved | 43% (3/7) | PASS | FAIL | PASS | PASS (`P99` fixed) | 6/10 |
| V8 | Post-six-fix hardening | 6 accepted / 6 rejected, all accepted retrieved | 43% (3/7 prompt), 50% (3/6 current contract) | PASS | PASS | PASS | PASS on `P99`, FAIL on upshift | 6/10 |

## What works well now

### 1. Bounded rejection is much safer

Rejecting `ST-008`, `ST-009`, and `ST-010` is a healthier product behavior than V7’s false precision.

### 2. Guardian workflow is trustworthy

The write path and read path now agree after:

- approve
- reject
- request_modification

That makes Guardian usable as a real operational gate again.

### 3. Kafka and TLS are materially better

The exact two verification targets that were called out as key V7 failures improved:

- `ST-004` → `INC005` now passes
- `ST-005` → `INC006` now passes

## What still does not work

### 1. Core supported-family misses remain

The current live system still misses several high-value Stratum patterns:

- DB pool exhaustion (`ST-001`) incorrectly becomes deploy regression
- auth dependency slowdown (`ST-003`) is rejected outright
- timeout cascade (`ST-007`) still becomes deploy regression

### 2. Severity consistency is still shaky

Even with `P99` gone, the classification layer still manufactures stronger severities than the intake / incident record on multiple cases.

### 3. Structured alert ingestion is still not ready

Prometheus-style input should be one of the easiest enterprise operational formats to support. In V8 it still fails at the intake boundary.

## Final verdict

### Verdict: **NOT READY FOR STAGING**

Why:

- boundedness is better
- Guardian persistence is good
- Kafka/TLS classification improved

But staging readiness still fails on three conditions that matter most to a Principal SRE:

1. the system still misses multiple core supported families
2. structured alert / Prometheus parsing is still not viable
3. severity consistency is still not trustworthy end-to-end

## Recommended next fixes before a staging recommendation

1. Fix `ST-001`, `ST-003`, and `ST-007` specifically and lock them down with regression cases.
2. Resolve classification-severity drift so the classification object cannot upshift independently of intake severity without an explicit, auditable rule.
3. Add a dedicated structured-alert normalization path for Prometheus / PagerDuty-style payloads before family selection.
4. Improve unsupported-family guidance so rejected incidents do not receive obviously mismatched fallback categories.

## Net Promoter Score

**Score:** 6/10

I would say NEXUS is now a more honest and operationally safer bounded system than it was in V7. That matters. But I still would not recommend staging it for a hybrid-cloud SRE team like Stratum until DB/auth/timeout-cascade reliability and structured-alert handling are materially better.
