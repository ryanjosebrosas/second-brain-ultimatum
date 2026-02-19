-- Migration 016: Vault ingestion columns and transcript summary table
-- Adds vault-specific metadata to knowledge_repo and creates vault_transcripts
-- for AI-generated meeting transcript summaries.

-- === ADD VAULT COLUMNS TO knowledge_repo ===
-- Note: user_id already exists from migration 015. Included for idempotency.
ALTER TABLE knowledge_repo ADD COLUMN IF NOT EXISTS user_id text;
ALTER TABLE knowledge_repo ADD COLUMN IF NOT EXISTS client text;
ALTER TABLE knowledge_repo ADD COLUMN IF NOT EXISTS content_type text;
ALTER TABLE knowledge_repo ADD COLUMN IF NOT EXISTS author text;
ALTER TABLE knowledge_repo ADD COLUMN IF NOT EXISTS vault_path text;
ALTER TABLE knowledge_repo ADD COLUMN IF NOT EXISTS ingested_at timestamptz;
ALTER TABLE knowledge_repo ADD COLUMN IF NOT EXISTS file_hash text;

-- === INDEXES FOR knowledge_repo ===
-- Note: idx_knowledge_repo_user_id already exists from migration 015.
CREATE INDEX IF NOT EXISTS idx_knowledge_repo_user_id ON knowledge_repo(user_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_repo_client ON knowledge_repo(client);
CREATE INDEX IF NOT EXISTS idx_knowledge_repo_content_type ON knowledge_repo(content_type);
CREATE INDEX IF NOT EXISTS idx_knowledge_repo_vault_path ON knowledge_repo(vault_path);

-- === TRANSCRIPT SUMMARIES TABLE ===
-- Stores AI-generated summaries of meeting transcripts
CREATE TABLE IF NOT EXISTS vault_transcripts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id text NOT NULL DEFAULT 'brainforge',
    client text,
    title text NOT NULL,
    meeting_date date,
    participants text[],
    summary text NOT NULL,
    key_points text[],
    key_quotes text[],
    topics text[],
    source_file text NOT NULL,
    file_hash text,
    embedding vector(1024),
    ingested_at timestamptz DEFAULT now(),
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- === INDEXES FOR vault_transcripts ===
CREATE INDEX IF NOT EXISTS idx_vault_transcripts_user_id ON vault_transcripts(user_id);
CREATE INDEX IF NOT EXISTS idx_vault_transcripts_client ON vault_transcripts(client);
CREATE INDEX IF NOT EXISTS idx_vault_transcripts_meeting_date ON vault_transcripts(meeting_date);
CREATE INDEX IF NOT EXISTS idx_vault_transcripts_source_file ON vault_transcripts(source_file);
CREATE INDEX IF NOT EXISTS vault_transcripts_embedding_idx
    ON vault_transcripts USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10);

-- === UNIQUE CONSTRAINTS FOR IDEMPOTENT UPSERTS ===
CREATE UNIQUE INDEX IF NOT EXISTS idx_knowledge_repo_vault_path_unique
    ON knowledge_repo(vault_path) WHERE vault_path IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_vault_transcripts_source_unique
    ON vault_transcripts(source_file);

-- === RECORD MIGRATION ===
INSERT INTO schema_migrations (version, description)
VALUES ('016_vault_ingestion', 'Add vault ingestion columns and transcript summary table')
ON CONFLICT (version) DO NOTHING;
