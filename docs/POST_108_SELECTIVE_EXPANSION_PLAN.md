# NEXUS Post-108 Selective Expansion Plan

Current as of 2026-06-15.

This document describes the phase after FR2 (`101–108`) is complete.

The purpose of this phase is to widen the current wedge carefully without changing the category.

This phase is:

**selective expansion, still inside the support-triage wedge**

## Product Position After 108

After FR2, NEXUS should be described as:

**a repeatable enterprise pilot product for recurring customer-facing outages, with bounded reproduction, bounded debugging, explicit downgrade behavior, and stronger buyer and engineering trust**

That is strong enough for 2–3 pilots.

The next gap is not general platform breadth.

The next gap is:

- slightly broader outage-family coverage inside the same category
- stronger buyer legibility for what is covered
- better live routing quality across a wider but still bounded wedge

## Goal

The goal of `109–116` is:

**expand from the current three-family wedge to a five-family wedge while keeping the product coherent, truthful, and runtime-backed where claimed**

This phase should not change the category.

It should still feel like one support-to-engineering investigation workflow.

## Fixed Expansion Scope

Add exactly two new outage families:

1. **auth dependency slowdown / token validation failures**
2. **queue / worker backlog affecting transaction completion**

These are adjacent to the existing support-triage story and still buyer-legible.

## What This Phase Should Do

This phase should contain:

- auth dependency family packet across seeded and live paths
- bounded REPLICA and TRACE support for auth dependency family
- queue / worker backlog family packet across seeded and live paths
- bounded REPLICA and TRACE support for queue / worker backlog family
- coverage matrix and scorecard extension for the five-family wedge
- fresh-incident routing and owner inference calibration across the five-family wedge
- buyer and demo refresh for five supported outage families
- five-family checkpoint and control-doc refresh

## What This Phase Should Not Do

Do not use `109–116` to:

- broaden into universal incident response
- broaden into generalized ITSM
- claim arbitrary reproduction
- claim arbitrary repository debugging
- claim autonomous remediation
- add many more families beyond the fixed two in this phase

## Acceptance Criteria

This phase is successful only when all of these are true:

1. NEXUS supports five bounded outage families that buyers can understand
2. each new family is coherent in seeded and live paths
3. each new family is runtime-backed only where a bounded pack actually exists
4. the coverage matrix and pilot proof surfaces reflect the widened wedge honestly
5. fresh incidents route more credibly without becoming overconfident
6. the product still reads as one coherent support-triage category
7. the repo ends the phase with current control docs and a clear handoff into ops maturity

## Recommendation

Treat `109–116` as the **five-family selective expansion sprint**.

If this phase lands cleanly, the product should be able to say:

**we support five recurring outage families inside one bounded support-to-engineering workflow, with explicit runtime-backed versus inference-first coverage and a clear investigation handoff story**
