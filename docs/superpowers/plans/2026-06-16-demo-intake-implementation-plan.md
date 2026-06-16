# Demo Intake Implementation Plan

Goal: make `/inputs` a stakeholder-ready demo entry point that can load realistic logs, explain what the chosen evidence proves, and carry that story into the fresh incident workspace without pretending the product is broader than it is.

Execution order:

1. build a curated five-family demo log corpus
2. add failing browser verification for the bundle flow
3. implement the `/inputs` bundle selector and proof surfaces
4. carry the chosen bundle context into the fresh incident page
5. update the single owner-facing demo guide
6. rerun the full validation set and refresh control docs

Scope boundaries:

- keep all evidence posture wording strict
- do not add new outage families
- do not fabricate backend runtime validation from UI metadata
- keep free-form paste available beside the curated demo path
- use bundle metadata only to guide the operator, not to mutate backend reasoning

Intended user story:

1. operator opens `/inputs`
2. operator chooses a known outage bundle such as checkout timeout or DB pool exhaustion
3. the page explains what the logs prove, which owner/family the product should converge on, and what runtime/debugging posture to expect
4. operator submits the logs
5. the fresh `nxs_...` incident opens with the same story carried forward, so the stakeholder can see why the six-agent handoff matters
