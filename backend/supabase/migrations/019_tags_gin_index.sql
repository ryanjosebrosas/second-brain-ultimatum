-- Migration: 019_tags_gin_index
-- Description: Add GIN index on knowledge_repo.tags for fast array element lookups.
--              Required by the PostgREST workaround that packs structured fields
--              (author, client, file_hash) into the tags array as prefixed strings.
--              Without this index, ANY(tags) queries do full table scans.

CREATE INDEX IF NOT EXISTS idx_knowledge_repo_tags_gin
    ON knowledge_repo USING GIN(tags);

INSERT INTO schema_migrations (version, description)
VALUES ('019_tags_gin_index', 'GIN index on knowledge_repo.tags for array element lookups')
ON CONFLICT (version) DO NOTHING;
