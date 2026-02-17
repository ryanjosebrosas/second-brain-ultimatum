-- Generic vector search RPC function
-- Supports searching any table with an embedding column

CREATE OR REPLACE FUNCTION vector_search(
  query_embedding vector(1536),
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
  -- Dynamic SQL to search any table with embedding column
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
VALUES ('010_vector_search_rpc', 'Generic vector search RPC function')
ON CONFLICT (version) DO NOTHING;
