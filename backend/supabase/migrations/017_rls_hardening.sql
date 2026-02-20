-- Migration: 017_rls_hardening
-- Description: Replace permissive RLS policies with production-grade user isolation.
--              Uses (SELECT auth.uid()) subquery pattern for performance optimization.
--              Only authenticated role gets access (anon policies removed).
--              Service role key (used by MCP server) bypasses RLS automatically.
--
-- IMPORTANT: After applying this migration, all client-side queries MUST include
--            a valid JWT. The MCP server uses the service role key, which bypasses
--            RLS — no changes needed there.

-- ============================================================
-- Drop ALL existing permissive policies
-- ============================================================

-- patterns
DROP POLICY IF EXISTS "Allow all for authenticated" ON patterns;
DROP POLICY IF EXISTS "Allow all for anon" ON patterns;

-- experiences
DROP POLICY IF EXISTS "Allow all for authenticated" ON experiences;
DROP POLICY IF EXISTS "Allow all for anon" ON experiences;

-- brain_health
DROP POLICY IF EXISTS "Allow all for authenticated" ON brain_health;
DROP POLICY IF EXISTS "Allow all for anon" ON brain_health;

-- memory_content
DROP POLICY IF EXISTS "Allow all for authenticated" ON memory_content;
DROP POLICY IF EXISTS "Allow all for anon" ON memory_content;

-- examples
DROP POLICY IF EXISTS "Allow all for authenticated" ON examples;
DROP POLICY IF EXISTS "Allow all for anon" ON examples;

-- knowledge_repo
DROP POLICY IF EXISTS "Allow all for authenticated" ON knowledge_repo;
DROP POLICY IF EXISTS "Allow all for anon" ON knowledge_repo;

-- growth_log
DROP POLICY IF EXISTS "Allow all for authenticated" ON growth_log;
DROP POLICY IF EXISTS "Allow all for anon" ON growth_log;

-- review_history
DROP POLICY IF EXISTS "Allow all for authenticated" ON review_history;
DROP POLICY IF EXISTS "Allow all for anon" ON review_history;

-- confidence_history
DROP POLICY IF EXISTS "Allow all for authenticated" ON confidence_history;
DROP POLICY IF EXISTS "Allow all for anon" ON confidence_history;

-- content_types (shared table — drop anon only, keep authenticated)
DROP POLICY IF EXISTS "Allow all for anon" ON content_types;
DROP POLICY IF EXISTS "Allow all for authenticated" ON content_types;

-- projects
DROP POLICY IF EXISTS "Allow all for authenticated" ON projects;
DROP POLICY IF EXISTS "Allow all for anon" ON projects;

-- project_artifacts
DROP POLICY IF EXISTS "Allow all for authenticated" ON project_artifacts;
DROP POLICY IF EXISTS "Allow all for anon" ON project_artifacts;

-- ============================================================
-- Create production RLS policies — user_id isolation
-- ============================================================

-- Helper: all user-scoped tables follow the same pattern:
--   SELECT: user_id = (SELECT auth.uid()::text)
--   INSERT: user_id = (SELECT auth.uid()::text)
--   UPDATE: user_id = (SELECT auth.uid()::text) on both USING and WITH CHECK
--   DELETE: user_id = (SELECT auth.uid()::text)
--
-- Note: auth.uid() returns UUID, user_id is TEXT, so we cast with ::text

-- patterns
CREATE POLICY "patterns_select_own" ON patterns
  FOR SELECT TO authenticated
  USING (user_id = (SELECT auth.uid()::text));
CREATE POLICY "patterns_insert_own" ON patterns
  FOR INSERT TO authenticated
  WITH CHECK (user_id = (SELECT auth.uid()::text));
CREATE POLICY "patterns_update_own" ON patterns
  FOR UPDATE TO authenticated
  USING (user_id = (SELECT auth.uid()::text))
  WITH CHECK (user_id = (SELECT auth.uid()::text));
CREATE POLICY "patterns_delete_own" ON patterns
  FOR DELETE TO authenticated
  USING (user_id = (SELECT auth.uid()::text));

-- experiences
CREATE POLICY "experiences_select_own" ON experiences
  FOR SELECT TO authenticated
  USING (user_id = (SELECT auth.uid()::text));
CREATE POLICY "experiences_insert_own" ON experiences
  FOR INSERT TO authenticated
  WITH CHECK (user_id = (SELECT auth.uid()::text));
CREATE POLICY "experiences_update_own" ON experiences
  FOR UPDATE TO authenticated
  USING (user_id = (SELECT auth.uid()::text))
  WITH CHECK (user_id = (SELECT auth.uid()::text));
CREATE POLICY "experiences_delete_own" ON experiences
  FOR DELETE TO authenticated
  USING (user_id = (SELECT auth.uid()::text));

-- brain_health
CREATE POLICY "brain_health_select_own" ON brain_health
  FOR SELECT TO authenticated
  USING (user_id = (SELECT auth.uid()::text));
CREATE POLICY "brain_health_insert_own" ON brain_health
  FOR INSERT TO authenticated
  WITH CHECK (user_id = (SELECT auth.uid()::text));
CREATE POLICY "brain_health_update_own" ON brain_health
  FOR UPDATE TO authenticated
  USING (user_id = (SELECT auth.uid()::text))
  WITH CHECK (user_id = (SELECT auth.uid()::text));
CREATE POLICY "brain_health_delete_own" ON brain_health
  FOR DELETE TO authenticated
  USING (user_id = (SELECT auth.uid()::text));

-- memory_content
CREATE POLICY "memory_content_select_own" ON memory_content
  FOR SELECT TO authenticated
  USING (user_id = (SELECT auth.uid()::text));
CREATE POLICY "memory_content_insert_own" ON memory_content
  FOR INSERT TO authenticated
  WITH CHECK (user_id = (SELECT auth.uid()::text));
CREATE POLICY "memory_content_update_own" ON memory_content
  FOR UPDATE TO authenticated
  USING (user_id = (SELECT auth.uid()::text))
  WITH CHECK (user_id = (SELECT auth.uid()::text));
CREATE POLICY "memory_content_delete_own" ON memory_content
  FOR DELETE TO authenticated
  USING (user_id = (SELECT auth.uid()::text));

-- examples
CREATE POLICY "examples_select_own" ON examples
  FOR SELECT TO authenticated
  USING (user_id = (SELECT auth.uid()::text));
CREATE POLICY "examples_insert_own" ON examples
  FOR INSERT TO authenticated
  WITH CHECK (user_id = (SELECT auth.uid()::text));
CREATE POLICY "examples_update_own" ON examples
  FOR UPDATE TO authenticated
  USING (user_id = (SELECT auth.uid()::text))
  WITH CHECK (user_id = (SELECT auth.uid()::text));
CREATE POLICY "examples_delete_own" ON examples
  FOR DELETE TO authenticated
  USING (user_id = (SELECT auth.uid()::text));

-- knowledge_repo
CREATE POLICY "knowledge_repo_select_own" ON knowledge_repo
  FOR SELECT TO authenticated
  USING (user_id = (SELECT auth.uid()::text));
CREATE POLICY "knowledge_repo_insert_own" ON knowledge_repo
  FOR INSERT TO authenticated
  WITH CHECK (user_id = (SELECT auth.uid()::text));
CREATE POLICY "knowledge_repo_update_own" ON knowledge_repo
  FOR UPDATE TO authenticated
  USING (user_id = (SELECT auth.uid()::text))
  WITH CHECK (user_id = (SELECT auth.uid()::text));
CREATE POLICY "knowledge_repo_delete_own" ON knowledge_repo
  FOR DELETE TO authenticated
  USING (user_id = (SELECT auth.uid()::text));

-- growth_log
CREATE POLICY "growth_log_select_own" ON growth_log
  FOR SELECT TO authenticated
  USING (user_id = (SELECT auth.uid()::text));
CREATE POLICY "growth_log_insert_own" ON growth_log
  FOR INSERT TO authenticated
  WITH CHECK (user_id = (SELECT auth.uid()::text));
CREATE POLICY "growth_log_delete_own" ON growth_log
  FOR DELETE TO authenticated
  USING (user_id = (SELECT auth.uid()::text));

-- review_history
CREATE POLICY "review_history_select_own" ON review_history
  FOR SELECT TO authenticated
  USING (user_id = (SELECT auth.uid()::text));
CREATE POLICY "review_history_insert_own" ON review_history
  FOR INSERT TO authenticated
  WITH CHECK (user_id = (SELECT auth.uid()::text));
CREATE POLICY "review_history_delete_own" ON review_history
  FOR DELETE TO authenticated
  USING (user_id = (SELECT auth.uid()::text));

-- confidence_history
CREATE POLICY "confidence_history_select_own" ON confidence_history
  FOR SELECT TO authenticated
  USING (user_id = (SELECT auth.uid()::text));
CREATE POLICY "confidence_history_insert_own" ON confidence_history
  FOR INSERT TO authenticated
  WITH CHECK (user_id = (SELECT auth.uid()::text));
CREATE POLICY "confidence_history_delete_own" ON confidence_history
  FOR DELETE TO authenticated
  USING (user_id = (SELECT auth.uid()::text));

-- content_types (shared table — all authenticated users can read, only service role can write)
CREATE POLICY "content_types_select_all" ON content_types
  FOR SELECT TO authenticated
  USING (true);
-- INSERT/UPDATE/DELETE for content_types is service-role only (no policy = denied)

-- projects (user-scoped)
CREATE POLICY "projects_select_own" ON projects
  FOR SELECT TO authenticated
  USING (user_id = (SELECT auth.uid()::text));
CREATE POLICY "projects_insert_own" ON projects
  FOR INSERT TO authenticated
  WITH CHECK (user_id = (SELECT auth.uid()::text));
CREATE POLICY "projects_update_own" ON projects
  FOR UPDATE TO authenticated
  USING (user_id = (SELECT auth.uid()::text))
  WITH CHECK (user_id = (SELECT auth.uid()::text));
CREATE POLICY "projects_delete_own" ON projects
  FOR DELETE TO authenticated
  USING (user_id = (SELECT auth.uid()::text));

-- project_artifacts (scoped via project ownership)
CREATE POLICY "project_artifacts_select_own" ON project_artifacts
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM projects
      WHERE projects.id = project_artifacts.project_id
      AND projects.user_id = (SELECT auth.uid()::text)
    )
  );
CREATE POLICY "project_artifacts_insert_own" ON project_artifacts
  FOR INSERT TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM projects
      WHERE projects.id = project_artifacts.project_id
      AND projects.user_id = (SELECT auth.uid()::text)
    )
  );
CREATE POLICY "project_artifacts_update_own" ON project_artifacts
  FOR UPDATE TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM projects
      WHERE projects.id = project_artifacts.project_id
      AND projects.user_id = (SELECT auth.uid()::text)
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM projects
      WHERE projects.id = project_artifacts.project_id
      AND projects.user_id = (SELECT auth.uid()::text)
    )
  );
CREATE POLICY "project_artifacts_delete_own" ON project_artifacts
  FOR DELETE TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM projects
      WHERE projects.id = project_artifacts.project_id
      AND projects.user_id = (SELECT auth.uid()::text)
    )
  );

-- Track migration
INSERT INTO schema_migrations (version, description)
VALUES ('017_rls_hardening', 'Production RLS policies with user_id isolation via (SELECT auth.uid()::text)')
ON CONFLICT (version) DO NOTHING;
