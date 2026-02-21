-- 022: Add writeprint column to templates table
-- Stores voice/tone/style fingerprint for template content
ALTER TABLE templates ADD COLUMN IF NOT EXISTS writeprint TEXT DEFAULT '';
