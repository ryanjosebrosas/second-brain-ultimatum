-- Migrate embedding columns from OpenAI (1536) to Voyage (1024) dimensions
-- WARNING: This drops existing embeddings. Re-run migration after deployment.

-- Step 1: Drop indexes that depend on embedding columns
DROP INDEX IF EXISTS patterns_embedding_idx;
DROP INDEX IF EXISTS memory_content_embedding_idx;
DROP INDEX IF EXISTS examples_embedding_idx;
DROP INDEX IF EXISTS knowledge_repo_embedding_idx;

-- Step 2: Drop the old vector_search function (depends on vector(1536))
DROP FUNCTION IF EXISTS vector_search(vector(1536), TEXT, INT, FLOAT);

-- Step 3: Alter embedding columns to vector(1024)
ALTER TABLE patterns ALTER COLUMN embedding TYPE vector(1024) USING NULL;
ALTER TABLE memory_content ALTER COLUMN embedding TYPE vector(1024) USING NULL;
ALTER TABLE examples ALTER COLUMN embedding TYPE vector(1024) USING NULL;
ALTER TABLE knowledge_repo ALTER COLUMN embedding TYPE vector(1024) USING NULL;

-- Step 4: Recreate indexes for vector(1024)
CREATE INDEX IF NOT EXISTS patterns_embedding_idx
  ON patterns USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10);
CREATE INDEX IF NOT EXISTS memory_content_embedding_idx
  ON memory_content USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10);
CREATE INDEX IF NOT EXISTS examples_embedding_idx
  ON examples USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10);
CREATE INDEX IF NOT EXISTS knowledge_repo_embedding_idx
  ON knowledge_repo USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10);

-- Step 5: Recreate vector_search RPC with vector(1024)
CREATE OR REPLACE FUNCTION vector_search(
  query_embedding vector(1024),
  match_table TEXT,
  match_count INT DEFAULT 10,
  match_threshold FLOAT DEFAULT 0.7
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
    'AND 1 - (embedding <=> $1) >= $2 '
    'ORDER BY embedding <=> $1 '
    'LIMIT $3',
    match_table
  ) USING query_embedding, match_threshold, match_count;
END;
$$;

INSERT INTO schema_migrations (version, description)
VALUES ('011_voyage_dimensions', 'Migrate embedding columns from vector(1536) to vector(1024) for Voyage AI')
ON CONFLICT (version) DO NOTHING;
