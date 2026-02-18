-- Content examples (mirrors memory/examples/ folders)
create table examples (
    id uuid primary key default gen_random_uuid(),
    content_type text not null,    -- 'linkedin', 'email', 'case-study', 'presentation', etc.
    title text not null,
    content text not null,
    source_file text,
    tags text[],
    embedding vector(1536),
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

-- Knowledge repository (mirrors memory/knowledge-repo/ folders)
create table knowledge_repo (
    id uuid primary key default gen_random_uuid(),
    category text not null,        -- 'framework', 'methodology', 'playbook', 'research', 'tool'
    title text not null,
    content text not null,
    source_file text,
    tags text[],
    embedding vector(1536),
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

-- Indexes
create index idx_examples_content_type on examples(content_type);
create index idx_knowledge_repo_category on knowledge_repo(category);
