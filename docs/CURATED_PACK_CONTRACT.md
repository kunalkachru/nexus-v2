# Curated Runtime Pack Onboarding Contract

**Current as of 2026-06-12.**

This document defines how a new outage class becomes a curated runtime and debugger pack in NEXUS. It standardizes the metadata, contract, and support requirements so NEXUS can grow through disciplined extension rather than ad hoc hardcoding.

## What Is A Curated Pack

A curated pack is a bounded Docker-based reproduction environment paired with explicit debugging checkpoints and mitigation validation hooks. It represents NEXUS's commitment to one specific outage class:

- **REPLICA support**: prove or disprove the hypothesis through bounded replay
- **TRACE support**: narrow the likely code path and suspected owner/function
- **GUARDIAN support**: measure outcome improvements and governance implications

A pack is not:
- general-purpose debugging for the stack
- a complete production deployment
- infinitely extensible to all problem variants

## Pack Requirements

Every curated pack must declare and satisfy these minimum requirements.

### 1. Incident Class Metadata

```python
pack_id: str                           # "service-language-framework-storage-v1"
incident_classes: tuple[str, ...]      # ("issue_family_one", "issue_family_two")
services: tuple[str, ...]              # ("api-gateway", "auth-svc", "checkout-api")
stack: tuple[str, ...]                 # ("python", "fastapi", "redis")
```

**Why it matters**: NEXUS uses incident class, service, and stack to route incoming incidents to the right pack. This metadata must be crisp and match the actual pack capabilities.

**Examples**:
- `checkout-python-fastapi-auth-redis-v1` covers timeout retry amplification on checkout
- `checkout-python-fastapi-postgres-v1` covers database pool exhaustion on checkout

### 2. Replay Contract

```python
compose_file: Path                     # path to docker-compose.yml
replay_profile: str                    # "checkout_retry_replay_v1"
expected_baseline_status: int | None   # HTTP status code (e.g., 504)
hypothesis_summary: str                # what the pack tests
```

**Why it matters**: Replay must be deterministic and bounded. The compose file must spin up a reproducible environment in seconds, not minutes. The replay profile must be a deterministic script that triggers the failure.

**Contract**:
- `docker-compose.yml` must be in `replica_packs/{pack_id}/`
- `scripts/replay_{replay_profile}.sh` must exist and be executable
- baseline status must match real-world failure signatures
- hypothesis must be falsifiable (provable right or wrong through replay)

**Example from INC001**:
```python
compose_file=replica_packs / "checkout-python-fastapi-auth-redis-v1" / "docker-compose.yml"
replay_profile="checkout_retry_replay_v1"
expected_baseline_status=504
hypothesis_summary="Prove that checkout timeouts persist only when downstream auth latency stays elevated while the retry-heavy auth path remains enabled."
```

### 3. Triggering Conditions

```python
triggering_conditions: tuple[str, ...]  # environmental preconditions
expected_failure_signature: tuple[str, ...]  # measurable failure characteristics
```

**Why it matters**: These are the state conditions that must be true in production for the pack to be relevant. They clarify scope and prevent false positives.

**Example from INC002**:
```python
triggering_conditions=(
    "The checkout retry patch stays active on the write path.",
    "The bounded Postgres pool is capped at the production threshold.",
    "Session cleanup does not complete after retry failure.",
)
expected_failure_signature=(
    "Baseline replay returns HTTP 503 once the pool saturates.",
    "QueuePool or session-leak anchors appear before checkout writes recover.",
    "Runtime clears only after leaked sessions are terminated or the retry patch is rolled back.",
)
```

### 4. Mitigation Hooks

```python
mitigation_hooks: tuple[str, ...]  # ordered list of mitigation scripts
```

**Why it matters**: Hooks test whether candidate mitigations actually improve the failure. They are ordered so that earlier hooks represent lower-risk changes.

**Contract**:
- Each hook has a script at `replica_packs/{pack_id}/hooks/{hook_name}.sh`
- Hooks are run sequentially and idempotently
- Each hook should test one discrete mitigation hypothesis
- Success means replay status improves after the hook runs

**Example from INC001**:
```python
mitigation_hooks=("cap_retries", "open_circuit_breaker", "disable_retry_middleware")
```

This means:
1. First test: cap retries to 1
2. Second test: open the circuit breaker
3. Third test: disable the entire retry middleware

### 5. Trace Support

```python
trace_source_map: dict[str, tuple[str, ...]]  # module -> (function, ...)
```

**Why it matters**: When an operator needs code-level debugging, TRACE uses this map to narrow to the suspected code path and function.

**Contract**:
- Keys are module paths (dot-separated)
- Values are tuples of function names to inspect first
- All referenced functions must exist in the production code

**Example from INC001**:
```python
trace_source_map={
    "auth.middleware.retry": ("apply_retry_policy",),
    "gateway.timeout_guard": ("await_upstream_auth",),
    "auth.circuit_breaker": ("record_timeout_budget",),
}
```

## Adding A New Pack: Step-by-Step

### Step 1: Choose an Incident Class

Pick one real, recurring outage class with:
- Clear business impact
- Believable diagnostic signals
- A measurable failure signature
- Known remediation options

### Step 2: Build the Docker Environment

Create `replica_packs/{pack_id}/`:

```
replica_packs/service-language-framework-storage-v1/
├── docker-compose.yml              # reproducible environment
├── scripts/
│   ├── replay_profile_name.sh       # trigger the failure
│   └── ...
└── hooks/
    ├── mitigation_one.sh            # test mitigation 1
    ├── mitigation_two.sh            # test mitigation 2
    └── ...
```

Constraints:
- Compose must use only publicly available images
- All services must healthcheck and be ready in < 60 seconds
- Replay script must trigger the failure deterministically
- Each mitigation hook must be idempotent

### Step 3: Declare the Pack in Code

Add an entry to `server/services/replica_runtime.py` registry():

```python
"service-language-framework-storage-v1": ReplicaEnvironmentPack(
    pack_id="service-language-framework-storage-v1",
    incident_classes=("issue_family_one", "issue_family_two"),
    services=("service-a", "service-b"),
    stack=("python", "fastapi", "postgres"),
    compose_file=packs_root / "service-language-framework-storage-v1" / "docker-compose.yml",
    replay_profile="replay_profile_name",
    mitigation_hooks=("mitigation_one", "mitigation_two", "mitigation_three"),
    hypothesis_summary="Prove that [specific failure] persists only when [conditions] and resolves when [mitigation].",
    expected_baseline_status=503,  # or None if not HTTP
    triggering_conditions=(
        "Condition one must be true.",
        "Condition two must be true.",
    ),
    expected_failure_signature=(
        "Expected signal one appears.",
        "Expected signal two appears.",
    ),
    trace_source_map={
        "module.path": ("function_name",),
    },
),
```

### Step 4: Declare Incident Class Awareness

Update `server/services/enterprise_runtime.py`:

1. Add the incident class to `infer_issue_family()` so new incidents are classified correctly
2. Update `select_environment_pack()` to map the issue family to your new pack
3. Update `build_execution_plan()` to instantiate your pack with the right incident class

### Step 5: Document the Debugging Path

Create a bounded TRACE packet entry in `server/services/enterprise_runtime.py` `build_trace_summary()`:

- Map the incident class to your trace_source_map
- Provide bounded ownership hints from your module names
- Keep the scope tight (2-4 modules, 1-2 functions per module)

### Step 6: Test

Run:
```bash
pytest tests/test_replica_runtime.py -q
npm run browser:verify
ENABLE_RUNTIME_HOST_RELAY=1 ./scripts/docker_fresh.sh
EXPECT_RUNTIME_HOST_RELAY=1 BASE_URL=http://127.0.0.1:7860 ./scripts/local_enterprise_smoke.sh
```

Verify:
- Your pack is discoverable via `replica_packs_root()`
- Incidents matching your incident_classes route to your pack
- Replay runs deterministically
- Each mitigation hook improves the replay outcome in order
- TRACE narrows to the right code path

## Operator-Facing Coverage Description

When operators ask "what outage classes does NEXUS support," the answer comes from the registry:

**Current packs** (as of 2026-06-12):

1. **Timeout retry amplification** (`checkout-python-fastapi-auth-redis-v1`)
   - Incident class: `timeout_retry_amplification`, `checkout_timeout_cascade`
   - Services: api-gateway, auth-svc, checkout-api
   - Hypothesis: checkout timeouts from auth degradation + retry storms
   - Replay: 504 baseline, recovers when retries capped or middleware disabled

2. **Database pool exhaustion** (`checkout-python-fastapi-postgres-v1`)
   - Incident class: `db_pool_exhaustion`, `session_leak`
   - Services: checkout-svc, postgres-orders
   - Hypothesis: session leak from retry patch exhausts bounded pool
   - Replay: 503 baseline, recovers when sessions terminated or patch rolled back

New packs follow the same pattern and are discoverable the same way.

## Design Principles

1. **Bounded not generic**: Each pack supports one outage class, not all database problems or all timeouts
2. **Reproducible not heuristic**: Failure must trigger deterministically, not probabilistically
3. **Measurable not subjective**: Success means an observable metric improves (status code, duration, log pattern)
4. **Extensible not hardcoded**: New packs are added through code, not by forking the entire system
5. **Honest not aspirational**: If you can't prove the hypothesis in bounded time, don't ship the pack

## Anti-Patterns to Avoid

❌ **Too broad**: "database debugging" — pick one failure class instead
❌ **Too slow**: replay takes > 90 seconds — tighten the environment
❌ **Non-deterministic**: replay sometimes fails, sometimes succeeds — find and remove randomness
❌ **Undeclared cost**: mitigation hooks silently improve but hypothesis doesn't explain why
❌ **Hidden assumptions**: trace_source_map references functions that don't exist
❌ **Orphaned packs**: pack is registered but replay script is deleted or broken

## References

- `server/services/replica_runtime.py`: Pack registry and execution
- `server/services/enterprise_runtime.py`: Incident class routing and TRACE support
- `replica_packs/`: Actual pack implementations
- `tests/test_replica_runtime.py`: Pack lifecycle tests
