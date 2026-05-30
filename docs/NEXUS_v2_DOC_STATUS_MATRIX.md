# NEXUS v2 Documentation Status Matrix

Current as of 2026-05-30.

Legend:
- `Done` means implemented in the repo and verified with tests/browser checks.
- `Partial` means the doc is directionally correct, but the repo only covers part of the intended scope.
- `Pending` means the section still describes work that is not yet in the repo.

## Overall Read

| Doc | Overall status | Notes |
|---|---|---|
| [docs/superpowers/specs/2026-05-29-enterprise-ui-product-roadmap.md](superpowers/specs/2026-05-29-enterprise-ui-product-roadmap.md) | Done / Partial | UI-first roadmap is complete; backend-reality phase is only partially complete. |
| [docs/superpowers/specs/2026-05-28-enterprise-workflow-ui-design.md](superpowers/specs/2026-05-28-enterprise-workflow-ui-design.md) | Done / Partial | UI surfaces are done; backend architecture is still mostly aspirational. |
| [docs/NEXUS_v2_PHASE2_ROADMAP.md](NEXUS_v2_PHASE2_ROADMAP.md) | Partial | Week 1 intake normalization is mostly real; Week 2-4 remain incomplete for true enterprise integrations. |
| [design-docs/NEXUS_v2_Design_Document.md](../design-docs/NEXUS_v2_Design_Document.md) | Partial | Real incident integration is only partially realized. |
| [design-docs/NEXUS_v2_ENTERPRISE_SPECIFICATION.md](../design-docs/NEXUS_v2_ENTERPRISE_SPECIFICATION.md) | Partial | The UI and demo contracts are in place, but the live enterprise pipeline is not. |
| [design-docs/NEXUS_v2_Master_Product_Document.md](../design-docs/NEXUS_v2_Master_Product_Document.md) | Partial / Pending | Vision and narrative are intact; business, legal, and scale sections are mostly not implemented in code. |
| [docs/OPERATIONS.md](OPERATIONS.md) | Partial | Local/Docker flow is valid; demo and product mode operations plus recovery are not fully hardened. |
| [docs/DEMO_CHEAT_SHEET.md](DEMO_CHEAT_SHEET.md) | Done | Quick live demo reference for fast navigation through the product. |
| [docs/LIVE_DEMO_SPEAKER_NOTES.md](LIVE_DEMO_SPEAKER_NOTES.md) | Done | Screen-by-screen speaking notes for live demos and walkthroughs. |
| [docs/DEMO_WALKTHROUGH.md](DEMO_WALKTHROUGH.md) | Done | This is the current screen-by-screen manual validation and demo script. |
| [docs/PRESENTATION_PACK.md](PRESENTATION_PACK.md) | Done | Single index for the demo walkthrough, speaker notes, and presenter deck. |
| [docs/AGENT_MODEL_MATRIX.md](AGENT_MODEL_MATRIX.md) | Done | Compact current-state matrix for the four agents, their LLM fit, and the remaining gaps. |

## Priority Backlog

If you want the shortest path to the next meaningful product step, use this order:

1. [Real observability ingestion and evidence fusion](NEXUS_v2_PRIORITY_BACKLOG.md#1-real-observability-ingestion-and-evidence-fusion)
2. [GUARDIAN execution policy and runbook governance](NEXUS_v2_PRIORITY_BACKLOG.md#2-guardian-execution-policy-and-runbook-governance)
3. [Production persistence and durable artifacts](NEXUS_v2_PRIORITY_BACKLOG.md#3-production-persistence-and-durable-artifacts)
4. [Auth, tenant, and deployment hardening](NEXUS_v2_PRIORITY_BACKLOG.md#4-auth-tenant-and-deployment-hardening)
5. [Further backend service decomposition and operational cleanup](NEXUS_v2_PRIORITY_BACKLOG.md#5-further-backend-service-decomposition-and-operational-cleanup)
6. [Docs and source-of-truth maintenance](NEXUS_v2_PRIORITY_BACKLOG.md#6-docs-and-source-of-truth-maintenance)

## Section Matrix

### 1) `docs/superpowers/specs/2026-05-29-enterprise-ui-product-roadmap.md`

| Section | Status | Notes |
|---|---|---|
| Objective | Done | The repo now reads as an enterprise product from the UX-first angle. |
| Guiding Principles | Done | Queue-first, clear narrative, and product feel are reflected in the UI. |
| Priority Order | Done | The shipped work follows the roadmap order closely. |
| Workstream 1: Product Shell And Navigation | Done | Shared shell, nav order, and active state are in place. |
| Workstream 2: Queue Experience | Done | Queue is the landing page and behaves like an operational entry point. |
| Workstream 3: Incident Console | Done | Workflow timeline, evidence, and agent narrative are present. |
| Workstream 4: Input Channels | Done | Webhook, manual, Slack, stream, and batch paths are represented. |
| Workstream 5: History And Replay | Done / Partial | Archive and replay surfaces exist; replay is still a deterministic launch path rather than a true replay engine. |
| Workstream 6: Training Lab | Done / Partial | Training UI is strong; backend data is still largely fixture-driven with live incident overlays. |
| Workstream 7: Settings And Trust | Done / Partial | Trust and posture are visible; production-grade controls are not complete. |
| Workstream 8: Visual Polish And Product Feel | Done | Visual hierarchy and motion are materially improved. |
| Near-Term Execution Sequence | Done | Sequence has been followed in the implementation. |
| What Not To Do Yet | Partial | The UI-first guidance is still useful, but backend realism has already started. |
| Stakeholder Roadmap Summary - Phase 1 | Done | Enterprise feel-first is achieved. |
| Stakeholder Roadmap Summary - Phase 2 | Partial | Thin backend seams exist; full enterprise backend reality is still pending. |
| Product Outcome | Partial | The product feels enterprise-grade, but deeper integrations are still missing. |

### 3) `docs/NEXUS_v2_PHASE2_ROADMAP.md`

| Section | Status | Notes |
|---|---|---|
| Week 1: Ingestion And Data Normalization | Partial | Multi-channel intake normalization is present, but live Prometheus/Datadog integrations are still not real. |
| Week 2: Correlation And Evidence Retrieval | Partial | Evidence presentation exists; ELK and deployment join logic are not real integrations yet. |
| Week 3: Runbook Matching And Safety Policy | Partial | Guardrails and execution narration exist; real runbook indexing and policy registry do not. |
| Week 4: UX, Validation, And Operational Readiness | Partial | Validation and dashboard UX are good; real operational readiness tasks remain. |
| Data Sources Needed | Pending | The listed external systems are not wired up in the repo. |
| Agent Integration Points | Partial | SENTINEL is closest to real, PRISM/FORGE/GUARDIAN are still partially simulated. |
| Success Metrics | Partial | Some metrics are demonstrable locally, but enterprise-scale targets remain aspirational. |
| Team And Resources Needed | Pending | Planning only; not a product feature. |

### 4) `design-docs/NEXUS_v2_Design_Document.md`

| Section | Status | Notes |
|---|---|---|
| Purpose | Done | The purpose matches the current repo story. |
| Current Architecture | Partial | The app shell is there, but some backend integration depth is still missing. |
| Phase 2: Real Incident Integration | Partial | The repo covers the demo path; the full phase-2 vision is not complete. |
| Objective | Done | The objective aligns with the current build direction. |
| SENTINEL: Real Alert Parsing From Prometheus and Datadog | Partial | Normalization exists; real upstream integrations do not. |
| PRISM: Log Correlation Through ELK Stack | Pending | No real ELK-backed log correlation service yet. |
| FORGE: Matching Against Real Runbook Templates | Partial | Replay/runbook story exists; real template ranking is not wired to a repository. |
| GUARDIAN: Safety Policy Enforcement | Partial | Safety review surfaces exist; durable policy registry and execution gating are incomplete. |
| Production Dependencies | Pending | The required external systems are not integrated. |
| Success Metrics For Phase 2 | Partial | Demo-level metrics are visible; production success metrics are not yet provable. |
| Phase 2 Deliverables | Partial | Core UI and thin APIs are done; enterprise backend parity is not. |

### 5) `design-docs/NEXUS_v2_ENTERPRISE_SPECIFICATION.md`

| Section | Status | Notes |
|---|---|---|
| 1. Executive Overview | Done | The enterprise framing matches the current product story. |
| 2. Input Channel Architecture | Partial | All channels are visible and normalized; external integrations are not production-grade. |
| 3. Log Ingestion Pipeline | Pending | No real ELK/Loki/Kafka/Kinesis pipeline is implemented. |
| 4. Agent Job Definitions & Contributions | Partial | The four-agent narrative is strong; live contribution sources are still thin. |
| 5. UI/UX Specifications | Done | Queue, incident, and supporting pages are represented in the shell. |
| 6. Data Models | Partial | The Pydantic models exist, but the spec is broader than the current storage layer. |
| 7. Integration Points & APIs | Partial | The contract surface exists, but production fidelity is still limited. |
| 8. Deployment Architecture | Partial | Docker/local deployment is valid; production deployment hardening remains. |
| 9. Stakeholder Presentation Flow | Done / Partial | The leadership demo story works; the enterprise backend story is still incomplete. |
| Summary: Enterprise Specification Complete | Partial | The document overstates completeness relative to the current repo. |

### 6) `design-docs/NEXUS_v2_Master_Product_Document.md`

| Section | Status | Notes |
|---|---|---|
| 1. Executive Summary | Partial | The product narrative is real; the numerical claims are still aspirational. |
| 2. Opportunity - Market & Problem | Pending | Strategic document, not product implementation. |
| 3. Solution - Product Vision & Architecture | Partial | Four-agent architecture and workflow are real; deeper backend vision is still incomplete. |
| 4. Business Model & Go-to-Market | Pending | Not implemented in code. |
| 5. Technical Specification & Implementation | Partial | The shell exists; the full platform spec is not realized. |
| 6. Product Roadmap & Feature Matrix | Partial | The UI-first roadmap is effectively done; later phases remain pending. |
| 7. Customer Experience & Success Metrics | Partial | UX goals are visible; live customer metrics are not yet real. |
| 8. Organization & Team | Pending | Planning content only. |
| 9. Financial Projections & Funding | Pending | Planning content only. |
| 10. Legal, Compliance & Data Governance | Partial | Basic auth/rate limiting/audit exist; compliance posture is not complete. |
| 11. Risk Management & Mitigation | Pending | Planning content only. |
| 12. Appendices | Partial | Some sample artifacts and catalogue material exist, but several appendices are still aspirational. |


### 8) `docs/superpowers/specs/2026-05-28-enterprise-workflow-ui-design.md`

| Section | Status | Notes |
|---|---|---|
| Goal / Source Context / Product Positioning | Done | The current app now matches the product positioning. |
| Primary User Experience | Done | Queue, incident, input, history, replay, training, and settings all exist. |
| Workflow Model | Done | The nine-step workflow is represented. |
| Agent Contribution Model | Done | SENTINEL, PRISM, FORGE, and GUARDIAN are present in the UI. |
| Input Channel Model | Done / Partial | Channel coverage is there; some channels are still more demo than production. |
| Sample Replay Model | Done / Partial | Replay is visible and launchable; live replay fidelity is still limited. |
| RL Training Lab Model | Done / Partial | The training surface works; the backend story is still partly deterministic. |
| Frontend Architecture | Done | The build-free frontend shell is in place. |
| Backend Architecture | Partial | Thin contracts exist; true backend realism is incomplete. |
| Containerization And Ops | Partial | Local and Docker flows work; production hardening is incomplete. |
| Success Criteria | Partial | The main user journey works; the full enterprise spec is not yet complete. |


### 10) Repo-Level Docs

| Doc | Status | Notes |
|---|---|---|
| `README.md` | Partial | Current entrypoint for product, architecture, setup, and documentation navigation; some forward-looking language remains. |
| `docs/OPERATIONS.md` | Partial | Good runtime guide; demo and product mode operations plus recovery still need hardening. |

## Current Deviations From The Active Plan

These are the main gaps that are still worth adding to the plan if you want to keep going beyond the current demo-grade state:

1. Add real observability adapters for Prometheus, Datadog, ELK/Loki, and deployment metadata instead of deterministic fixture joins.
2. Add a stronger execution-policy layer for GUARDIAN, including explicit approval/rejection state and more visible gate outcomes.
3. Add a real production persistence story for incident events, replay, and training artifacts if this moves beyond demo mode.
4. Harden auth and tenant boundaries for true production mode, including signature verification and clearer gateway posture.
5. Continue backend service decomposition where helper logic still belongs in focused modules.
6. Keep the README and docs matrix as the canonical source of truth.

## Bottom Line

- The UI-first roadmap is done.
- The thin backend/demo realism layer is done enough for a credible demo.
- The enterprise-spec production layer is still partial.
