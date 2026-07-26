CREATE TABLE IF NOT EXISTS entity (
    entity_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    normalized_name TEXT,
    entity_type TEXT NOT NULL,
    source TEXT NOT NULL,
    designated BOOLEAN NOT NULL DEFAULT FALSE,
    programs JSONB NOT NULL DEFAULT '[]'::jsonb,
    country TEXT NOT NULL DEFAULT '',
    identifiers JSONB NOT NULL DEFAULT '{}'::jsonb,
    remarks TEXT NOT NULL DEFAULT '',
    retrieved_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS entity_alias (
    alias_id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL REFERENCES entity(entity_id),
    name TEXT NOT NULL,
    normalized_name TEXT,
    alias_type TEXT NOT NULL,
    source TEXT NOT NULL,
    weak BOOLEAN NOT NULL DEFAULT FALSE,
    remarks TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS entity_address (
    address_id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL REFERENCES entity(entity_id),
    address TEXT NOT NULL DEFAULT '',
    city_state_postal TEXT NOT NULL DEFAULT '',
    country TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL,
    remarks TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS relationship (
    relationship_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES entity(entity_id),
    target_id TEXT NOT NULL REFERENCES entity(entity_id),
    relationship_type TEXT NOT NULL,
    source TEXT NOT NULL,
    ownership_pct NUMERIC(7,3),
    confidence NUMERIC(5,4) NOT NULL DEFAULT 1,
    valid_from DATE,
    valid_to DATE,
    evidence TEXT NOT NULL DEFAULT '',
    analyst_status TEXT NOT NULL DEFAULT 'unreviewed',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS screening_result (
    screening_result_id BIGSERIAL PRIMARY KEY,
    run_id TEXT NOT NULL,
    query TEXT NOT NULL,
    entity_id TEXT NOT NULL REFERENCES entity(entity_id),
    matched_name TEXT NOT NULL,
    match_type TEXT NOT NULL,
    score NUMERIC(6,2) NOT NULL,
    reasons JSONB NOT NULL DEFAULT '[]'::jsonb,
    review_status TEXT NOT NULL DEFAULT 'unreviewed',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS analyst_review (
    review_id BIGSERIAL PRIMARY KEY,
    run_id TEXT NOT NULL,
    entity_id TEXT NOT NULL DEFAULT '',
    target_name TEXT NOT NULL DEFAULT '',
    system_classification TEXT NOT NULL,
    system_version TEXT NOT NULL DEFAULT '',
    disposition TEXT NOT NULL CHECK (
        disposition IN (
            'needs_more_information',
            'identity_confirmed',
            'identity_rejected',
            'escalated_for_compliance_review',
            'closed_no_material_indicator'
        )
    ),
    reviewer TEXT NOT NULL,
    notes TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS case_workflow_event (
    event_id BIGSERIAL PRIMARY KEY,
    run_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('open', 'in_review', 'pending_information', 'escalated', 'closed')
    ),
    priority TEXT NOT NULL CHECK (
        priority IN ('low', 'normal', 'high', 'critical')
    ),
    assignee TEXT NOT NULL DEFAULT '',
    tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    actor TEXT NOT NULL,
    notes TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_entity_normalized_name ON entity(normalized_name);
CREATE INDEX IF NOT EXISTS idx_alias_normalized_name ON entity_alias(normalized_name);
CREATE INDEX IF NOT EXISTS idx_relationship_source ON relationship(source_id);
CREATE INDEX IF NOT EXISTS idx_relationship_target ON relationship(target_id);
CREATE INDEX IF NOT EXISTS idx_screening_run ON screening_result(run_id);
CREATE INDEX IF NOT EXISTS idx_analyst_review_run ON analyst_review(run_id);
CREATE INDEX IF NOT EXISTS idx_analyst_review_created ON analyst_review(created_at);
CREATE INDEX IF NOT EXISTS idx_case_workflow_run ON case_workflow_event(run_id);
CREATE INDEX IF NOT EXISTS idx_case_workflow_created ON case_workflow_event(created_at);
