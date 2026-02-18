-- Data validation constraints
-- Enforce valid values at DB level to complement Python validation

-- patterns.use_count must be non-negative
ALTER TABLE patterns
  ADD CONSTRAINT patterns_use_count_nonneg
  CHECK (use_count >= 0);

-- patterns.confidence must be valid level
-- Note: 003_pattern_constraints.sql already has patterns_confidence_check — skip if exists
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'patterns_confidence_valid'
  ) THEN
    ALTER TABLE patterns
      ADD CONSTRAINT patterns_confidence_valid
      CHECK (confidence IN ('LOW', 'MEDIUM', 'HIGH'));
  END IF;
END $$;

-- experiences.category validation
ALTER TABLE experiences
  ADD CONSTRAINT experiences_category_valid
  CHECK (category IN ('content', 'prospects', 'clients'));

-- growth_log.event_type validation
-- Includes all event types used in learn.py + future types from plan
ALTER TABLE growth_log
  ADD CONSTRAINT growth_log_event_type_valid
  CHECK (event_type IN (
    'pattern_created', 'pattern_reinforced', 'pattern_graduated',
    'confidence_upgraded', 'experience_added', 'memory_consolidated',
    'content_reviewed'
  ));

-- content_types.slug format (lowercase alphanumeric + hyphens)
ALTER TABLE content_types
  ADD CONSTRAINT content_types_slug_format
  CHECK (slug ~ '^[a-z0-9][a-z0-9-]*[a-z0-9]$' OR length(slug) = 1);

-- Record migration
INSERT INTO schema_migrations (version, description)
VALUES ('008_data_constraints', 'CHECK constraints for data validation')
ON CONFLICT (version) DO NOTHING;
