-- Pattern reinforcement robustness: add type safety and uniqueness constraints.
-- CHECK ensures confidence column only accepts valid values (LOW, MEDIUM, HIGH).
-- UNIQUE index on lower(name) prevents duplicate patterns regardless of casing.
-- NOTE: Will fail if existing data contains invalid confidence values (fresh DB assumed).

ALTER TABLE patterns
ADD CONSTRAINT patterns_confidence_check
CHECK (confidence IN ('LOW', 'MEDIUM', 'HIGH'));

CREATE UNIQUE INDEX idx_patterns_name_unique
ON patterns (lower(name));
