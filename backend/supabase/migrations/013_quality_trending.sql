-- Quality trending indexes on review_history
CREATE INDEX IF NOT EXISTS idx_review_history_type_date
    ON review_history(content_type, review_date DESC);
CREATE INDEX IF NOT EXISTS idx_review_history_score
    ON review_history(overall_score);

-- Extend growth_log event_type to include new lifecycle events
-- Must drop and recreate CHECK constraint (actual name from 008: growth_log_event_type_valid)
ALTER TABLE growth_log DROP CONSTRAINT IF EXISTS growth_log_event_type_valid;
ALTER TABLE growth_log DROP CONSTRAINT IF EXISTS growth_log_event_type_check;
ALTER TABLE growth_log ADD CONSTRAINT growth_log_event_type_valid CHECK (
    event_type IN (
        'pattern_created', 'pattern_reinforced', 'pattern_graduated',
        'confidence_upgraded', 'confidence_downgraded',
        'experience_added', 'memory_consolidated', 'content_reviewed',
        'project_created', 'project_completed',
        'milestone_reached', 'example_promoted'
    )
);

-- Extend experiences category to include 'products' and 'general'
-- Must drop and recreate CHECK constraint (actual name from 008: experiences_category_valid)
ALTER TABLE experiences DROP CONSTRAINT IF EXISTS experiences_category_valid;
ALTER TABLE experiences DROP CONSTRAINT IF EXISTS experiences_category_check;
ALTER TABLE experiences ADD CONSTRAINT experiences_category_valid CHECK (
    category IN ('content', 'prospects', 'clients', 'products', 'general')
);

-- Add optional project_id FK to experiences (nullable for existing records)
ALTER TABLE experiences ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES projects(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_experiences_project ON experiences(project_id);

-- Add review_dimensions JSONB column to review_history for dimensional tracking
ALTER TABLE review_history ADD COLUMN IF NOT EXISTS dimension_details JSONB DEFAULT '{}';

-- Add consecutive_failures tracking to patterns for confidence downgrade
ALTER TABLE patterns ADD COLUMN IF NOT EXISTS consecutive_failures INT DEFAULT 0;

-- Track schema migration
INSERT INTO schema_migrations (version, description)
VALUES ('012_projects_lifecycle', 'Project lifecycle tables (projects + project_artifacts)')
ON CONFLICT (version) DO NOTHING;

INSERT INTO schema_migrations (version, description)
VALUES ('013_quality_trending', 'Quality trending indexes, extended constraints, project FK')
ON CONFLICT (version) DO NOTHING;
