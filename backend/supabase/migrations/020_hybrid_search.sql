-- Migration: 020_hybrid_search
-- Description: Add full-text search columns (tsvector) to 4 existing tables,
--              add embedding column to experiences table,
--              create hybrid_search RPC combining vector + keyword via RRF.

-- Step 1: Add tsvector columns (generated, auto-populated on insert/update)
-- patterns: search over pattern_text + name
ALTER TABLE patterns ADD COLUMN IF NOT EXISTS fts tsvector
  GENERATED ALWAYS AS (
    to_tsvector('english', COALESCE(name, '') || ' ' || COALESCE(pattern_text, ''))
  ) STORED;

-- memory_content: search over content + title
ALTER TABLE memory_content ADD COLUMN IF NOT EXISTS fts tsvector
  GENERATED ALWAYS AS (
    to_tsvector('english', COALESCE(title, '') || ' ' || COALESCE(content, ''))
  ) STORED;

-- examples: search over content + title
ALTER TABLE examples ADD COLUMN IF NOT EXISTS fts tsvector
  GENERATED ALWAYS AS (
    to_tsvector('english', COALESCE(title, '') || ' ' || COALESCE(content, ''))
  ) STORED;

-- knowledge_repo: search over content + title
ALTER TABLE knowledge_repo ADD COLUMN IF NOT EXISTS fts tsvector
  GENERATED ALWAYS AS (
    to_tsvector('english', COALESCE(title, '') || ' ' || COALESCE(content, ''))
  ) STORED;

-- Step 2: Create GIN indexes for full-text search
CREATE INDEX IF NOT EXISTS patterns_fts_idx ON patterns USING gin(fts);
CREATE INDEX IF NOT EXISTS memory_content_fts_idx ON memory_content USING gin(fts);
CREATE INDEX IF NOT EXISTS examples_fts_idx ON examples USING gin(fts);
CREATE INDEX IF NOT EXISTS knowledge_repo_fts_idx ON knowledge_repo USING gin(fts);

-- Step 3: Add embedding column to experiences table (currently missing)
ALTER TABLE experiences ADD COLUMN IF NOT EXISTS embedding vector(1024);
CREATE INDEX IF NOT EXISTS experiences_embedding_hnsw_idx
  ON experiences USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 128);

-- Step 4: Add experiences to the valid tables for vector_search RPC
-- (The RPC uses dynamic SQL with format(), so no change needed to the function itself.
--  The whitelist is enforced in Python StorageService.vector_search, not in SQL.)

-- Step 5: Create hybrid_search RPC combining vector similarity + full-text via RRF
CREATE OR REPLACE FUNCTION hybrid_search(
  query_text TEXT,
  query_embedding vector(1024),
  match_table TEXT,
  match_count INT DEFAULT 10,
  full_text_weight FLOAT DEFAULT 1.0,
  semantic_weight FLOAT DEFAULT 1.0,
  rrf_k INT DEFAULT 50,
  p_user_id TEXT DEFAULT 'ryan',
  p_ef_search INT DEFAULT 100
)
RETURNS TABLE (
  id UUID,
  content TEXT,
  title TEXT,
  category TEXT,
  similarity FLOAT,
  search_type TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
  -- Set HNSW search parameter for this query
  EXECUTE format('SET LOCAL hnsw.ef_search = %s', p_ef_search);

  RETURN QUERY EXECUTE format(
    'WITH full_text AS (
      SELECT
        id,
        ROW_NUMBER() OVER (
          ORDER BY ts_rank_cd(fts, websearch_to_tsquery(''english'', $1)) DESC
        ) AS rank_ix
      FROM %I
      WHERE fts IS NOT NULL
        AND user_id = $6
        AND fts @@ websearch_to_tsquery(''english'', $1)
      ORDER BY rank_ix
      LIMIT LEAST($2, 30) * 2
    ),
    semantic AS (
      SELECT
        id,
        ROW_NUMBER() OVER (ORDER BY embedding <=> $3) AS rank_ix
      FROM %I
      WHERE embedding IS NOT NULL
        AND user_id = $6
      ORDER BY rank_ix
      LIMIT LEAST($2, 30) * 2
    )
    SELECT
      t.id,
      COALESCE(t.content, t.pattern_text, '''') AS content,
      COALESCE(t.title, t.name, '''') AS title,
      COALESCE(t.category, t.topic, '''') AS category,
      (
        COALESCE(1.0 / ($4 + full_text.rank_ix), 0.0) * $7 +
        COALESCE(1.0 / ($4 + semantic.rank_ix), 0.0) * $8
      ) AS similarity,
      CASE
        WHEN full_text.id IS NOT NULL AND semantic.id IS NOT NULL THEN ''hybrid''
        WHEN full_text.id IS NOT NULL THEN ''keyword''
        ELSE ''semantic''
      END AS search_type
    FROM full_text
    FULL OUTER JOIN semantic ON full_text.id = semantic.id
    JOIN %I t ON COALESCE(full_text.id, semantic.id) = t.id
    ORDER BY similarity DESC
    LIMIT LEAST($2, 30)',
    match_table, match_table, match_table
  ) USING query_text, match_count, query_embedding, rrf_k, p_ef_search, p_user_id, full_text_weight, semantic_weight;
END;
$$;

INSERT INTO schema_migrations (version, description)
VALUES ('020_hybrid_search', 'Add tsvector FTS columns, GIN indexes, experiences embedding, and hybrid_search RPC')
ON CONFLICT (version) DO NOTHING;
