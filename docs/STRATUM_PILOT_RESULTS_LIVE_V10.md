# STRATUM INFRASTRUCTURE — NEXUS PILOT REPORT (V10)
**Date:** 2026-06-26  
**Pilot type:** DevOps / Platform Engineering (B2B)  
**Evaluator:** Principal SRE, Stratum Infrastructure  
**Incidents submitted:** 12  
**Submission outcome:** 8 accepted, 4 rejected at intake  
**Incidents retrieved:** 8 of 8 accepted incidents  
**Mode:** Live reasoning enabled on production (`NEXUS_USE_OPENAI=1`)  
**Code baseline under test:** commit `776b90c`

## Executive summary

V10 is the first Stratum run that feels operationally coherent and classification-correct at the same time.

The most important result is that the recurring supported-family misses from V9 are fixed in live production:

- `ST-001` now lands on `INC002`
- `ST-003` now lands on `INC007`
- `ST-007` now lands on `INC001`
- `ST-011` now lands on `INC003` instead of being rejected

The other important result is that the trust surfaces stayed intact while accuracy improved:

- live reasoning was active on every accepted incident
- no `P99` / percentile severity leakage appeared
- no artificial severity upshift appeared
- Guardian approve / reject / request-modification all persisted correctly
- unsupported incidents remained bounded and were rejected instead of being silently accepted into unsupported families

Bottom line: V10 is the first Stratum run that clears the bar for a bounded staging pilot.

**NPS:** 8/10

Why 8/10:

- the supported-family contract now behaves credibly on the incident patterns Stratum actually cares about
- the operator truth surfaces are much more trustworthy than the earlier live runs
- but the unsupported guidance is still generic for Kubernetes / Terraform-style incidents, and the product remains a bounded wedge rather than a broad platform-SRE incident engine

## What changed versus V9

V10 materially improves the exact places where V9 was still weak:

1. **Supported-family classification moved from 3/7 to 7/7 on the current accepted Stratum corpus**
   - `ST-001`, `ST-003`, `ST-007`, and `ST-011` all flipped from fail to pass

2. **Prometheus-style structured alert intake is now operationally useful**
   - `ST-011` is accepted and classified as `INC003`

3. **The timeout-cascade / auth / DB-pool branches are no longer collapsing into deploy-regression**
   - this was the main recurring regression pattern in V8/V9

4. **Boundedness remains intact**
   - `ST-006`, `ST-008`, `ST-009`, and `ST-010` are still rejected at intake
   - no false confidence through over-acceptance

## Full classification table

| ID | Description | Expected | Submission result | NEXUS result | Strategy | Type | Confidence | Severity | Status |
|---|---|---|---|---|---|---|---:|---|---|
| ST-001 | DB connection pool | `INC002` | Accepted | `INC002` | `intake_canonical` | `single` | 93.7% | incident `P1`, classification `P1` | PASS |
| ST-002 | Deploy regression / Go panic | `INC003` | Accepted | `INC003` | `intake_canonical` | `single` | 92.4% | incident `P1`, classification `P1` | PASS |
| ST-003 | Auth / SSO dependency | `INC007` | Accepted | `INC007` | `intake_canonical` | `single` | 88.4% | incident `P3`, classification `P3` | PASS |
| ST-004 | Kafka consumer lag | `INC005` | Accepted | `INC005` | `intake_canonical` | `single` | 78.0% | incident `P3`, classification `P3` | PASS |
| ST-005 | TLS certificate expiry | `INC006` | Accepted | `INC006` | `intake_canonical` | `single` | 78.0% | incident `P1`, classification `P1` | PASS |
| ST-006 | Redis cardinality / cache explosion | `INC004` (catalogued but outside current raw-text contract) | Rejected | Unsupported, matched `INC004` | intake rejection | n/a | — | submission `P2` | PASS* |
| ST-007 | API timeout cascade | `INC001` | Accepted | `INC001` | `intake_canonical` | `single` | 83.5% | incident `P1`, classification `P1` | PASS |
| ST-008 | Kubernetes OOMKilled | Unsupported | Rejected | Unsupported, matched `INC004` | intake rejection | n/a | — | submission `P2` | PASS |
| ST-009 | Terraform state lock | Unsupported | Rejected | Unsupported, matched `INC004` | intake rejection | n/a | — | submission `P2` | PASS |
| ST-010 | Ambiguous / noisy intake | Unsupported | Rejected | Unsupported, matched `INC008` | intake rejection | n/a | — | submission `P3` | PASS |
| ST-011 | Prometheus-style structured alert | `INC003` | Accepted | `INC003` | `intake_canonical` | `single` | 86.5% | incident `P1`, classification `P1` | PASS |
| ST-012 | Multi-symptom complex incident | Honest ambiguity or dominant-family choice | Accepted | `INC005` | `intake_canonical` | `ambiguous` | 58.0% | incident `P2`, classification `P2` | PASS |

\* Under the shipped raw-text contract, `ST-006` is intentionally outside supported intake and should be rejected rather than accepted with incomplete runtime coverage.

## Explicit verification summary

| Verification | Expected | Actual | Status |
|---|---|---|---|
| ST-001 → `INC002` | Must hold | Returned `INC002` | PASS |
| ST-002 → `INC003` | Must hold | Returned `INC003` | PASS |
| ST-003 → `INC007` | Must hold | Returned `INC007` | PASS |
| ST-004 → `INC005` | Kafka fix must hold | Returned `INC005` | PASS |
| ST-005 → `INC006` | TLS fix must hold | Returned `INC006` | PASS |
| ST-006 bounded handling | Must stay outside current raw-text contract | Rejected as unsupported `INC004` | PASS |
| ST-007 → `INC001` | Timeout-cascade fix must hold | Returned `INC001` | PASS |
| ST-008 / ST-009 / ST-010 not accepted into supported family | Must stay bounded | All 3 rejected at intake | PASS |
| ST-011 Prometheus parsing | Should classify usefully | Accepted and classified as `INC003` | PASS |
| ST-012 ambiguity handling | Should stay honestly mixed or choose clearly | Returned `classification_type=ambiguous`, top family `INC005`, 3 candidates | PASS |
| Live reasoning enabled | Must be on for accepted contexts | `live_reasoning=true` on all 8 accepted cases | PASS |
| No `P99` severities | Must hold | No percentile severity surfaced | PASS |
| No artificial severity upshift | Must hold | Incident and classification severities matched on all accepted cases | PASS |
| Guardian persistence | Must hold on approve / reject / request-modification | All 3 persisted correctly | PASS |

## Guardian persistence — critical operational test

All three Guardian decisions persisted correctly again in V10.

| Incident | Submitted decision | Refetched `guardian.decision` | Refetched `/status` value | Refetched `execution_result` | Verdict |
|---|---|---|---|---|---|
| ST-001 | `approve` | `approve` | `investigating` | `approved` | PASS |
| ST-002 | `reject` | `reject` | `blocked_by_guardian` | `blocked` | PASS |
| ST-005 | `request_modification` | `request_modification` | `needs_modification` | `needs_modification` | PASS |

This is now good enough for a bounded operator workflow. The split truth problem that used to show up between write, `/context`, and `/status` did not reproduce in this run.

## Live reasoning observations

Every accepted context showed:

- `classification_strategy=intake_canonical`
- `structured_result.live_reasoning=true`
- no `degraded_mode`
- no `degraded_agents`
- no surfaced `agent_failures`

That means the live path stayed active, but the canonical intake classification remained the visible truth surface. This is the safer design for a pilot like Stratum because it lets live reasoning enrich without silently re-routing the accepted family downstream.

## Unsupported handling

Unsupported cases remained bounded:

- `ST-006` → rejected, matched `INC004`
- `ST-008` → rejected, matched `INC004`
- `ST-009` → rejected, matched `INC004`
- `ST-010` → rejected, matched `INC008`

That is operationally preferable to false acceptance, but the domain guidance is still generic:

- Kubernetes OOMKill and Terraform state-lock incidents still inherit generic cache / memory style investigation guidance rather than K8s / IaC-native guidance
- noisy ambiguous intake (`ST-010`) now matched `INC008` rather than `INC009`, which is still acceptable for a rejected bounded case but shows that unsupported-family matching is approximate rather than semantically rich

## Prometheus / structured alert handling

This area is now materially improved.

`ST-011` was accepted and classified as `INC003` with:

- `classification_strategy=intake_canonical`
- `classification_type=single`
- `severity=P1`

That is the first Stratum live run where machine-generated alert format feels viable as direct intake instead of requiring human rewrite first.

**Verdict:** PASS

## Comparison across all 10 Stratum runs

| Run | Mode | Retrieval / acceptance outcome | Supported-family accuracy | ST-002 | ST-004 | Guardian persistence | Severity state | NPS |
|---|---|---|---|---|---|---|---|---|
| V1 | Static baseline | 12/12 evaluated | 57% (4/7) | FAIL | FAIL | PASS | FAIL (`P99`) | 6/10 |
| V2 | Live reasoning v1 | 12/12 evaluated | 29% (2/7) | FAIL | FAIL | FAIL | FAIL (`P99`) | 5/10 |
| V3 | Post-fix standard engine | Partial retrieval | 60% (3/5 partial) | FAIL | FAIL | PASS | PASS | 6/10 |
| V4 | Phase 1/2 hybrid introduced | 4/12 retrieved | 75% (3/4 retrieved) | PARTIAL | UNKNOWN | PASS | PASS | 6/10 |
| V5 | API fields exposed | Partial supported retrieval | Inconclusive overall | TIMEOUT | PASS | FAIL | PASS | 5/10 |
| V6 | Endpoint / cache / rate-limit fixes | 8/9 supported retrieved | Strong but incomplete | PASS | PASS | FAIL | PASS | 7/10 |
| V7 | Post-persistence fix | 12/12 retrieved | 43% (3/7) | PASS | FAIL | PASS | PASS (`P99` fixed) | 6/10 |
| V8 | Post-six-fix hardening | 6 accepted / 6 rejected, all accepted retrieved | 43% (3/7 prompt), 50% (3/6 contract) | PASS | PASS | PASS | PASS on `P99`, FAIL on upshift | 6/10 |
| V9 | Post-structural stabilization | 6 accepted / 6 rejected, all accepted retrieved | 43% (3/7 prompt), 50% (3/6 contract) | PASS | PASS | PASS | PASS on `P99` and upshift | 6/10 |
| **V10** | **Post-intake classification repair** | **8 accepted / 4 rejected, all accepted retrieved** | **100% (7/7 accepted supported cases), plus 4/4 bounded rejections** | **PASS** | **PASS** | **PASS** | **PASS** | **8/10** |

## What is genuinely fixed now

1. **DB pool, auth slowdown, timeout cascade, and Prometheus alert intake**
   - the most stubborn recurring Stratum misses are now routed correctly

2. **Severity trust surface**
   - no percentile contamination
   - no artificial upshift
   - incident and classification severities stayed aligned

3. **Guardian persistence**
   - approve / reject / request-modification all persisted correctly in production

4. **Live reasoning truth posture**
   - live reasoning stayed on
   - no degraded mode surfaced
   - canonical intake truth remained stable through `/context`

## Remaining gaps

V10 is strong enough for a bounded staging pilot, but not “solve every platform incident” strong.

The main remaining gaps are:

1. **Unsupported-family guidance is still too generic for real K8s / IaC incidents**
   - `ST-008` and `ST-009` are safely rejected, but the investigation guidance is not yet expert-level for those domains

2. **Unsupported-family matching is still fuzzy**
   - `ST-010` matched `INC008` in this run; that is acceptable for a rejected bounded case, but it still shows semantic looseness outside the supported contract

3. **ST-012 is appropriately ambiguous, but still not a deep multi-root-cause synthesis**
   - it now behaves honestly rather than overconfidently
   - that is a trust win, but there is still room for richer cross-family decomposition

## Principal SRE verdict

If I were evaluating NEXUS as Jordan Mills, Principal SRE at Stratum Infrastructure:

- I would now approve a **bounded staging pilot**
- I would not yet approve broad production rollout across all platform incident types

What changed my view from V9:

- the system now gets the core supported-family Stratum patterns right
- it does so with live reasoning on, not hidden deterministic fallback
- the operator workflow is trustworthy enough to trial with real humans in the loop

What would still stop me from full production rollout:

- unsupported Kubernetes / Terraform / IaC cases are still handled safely, but not expertly
- the product remains intentionally narrow, which is fine as long as that boundary is explicit to buyers

## Net Promoter Score

**Score:** 8/10

**Would I recommend NEXUS to another Principal SRE at a platform company?**

Yes — with conditions. I would recommend it for a bounded pilot focused on the currently supported outage families and live human-in-the-loop triage. I would not yet recommend it as a general-purpose SRE incident brain for Kubernetes, Terraform, or broad infrastructure failure modes outside the current raw-text contract.

## Final verdict

**STAGING READY — for the bounded Stratum contract**

Conditions:

1. keep the current supported-family boundary explicit in buyer-facing materials
2. do not market unsupported Kubernetes / Terraform coverage as first-class yet
3. keep the Stratum corpus in CI and treat any regression on `ST-001`, `ST-003`, `ST-007`, or `ST-011` as a release blocker
