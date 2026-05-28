from server.models import IncidentDefinition


INCIDENT_TYPES: tuple[IncidentDefinition, ...] = (
    IncidentDefinition(
        id="INC001",
        name="Payment Service Timeout",
        severity="P2",
        difficulty="Easy",
        symptoms=[
            "Payment API returning HTTP 504 after 30s",
            "Error rate spiked from 0.1% to 18%",
            "Downstream order service reporting failed transactions",
        ],
        system_context={
            "service": "payment-svc",
            "language": "Python/FastAPI",
            "infra": "AWS ECS Fargate",
            "dependencies": ["postgres-payments", "stripe-api", "redis-sessions"],
        },
        root_cause="Third-party Stripe API degradation causing upstream timeout",
        fix="Increase timeout from 10s to 30s and add retry logic with exponential backoff",
    ),
    IncidentDefinition(
        id="INC002",
        name="Checkout Database Connection Pool Exhaustion",
        severity="P1",
        difficulty="Easy",
        symptoms=[
            "Checkout API latency exceeds 12 seconds",
            "Database connection pool saturated at 100%",
            "Pods remain healthy but requests queue indefinitely",
        ],
        system_context={
            "service": "checkout-svc",
            "language": "Python/FastAPI",
            "infra": "Kubernetes on EKS",
            "dependencies": ["postgres-orders", "redis-cart"],
        },
        root_cause="Leaked database sessions exhaust the connection pool",
        fix="Recycle affected pods and patch the request path to close idle sessions promptly",
    ),
    IncidentDefinition(
        id="INC003",
        name="Worker Memory Leak",
        severity="P1",
        difficulty="Medium",
        symptoms=[
            "Background workers restart every 20 minutes",
            "RSS memory climbs linearly until OOM kill",
            "Queue backlog grows while CPU stays moderate",
        ],
        system_context={
            "service": "jobs-worker",
            "language": "Python/Celery",
            "infra": "AWS ECS EC2",
            "dependencies": ["redis-queue", "s3-assets"],
        },
        root_cause="Image-processing tasks retain large objects between jobs",
        fix="Restart workers, lower concurrency temporarily, and release task buffers after each job",
    ),
    IncidentDefinition(
        id="INC004",
        name="Redis Cache Eviction Storm",
        severity="P2",
        difficulty="Medium",
        symptoms=[
            "Cache hit rate fell from 94% to 21%",
            "Redis reports evicted_keys surging",
            "Application latency spikes during hot reads",
        ],
        system_context={
            "service": "catalog-api",
            "language": "Node.js",
            "infra": "GCP Cloud Run",
            "dependencies": ["redis-cache", "postgres-catalog"],
        },
        root_cause="New key pattern exploded cache cardinality and forced aggressive eviction",
        fix="Roll back the cache key change and raise TTL discipline for large payloads",
    ),
    IncidentDefinition(
        id="INC005",
        name="Kafka Consumer Lag Surge",
        severity="P1",
        difficulty="Medium",
        symptoms=[
            "Consumer lag jumps past 3 million messages",
            "Autoscaling is flat despite backlog growth",
            "Billing events arrive hours late downstream",
        ],
        system_context={
            "service": "billing-consumer",
            "language": "Go",
            "infra": "Kubernetes on GKE",
            "dependencies": ["kafka-cluster", "postgres-billing"],
        },
        root_cause="A bad deployment disabled partition rebalancing and left consumers idle",
        fix="Roll back the deployment and force a consumer group rebalance",
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
