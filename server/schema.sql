-- NEXUS Production Database Schema
-- SQLite database for incident and audit log storage
-- Supports multi-tenant, multi-operator deployment
-- Created: 2026-06-17

-- ============================================================================
-- TABLE: incidents
-- Purpose: Store NEXUS incidents with tenant isolation
-- ============================================================================

CREATE TABLE IF NOT EXISTS incidents (
    -- Primary identifier (globally unique)
    nexus_incident_id TEXT PRIMARY KEY,

    -- Tenant isolation (critical for security)
    tenant_id TEXT NOT NULL,

    -- Timestamps for lifecycle tracking
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Flexible data storage (JSON for extensibility)
    data JSONB NOT NULL,

    -- Compound unique constraint (tenant + incident_id)
    UNIQUE(tenant_id, nexus_incident_id),

    -- Data integrity checks
    CHECK (length(nexus_incident_id) > 0),
    CHECK (length(tenant_id) > 0),
    CHECK (json_valid(data))
);

-- Index 1: Tenant isolation (critical for queries)
CREATE INDEX IF NOT EXISTS idx_incidents_tenant_id
ON incidents(tenant_id);

-- Index 2: Created timestamp (for recent incidents, sorting)
CREATE INDEX IF NOT EXISTS idx_incidents_created_at
ON incidents(created_at DESC);

-- Index 3: Updated timestamp (for modified incidents)
CREATE INDEX IF NOT EXISTS idx_incidents_updated_at
ON incidents(updated_at DESC);

-- Compound index for tenant + created_at (common query pattern)
CREATE INDEX IF NOT EXISTS idx_incidents_tenant_created
ON incidents(tenant_id, created_at DESC);

-- ============================================================================
-- TABLE: audit_logs
-- Purpose: Complete audit trail for compliance and debugging
-- ============================================================================

CREATE TABLE IF NOT EXISTS audit_logs (
    -- Auto-incrementing primary key
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Timestamp of audit event
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Event classification (e.g., 'incident_created', 'guardian_decision', 'auth_failure')
    event_type TEXT NOT NULL,

    -- Tenant isolation (critical for multi-tenant)
    tenant_id TEXT NOT NULL,

    -- User who triggered the event (nullable for system events)
    user_id TEXT,

    -- Flexible event data (what happened, why, outcome)
    data JSONB NOT NULL,

    -- Data integrity checks
    CHECK (length(event_type) > 0),
    CHECK (length(tenant_id) > 0),
    CHECK (json_valid(data))
);

-- Index 1: Tenant isolation
CREATE INDEX IF NOT EXISTS idx_audit_logs_tenant_id
ON audit_logs(tenant_id);

-- Index 2: Event timestamp (for recent audits)
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at
ON audit_logs(created_at DESC);

-- Index 3: Event type classification
CREATE INDEX IF NOT EXISTS idx_audit_logs_event_type
ON audit_logs(event_type);

-- Compound index for tenant + created_at (common query pattern)
CREATE INDEX IF NOT EXISTS idx_audit_logs_tenant_created
ON audit_logs(tenant_id, created_at DESC);

-- Compound index for tenant + event_type (filter by event in tenant)
CREATE INDEX IF NOT EXISTS idx_audit_logs_tenant_event
ON audit_logs(tenant_id, event_type);

-- ============================================================================
-- SCHEMA NOTES
-- ============================================================================
--
-- Tenant Isolation:
--   - CRITICAL for security: all queries must include tenant_id
--   - Indexed for performance: no full table scans by tenant
--   - Enforced at query level (application must validate)
--
-- JSONB Data Storage:
--   - Provides flexibility for schema evolution
--   - Validates JSON structure on insert
--   - Can be indexed for specific fields if needed (JSON1 extension)
--
-- Timestamps:
--   - created_at: immutable (incident creation time)
--   - updated_at: mutable (last modification time)
--   - Both indexed for time-based queries
--
-- Performance Considerations:
--   - Compound indexes on (tenant_id, timestamp) for common queries
--   - Index on event_type for audit filtering
--   - All indexes support DESC ordering for "most recent" queries
--
-- Scalability:
--   - SQLite handles up to ~10K concurrent requests well
--   - For 100K+ requests, migrate to PostgreSQL (no schema changes needed)
--   - JSONB storage allows schema-less extensibility
--
-- ============================================================================
