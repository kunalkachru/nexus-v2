# STRATUM INFRASTRUCTURE — NEXUS PILOT REPORT (LIVE REASONING)
**Date:** 2026-06-25
**Pilot type:** DevOps/Platform Engineering (B2B)
**Evaluator:** Principal SRE, Stratum Infrastructure
**Incidents submitted:** 12
**Mode:** Live reasoning enabled (`NEXUS_USE_OPENAI=1`, server-side GPT-4o)
**Baseline for comparison:** Static run — NPS 6/10, supported-family accuracy 57%

## PRE-PILOT HYPOTHESIS vs REALITY
Live reasoning did improve the *quality* of many explanations. When GPT-4o engaged, root-cause narratives and runbooks were noticeably more specific and more operator-usable than the static pass.

But the more important pilot outcome is that explanation quality and product reliability are not the same thing. In this fresh run, supported-family accuracy actually got worse, live-mode activation was inconsistent across incidents, severity parsing still produced `P99`, and the Guardian read path still contradicted stored reject/request-modification decisions.

## EXECUTIVE SUMMARY
This live-reasoning run makes NEXUS feel smarter, but it does not make it trustworthy enough for Stratum Infra. The writing improved; the front-door incident classification and state-truth surfaces did not.

**NPS:** 5/10 — lower than the static run, because the richer GPT-4o language raises expectations that the underlying classification and Guardian truth surfaces do not consistently meet.

## COMPARISON VS STATIC RUN
| Dimension | Static run | Live reasoning run | Change |
|---|---:|---:|---|
| Supported-family accuracy | 57% (4/7) | 29% (2/7) | Worse |
| NPS | 6/10 | 5/10 | Worse |
| Severity parsing | Incorrect `P99` severities | Incorrect `P99` severities still present | No improvement |
| Live reasoning availability | N/A | Active on 8/12 incidents | Inconsistent |
| Runbook specificity | Mixed / often generic | Sharper and more concrete when live | Improved |
| Kubernetes handling | Generic fallback | Slightly more specific, still not Kubernetes-native | Minor improvement only |
| Terraform handling | Generic fallback | More specific causal narrative on ST-009 | Partial improvement |
| Guardian truth surface | Worked in static run | Context can still show `approve/executed` after reject or modification | Regressed |

## CLASSIFICATION ACCURACY TABLE
| ID | Description | Expected | Live NEXUS Result | Confidence | Correct? |
|---|---|---|---|---:|---|
| ST-001 | DB connection pool | INC002 | Timeout cascade / retry amplification | 95% | No |
| ST-002 | Deploy regression with Go panic | INC003 | Production incident investigation | 72% | No |
| ST-003 | Auth/SSO dependency | INC007 | Timeout cascade / retry amplification | 78% | No |
| ST-004 | Kafka consumer lag | INC005 | Production incident investigation | 70% | No |
| ST-005 | TLS certificate expiry | INC006 | Certificate expiry / trust boundary outage | 72% | Yes |
| ST-006 | Cache cardinality explosion | INC004 | Production incident investigation | 58% | No |
| ST-007 | API timeout cascade | INC001 | Timeout cascade / retry amplification | 78% | Yes |
| ST-008 | Kubernetes OOMKilled | Unsupported | Memory leak / runtime degradation | 78% | Partial |
| ST-009 | Terraform state lock | Unsupported | Memory leak / runtime degradation | 58% | Partial |
| ST-010 | Ambiguous/noisy | Unsupported | Production incident investigation | 58% | Partial |
| ST-011 | Prometheus alert format | Structured alert parsing | Timeout cascade / retry amplification | 78% | Partial |
| ST-012 | Multi-symptom complex | Dominant family or explicit ambiguity | Auth dependency slowdown / token validation failures | 72% | Partial |

**Supported-family score:** 2/7 (29%)

**Strict score across all 12:** 2/12 exact family matches

**Unsupported/edge handling:** 5/5 graceful, but still not domain-native enough for platform engineering teams.

## LIVE-REASONING CONFIRMATION
Live reasoning was definitely enabled at the deployment level and on the test probe incident:
- `NEXUS_USE_OPENAI=1` confirmed from the running Docker container
- Fresh probe incident returned `live_reasoning: true` and `llm_access.mode: live`
- Probe runbook reasoning explicitly said: `Generated bash runbook ... using gpt-4o`

However, the fresh pilot run showed **inconsistent live activation**:
- Live incidents: ST-001, ST-003, ST-004, ST-007, ST-008, ST-009, ST-010, ST-011
- Deterministic incidents: ST-002, ST-005, ST-006, ST-012

That inconsistency itself is a product problem. An evaluator cannot easily tell when the system silently stopped using live reasoning on a subset of fresh incidents.

## SEVERITY PARSING
No improvement. The same trust issue remains.

Incidents still emitted `P99` as a severity label:
- ST-003
- ST-007
- ST-012

For a real SRE team, this is still a hard stop. Percentile latency notation must not leak into incident severity.

## CLASSIFICATION QUALITY
This is the biggest disappointment of the live run. GPT-4o made the explanations more detailed, but it did **not** improve the actual family-selection quality. In this fresh run it got materially worse than the static baseline.

Two examples:
- **ST-001** clearly described a DB connection pool incident, but live reasoning classified it as **Timeout cascade / retry amplification**.
- **ST-003** clearly described auth/SSO degradation, but live reasoning again classified it as **Timeout cascade / retry amplification**.

So the model sometimes understood the narrative but still anchored it to the wrong family.

## KUBERNETES / TERRAFORM HANDLING
### Kubernetes
Only minor improvement.
- Static: ST-008 fell into generic production investigation
- Live: ST-008 became **Memory leak / runtime degradation** with a more concrete causal story
- But it still did not become Kubernetes-native: no real namespace-capacity, scheduler, or pod-eviction investigation pattern

### Terraform
Partial improvement.
- Static: ST-009 was generic
- Live: ST-009 connected the stale lock to an OOMKilled `terraform-executor` and suggested releasing the lock
- That is more useful, but it is still not a true Terraform family or Terraform-aware workflow

So live reasoning helped *narrative specificity* more than *domain modeling*.

## GUARDIAN WORKFLOW EVALUATION
The Guardian POST path still changes stored incident status correctly, but the live incident context remains untrustworthy after non-approve decisions.

Submitted decisions in this fresh run:
- ST-001 → approve
- ST-002 → reject
- ST-005 → request modification

Observed results:
- ST-002 status became `blocked_by_guardian`
- ST-005 status became `needs_modification`

But the live context still showed:
- `guardian.decision = approve`
- `structured_result.safety_decision = approve`
- `execution_status = executed`

for both ST-002 and ST-005.

That is a major trust bug. An operator cannot rely on a system that visually reports approval/execution after they explicitly rejected or sent a runbook back for modification.

## WHAT IMPROVED WITH LIVE REASONING
- Root-cause narratives became more concrete when live mode actually engaged.
- Runbooks were much less generic and more like real first-response drafts.
- Terraform-like incidents got somewhat more actionable language.
- The system still fails soft instead of crashing on unsupported/edge cases.

## WHAT DID NOT IMPROVE
- Severity parsing
- Supported-family classification accuracy
- Structured-alert parsing
- Kubernetes-native investigation depth
- Consistency of live-mode activation
- Guardian read-path truthfulness

## TOP 3 GAPS AFTER THE LIVE RUN
1. **Fix severity parsing and Guardian truthfulness immediately.** These are hard trust blockers.
2. **Separate explanation quality from family selection quality.** GPT-4o currently makes the answer sound better without making routing reliably better.
3. **Add first-class platform families / parsers** for Kubernetes resource failures, Terraform state incidents, and structured Prometheus-style alerts.

## RESPONSE TIME
- Live-mode response time test: 522.23 ms

That is acceptable for pilot usage, but response speed does not compensate for classification/trust issues.

## FINAL VERDICT
**DO NOT ADOPT**

The live GPT-4o deployment improved language quality but worsened the supported-family score in this fresh pilot run and exposed a serious Guardian truth-surface issue. For Stratum Infra, that moves the product in the wrong direction from an adoption standpoint.
