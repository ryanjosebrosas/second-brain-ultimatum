-- Template Bank: persistent storage for reusable content templates
CREATE TABLE IF NOT EXISTS templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,

    -- Core metadata
    name TEXT NOT NULL,
    content_type TEXT NOT NULL,
    description TEXT DEFAULT '',
    tags TEXT[] DEFAULT '{}',

    -- Template body (full structure with [PLACEHOLDER] markers)
    body TEXT NOT NULL DEFAULT '',
    structure_hint TEXT DEFAULT '',

    -- Usage guidance
    when_to_use TEXT DEFAULT '',
    when_not_to_use TEXT DEFAULT '',
    customization_guide TEXT DEFAULT '',

    -- Provenance
    source_deliverable TEXT DEFAULT '',
    ai_generated BOOLEAN DEFAULT FALSE,

    -- Usage tracking
    use_count INT DEFAULT 0,
    last_used_at TIMESTAMPTZ,

    -- Flags
    is_active BOOLEAN DEFAULT TRUE,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_templates_user_id ON templates(user_id);
CREATE INDEX IF NOT EXISTS idx_templates_content_type ON templates(content_type);
CREATE INDEX IF NOT EXISTS idx_templates_tags ON templates USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_templates_active ON templates(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_templates_updated ON templates(updated_at DESC);

-- Row Level Security
ALTER TABLE templates ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users see own templates" ON templates
    FOR ALL USING (user_id = current_setting('app.user_id', true));

-- Register migration
INSERT INTO schema_migrations (version, description)
VALUES ('021_template_bank', 'Template bank table for reusable content templates')
ON CONFLICT (version) DO NOTHING;
