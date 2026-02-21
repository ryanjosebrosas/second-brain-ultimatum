-- Migration: 023_fix_rpc_column_refs
-- Description: Fix hybrid_search and vector_search RPCs that reference non-existent
--              columns via COALESCE. PostgreSQL validates ALL column references at
--              parse time, so COALESCE(t.content, t.pattern_text, '') fails when the
--              table doesn't have both columns. Fix: compute column names from
--              match_table, then use %I format specifiers for safe identifier quoting.
--
-- Affected tables and their column mappings:
--   patterns:       pattern_text (content), name (title), topic (category)
--   memory_content: content, title, category
--   examples:       content, title, content_type (category)
--   knowledge_repo: content, title, category
--   experiences:    output_summary/plan_summary (content), name (title), category

-- ============================================================
-- Fix 1: hybrid_search RPC
-- ============================================================

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
DECLARE
  col_content TEXT;
  col_title TEXT;
  col_category TEXT;
BEGIN
  -- Map table-specific column names
  -- hybrid_search valid tables: patterns, memory_content, examples, knowledge_repo
  CASE match_table
    WHEN 'patterns' THEN
      col_content  := 'pattern_text';
      col_title    := 'name';
      col_category := 'topic';
    WHEN 'examples' THEN
      col_content  := 'content';
      col_title    := 'title';
      col_category := 'content_type';
    ELSE  -- memory_content, knowledge_repo
      col_content  := 'content';
      col_title    := 'title';
      col_category := 'category';
  END CASE;

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
      COALESCE(t.%I, '''') AS content,
      COALESCE(t.%I, '''') AS title,
      COALESCE(t.%I, '''') AS category,
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
    match_table, match_table, col_content, col_title, col_category, match_table
  ) USING query_text, match_count, query_embedding, rrf_k, p_ef_search, p_user_id, full_text_weight, semantic_weight;
END;
$$;

-- ============================================================
-- Fix 2: vector_search RPC (same column reference bug)
-- ============================================================

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
DECLARE
  col_content TEXT;
  col_title TEXT;
  col_category TEXT;
BEGIN
  -- Set HNSW search parameter for this query
  EXECUTE format('SET LOCAL hnsw.ef_search = %s', p_ef_search);

  -- Experiences table has different structure (no single content column),
  -- so handle it with a dedicated query branch.
  IF match_table = 'experiences' THEN
    RETURN QUERY EXECUTE
      'SELECT id, '
      'COALESCE(output_summary, plan_summary, '''') as content, '
      'COALESCE(name, '''') as title, '
      'COALESCE(category, '''') as category, '
      '1 - (embedding <=> $1) as similarity '
      'FROM experiences '
      'WHERE embedding IS NOT NULL '
      'AND user_id = $4 '
      'AND 1 - (embedding <=> $1) >= $2 '
      'ORDER BY embedding <=> $1 '
      'LIMIT $3'
    USING query_embedding, match_threshold, match_count, p_user_id;
    RETURN;
  END IF;

  -- Map table-specific column names for remaining tables
  CASE match_table
    WHEN 'patterns' THEN
      col_content  := 'pattern_text';
      col_title    := 'name';
      col_category := 'topic';
    WHEN 'examples' THEN
      col_content  := 'content';
      col_title    := 'title';
      col_category := 'content_type';
    ELSE  -- memory_content, knowledge_repo
      col_content  := 'content';
      col_title    := 'title';
      col_category := 'category';
  END CASE;

  RETURN QUERY EXECUTE format(
    'SELECT id, COALESCE(%I, '''') as content, '
    'COALESCE(%I, '''') as title, '
    'COALESCE(%I, '''') as category, '
    '1 - (embedding <=> $1) as similarity '
    'FROM %I '
    'WHERE embedding IS NOT NULL '
    'AND user_id = $4 '
    'AND 1 - (embedding <=> $1) >= $2 '
    'ORDER BY embedding <=> $1 '
    'LIMIT $3',
    col_content, col_title, col_category, match_table
  ) USING query_embedding, match_threshold, match_count, p_user_id;
END;
$$;

-- ============================================================
-- Record migration
-- ============================================================

INSERT INTO schema_migrations (version, description)
VALUES ('023_fix_rpc_column_refs', 'Fix hybrid_search and vector_search column references — use table-specific column mapping instead of cross-table COALESCE')
ON CONFLICT (version) DO NOTHING;
