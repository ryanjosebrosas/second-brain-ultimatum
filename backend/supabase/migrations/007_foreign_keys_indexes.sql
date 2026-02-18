-- Foreign key constraints, missing indexes, unique constraints, schema versioning
-- Using ON DELETE CASCADE to prevent orphaned records

-- Clean up orphaned entries before adding FK constraints
DELETE FROM growth_log WHERE pattern_name NOT IN (SELECT name FROM patterns);
DELETE FROM confidence_history WHERE pattern_name NOT IN (SELECT name FROM patterns);

-- growth_log.pattern_name → patterns.name
ALTER TABLE growth_log
  ADD CONSTRAINT fk_growth_log_pattern
  FOREIGN KEY (pattern_name) REFERENCES patterns(name) ON DELETE CASCADE;

-- confidence_history.pattern_name → patterns.name
ALTER TABLE confidence_history
  ADD CONSTRAINT fk_confidence_history_pattern
  FOREIGN KEY (pattern_name) REFERENCES patterns(name) ON DELETE CASCADE;

-- Missing indexes for frequently queried columns
CREATE INDEX IF NOT EXISTS idx_patterns_date_updated
  ON patterns(date_updated DESC);

CREATE INDEX IF NOT EXISTS idx_examples_created_at
  ON examples(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_knowledge_repo_created_at
  ON knowledge_repo(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_growth_log_pattern_name
  ON growth_log(pattern_name);

-- Unique constraints for migration idempotency (enable safe upsert on re-migration)
ALTER TABLE memory_content
  ADD CONSTRAINT memory_content_unique_source
  UNIQUE (category, subcategory, source_file);

ALTER TABLE examples
  ADD CONSTRAINT examples_unique_source
  UNIQUE (content_type, source_file);

ALTER TABLE knowledge_repo
  ADD CONSTRAINT knowledge_repo_unique_source
  UNIQUE (category, source_file);

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_migrations (
  version TEXT PRIMARY KEY,
  applied_at TIMESTAMPTZ DEFAULT now(),
  description TEXT
);

-- Record all migrations applied so far
INSERT INTO schema_migrations (version, description) VALUES
  ('001_initial_schema', 'Core tables: patterns, experiences, brain_health, memory_content'),
  ('002_examples_knowledge', 'Examples and knowledge_repo tables'),
  ('003_pattern_constraints', 'Pattern uniqueness and confidence validation'),
  ('004_content_types', 'Dynamic content types with seed data'),
  ('005_growth_tracking_tables', 'Growth log, review history, confidence history'),
  ('006_rls_policies', 'Row Level Security on all tables'),
  ('007_foreign_keys_indexes', 'Foreign keys, indexes, unique constraints, schema versioning')
ON CONFLICT (version) DO NOTHING;
