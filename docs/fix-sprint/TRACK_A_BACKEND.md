You are running a focused backend fix sprint for NEXUS. Work continuously through all items below without stopping for approval between items. Apply governance rules throughout: compact at 50% context, 2-failure retry limit then mark blocked, never call ScheduleWakeup, ask only if genuinely uncertain about implementation approach.

Current baseline: 450 tests passing (pytest tests/ --ignore=tests/test_production_gate3.py -q)
Every item must leave this baseline intact or higher. Run pytest after every item before moving to the next.

---

ITEM A1 — Fix hardcoded pilot scorecard (CRITICAL — do this first)

The endpoints /api/v1/tenant/pilot-scorecard, /api/v1/tenant/weekly-review-package, and /api/v1/tenant/pilot-closeout-package all return hardcoded values (incidents_handled=5, incidents_runtime_backed=3, total_triage_time_saved_minutes=60). This will destroy pilot customer trust immediately. Fix it.

Implementation:
1. Create server/services/metrics_service.py with a PilotMetricsService class
2. Implement compute_pilot_metrics(tenant_id, database) that queries real data:
   - incidents_handled = COUNT of incidents in DB for this tenant
   - incidents_runtime_backed = COUNT where evidence_posture field in data JSON = 'runtime_backed'
   - incidents_inferred = COUNT where evidence_posture = 'inferred_only'
   - handoff_completion_count = COUNT where handoff_status in data JSON = 'sent'
   - total_triage_time_saved_minutes = incidents_handled * 15 (document this assumption in a comment)
   - Add computed_at = datetime.now(UTC).isoformat() to every response
3. Replace hardcoded values in all three endpoint handlers in server/app.py with calls to PilotMetricsService
4. Write tests/test_metrics_service.py: test that submitting 3 incidents makes incidents_handled return 3, test that computed_at is present, test graceful handling of empty database

Done when: pytest tests/test_metrics_service.py passes, /api/v1/tenant/pilot-scorecard returns real counts, submitting a new incident changes the count on next call.

---

ITEM A2 — Add CORS configuration (SECURITY — do this second)

FastAPI currently serves all origins. Any website can make cross-origin API calls using a visitor's browser context. Add explicit CORS allowlist.

Implementation:
1. Add CORSMiddleware to server/app.py:
   from fastapi.middleware.cors import CORSMiddleware
   Add after app = FastAPI(...):
   app.add_middleware(
       CORSMiddleware,
       allow_origins=config.allowed_origins,
       allow_credentials=True,
       allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
       allow_headers=["Content-Type", "X-User-ID", "X-Tenant-ID", "X-Roles", "X-Signature", "X-Runtime-Host-Token"],
   )
2. Add allowed_origins to AppConfig in server/config.py:
   allowed_origins: list[str] = Field(default_factory=lambda: _env_list("NEXUS_ALLOWED_ORIGINS", [
       "https://nexus-triage.duckdns.org",
       "https://nexus-uny5.onrender.com",
       "http://localhost:7860",
       "http://127.0.0.1:7860",
   ]))
3. Add NEXUS_ALLOWED_ORIGINS to .env.example with documentation comment
4. Write tests/test_cors.py: test that allowed origin gets CORS headers, test that unlisted origin does not

Note: The CORSMiddleware must be added AFTER the lifespan context manager is defined but the config isn't available at that point. Read how the existing middleware/config is structured before implementing — you may need to read the allowed_origins from env directly rather than from AppConfig at middleware registration time.

Done when: pytest tests/test_cors.py passes, cross-origin requests from unlisted origins get no CORS headers.

---

ITEM A3 — Add request body size limits (SECURITY)

Webhook and raw-text endpoints accept unbounded payloads. Add a 1MB limit.

Implementation:
1. Create a simple size-checking middleware in server/app.py:
   @app.middleware("http")
   async def limit_request_size(request: Request, call_next):
       max_size = int(os.environ.get("NEXUS_MAX_REQUEST_SIZE_BYTES", 1048576))
       content_length = request.headers.get("content-length")
       if content_length and int(content_length) > max_size:
           return JSONResponse(status_code=413, content={"detail": f"Request body too large. Maximum size is {max_size} bytes."})
       return await call_next(request)
2. Add NEXUS_MAX_REQUEST_SIZE_BYTES to .env.example
3. Write tests/test_request_limits.py: test that a request with Content-Length > 1MB returns 413, test that a normal request passes through

Done when: pytest tests/test_request_limits.py passes, requests claiming to be > 1MB are rejected with 413.

---

ITEM A4 — Extract health endpoint into HealthService (CODE QUALITY)

The /api/v1/observability/health route handler is 200+ lines of business logic. Extract into a service class.

Implementation:
1. Create server/services/health_service.py
2. Create a SubsystemHealth dataclass:
   from dataclasses import dataclass
   @dataclass
   class SubsystemHealth:
       status: str
       guidance: list[str]
       next_checks: list[str]
       summary: str = ""
3. Move each subsystem check into its own method on HealthService:
   - check_queue_health(queue_items: list) -> SubsystemHealth
   - check_memory_health(service) -> SubsystemHealth
   - check_delivery_health(deployment_readiness: dict) -> SubsystemHealth
   - check_replay_health(execution_state, deployment_readiness: dict) -> SubsystemHealth
   - check_runtime_queue_health(runtime_recovery: dict) -> SubsystemHealth
4. Create get_platform_health(tenant_id, service, execution_state) -> dict as the main method that calls all the above and assembles the final response
5. The response dict must be IDENTICAL to the current response — no fields added or removed, same structure
6. Replace the 200-line route handler in app.py with a ~10-line call to HealthService
7. Write tests/test_health_service.py: unit test each subsystem check in isolation

Done when: route handler is ≤ 15 lines, response shape identical, pytest tests/test_health_service.py passes, all 450 existing tests pass.

---

ITEM A5 — Add OpenAPI documentation to all routes (DEVELOPER EXPERIENCE)

The 30+ routes have no summaries, descriptions, or tags. Add them.

Implementation:
1. Add FastAPI app metadata:
   app = FastAPI(
       title="NEXUS Incident Investigation API",
       description="AI-powered incident triage and investigation with human governance gate",
       version="1.0.0",
       lifespan=lifespan,
   )
2. Add tags to every route grouping by domain:
   - ["Incidents"] for all /api/v1/incidents/ routes
   - ["Webhooks"] for /webhooks/ routes
   - ["Training"] for /api/v1/training/ routes
   - ["Platform"] for /api/v1/platform/ and /api/v1/runtime/ routes
   - ["Tenant"] for /api/v1/tenant/ routes
   - ["Auth"] for /api/v1/auth/ routes
   - ["Replay"] for /api/v1/replay/ routes
   - ["UI"] for all HTML-serving routes (/, /queue, /incident, etc.)
3. Add summary= and description= to every route decorator. Keep summaries under 10 words, descriptions 1-2 sentences.
4. No functional changes — only metadata additions

Done when: /docs shows meaningful descriptions for every endpoint, all 450 existing tests pass (no functional change).

---

ITEM A6 — Fix RuntimeExecutionState restart recovery (RELIABILITY)

RuntimeExecutionState stores state in memory. If container restarts mid-replay, state is lost.

Implementation:
1. Add a runtime_executions table to the database schema in db.py _ensure_schema():
   conn.execute("""
       CREATE TABLE IF NOT EXISTS runtime_executions (
           id INTEGER PRIMARY KEY AUTOINCREMENT,
           incident_id TEXT NOT NULL,
           pack_id TEXT NOT NULL,
           status TEXT NOT NULL DEFAULT 'running',
           started_at TEXT NOT NULL,
           finished_at TEXT,
           created_at TEXT NOT NULL
       )
   """)
2. In RuntimeExecutionState.start_execution(): write a record to runtime_executions with status='running'
3. In RuntimeExecutionState.finish_execution(): update the record with final status and finished_at
4. In the lifespan startup in app.py: query runtime_executions for any records with status='running' and mark them 'interrupted'. Add these to a new interrupted_executions list on the RuntimeExecutionState.
5. Include interrupted_executions in the to_dict() response
6. Write tests/test_runtime_execution_recovery.py: test that a running execution persisted to DB, simulate restart, verify it shows as interrupted

Done when: pytest tests/test_runtime_execution_recovery.py passes, execution history survives container restart, all 450 existing tests pass.

---

AFTER ALL ITEMS:

1. Run: pytest tests/ --ignore=tests/test_production_gate3.py -q
   Report exact count — must be 450+ passing, 0 failing

2. Run: git add -A && git commit -m "fix(backend): CORS, request limits, real scorecard metrics, health service, OpenAPI docs, execution state persistence" && git push origin master

3. Report final status table:
   | Item | Status | Tests Added | Notes |
   |------|--------|-------------|-------|
   | A1: Scorecard | PASS/FAIL | X new | |
   | A2: CORS | PASS/FAIL | X new | |
   | A3: Size limits | PASS/FAIL | X new | |
   | A4: Health service | PASS/FAIL | X new | |
   | A5: OpenAPI docs | PASS/FAIL | X new | |
   | A6: Execution recovery | PASS/FAIL | X new | |
