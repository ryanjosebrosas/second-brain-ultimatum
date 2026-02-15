-- Growth Tracking Tables for Second Brain
-- Run this in your Supabase SQL Editor

-- 1. Growth Log — records every brain growth event
CREATE TABLE IF NOT EXISTS growth_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type TEXT NOT NULL,  -- pattern_created, pattern_reinforced, confidence_upgraded, experience_recorded
    event_date DATE NOT NULL DEFAULT current_date,
    pattern_name TEXT,
    pattern_topic TEXT,
    details JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_growth_log_date ON growth_log(event_date DESC);
CREATE INDEX IF NOT EXISTS idx_growth_log_type ON growth_log(event_type);

-- 2. Review History — records every content review result
CREATE TABLE IF NOT EXISTS review_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_date DATE NOT NULL DEFAULT current_date,
    content_type TEXT,
    overall_score FLOAT NOT NULL,
    verdict TEXT NOT NULL,
    dimension_scores JSONB DEFAULT '[]',
    top_strengths JSONB DEFAULT '[]',
    critical_issues JSONB DEFAULT '[]',
    content_preview TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_review_history_date ON review_history(review_date DESC);

-- 3. Confidence History — records every confidence level transition
CREATE TABLE IF NOT EXISTS confidence_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transition_date DATE NOT NULL DEFAULT current_date,
    pattern_name TEXT NOT NULL,
    pattern_topic TEXT,
    from_confidence TEXT NOT NULL,
    to_confidence TEXT NOT NULL,
    use_count INT NOT NULL DEFAULT 1,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_confidence_history_date ON confidence_history(transition_date DESC);
CREATE INDEX IF NOT EXISTS idx_confidence_history_pattern ON confidence_history(pattern_name);
