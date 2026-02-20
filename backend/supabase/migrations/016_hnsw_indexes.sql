-- Migration: 016_hnsw_indexes
-- Description: Replace IVFFlat vector indexes with HNSW for better recall and
--              performance with changing data. HNSW does not require training data
--              and handles incremental inserts without stale centroids.
--
-- Parameters chosen:
--   m = 16 (default, good balance of recall vs memory)
--   ef_construction = 128 (2x default for better index quality)
--
-- Note: On large tables, consider running these outside a transaction with
--       CREATE INDEX CONCURRENTLY for zero-downtime. Supabase dashboard
--       migrations run inside transactions, so for production with large
--       datasets, execute these via psql directly.

-- Drop existing IVFFlat indexes
DROP INDEX IF EXISTS patterns_embedding_idx;
DROP INDEX IF EXISTS memory_content_embedding_idx;
DROP INDEX IF EXISTS examples_embedding_idx;
DROP INDEX IF EXISTS knowledge_repo_embedding_idx;

-- Create HNSW indexes with cosine distance ops
CREATE INDEX IF NOT EXISTS patterns_embedding_hnsw_idx
  ON patterns USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 128);

CREATE INDEX IF NOT EXISTS memory_content_embedding_hnsw_idx
  ON memory_content USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 128);

CREATE INDEX IF NOT EXISTS examples_embedding_hnsw_idx
  ON examples USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 128);

CREATE INDEX IF NOT EXISTS knowledge_repo_embedding_hnsw_idx
  ON knowledge_repo USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 128);

-- Track migration
INSERT INTO schema_migrations (version, description)
VALUES ('016_hnsw_indexes', 'Replace IVFFlat with HNSW vector indexes (m=16, ef_construction=128)')
ON CONFLICT (version) DO NOTHING;
