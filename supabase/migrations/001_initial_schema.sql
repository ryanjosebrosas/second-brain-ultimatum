-- Enable pgvector extension
create extension if not exists vector;

-- Pattern registry (mirrors memory/patterns/INDEX.md)
create table patterns (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    topic text not null,          -- e.g., 'Messaging', 'Process', 'Positioning'
    confidence text not null default 'LOW',  -- LOW, MEDIUM, HIGH
    source_file text,             -- original markdown file
    source_experience text,       -- experience that generated this pattern
    date_added date not null default current_date,
    date_updated date,
    use_count int default 1,
    context text,                 -- when to use
    pattern_text text not null,   -- the actual pattern
    evidence text[],              -- array of evidence strings
    anti_patterns text[],         -- what NOT to do
    embedding vector(1536),       -- for semantic search
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

-- Experiences log (mirrors experiences/ folder structure)
create table experiences (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    category text not null,       -- 'content', 'prospects', 'clients'
    plan_summary text,
    output_summary text,
    review_score numeric(3,1),
    patterns_extracted text[],
    patterns_upgraded text[],
    learnings text,
    source_path text,             -- original folder path
    created_at timestamptz default now()
);

-- Brain health metrics (mirrors brain-health/)
create table brain_health (
    id uuid primary key default gen_random_uuid(),
    date date not null default current_date,
    total_patterns int default 0,
    high_confidence int default 0,
    medium_confidence int default 0,
    low_confidence int default 0,
    total_experiences int default 0,
    avg_review_score numeric(3,1),
    patterns_added int default 0,
    patterns_upgraded int default 0,
    notes text,
    created_at timestamptz default now()
);

-- Memory content (semantic knowledge from memory/ folders)
create table memory_content (
    id uuid primary key default gen_random_uuid(),
    category text not null,       -- 'company', 'customers', 'style-voice', 'values-beliefs', 'audience'
    subcategory text,             -- 'products', 'positioning', 'tone-guide', etc.
    title text not null,
    content text not null,
    source_file text,             -- original markdown path
    embedding vector(1536),
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

-- Create indexes for vector search
create index on patterns using ivfflat (embedding vector_cosine_ops) with (lists = 10);
create index on memory_content using ivfflat (embedding vector_cosine_ops) with (lists = 10);

-- Create indexes for common queries
create index idx_patterns_topic on patterns(topic);
create index idx_patterns_confidence on patterns(confidence);
create index idx_experiences_category on experiences(category);
create index idx_brain_health_date on brain_health(date);
create index idx_memory_content_category on memory_content(category);
