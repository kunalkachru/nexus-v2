# NEXUS v2 Agent Model Matrix

Current as of 2026-05-30.

This matrix records what each agent does today, how much of that behavior is LLM-backed, and what is still missing for the recommended enterprise shape.

## Current Runtime Truth

- Default web app: deterministic agent stack.
- `FORGE`: optional live OpenAI path only when `NEXUS_USE_OPENAI=1` and `OPENAI_API_KEY` are present in `demo.py`.
- `server/config.py` now carries the explicit Forge model default as `forge_model_name`.
- `GUARDIAN` remains deterministic by design.

## Matrix

| Agent | Current implementation | LLM fit | Recommended production pattern | Gap to close | Status |
|---|---|---|---|---|---|
| `SENTINEL` | Deterministic catalogue-based classifier. | Medium to high for ambiguous free-text incidents. | Hybrid: rules and catalogue matching first, LLM fallback only for ambiguous cases. | Add an optional LLM fallback path with confidence and traceability. | Partial |
| `PRISM` | Deterministic observability-backed correlation and diagnosis. | High for synthesis, summarization, and noisy evidence. | Retrieval-grounded LLM synthesis with explicit citations and evidence provenance. | Add structured model/provider wiring and keep all claims grounded in evidence. | Partial |
| `FORGE` | Injectable client already exists; default web app uses the deterministic path, and `demo.py` can opt into OpenAI. | High for remediation drafting and runbook generation. | LLM-backed runbook generation with sandbox validation, policy checks, and audit logging. | Make the app-level model/provider config explicit and keep the optional live path easy to enable. | Partial |
| `GUARDIAN` | Deterministic safety and policy gate. | Low for enforcement, medium for explanation. | Keep enforcement deterministic; optionally use an LLM only for human-readable explanation. | Make approval, block, execute, and learn outcomes more explicit in the UI and policy records. | Done / Partial |

## What This Means

- The product is not a fake demo shell.
- The workflow, audit trail, queue, replay, and settings surfaces are real.
- The current reasoning layer is hybrid: deterministic by default, optional live LLM only for the FORGE demo path.
- The next enterprise step is to ground `PRISM` and `FORGE` more explicitly in a real model/provider layer while keeping `GUARDIAN` deterministic.

## Recommended Next Implementation Order

1. Make `FORGE` model/provider selection explicit in app config and web-app wiring.
2. Add grounded LLM-assisted synthesis for `PRISM`.
3. Keep `SENTINEL` hybrid so common cases stay deterministic and ambiguous cases can escalate.
4. Keep `GUARDIAN` deterministic and improve the visibility of its control decisions.
