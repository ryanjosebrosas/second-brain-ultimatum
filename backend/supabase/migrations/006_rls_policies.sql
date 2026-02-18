-- Row Level Security policies for all tables
-- The Python backend uses supabase_key (anon key) which respects RLS.
-- If the app uses service_role key, RLS is bypassed automatically by Supabase.
--
-- Currently a single-user application — using permissive policies for both
-- 'authenticated' and 'anon' roles. Remove the anon policies when auth is configured.

-- patterns
ALTER TABLE patterns ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all for authenticated" ON patterns
  FOR ALL USING (auth.role() = 'authenticated')
  WITH CHECK (auth.role() = 'authenticated');
CREATE POLICY "Allow all for anon" ON patterns
  FOR ALL USING (auth.role() = 'anon')
  WITH CHECK (auth.role() = 'anon');

-- experiences
ALTER TABLE experiences ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all for authenticated" ON experiences
  FOR ALL USING (auth.role() = 'authenticated')
  WITH CHECK (auth.role() = 'authenticated');
CREATE POLICY "Allow all for anon" ON experiences
  FOR ALL USING (auth.role() = 'anon')
  WITH CHECK (auth.role() = 'anon');

-- brain_health
ALTER TABLE brain_health ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all for authenticated" ON brain_health
  FOR ALL USING (auth.role() = 'authenticated')
  WITH CHECK (auth.role() = 'authenticated');
CREATE POLICY "Allow all for anon" ON brain_health
  FOR ALL USING (auth.role() = 'anon')
  WITH CHECK (auth.role() = 'anon');

-- memory_content
ALTER TABLE memory_content ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all for authenticated" ON memory_content
  FOR ALL USING (auth.role() = 'authenticated')
  WITH CHECK (auth.role() = 'authenticated');
CREATE POLICY "Allow all for anon" ON memory_content
  FOR ALL USING (auth.role() = 'anon')
  WITH CHECK (auth.role() = 'anon');

-- examples
ALTER TABLE examples ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all for authenticated" ON examples
  FOR ALL USING (auth.role() = 'authenticated')
  WITH CHECK (auth.role() = 'authenticated');
CREATE POLICY "Allow all for anon" ON examples
  FOR ALL USING (auth.role() = 'anon')
  WITH CHECK (auth.role() = 'anon');

-- knowledge_repo
ALTER TABLE knowledge_repo ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all for authenticated" ON knowledge_repo
  FOR ALL USING (auth.role() = 'authenticated')
  WITH CHECK (auth.role() = 'authenticated');
CREATE POLICY "Allow all for anon" ON knowledge_repo
  FOR ALL USING (auth.role() = 'anon')
  WITH CHECK (auth.role() = 'anon');

-- content_types
ALTER TABLE content_types ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all for authenticated" ON content_types
  FOR ALL USING (auth.role() = 'authenticated')
  WITH CHECK (auth.role() = 'authenticated');
CREATE POLICY "Allow all for anon" ON content_types
  FOR ALL USING (auth.role() = 'anon')
  WITH CHECK (auth.role() = 'anon');

-- growth_log
ALTER TABLE growth_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all for authenticated" ON growth_log
  FOR ALL USING (auth.role() = 'authenticated')
  WITH CHECK (auth.role() = 'authenticated');
CREATE POLICY "Allow all for anon" ON growth_log
  FOR ALL USING (auth.role() = 'anon')
  WITH CHECK (auth.role() = 'anon');

-- review_history
ALTER TABLE review_history ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all for authenticated" ON review_history
  FOR ALL USING (auth.role() = 'authenticated')
  WITH CHECK (auth.role() = 'authenticated');
CREATE POLICY "Allow all for anon" ON review_history
  FOR ALL USING (auth.role() = 'anon')
  WITH CHECK (auth.role() = 'anon');

-- confidence_history
ALTER TABLE confidence_history ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all for authenticated" ON confidence_history
  FOR ALL USING (auth.role() = 'authenticated')
  WITH CHECK (auth.role() = 'authenticated');
CREATE POLICY "Allow all for anon" ON confidence_history
  FOR ALL USING (auth.role() = 'anon')
  WITH CHECK (auth.role() = 'anon');
