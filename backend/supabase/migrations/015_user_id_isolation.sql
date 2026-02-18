-- Migration 015: Add user_id isolation to all user-scoped tables
-- Allows multiple users to share one Supabase deployment with fully isolated data.
-- PostgreSQL 15+ (Supabase): ADD COLUMN NOT NULL DEFAULT 'constant' is a near-instant
-- metadata operation — no table rewrite, no backfill needed.

-- === ADD user_id COLUMN TO ALL USER-SCOPED TABLES ===

ALTER TABLE patterns            ADD COLUMN IF NOT EXISTS user_id TEXT NOT NULL DEFAULT 'ryan';
ALTER TABLE experiences         ADD COLUMN IF NOT EXISTS user_id TEXT NOT NULL DEFAULT 'ryan';
ALTER TABLE brain_health        ADD COLUMN IF NOT EXISTS user_id TEXT NOT NULL DEFAULT 'ryan';
ALTER TABLE growth_log          ADD COLUMN IF NOT EXISTS user_id TEXT NOT NULL DEFAULT 'ryan';
ALTER TABLE review_history      ADD COLUMN IF NOT EXISTS user_id TEXT NOT NULL DEFAULT 'ryan';
ALTER TABLE confidence_history  ADD COLUMN IF NOT EXISTS user_id TEXT NOT NULL DEFAULT 'ryan';
ALTER TABLE memory_content      ADD COLUMN IF NOT EXISTS user_id TEXT NOT NULL DEFAULT 'ryan';
ALTER TABLE examples            ADD COLUMN IF NOT EXISTS user_id TEXT NOT NULL DEFAULT 'ryan';
ALTER TABLE knowledge_repo      ADD COLUMN IF NOT EXISTS user_id TEXT NOT NULL DEFAULT 'ryan';
ALTER TABLE projects            ADD COLUMN IF NOT EXISTS user_id TEXT NOT NULL DEFAULT 'ryan';

-- === INDEXES FOR QUERY PERFORMANCE ===

CREATE INDEX IF NOT EXISTS idx_patterns_user_id           ON patterns(user_id);
CREATE INDEX IF NOT EXISTS idx_experiences_user_id        ON experiences(user_id);
CREATE INDEX IF NOT EXISTS idx_brain_health_user_id       ON brain_health(user_id);
CREATE INDEX IF NOT EXISTS idx_growth_log_user_id         ON growth_log(user_id);
CREATE INDEX IF NOT EXISTS idx_review_history_user_id     ON review_history(user_id);
CREATE INDEX IF NOT EXISTS idx_confidence_history_user_id ON confidence_history(user_id);
CREATE INDEX IF NOT EXISTS idx_memory_content_user_id     ON memory_content(user_id);
CREATE INDEX IF NOT EXISTS idx_examples_user_id           ON examples(user_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_repo_user_id     ON knowledge_repo(user_id);
CREATE INDEX IF NOT EXISTS idx_projects_user_id           ON projects(user_id);

-- === UPDATE vector_search FUNCTION TO FILTER BY USER ===
-- Adds p_user_id parameter so vector searches only return the requesting user's rows.
-- Default 'ryan' preserves backward compatibility for any callers not yet updated.

CREATE OR REPLACE FUNCTION vector_search(
  query_embedding vector(1024),
  match_table TEXT,
  match_count INT DEFAULT 10,
  match_threshold FLOAT DEFAULT 0.7,
  p_user_id TEXT DEFAULT 'ryan'
)
RETURNS TABLE (
  id UUID,
  content TEXT,
  title TEXT,
  category TEXT,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY EXECUTE format(
    'SELECT id, COALESCE(content, pattern_text, '''') as content, '
    'COALESCE(title, name, '''') as title, '
    'COALESCE(category, topic, '''') as category, '
    '1 - (embedding <=> $1) as similarity '
    'FROM %I '
    'WHERE embedding IS NOT NULL '
    'AND user_id = $4 '
    'AND 1 - (embedding <=> $1) >= $2 '
    'ORDER BY embedding <=> $1 '
    'LIMIT $3',
    match_table
  ) USING query_embedding, match_threshold, match_count, p_user_id;
END;
$$;

-- === RECORD MIGRATION ===

INSERT INTO schema_migrations (version, description)
VALUES ('015_user_id_isolation', 'Add user_id column to all user-scoped tables for multi-user isolation')
ON CONFLICT (version) DO NOTHING;
