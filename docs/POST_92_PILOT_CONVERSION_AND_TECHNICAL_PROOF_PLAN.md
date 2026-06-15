# NEXUS Post-92 Pilot Conversion And Technical Proof Plan

Current as of 2026-06-15.

This document describes the phase after the wedge-strengthening sprint (`86–92`) is complete.

The purpose of this phase is to take the stronger three-outage wedge and make it easier to:

- sell into a real pilot
- onboard for a real pilot
- prove value during a real pilot
- withstand deeper engineering scrutiny during a pilot

This phase still does not broaden NEXUS into a general incident platform.

## Product Position After 92

After `86–92`, NEXUS should be described as:

**a repeatable support-to-engineering investigation workflow for recurring customer-facing outage families, with bounded reproduction, bounded debugging, and governed action**

That is stronger than the narrow v1 release posture.

The next gap is not basic wedge credibility.

The next gap is:

- pilot setup repeatability
- durable pilot-value proof
- stronger engineering trust in the handoff and runtime evidence
- better fresh-incident triage consistency

## Priority Order

This phase should optimize in this order:

1. pilot conversion hardening
2. technical proof deepening
3. broader outage-family expansion later

The phase should therefore prioritize making the current three-outage wedge easier to deploy, evaluate, trust, and prove before adding more surface area.

## The Problem Still Stays The Same

The product still solves one problem:

**too many expensive human relays happen between support and engineering before a confident action exists during recurring customer-facing incidents**

This phase does not change the category or the wedge.

It makes the wedge more operationally and commercially repeatable.

## Recommended Next Boundary

Use `93–100` for the next short execution phase.

That phase should stay inside the current product category:

**support-to-engineering investigation workflow for recurring customer-facing outages**

It should not drift into:

- broad ITSM replacement
- universal incident response
- universal debugger
- arbitrary reproduction platform

## Recommended Scope

The next phase should contain:

- tenant onboarding v2 and pilot setup kit
- pilot ROI instrumentation and case-based proof capture
- delivery and feedback closure v2
- operator workflow simplification and role clarity v2
- repo-aware debugger handoff deepening
- runtime evidence weighting and mitigation confidence deepening
- fresh-incident triage quality calibration and evaluation
- a deliberate post-92 checkpoint

## Why This Is The Right Next Move

After `92`, the biggest risk is not that the product lacks one more outage family.

The bigger risk is that:

- a real pilot still depends too much on founder guidance
- buyer value still looks demo-shaped instead of operationally durable
- engineering teams still want stronger evidence that the handoff is actionable
- fresh-incident quality still varies too much

This phase directly addresses those concerns.

## Pilot Conversion Principle

The product should become easier to evaluate in a customer setting by making these clearer:

- what setup a tenant needs
- how success will be measured
- what incidents are supported strongly today
- what the support team should do in a real pilot
- what engineering will receive and why it is useful

## Technical Proof Principle

The product should become more persuasive to engineering buyers by making these stronger:

- repo-aware debugging cues
- runtime comparison quality
- mitigation recommendation confidence
- evidence weighting across inference, memory, and runtime
- fresh-incident triage consistency

This should deepen technical trust without turning the system into a broad platform.

## What This Phase Should Not Do

Do not use this phase to:

- add many new outage families
- build a universal debugger story
- promise arbitrary repo support
- add autonomous production remediation
- widen the product category beyond customer-facing outage investigation

## Acceptance Criteria

The phase is successful only when all of these are true:

1. a new tenant can be prepared for a bounded pilot with less founder intervention
2. the product captures and presents pilot-value evidence in a more durable way
3. downstream handoff and feedback loops feel more complete for repeated workflow use
4. operator workflow is clearer and lower-friction during real pilot usage
5. engineering handoff packets are more repo-aware and inspection-ready
6. runtime evidence more strongly drives mitigation ranking and confidence
7. fresh-incident triage quality is more stable and more honestly evaluated
8. the repo ends the phase with a clean checkpoint and current control docs

## Recommendation

Treat `93–100` as the **pilot conversion and technical proof sprint**.

If this phase lands cleanly, NEXUS should be able to present itself not just as a convincing wedge, but as:

**a pilot-ready, repeatable support-triage product that can prove value and hold up under real support and engineering evaluation**
