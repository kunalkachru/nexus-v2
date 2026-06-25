# STRATUM INFRASTRUCTURE — NEXUS PILOT REPORT
**Date:** 2026-06-25
**Pilot type:** DevOps/Platform Engineering (B2B)
**Evaluator:** Principal SRE, Stratum Infrastructure
**Incidents submitted:** 12
**Previous pilots:** Kartik Commerce (B2C, NPS 8/10), Meridian Analytics (B2B SaaS, NPS 8/10)

## PRE-PILOT HYPOTHESIS vs REALITY
The pre-pilot hypothesis was mostly right. NEXUS performed well on a subset of bounded incident shapes where the symptom language closely matched its supported wedge: DB pool exhaustion, auth dependency slowdown, TLS/trust-boundary outage, and timeout cascade. It also delivered a readable agent-by-agent narrative and kept the human approval boundary explicit, which is exactly what an enterprise SRE team wants.

The concerns were also confirmed. Platform-specific cases drifted quickly into a generic “Production incident investigation” bucket, structured Prometheus-style alerts were accepted but not semantically parsed, and mixed-symptom incidents were overfit to one symptom rather than called ambiguous. The hosted pilot remained largely scaffold/inference-first, so the workflow feels credible but not yet strong enough for high-trust platform operations.

## EXECUTIVE SUMMARY
NEXUS is promising as a triage accelerator for bounded application/platform outage families, but it is not yet a strong enough fit for a hybrid-cloud platform engineering team like Stratum Infra. The workflow is usable and the Guardian gate is real, but classification breadth and platform-specific specificity miss our success bar.

**NPS:** 6/10 — I would not recommend it yet to another Principal SRE at a platform engineering company without additional family coverage and better structured-alert / Kubernetes / Terraform understanding.

## CLASSIFICATION ACCURACY TABLE
| ID | Description | Expected | NEXUS Result | Confidence | Correct? |
|---|---|---|---|---:|---|
| ST-001 | DB connection pool | INC002 | Database pool exhaustion / session leak | 86% | Yes |
| ST-002 | Deploy regression with Go panic | INC003 | Production incident investigation | 72% | No |
| ST-003 | Auth/SSO dependency | INC007 | Auth dependency slowdown / token validation failures | 72% | Yes |
| ST-004 | Kafka consumer lag | INC005 | Production incident investigation | 72% | No |
| ST-005 | TLS certificate expiry | INC006 | Certificate expiry / trust boundary outage | 72% | Yes |
| ST-006 | Cache cardinality explosion | INC004 | Production incident investigation | 58% | No |
| ST-007 | API timeout cascade | INC001 | Timeout cascade / retry amplification | 72% | Yes |
| ST-008 | Kubernetes OOMKilled | Unsupported | Production incident investigation | 72% | Partial |
| ST-009 | Terraform state lock | Unsupported | Production incident investigation | 58% | Partial |
| ST-010 | Ambiguous/noisy | Unsupported | Production incident investigation | 58% | Partial |
| ST-011 | Prometheus alert format | Structured alert parsing | Production incident investigation | 72% | Partial |
| ST-012 | Multi-symptom complex | Dominant family or explicit ambiguity | Auth dependency slowdown / token validation failures | 72% | Partial |

**Strict classification score:** 4/12 (33%)

**Supported-family score:** 4/7 (57%)

**Unsupported/edge handling:** 5/5 incidents were handled gracefully without crash or silent failure, but most were routed into a generic bucket rather than meaningfully classified.

## COMPARISON VS PREVIOUS PILOTS
| Dimension | Kartik (B2C) | Meridian (B2B SaaS) | Stratum (DevOps) |
|---|---|---|---|
| Classification accuracy | 100% | 100% | 57% on supported Stratum cases |
| NPS | 8/10 | 8/10 | 6/10 |
| Stack fit | Good | Good | Mixed / below threshold |
| Top gap | Manual intake | None critical | Platform-specific incident coverage |

## DEVOPS/PLATFORM ENGINEERING SPECIFIC FINDINGS
- **Kubernetes vocabulary handling:** OOMKilled, cluster capacity pressure, and namespace-level blast radius did not trigger Kubernetes-aware investigation; they collapsed into generic production routing.
- **Terraform/IaC incident patterns:** Terraform state locking was handled safely but generically, with no awareness of stale DynamoDB lock rows, S3 lock ownership, or executor crash recovery.
- **Prometheus alert format parsing:** Machine-generated alert fields were accepted as text but not parsed into a domain-aware diagnosis.
- **Multi-symptom classification:** When several plausible families appeared together, NEXUS chose one family rather than explicitly surfacing “ambiguous multi-family incident” as a first-class outcome.
- **Platform-level vs tenant-level distinction:** The current output talks about production impact, but it does not clearly reason about shared-platform impact versus isolated tenant/namespace failures.
- **Severity parsing bug:** Multiple incidents with “p99 latency” text were assigned severity `P99`, which is a real trust issue for an SRE audience.

## GUARDIAN WORKFLOW EVALUATION
The Guardian workflow is one of the stronger parts of the product. I submitted three real decisions and all three persisted correctly:

- **ST-001:** approve → persisted as `approve`
- **ST-002:** reject → status changed to `blocked_by_guardian`
- **ST-005:** request modification → status changed to `needs_modification`

That feels production-shaped. It supports actual operator judgment instead of pretending the model should decide unilaterally. The weakness is upstream: when the diagnosis/runbook is generic, Guardian becomes a review shell around weak content.

## WHAT WORKS EXCEPTIONALLY WELL
- The **operator narrative** is strong. NEXUS makes the handoff chain visible instead of dumping a single blob of AI text.
- The **Guardian gate** is real and auditable. The decision states changed correctly and persisted after review.
- For bounded cases like ST-001 and ST-007, the system gives a credible first-pass route into the incident.
- The product **fails soft**, not hard. Even unsupported/edge cases stayed within a structured workflow instead of erroring out.

## WHAT DOESN'T WORK
- **Platform-specific cases over-collapse to generic routing.** ST-002, ST-004, ST-006, ST-008, ST-009, ST-010, and ST-011 all showed variants of “Production incident investigation” instead of a meaningful family.
- **Severity parsing is unsafe.** ST-003, ST-007, and ST-012 were tagged `P99`, which strongly suggests latency percentile tokens are leaking into severity extraction.
- **Structured alerts are not truly structured yet.** ST-011 accepted the alert string but did not reason over the fields as a Prometheus alert.
- **Multi-symptom ambiguity is not surfaced honestly.** ST-012 was forced into auth slowdown instead of being called mixed-signal / ambiguous.
- **Trace depth is inconsistent.** Unsupported or generic incidents often devolve to “Wait for REPLICA” or ownership validation instead of giving a meaningful next debugging step.

## TOP 3 GAPS FOR DEVOPS/PLATFORM ENGINEERING COMPANIES
1. **Native platform incident families** for Kubernetes resource pressure, Terraform/IaC failures, and observability-cardinality/cache explosions.
2. **Structured alert parsing** for Prometheus/PagerDuty/Datadog-style payloads, including field-aware normalization instead of raw-text fallback.
3. **Ambiguity-aware classification** that can explicitly say “this spans multiple families” rather than overfitting one symptom.

## UNSUPPORTED INCIDENT HANDLING
Unsupported incidents were handled gracefully in the sense that the product kept them inside a structured case workflow. That matters. There were no crashes, empty payloads, or silent failures.

However, the fallback guidance was usually too generic to be truly helpful to a platform team. “Validate ownership and confirm incident scope” is fine as a safety rail, but it is not enough for Kubernetes OOM or Terraform lock incidents where the first useful steps are already well-known and domain-specific.

## PROMETHEUS/STRUCTURED ALERT FORMAT
This is a gap today. ST-011 proved that NEXUS can ingest a Prometheus-style alert blob, but it did not translate the fields into a meaningful alert-aware diagnosis. For a DevOps organization that routes machine-generated alerts into the system, this is one of the highest-priority improvements.

## PRODUCTION READINESS FOR STRATUM
I would **not** deploy NEXUS as a production-facing first-line incident classifier for Stratum today.

Conditions required before production reconsideration:
1. Fix severity parsing so percentile strings like `p99` can never become severity labels.
2. Add platform-native families or sub-families for Kubernetes, Terraform, and observability-cardinality incidents.
3. Add real structured-alert parsing and preserve alert metadata semantically.
4. Add an explicit ambiguous/multi-family outcome instead of forcing one family.
5. Increase specificity of TRACE/FORGE output for unsupported-but-common platform incidents.

**Timeline to production readiness for Stratum:** roughly 4–8 weeks if the product team focuses on the three gaps above and validates them in a follow-up pilot.

## NET PROMOTER SCORE
**Score:** 6/10

**Would you recommend NEXUS to another Principal SRE at a DevOps/platform company?** Not yet. I can see the product direction and I think the workflow design is stronger than many AI-incident tools I have tested, but the current family coverage and platform specificity are not yet enough for a hybrid-cloud platform team to rely on it at the front door of incident triage.

## RECOMMENDED NEXT FEATURES FOR NEXUS TEAM
1. Add **Kubernetes / Terraform / observability** incident-family support with first-class terminology and mitigation playbooks.
2. Build **structured alert normalization** for Prometheus/PagerDuty payloads so machine-generated alerts become rich incident context, not just pasted strings.
3. Introduce **ambiguity-aware routing** with explicit multi-family and low-confidence states, plus stronger operator messaging around uncertainty.

## FINAL VERDICT
**DO NOT ADOPT**

**Conditions for re-evaluation:**
- Fix severity parsing (`P99` bug)
- Improve platform-specific family coverage
- Parse structured alerts semantically
- Surface ambiguity honestly on multi-symptom incidents
- Re-run a focused platform-engineering pilot after those changes
