-- Migration: 018_vector_search_hnsw
-- Description: Update vector_search RPC to support HNSW ef_search tuning.
--              Higher ef_search = better recall at cost of latency.
--              Default 100 (up from pgvector default of 40) for good baseline recall.

CREATE OR REPLACE FUNCTION vector_search(
  query_embedding vector(1024),
  match_table TEXT,
  match_count INT DEFAULT 10,
  match_threshold FLOAT DEFAULT 0.7,
  p_user_id TEXT DEFAULT 'ryan',
  p_ef_search INT DEFAULT 100
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
  -- Set HNSW search parameter for this query
  EXECUTE format('SET LOCAL hnsw.ef_search = %s', p_ef_search);

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

INSERT INTO schema_migrations (version, description)
VALUES ('018_vector_search_hnsw', 'Add ef_search parameter to vector_search RPC for HNSW tuning')
ON CONFLICT (version) DO NOTHING;
