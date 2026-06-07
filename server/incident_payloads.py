from __future__ import annotations

from copy import deepcopy

from incidents.catalogue import load_incident_types
from server.models import IncidentDefinition


INCIDENT_DEFINITION_BY_ID: dict[str, IncidentDefinition] = {
    incident.id: incident for incident in load_incident_types()
}


INCIDENT_DETAILS: dict[str, dict[str, object]] = {
    "INC001": {
        "summary": "API timeout cascade saturating the edge gateway after a retry storm.",
        "detected_at": "2026-05-28T09:14:00Z",
        "duration_minutes": 11,
        "related_services": ["api-gateway", "auth-svc", "orders-api", "stripe-api"],
        "metrics": [
            {"name": "CPU", "unit": "%", "current": 95, "series": [54, 61, 68, 77, 84, 90, 95]},
            {"name": "Memory", "unit": "%", "current": 81, "series": [56, 59, 63, 69, 73, 78, 81]},
            {"name": "Latency", "unit": "ms", "current": 5000, "series": [240, 310, 520, 1400, 2600, 4100, 5000]},
            {"name": "Network", "unit": "Mbps", "current": 780, "series": [310, 355, 420, 560, 640, 710, 780]},
        ],
        "recent_logs": [
            "09:05:12 WARN api-gateway retry budget exceeded for POST /payments after 4 upstream attempts",
            "09:05:34 ERROR auth-svc upstream timeout after 5000ms request_id=req-8e12",
            "09:06:01 WARN api-gateway worker pool saturation 93/96 workers busy",
            "09:06:17 ERROR api-gateway request timed out after 5001ms route=/v1/checkout",
            "09:06:49 WARN orders-api fallback queue length growing to 1200",
            "09:07:10 ERROR api-gateway client connection reset during upstream wait",
            "09:07:45 WARN stripe-api external latency elevated 2.8s p95",
            "09:08:12 ERROR api-gateway 504 returned for request_id=req-90af",
            "09:09:03 WARN auth-svc circuit breaker still closed despite timeout surge",
            "09:10:41 ERROR api-gateway 5xx rate exceeded 50/sec rolling window",
            "09:11:05 WARN pod/api-gateway-7d9db hot thread pool at 100%",
            "09:11:59 ERROR api-gateway healthcheck degraded by event-loop starvation",
            "09:12:34 WARN orders-api downstream auth dependency flapping",
            "09:12:58 ERROR api-gateway upstream read timeout after 5.0s",
            "09:13:11 WARN kube-hpa api-gateway max replicas reached",
            "09:13:37 ERROR api-gateway checkout request failed with HTTP 504",
            "09:13:49 WARN auth-svc timeout retry amplification detected",
            "09:13:55 ERROR api-gateway customer-visible timeout count above SLA threshold",
            "09:14:01 WARN pagerduty trigger P1 API timeout cascade",
            "09:14:06 ERROR api-gateway incident snapshot captured for SENTINEL",
        ],
        "alert_timeline": [
            {"time": "09:03", "event": "Latency rose above 1.5s p95"},
            {"time": "09:07", "event": "CPU passed 90% on 3 of 4 gateway pods"},
            {"time": "09:10", "event": "5xx rate breached 50/sec"},
            {"time": "09:14", "event": "PagerDuty P1 fired for API timeout cascade"},
        ],
        "similar_past_incidents": [
            {"id": "INC-2026-0411", "summary": "Gateway retry storm after auth deploy", "success_rate": 0.91},
            {"id": "INC-2026-0328", "summary": "Checkout timeout from worker starvation", "success_rate": 0.87},
        ],
        "recent_deployments": [
            {"time": "08:58", "service": "auth-svc", "version": "2026.05.28.4", "change": "Retry middleware refactor"},
            {"time": "08:41", "service": "api-gateway", "version": "2026.05.28.2", "change": "Timeout telemetry patch"},
        ],
        "recommended_runbooks": [
            {"name": "gateway-retry-storm-mitigation", "success_rate": 0.89},
            {"name": "auth-timeout-circuit-breaker-reset", "success_rate": 0.84},
        ],
        "triage": {
            "issue_family": "Timeout cascade / retry amplification",
            "impacted_customer_path": "Checkout and payment authorization",
            "likely_owner_service": "auth-svc",
            "likely_owner_team": "Identity Platform",
            "responder_team": "API Platform incident command with Identity Platform on-call",
            "support_queue": "Customer checkout escalation",
            "blast_radius": "Customer checkout requests time out at the edge while downstream payment attempts queue up.",
            "manual_relay_removed": "NEXUS replaces the old relay of pasting gateway, auth, and deployment clues across multiple support tiers by assembling one prepared incident packet.",
            "approval_focus": "Start with reversible mitigation: cap retries, open the circuit breaker, and only then consider rollback.",
        },
        "sentinel": {
            "confidence": 0.97,
            "confidence_breakdown": {"metrics": 0.4, "logs": 0.35, "topology": 0.22},
            "evidence": [
                "Latency plateau at 5000ms matches timeout signature",
                "CPU 95% and worker saturation indicate thread starvation",
                "5xx rate 50/sec aligned with prior retry-storm incidents",
            ],
            "reasoning": "SENTINEL classified this as an API timeout cascade because latency, CPU saturation, and upstream timeout logs all match the learned gateway retry-storm pattern.",
        },
        "prism": {
            "confidence": 0.94,
            "correlation_analysis": "Correlated gateway timeout alerts with auth-svc retry spikes and worker-pool saturation in the same 10 minute window.",
            "log_snippets": [
                "ERROR auth-svc upstream timeout after 5000ms request_id=req-8e12",
                "WARN api-gateway worker pool saturation 93/96 workers busy",
                "ERROR api-gateway customer-visible timeout count above SLA threshold",
            ],
            "reasoning": "PRISM identified a retry amplification loop in auth-svc as the root cause that exhausted api-gateway workers.",
        },
        "forge": {
            "confidence": 0.91,
            "selection_logic": "Matched the gateway-retry-storm-mitigation runbook because the current alert fingerprint overlaps 89% with two prior successful incidents.",
            "candidate_fixes": [
                {"action": "Drain hot gateway pods and scale replicas +2", "success_rate": 0.88},
                {"action": "Enable auth-svc circuit breaker and cap retries to 1", "success_rate": 0.91},
                {"action": "Roll back auth-svc retry middleware", "success_rate": 0.79},
            ],
            "recommended_runbook": "gateway-retry-storm-mitigation",
            "reasoning": "FORGE selected the retry-storm mitigation runbook before rollback because it has the highest historical success rate with lower blast radius.",
        },
        "guardian": {
            "confidence": 0.96,
            "decision": "approve",
            "safety_checks": [
                "Verified actions are scoped to api-gateway and auth-svc deployments",
                "Checked proposed commands avoid destructive data operations",
                "Confirmed rollback and scale actions are covered by approved change windows",
            ],
            "policy_violations": [],
            "reasoning": "GUARDIAN approved the runbook because it limits scope to reversible deployment changes and does not touch persistent data.",
        },
    },
    "INC002": {
        "summary": "Checkout write path stalled by database pool exhaustion.",
        "detected_at": "2026-05-28T10:22:00Z",
        "duration_minutes": 14,
        "related_services": ["checkout-svc", "postgres-orders", "inventory-svc", "redis-cart"],
        "metrics": [
            {"name": "CPU", "unit": "%", "current": 72, "series": [38, 42, 49, 55, 61, 68, 72]},
            {"name": "Memory", "unit": "%", "current": 69, "series": [44, 47, 53, 57, 62, 66, 69]},
            {"name": "Latency", "unit": "s", "current": 10, "series": [0.8, 1.3, 2.4, 4.6, 6.2, 8.8, 10]},
            {"name": "Connections", "unit": "used", "current": 500, "series": [210, 260, 320, 410, 460, 492, 500]},
        ],
        "recent_logs": [
            "10:12:04 WARN checkout-svc db wait time above 1.2s",
            "10:12:31 ERROR postgres-orders remaining connection slots are reserved",
            "10:12:47 WARN checkout-svc session checkout retries exhausted",
            "10:13:02 ERROR SQLAlchemy QueuePool limit of size 500 overflow 0 reached",
            "10:13:24 WARN inventory-svc dependent writes delayed by checkout lock contention",
            "10:13:55 ERROR checkout-svc transaction commit timed out after 10.0s",
            "10:14:19 WARN postgres-orders active queries above 200",
            "10:14:43 ERROR checkout-svc leaked session detected request_id=req-2451",
            "10:15:01 WARN redis-cart cart reservation extension delayed",
            "10:15:28 ERROR checkout-svc worker blocked waiting for DB connection",
            "10:16:05 WARN postgres-orders idle in transaction sessions accumulating",
            "10:16:48 ERROR checkout-svc checkout request failed after pool timeout",
            "10:17:15 WARN api edge checkout success rate below 62%",
            "10:17:51 ERROR checkout-svc session cleanup hook missing on retry path",
            "10:18:17 WARN inventory-svc write queue depth rising",
            "10:18:43 ERROR postgres-orders max_connections reached 500/500",
            "10:19:06 WARN checkout-svc recent deploy correlates with session leak",
            "10:19:44 ERROR checkout-svc request cancelled while waiting for pool slot",
            "10:21:31 WARN pagerduty trigger P1 DB pool exhaustion",
            "10:21:59 ERROR checkout-svc incident snapshot captured for SENTINEL",
        ],
        "alert_timeline": [
            {"time": "10:12", "event": "Checkout DB wait time crossed 1s"},
            {"time": "10:15", "event": "Connection pool hit 95% utilization"},
            {"time": "10:18", "event": "Pool saturated at 500/500 and active queries exceeded 200"},
            {"time": "10:22", "event": "PagerDuty P1 fired for checkout degradation"},
        ],
        "similar_past_incidents": [
            {"id": "INC-2026-0507", "summary": "Connection leak on retry middleware", "success_rate": 0.94},
            {"id": "INC-2026-0219", "summary": "Long-lived transactions blocked checkout pool", "success_rate": 0.82},
        ],
        "recent_deployments": [
            {"time": "10:05", "service": "checkout-svc", "version": "2026.05.28.8", "change": "Retry-on-timeout patch"},
            {"time": "09:50", "service": "inventory-svc", "version": "2026.05.28.3", "change": "Reservation index tuning"},
        ],
        "recommended_runbooks": [
            {"name": "postgres-pool-exhaustion-mitigation", "success_rate": 0.94},
            {"name": "checkout-session-leak-rollback", "success_rate": 0.9},
        ],
        "triage": {
            "issue_family": "Database pool exhaustion / session leak",
            "impacted_customer_path": "Checkout write path and order confirmation",
            "likely_owner_service": "checkout-svc",
            "likely_owner_team": "Checkout Platform",
            "responder_team": "Checkout Platform with Database Operations on-call",
            "support_queue": "Checkout degradation escalation",
            "blast_radius": "Checkout requests queue behind saturated database connections and order confirmation stalls for active sessions.",
            "manual_relay_removed": "NEXUS pre-assembles the leaked-session evidence, pool metrics, and deploy context before the incident reaches the database or checkout owner.",
            "approval_focus": "Recover pool capacity first, then remove the leaking build without increasing database pressure.",
        },
        "sentinel": {
            "confidence": 0.98,
            "confidence_breakdown": {"metrics": 0.46, "logs": 0.33, "topology": 0.19},
            "evidence": [
                "Connections pinned at 500/500 is a direct pool exhaustion signature",
                "10s query latency and active queries >200 indicate saturation rather than node failure",
                "SQLAlchemy QueuePool errors match prior session leak incidents",
            ],
            "reasoning": "SENTINEL classified this as database connection pool exhaustion because the connection, latency, and ORM error signals converge on a session leak pattern.",
        },
        "prism": {
            "confidence": 0.95,
            "correlation_analysis": "Joined Postgres max_connections alerts with checkout-svc QueuePool errors and the 10:05 retry patch deployment.",
            "log_snippets": [
                "ERROR SQLAlchemy QueuePool limit of size 500 overflow 0 reached",
                "ERROR checkout-svc leaked session detected request_id=req-2451",
                "WARN postgres-orders idle in transaction sessions accumulating",
            ],
            "reasoning": "PRISM isolated the retry patch as the path leaking SQLAlchemy sessions and exhausting the primary pool.",
        },
        "forge": {
            "confidence": 0.93,
            "selection_logic": "Prioritized mitigation steps that recover capacity first, then remove the leaking deploy, based on the top historical fix sequence.",
            "candidate_fixes": [
                {"action": "Terminate orphaned sessions and restart checkout pods", "success_rate": 0.94},
                {"action": "Roll back checkout retry patch", "success_rate": 0.9},
                {"action": "Increase pool size temporarily to 650", "success_rate": 0.41},
            ],
            "recommended_runbook": "postgres-pool-exhaustion-mitigation",
            "reasoning": "FORGE recommends pod recycle plus rollback because that sequence has the highest recovery rate without increasing database risk.",
        },
        "guardian": {
            "confidence": 0.94,
            "decision": "approve",
            "safety_checks": [
                "Confirmed no data-destructive SQL is proposed",
                "Validated session termination targets idle and leaked sessions only",
                "Checked rollback target is the last known good checkout build",
            ],
            "policy_violations": [],
            "reasoning": "GUARDIAN approved because the runbook is reversible and avoids schema or data mutations under incident pressure.",
        },
    },
    "INC003": {
        "summary": "Image workers degrading due to a sustained heap leak.",
        "detected_at": "2026-05-28T11:03:00Z",
        "duration_minutes": 18,
        "related_services": ["image-worker", "thumbnail-api", "redis-queue", "s3-assets"],
        "metrics": [
            {"name": "CPU", "unit": "%", "current": 67, "series": [41, 43, 49, 54, 58, 62, 67]},
            {"name": "Memory", "unit": "%", "current": 92, "series": [55, 60, 67, 74, 82, 88, 92]},
            {"name": "GC Time", "unit": "ms", "current": 500, "series": [90, 110, 150, 220, 310, 420, 500]},
            {"name": "Objects", "unit": "M", "current": 5.2, "series": [1.2, 1.6, 2.3, 3.1, 4.0, 4.7, 5.2]},
        ],
        "recent_logs": [
            "10:53:07 WARN image-worker heap growth exceeds expected slope",
            "10:53:42 ERROR image-worker task batch-771 retained 428MB after completion",
            "10:54:15 WARN python gc generation2 pause 311ms",
            "10:54:51 ERROR image-worker live object count above 4.1M",
            "10:55:18 WARN thumbnail-api downstream queue ack latency rising",
            "10:55:47 ERROR image-worker memory watermark crossed 88%",
            "10:56:09 WARN redis-queue consumer throughput dropping",
            "10:56:41 ERROR image-worker decoded frame cache not released for job=img-8821",
            "10:57:14 WARN image-worker gc pause 402ms",
            "10:57:46 ERROR image-worker task batch-773 retained 451MB after completion",
            "10:58:22 WARN image-worker object graph dominated by frame_buffer references",
            "10:58:53 ERROR image-worker RSS trend predicts OOM within 8 minutes",
            "10:59:17 WARN thumbnail-api worker pool underfed due to slow acks",
            "10:59:49 ERROR image-worker heap usage above 90%",
            "11:00:26 WARN python gc generation2 pause 488ms",
            "11:01:03 ERROR image-worker 5.0M live objects observed",
            "11:01:42 WARN image-worker release hook missing after transform task",
            "11:02:08 ERROR image-worker memory leak signature matched prior incident",
            "11:02:36 WARN pagerduty trigger P1 worker memory leak",
            "11:02:57 ERROR image-worker incident snapshot captured for SENTINEL",
        ],
        "alert_timeline": [
            {"time": "10:53", "event": "Heap growth alert triggered"},
            {"time": "10:57", "event": "GC pause exceeded 400ms"},
            {"time": "11:01", "event": "Live objects crossed 5M"},
            {"time": "11:03", "event": "PagerDuty P1 fired for memory leak"},
        ],
        "similar_past_incidents": [
            {"id": "INC-2026-0426", "summary": "Frame buffer retention in image pipeline", "success_rate": 0.9},
            {"id": "INC-2026-0302", "summary": "Celery object leak after batch transform change", "success_rate": 0.86},
        ],
        "recent_deployments": [
            {"time": "10:44", "service": "image-worker", "version": "2026.05.28.5", "change": "Frame cache optimization"},
            {"time": "10:18", "service": "thumbnail-api", "version": "2026.05.28.1", "change": "Thumbnail concurrency tuning"},
        ],
        "recommended_runbooks": [
            {"name": "worker-memory-leak-drain-and-rollback", "success_rate": 0.9},
            {"name": "celery-concurrency-throttle", "success_rate": 0.74},
        ],
        "sentinel": {
            "confidence": 0.96,
            "confidence_breakdown": {"metrics": 0.44, "logs": 0.31, "topology": 0.21},
            "evidence": [
                "Heap usage at 92% with object count above 5M fits the leak profile",
                "GC pauses above 500ms show the runtime is trying and failing to reclaim memory",
                "Repeated retained-frame errors identify the leaking code path",
            ],
            "reasoning": "SENTINEL classified this as a memory leak because heap growth, GC time, and retained object logs all point to persistent object retention in image workers.",
        },
        "prism": {
            "confidence": 0.93,
            "correlation_analysis": "Mapped heap growth and GC pause alerts to the 10:44 frame cache optimization deployment in image-worker.",
            "log_snippets": [
                "ERROR image-worker decoded frame cache not released for job=img-8821",
                "WARN image-worker object graph dominated by frame_buffer references",
                "ERROR image-worker 5.0M live objects observed",
            ],
            "reasoning": "PRISM traced the leak to unreleased frame buffers introduced by the latest image-worker optimization.",
        },
        "forge": {
            "confidence": 0.9,
            "selection_logic": "Chose the drain-and-rollback runbook because it quickly restores capacity while preserving in-flight work via controlled worker replacement.",
            "candidate_fixes": [
                {"action": "Drain and restart image workers in batches", "success_rate": 0.9},
                {"action": "Throttle Celery concurrency to 50%", "success_rate": 0.74},
                {"action": "Purge the Redis queue to drop backlog", "success_rate": 0.12},
            ],
            "recommended_runbook": "worker-memory-leak-drain-and-rollback",
            "reasoning": "FORGE rejected queue purge and selected controlled worker restart plus rollback because it has the best success rate and preserves customer jobs.",
        },
        "guardian": {
            "confidence": 0.92,
            "decision": "approve",
            "safety_checks": [
                "Validated rolling restarts preserve queue durability",
                "Ensured rollback target matches signed image-worker artifact",
                "Rejected any step that would purge queued customer uploads",
            ],
            "policy_violations": [],
            "reasoning": "GUARDIAN approved the controlled drain path because it avoids data loss and uses reversible worker operations.",
        },
    },
    "INC004": {
        "summary": "Redis namespace explosion after malformed cache key rollout.",
        "detected_at": "2026-05-28T12:11:00Z",
        "duration_minutes": 13,
        "related_services": ["catalog-api", "redis-cache", "pricing-svc", "search-api"],
        "metrics": [
            {"name": "CPU", "unit": "%", "current": 79, "series": [40, 44, 52, 61, 66, 73, 79]},
            {"name": "Memory", "unit": "%", "current": 88, "series": [58, 62, 68, 73, 79, 84, 88]},
            {"name": "Cache Size", "unit": "GB", "current": 50, "series": [8, 12, 18, 26, 33, 41, 50]},
            {"name": "Evictions", "unit": "/sec", "current": 1000, "series": [40, 55, 120, 280, 520, 760, 1000]},
        ],
        "recent_logs": [
            "12:01:05 WARN catalog-api cache hit ratio fell below 60%",
            "12:01:44 ERROR redis-cache memory usage jumped 4GB in 2 minutes",
            "12:02:09 WARN catalog-api cache key cardinality anomaly detected",
            "12:02:51 ERROR redis-cache evicted_keys rate exceeded 250/sec",
            "12:03:18 WARN pricing-svc repeated cache misses for price shards",
            "12:03:57 ERROR catalog-api cache key template emitted request UUID suffix",
            "12:04:21 WARN search-api catalog latency up 2.3x due to cache misses",
            "12:04:43 ERROR redis-cache key count passed 40M",
            "12:05:19 WARN catalog-api namespace catalog:v3 exploded unexpectedly",
            "12:05:48 ERROR redis-cache memory fragmentation ratio above 1.8",
            "12:06:17 WARN pricing-svc fallback DB reads saturating",
            "12:06:52 ERROR redis-cache evictions sustained above 800/sec",
            "12:07:14 WARN catalog-api recent deploy correlates with key growth",
            "12:07:49 ERROR redis-cache key count passed 75M",
            "12:08:22 WARN catalog-api cache namespace rollback recommended",
            "12:08:57 ERROR redis-cache memory usage reached 50GB",
            "12:09:18 WARN search-api elevated read latency from cache churn",
            "12:09:51 ERROR redis-cache evictions sustained above 1000/sec",
            "12:10:32 WARN pagerduty trigger P2 cache explosion",
            "12:10:56 ERROR catalog-api incident snapshot captured for SENTINEL",
        ],
        "alert_timeline": [
            {"time": "12:01", "event": "Cache hit rate fell below 60%"},
            {"time": "12:04", "event": "Redis key count passed 40M"},
            {"time": "12:08", "event": "Cache size crossed 50GB and evictions >1000/sec"},
            {"time": "12:11", "event": "PagerDuty P2 fired for cache explosion"},
        ],
        "similar_past_incidents": [
            {"id": "INC-2026-0430", "summary": "UUID in cache key caused Redis storm", "success_rate": 0.92},
            {"id": "INC-2026-0126", "summary": "Catalog fragment TTL regression", "success_rate": 0.78},
        ],
        "recent_deployments": [
            {"time": "11:57", "service": "catalog-api", "version": "2026.05.28.7", "change": "Cache key template refactor"},
            {"time": "11:36", "service": "pricing-svc", "version": "2026.05.28.2", "change": "Pricing cache warmup"},
        ],
        "recommended_runbooks": [
            {"name": "redis-namespace-rollback", "success_rate": 0.92},
            {"name": "catalog-cache-fragment-ttl-reset", "success_rate": 0.78},
        ],
        "sentinel": {
            "confidence": 0.95,
            "confidence_breakdown": {"metrics": 0.43, "logs": 0.34, "topology": 0.18},
            "evidence": [
                "Cache size 50GB and keys 100M indicate runaway cardinality",
                "Evictions at 1000/sec show cache pressure rather than node unavailability",
                "Malformed key template logs align with prior cache explosion history",
            ],
            "reasoning": "SENTINEL classified this as a cache explosion because Redis growth, eviction pressure, and cache-key logs point to unbounded namespace creation.",
        },
        "prism": {
            "confidence": 0.92,
            "correlation_analysis": "Linked the key-cardinality anomaly to the 11:57 catalog-api key template deploy and the redis-cache eviction storm.",
            "log_snippets": [
                "ERROR catalog-api cache key template emitted request UUID suffix",
                "ERROR redis-cache key count passed 75M",
                "WARN catalog-api namespace catalog:v3 exploded unexpectedly",
            ],
            "reasoning": "PRISM traced the incident to a cache key template that embedded request UUIDs and created unique keys per request.",
        },
        "forge": {
            "confidence": 0.89,
            "selection_logic": "Recommended namespace rollback over full cache flush because the historical data shows faster recovery with lower customer impact.",
            "candidate_fixes": [
                {"action": "Roll back cache key template and flush poisoned namespace only", "success_rate": 0.92},
                {"action": "Increase Redis memory limit temporarily", "success_rate": 0.37},
                {"action": "Flush the entire cache cluster", "success_rate": 0.28},
            ],
            "recommended_runbook": "redis-namespace-rollback",
            "reasoning": "FORGE chose the scoped namespace rollback because it corrects the source of growth without erasing healthy cache state.",
        },
        "guardian": {
            "confidence": 0.91,
            "decision": "approve",
            "safety_checks": [
                "Confirmed the runbook flushes only the poisoned namespace",
                "Rejected any proposal to flush the full cache cluster",
                "Verified rollback artifact exists for catalog-api 2026.05.28.6",
            ],
            "policy_violations": [],
            "reasoning": "GUARDIAN approved the scoped cache cleanup because it contains the change to a reversible namespace rollback.",
        },
    },
    "INC005": {
        "summary": "Billing queue backlog growing after consumers stopped rebalancing.",
        "detected_at": "2026-05-28T13:26:00Z",
        "duration_minutes": 17,
        "related_services": ["billing-consumer", "kafka-cluster", "ledger-writer", "postgres-billing"],
        "metrics": [
            {"name": "CPU", "unit": "%", "current": 49, "series": [31, 33, 34, 38, 41, 46, 49]},
            {"name": "Memory", "unit": "%", "current": 58, "series": [40, 41, 45, 48, 51, 55, 58]},
            {"name": "Lag", "unit": "messages", "current": 50000, "series": [4200, 6100, 8900, 15200, 24800, 37200, 50000]},
            {"name": "Throughput", "unit": "msg/s", "current": 100, "series": [420, 390, 340, 260, 190, 130, 100]},
        ],
        "recent_logs": [
            "13:16:02 WARN billing-consumer lag exceeded 5000 messages",
            "13:16:38 ERROR kafka coordinator rebalance callback not invoked",
            "13:17:05 WARN billing-consumer throughput dropped below 250 msg/s",
            "13:17:41 ERROR billing-consumer partitions 4,5,9 unassigned",
            "13:18:13 WARN ledger-writer delayed settlement writes",
            "13:18:49 ERROR billing-consumer consumer group stuck in PreparingRebalance",
            "13:19:22 WARN kafka-cluster group heartbeat instability detected",
            "13:19:58 ERROR billing-consumer rollout 2026.05.28.6 changed partition assignment logic",
            "13:20:17 WARN postgres-billing settlement write queue depth rising",
            "13:20:43 ERROR billing-consumer lag crossed 20000 messages",
            "13:21:11 WARN billing-consumer autoscaler unchanged because CPU remained low",
            "13:21:56 ERROR kafka-cluster half the partitions remain idle",
            "13:22:14 WARN ledger-writer customer billing delays now customer visible",
            "13:22:47 ERROR billing-consumer throughput flattened at 100 msg/s",
            "13:23:20 WARN kafka-cluster backlog growth still positive",
            "13:23:54 ERROR billing-consumer lag crossed 50000 messages",
            "13:24:21 WARN recent deployment correlates with rebalance failure",
            "13:24:58 ERROR billing-consumer rebalance hooks disabled by feature flag",
            "13:25:36 WARN pagerduty trigger P1 queue backlog surge",
            "13:25:59 ERROR billing-consumer incident snapshot captured for SENTINEL",
        ],
        "alert_timeline": [
            {"time": "13:16", "event": "Consumer lag crossed 5K messages"},
            {"time": "13:19", "event": "Partitions reported unassigned"},
            {"time": "13:23", "event": "Lag passed 50K and throughput fell to 100 msg/s"},
            {"time": "13:26", "event": "PagerDuty P1 fired for queue backlog surge"},
        ],
        "similar_past_incidents": [
            {"id": "INC-2026-0503", "summary": "Consumer rebalance flag disabled after rollout", "success_rate": 0.93},
            {"id": "INC-2026-0114", "summary": "Low CPU masked Kafka lag growth", "success_rate": 0.81},
        ],
        "recent_deployments": [
            {"time": "13:11", "service": "billing-consumer", "version": "2026.05.28.6", "change": "Partition assignment refactor"},
            {"time": "12:48", "service": "ledger-writer", "version": "2026.05.28.2", "change": "Write batching tuning"},
        ],
        "recommended_runbooks": [
            {"name": "kafka-rebalance-rollback-and-scale", "success_rate": 0.93},
            {"name": "consumer-group-hotfix-enable-rebalance", "success_rate": 0.88},
        ],
        "sentinel": {
            "confidence": 0.97,
            "confidence_breakdown": {"metrics": 0.45, "logs": 0.32, "topology": 0.2},
            "evidence": [
                "Lag 50K with throughput only 100 msg/s indicates consumer starvation",
                "Unassigned partitions point to a rebalance failure, not pure load growth",
                "Low CPU confirms consumers are idle rather than overloaded",
            ],
            "reasoning": "SENTINEL classified this as a queue backlog surge because lag growth, low throughput, and partition assignment errors match a rebalance failure pattern.",
        },
        "prism": {
            "confidence": 0.94,
            "correlation_analysis": "Connected Kafka rebalance errors with the 13:11 partition assignment refactor in billing-consumer.",
            "log_snippets": [
                "ERROR billing-consumer partitions 4,5,9 unassigned",
                "ERROR billing-consumer rollout 2026.05.28.6 changed partition assignment logic",
                "ERROR billing-consumer rebalance hooks disabled by feature flag",
            ],
            "reasoning": "PRISM determined the rollout disabled consumer group rebalancing and left multiple partitions idle.",
        },
        "forge": {
            "confidence": 0.92,
            "selection_logic": "Preferred rollback plus temporary scale-out because historical cases show it restores partition ownership faster than feature-flag hotfixes alone.",
            "candidate_fixes": [
                {"action": "Roll back billing-consumer and force group rebalance", "success_rate": 0.93},
                {"action": "Re-enable rebalance feature flag in place", "success_rate": 0.88},
                {"action": "Increase partition count immediately", "success_rate": 0.24},
            ],
            "recommended_runbook": "kafka-rebalance-rollback-and-scale",
            "reasoning": "FORGE selected rollback first because it is faster, safer, and historically more reliable than resizing the topic mid-incident.",
        },
        "guardian": {
            "confidence": 0.93,
            "decision": "approve",
            "safety_checks": [
                "Validated the runbook preserves Kafka offsets and does not reset consumer positions",
                "Ensured rollback uses the last signed deployment artifact",
                "Rejected topic-partition mutations during active customer backlog",
            ],
            "policy_violations": [],
            "reasoning": "GUARDIAN approved because the plan restores consumption without mutating topics or discarding queued billing events.",
        },
    },
    "INC006": {
        "summary": "Expired TLS certificate on the edge gateway blocked all external API traffic while internal services stayed healthy.",
        "detected_at": "2026-05-28T14:42:00Z",
        "duration_minutes": 9,
        "related_services": ["edge-gateway", "acm-cert", "public-dns", "checkout-api"],
        "metrics": [
            {"name": "TLS Handshake Failures", "unit": "/min", "current": 12400, "series": [250, 840, 2200, 5100, 8200, 10300, 12400]},
            {"name": "External Success Rate", "unit": "%", "current": 3, "series": [98, 90, 72, 40, 18, 8, 3]},
            {"name": "Gateway CPU", "unit": "%", "current": 24, "series": [18, 19, 20, 21, 22, 23, 24]},
            {"name": "Synthetic Probe Failures", "unit": "%", "current": 100, "series": [0, 12, 37, 64, 83, 96, 100]},
        ],
        "recent_logs": [
            "14:33:04 WARN edge-gateway tls handshake failures rising above 300/min",
            "14:33:29 ERROR edge-gateway remote error tls: certificate expired for api.company.com",
            "14:34:01 WARN synthetic-probe ingress-canary reported x509 certificate has expired",
            "14:34:42 ERROR alb listener 443 rejected client negotiation due to expired cert chain",
            "14:35:08 WARN checkout-api internal health checks remain green behind the gateway",
            "14:35:39 ERROR edge-gateway external success rate dropped below 40%",
            "14:36:04 WARN acm-cert renewal workflow last success more than 92 days ago",
            "14:36:31 ERROR cert-rotation lambda AccessDenied on acm:ImportCertificate",
            "14:36:58 WARN public-dns records remain healthy and unchanged",
            "14:37:25 ERROR edge-gateway clients receiving x509 certificate expired responses",
            "14:37:57 WARN synthetic-probe regional failures now global",
            "14:38:22 ERROR edge-gateway external traffic down to 8% success",
            "14:38:46 WARN incident note: internal east-west traffic still healthy",
            "14:39:11 ERROR cert-rotation alert channel silent due to webhook drift",
            "14:39:39 WARN acm-cert latest valid replacement already issued but unattached",
            "14:40:03 ERROR edge-gateway listener still bound to expired certificate arn:aws:acm:old-cert",
            "14:40:41 WARN operator escalation requested for customer-visible outage",
            "14:41:06 ERROR synthetic-probe full outage on public endpoints",
            "14:41:34 WARN pagerduty trigger P0 certificate expiry outage",
            "14:41:58 ERROR edge-gateway incident snapshot captured for SENTINEL",
        ],
        "alert_timeline": [
            {"time": "14:33", "event": "TLS handshake failures breached warning threshold"},
            {"time": "14:36", "event": "ACM renewal workflow reported access failure"},
            {"time": "14:39", "event": "Global synthetic probes failed and success rate dropped below 10%"},
            {"time": "14:42", "event": "PagerDuty P0 fired for public TLS outage"},
        ],
        "similar_past_incidents": [
            {"id": "INC-2026-0449", "summary": "Expired ingress certificate after renewal lambda permission drift", "success_rate": 0.95},
            {"id": "INC-2026-0208", "summary": "Standby ACM cert issued but never attached to ALB listener", "success_rate": 0.89},
        ],
        "recent_deployments": [
            {"time": "14:24", "service": "cert-rotation", "version": "2026.05.28.4", "change": "IAM policy tightening for ACM import"},
            {"time": "13:58", "service": "edge-gateway", "version": "2026.05.28.2", "change": "Listener policy hardening"},
        ],
        "recommended_runbooks": [
            {"name": "edge-certificate-hot-swap", "success_rate": 0.95},
            {"name": "renewal-automation-permission-rollback", "success_rate": 0.88},
        ],
        "sentinel": {
            "confidence": 0.99,
            "confidence_breakdown": {"metrics": 0.41, "logs": 0.39, "topology": 0.17},
            "evidence": [
                "Handshake failures at 12.4K/min match a full TLS outage rather than an app regression",
                "Synthetic probes failed globally while internal checks remained healthy",
                "Expired certificate errors and ACM automation failures point to the same trust boundary",
            ],
            "reasoning": "SENTINEL classified this as an edge TLS outage because certificate-expired errors, synthetic probe failures, and healthy internal services isolate the failure to the public gateway trust path.",
        },
        "prism": {
            "confidence": 0.96,
            "correlation_analysis": "Linked global handshake failures to an expired ACM certificate on the ALB listener and a failed renewal workflow caused by IAM policy drift in cert-rotation.",
            "log_snippets": [
                "ERROR edge-gateway remote error tls: certificate expired for api.company.com",
                "ERROR cert-rotation lambda AccessDenied on acm:ImportCertificate",
                "WARN acm-cert latest valid replacement already issued but unattached",
            ],
            "reasoning": "PRISM determined the outage was not in application code: the edge listener was still attached to an expired certificate because renewal automation failed silently after an IAM change.",
        },
        "forge": {
            "confidence": 0.94,
            "selection_logic": "Selected the hot-swap runbook because it restores public trust fastest, keeps internal services untouched, and defers automation repair until customer traffic is stable.",
            "candidate_fixes": [
                {"action": "Attach the already-issued replacement ACM certificate to the public listener", "success_rate": 0.95},
                {"action": "Roll back the cert-rotation IAM policy and rerun automated import", "success_rate": 0.88},
                {"action": "Bypass TLS temporarily with a plain HTTP listener", "success_rate": 0.03},
            ],
            "recommended_runbook": "edge-certificate-hot-swap",
            "reasoning": "FORGE rejected unsafe trust bypasses and prioritized the smallest reversible action: hot-swap the valid certificate, verify client recovery, then repair rotation automation.",
        },
        "guardian": {
            "confidence": 0.97,
            "decision": "approve",
            "safety_checks": [
                "Verified the replacement certificate is already issued and scoped to the same public domains",
                "Confirmed the runbook changes only listener bindings and does not touch application or data paths",
                "Rejected any workaround that would weaken TLS trust or bypass certificate validation",
            ],
            "policy_violations": [],
            "reasoning": "GUARDIAN approved because the plan restores customer trust with a reversible listener update and keeps the automation repair as a controlled follow-up instead of a live-incident improvisation.",
        },
    },
}


def get_incident_definition(incident_id: str) -> IncidentDefinition:
    try:
        return INCIDENT_DEFINITION_BY_ID[incident_id]
    except KeyError as exc:
        raise ValueError(f"unknown incident_id: {incident_id}") from exc


def list_supported_incident_ids() -> list[str]:
    return sorted(INCIDENT_DETAILS)


def get_incident_details(incident_id: str) -> dict[str, object]:
    if incident_id not in INCIDENT_DETAILS:
        raise ValueError(f"unknown incident_id: {incident_id}")
    return deepcopy(INCIDENT_DETAILS[incident_id])
