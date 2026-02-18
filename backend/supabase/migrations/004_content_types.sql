-- Dynamic Content Types: content_types table, patterns column, seed data
-- Depends on: 001_initial_schema.sql (patterns table)

-- ============================================================
-- Section 1: content_types table
-- ============================================================

CREATE TABLE IF NOT EXISTS content_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    default_mode TEXT NOT NULL DEFAULT 'professional',
    structure_hint TEXT NOT NULL,
    example_type TEXT NOT NULL,
    max_words INT DEFAULT 0,
    description TEXT DEFAULT '',
    review_dimensions JSONB DEFAULT NULL,
    is_builtin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_content_types_slug ON content_types(slug);

ALTER TABLE content_types
ADD CONSTRAINT content_types_mode_check
CHECK (default_mode IN ('casual', 'professional', 'formal'));

-- ============================================================
-- Section 2: Add applicable_content_types to patterns table
-- ============================================================

ALTER TABLE patterns
ADD COLUMN IF NOT EXISTS applicable_content_types TEXT[] DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_patterns_content_types
ON patterns USING GIN (applicable_content_types);

-- ============================================================
-- Section 3: Seed the 9 existing content types
-- ============================================================

INSERT INTO content_types (slug, name, default_mode, structure_hint, example_type, max_words, description, review_dimensions, is_builtin)
VALUES (
    'linkedin',
    'LinkedIn Post',
    'casual',
    'Hook -> Body (2-3 paragraphs) -> CTA/Question',
    'linkedin',
    300,
    'LinkedIn feed post',
    '[{"name": "Messaging", "weight": 1.0, "enabled": true}, {"name": "Positioning", "weight": 1.0, "enabled": true}, {"name": "Quality", "weight": 1.0, "enabled": true}, {"name": "Data Accuracy", "weight": 0.5, "enabled": true}, {"name": "Brand Voice", "weight": 1.5, "enabled": true}, {"name": "Competitive", "weight": 1.0, "enabled": true}]'::jsonb,
    TRUE
) ON CONFLICT (slug) DO NOTHING;

INSERT INTO content_types (slug, name, default_mode, structure_hint, example_type, max_words, description, review_dimensions, is_builtin)
VALUES (
    'email',
    'Professional Email',
    'professional',
    'Subject -> Opening -> Body -> Closing -> Next Steps',
    'email',
    500,
    'Client or prospect email',
    '[{"name": "Messaging", "weight": 1.5, "enabled": true}, {"name": "Positioning", "weight": 1.0, "enabled": true}, {"name": "Quality", "weight": 1.0, "enabled": true}, {"name": "Data Accuracy", "weight": 1.0, "enabled": true}, {"name": "Brand Voice", "weight": 1.0, "enabled": true}, {"name": "Competitive", "weight": 1.0, "enabled": true}]'::jsonb,
    TRUE
) ON CONFLICT (slug) DO NOTHING;

INSERT INTO content_types (slug, name, default_mode, structure_hint, example_type, max_words, description, review_dimensions, is_builtin)
VALUES (
    'landing-page',
    'Landing Page',
    'professional',
    'Headline -> Subhead -> Problem -> Solution -> Proof -> CTA',
    'landing-page',
    1000,
    'Homepage or landing page copy',
    '[{"name": "Messaging", "weight": 1.0, "enabled": true}, {"name": "Positioning", "weight": 1.0, "enabled": true}, {"name": "Quality", "weight": 1.0, "enabled": true}, {"name": "Data Accuracy", "weight": 1.0, "enabled": true}, {"name": "Brand Voice", "weight": 1.0, "enabled": true}, {"name": "Competitive", "weight": 1.0, "enabled": true}]'::jsonb,
    TRUE
) ON CONFLICT (slug) DO NOTHING;

INSERT INTO content_types (slug, name, default_mode, structure_hint, example_type, max_words, description, review_dimensions, is_builtin)
VALUES (
    'comment',
    'Comment/Reply',
    'casual',
    'Acknowledgment -> Insight/Value -> Question (optional)',
    'comment',
    150,
    'Social media comment or reply',
    '[{"name": "Messaging", "weight": 1.0, "enabled": true}, {"name": "Positioning", "weight": 0.0, "enabled": false}, {"name": "Quality", "weight": 1.0, "enabled": true}, {"name": "Data Accuracy", "weight": 0.0, "enabled": false}, {"name": "Brand Voice", "weight": 1.0, "enabled": true}, {"name": "Competitive", "weight": 0.0, "enabled": false}]'::jsonb,
    TRUE
) ON CONFLICT (slug) DO NOTHING;

INSERT INTO content_types (slug, name, default_mode, structure_hint, example_type, max_words, description, review_dimensions, is_builtin)
VALUES (
    'case-study',
    'Case Study',
    'professional',
    'Client Context -> Challenge -> Approach -> Results (quantified) -> Key Takeaways',
    'case-study',
    1500,
    'Client success story with measurable results',
    '[{"name": "Messaging", "weight": 1.0, "enabled": true}, {"name": "Positioning", "weight": 1.0, "enabled": true}, {"name": "Quality", "weight": 1.0, "enabled": true}, {"name": "Data Accuracy", "weight": 1.5, "enabled": true}, {"name": "Brand Voice", "weight": 1.0, "enabled": true}, {"name": "Competitive", "weight": 1.0, "enabled": true}]'::jsonb,
    TRUE
) ON CONFLICT (slug) DO NOTHING;

INSERT INTO content_types (slug, name, default_mode, structure_hint, example_type, max_words, description, review_dimensions, is_builtin)
VALUES (
    'proposal',
    'Sales Proposal',
    'professional',
    'Executive Summary -> Problem -> Proposed Solution -> Deliverables -> Timeline -> Investment -> Next Steps',
    'proposal',
    2000,
    'Sales or project proposal with scope and pricing',
    '[{"name": "Messaging", "weight": 1.5, "enabled": true}, {"name": "Positioning", "weight": 1.0, "enabled": true}, {"name": "Quality", "weight": 1.0, "enabled": true}, {"name": "Data Accuracy", "weight": 1.5, "enabled": true}, {"name": "Brand Voice", "weight": 1.0, "enabled": true}, {"name": "Competitive", "weight": 1.0, "enabled": true}]'::jsonb,
    TRUE
) ON CONFLICT (slug) DO NOTHING;

INSERT INTO content_types (slug, name, default_mode, structure_hint, example_type, max_words, description, review_dimensions, is_builtin)
VALUES (
    'one-pager',
    'One-Pager',
    'professional',
    'Headline -> Problem (1-2 sentences) -> Solution -> Key Benefits (3-4) -> Social Proof -> CTA',
    'one-pager',
    500,
    'Compact executive summary or overview document',
    '[{"name": "Messaging", "weight": 1.5, "enabled": true}, {"name": "Positioning", "weight": 1.0, "enabled": true}, {"name": "Quality", "weight": 1.5, "enabled": true}, {"name": "Data Accuracy", "weight": 1.0, "enabled": true}, {"name": "Brand Voice", "weight": 1.0, "enabled": true}, {"name": "Competitive", "weight": 1.0, "enabled": true}]'::jsonb,
    TRUE
) ON CONFLICT (slug) DO NOTHING;

INSERT INTO content_types (slug, name, default_mode, structure_hint, example_type, max_words, description, review_dimensions, is_builtin)
VALUES (
    'presentation',
    'Presentation Script',
    'professional',
    'Opening Hook -> Key Points (3-5) -> Supporting Data -> Audience Messaging -> Call to Action',
    'presentation',
    800,
    'Presentation talking points and script (not slide text)',
    '[{"name": "Messaging", "weight": 1.5, "enabled": true}, {"name": "Positioning", "weight": 1.0, "enabled": true}, {"name": "Quality", "weight": 1.0, "enabled": true}, {"name": "Data Accuracy", "weight": 1.0, "enabled": true}, {"name": "Brand Voice", "weight": 1.0, "enabled": true}, {"name": "Competitive", "weight": 0.5, "enabled": true}]'::jsonb,
    TRUE
) ON CONFLICT (slug) DO NOTHING;

INSERT INTO content_types (slug, name, default_mode, structure_hint, example_type, max_words, description, review_dimensions, is_builtin)
VALUES (
    'instagram',
    'Instagram Post',
    'casual',
    'Hook (first line, attention-grabbing) -> Story/Value (2-3 short paragraphs) -> CTA -> Hashtags',
    'instagram',
    200,
    'Instagram caption with hook, story, and hashtags',
    '[{"name": "Messaging", "weight": 1.0, "enabled": true}, {"name": "Positioning", "weight": 0.0, "enabled": false}, {"name": "Quality", "weight": 1.0, "enabled": true}, {"name": "Data Accuracy", "weight": 0.0, "enabled": false}, {"name": "Brand Voice", "weight": 1.0, "enabled": true}, {"name": "Competitive", "weight": 0.0, "enabled": false}]'::jsonb,
    TRUE
) ON CONFLICT (slug) DO NOTHING;
