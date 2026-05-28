from server.models import IncidentDefinition


INCIDENT_TYPES: tuple[IncidentDefinition, ...] = (
    IncidentDefinition(
        id="INC001",
        name="API Timeout Cascade",
        severity="P2",
        difficulty="Easy",
        symptoms=[
            "Public API latency sustained above 5000ms for 11 minutes",
            "CPU saturation reached 95% on api-gateway pods",
            "HTTP 5xx error rate climbed to 50 requests per second",
        ],
        system_context={
            "service": "api-gateway",
            "language": "Python/FastAPI",
            "infra": "Kubernetes on EKS",
            "dependencies": ["auth-svc", "orders-api", "redis-sessions", "stripe-api"],
        },
        root_cause="Runaway retry storm on downstream auth calls exhausted worker threads and drove API timeouts",
        fix="Drain hot pods, cap downstream retries, and scale the gateway deployment while the auth timeout patch rolls out",
    ),
    IncidentDefinition(
        id="INC002",
        name="Database Connection Pool Exhaustion",
        severity="P1",
        difficulty="Easy",
        symptoms=[
            "Database pool usage locked at 500 of 500 connections",
            "P95 query latency exceeded 10 seconds for checkout writes",
            "Active query count held above 200 while request queues grew",
        ],
        system_context={
            "service": "checkout-svc",
            "language": "Python/FastAPI",
            "infra": "Kubernetes on EKS",
            "dependencies": ["postgres-orders", "redis-cart", "inventory-svc"],
        },
        root_cause="Leaked SQLAlchemy sessions after a checkout retry patch exhausted the primary Postgres pool",
        fix="Recycle checkout pods, terminate orphaned sessions, and roll back the retry patch until connection cleanup is fixed",
    ),
    IncidentDefinition(
        id="INC003",
        name="Worker Memory Leak",
        severity="P1",
        difficulty="Medium",
        symptoms=[
            "Heap usage reached 92% across image-worker tasks",
            "Garbage collection pauses exceeded 500ms on every major cycle",
            "Live object count crossed 5 million and continued growing",
        ],
        system_context={
            "service": "image-worker",
            "language": "Python/Celery",
            "infra": "AWS ECS EC2",
            "dependencies": ["redis-queue", "s3-assets", "thumbnail-api"],
        },
        root_cause="Image-processing tasks retained decoded frames in a shared cache and never released references between jobs",
        fix="Restart leaking workers, reduce concurrency, and ship the object lifecycle patch that clears frame buffers after each task",
    ),
    IncidentDefinition(
        id="INC004",
        name="Cache Cardinality Explosion",
        severity="P2",
        difficulty="Medium",
        symptoms=[
            "Redis cache size expanded to 50GB in under 15 minutes",
            "Key cardinality crossed 100 million after the latest deploy",
            "Eviction rate sustained above 1000 keys per second",
        ],
        system_context={
            "service": "catalog-api",
            "language": "Node.js",
            "infra": "GCP Cloud Run",
            "dependencies": ["redis-cache", "postgres-catalog", "pricing-svc"],
        },
        root_cause="A malformed cache key template embedded request UUIDs and caused unbounded key growth",
        fix="Roll back the cache key template, flush only the poisoned namespace, and reapply bounded TTLs for catalog fragments",
    ),
    IncidentDefinition(
        id="INC005",
        name="Queue Backlog Surge",
        severity="P1",
        difficulty="Medium",
        symptoms=[
            "Queue lag crossed 50000 messages and kept growing",
            "Consumer throughput flattened at 100 messages per second",
            "Partition depth increased continuously after the latest rollout",
        ],
        system_context={
            "service": "billing-consumer",
            "language": "Go",
            "infra": "Kubernetes on GKE",
            "dependencies": ["kafka-cluster", "postgres-billing", "ledger-writer"],
        },
        root_cause="A rollout disabled consumer group rebalancing and left half the partitions unassigned",
        fix="Roll back the consumer deployment, trigger a rebalance, and temporarily scale workers until backlog returns to baseline",
    ),
    IncidentDefinition(
        id="INC006",
        name="Expired TLS Certificate On API Gateway",
        severity="P0",
        difficulty="Hard",
        symptoms=[
            "All external API calls fail TLS handshake",
            "Synthetic checks report certificate expired",
            "Internal services remain healthy behind the gateway",
        ],
        system_context={
            "service": "edge-gateway",
            "language": "Nginx",
            "infra": "AWS ALB + EC2",
            "dependencies": ["acm-cert", "public-dns"],
        },
        root_cause="Certificate rotation automation failed silently before renewal",
        fix="Attach the renewed certificate and restore the rotation alerting path",
    ),
    IncidentDefinition(
        id="INC007",
        name="Kubernetes DNS Resolution Failure",
        severity="P0",
        difficulty="Hard",
        symptoms=[
            "Multiple services return host not found errors",
            "CoreDNS pods show crash loops after config rollout",
            "Cross-service traffic failure spans three namespaces",
        ],
        system_context={
            "service": "cluster-network",
            "language": "Platform",
            "infra": "Kubernetes on EKS",
            "dependencies": ["coredns", "route53", "service-mesh"],
        },
        root_cause="Invalid CoreDNS config map rollout broke internal name resolution",
        fix="Revert the CoreDNS config and restart the DNS deployment",
    ),
    IncidentDefinition(
        id="INC008",
        name="Primary Region Message Queue Outage",
        severity="P0",
        difficulty="Nightmare",
        symptoms=[
            "Primary queue endpoint is unreachable from all app tiers",
            "Failover queue remains idle despite outage",
            "Order processing halts across two critical workflows",
        ],
        system_context={
            "service": "messaging-backbone",
            "language": "Platform",
            "infra": "Multi-region AWS",
            "dependencies": ["sqs-primary", "sqs-secondary", "route53-health-checks"],
        },
        root_cause="Regional failover automation did not switch producers to the standby queue",
        fix="Promote the standby queue endpoint and replay queued messages after traffic recovers",
    ),
)


def load_incident_types() -> list[IncidentDefinition]:
    return list(INCIDENT_TYPES)
