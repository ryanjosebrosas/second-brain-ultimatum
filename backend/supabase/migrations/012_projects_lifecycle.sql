-- Projects table: tracks full lifecycle of a piece of work
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    lifecycle_stage TEXT NOT NULL DEFAULT 'planning',
    current_phase TEXT,
    category TEXT NOT NULL DEFAULT 'content',
    started_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ,
    review_score NUMERIC(3,1),
    patterns_extracted TEXT[] DEFAULT '{}',
    patterns_upgraded TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    CONSTRAINT projects_lifecycle_stage_check CHECK (
        lifecycle_stage IN ('planning', 'executing', 'reviewing', 'learning', 'complete', 'archived')
    ),
    CONSTRAINT projects_category_check CHECK (
        category IN ('content', 'prospects', 'clients', 'products', 'general')
    )
);

-- Project artifacts: 5 artifact types per project (plan, research, output, review, learnings)
CREATE TABLE IF NOT EXISTS project_artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    artifact_type TEXT NOT NULL,
    title TEXT,
    content TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    CONSTRAINT artifacts_type_check CHECK (
        artifact_type IN ('plan', 'research', 'output', 'review', 'learnings')
    ),
    CONSTRAINT artifacts_unique_type_per_project UNIQUE (project_id, artifact_type)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_projects_lifecycle ON projects(lifecycle_stage);
CREATE INDEX IF NOT EXISTS idx_projects_category ON projects(category);
CREATE INDEX IF NOT EXISTS idx_projects_updated ON projects(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_artifacts_project ON project_artifacts(project_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_type ON project_artifacts(artifact_type);
