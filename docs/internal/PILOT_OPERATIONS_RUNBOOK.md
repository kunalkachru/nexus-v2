# NEXUS Pilot Operations Runbook

This runbook covers tenant onboarding, operational procedures, and governance for running NEXUS across 2–3 pilot tenants.

## Pilot Program Structure

NEXUS pilots run within these bounded incident families:

- `INC001` checkout timeout / retry amplification
- `INC002` checkout DB pool exhaustion / session leak
- `INC003` deploy regression / 5xx spike
- `INC005` queue / worker backlog affecting transaction completion
- `INC007` auth dependency slowdown / token validation failures

Tenant scope:

- 2–3 qualified tenants per wave
- 4–6 week evaluation cycles
- runtime-backed handling should grow while unsupported cases remain explicitly downgraded

## Weekly Pilot Review

Review:

1. incident volume
2. support quality
3. engineering feedback
4. runtime-backed versus inference-first ratio
5. time savings and handoff quality
6. recurring unsupported family patterns

## Downstream Delivery And Replay Failure Vocabulary

Operators should use one shared vocabulary across UI, audit, and review docs:

- `delivered` — the packet or replay action completed and is now waiting on human review or follow-on work
- `retryable_failure` — the action failed for a transient reason such as connectivity or timeout; retry only after the dependency recovers
- `terminal_failure` — the action failed in a way that blocks retry until configuration or destination state is fixed
- `partial_follow_up` — downstream acknowledged the packet but asked for more evidence, debugging, or review
- `closed_with_feedback` — downstream accepted or resolved the packet and the case can move toward closure
- `rejected_downstream` — downstream rejected the packet; review evidence posture before re-sending

## Duplicate Delivery Semantics

When a packet is sent more than once, NEXUS should make that explicit:

- `first_send`
- `retry_after_failure`
- `repeat_send_after_delivery`
- `retry_blocked_after_terminal_failure`

Operators should not keep re-sending the same packet without a stated downstream reason.
