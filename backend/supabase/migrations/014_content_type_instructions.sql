-- Content Type Enrichment: writing_instructions, validation_rules, ui_config
-- Depends on: 004_content_types.sql

-- ============================================================
-- Section 1: Add new columns to content_types
-- ============================================================

ALTER TABLE content_types
ADD COLUMN IF NOT EXISTS writing_instructions TEXT DEFAULT '';

ALTER TABLE content_types
ADD COLUMN IF NOT EXISTS validation_rules JSONB DEFAULT '{}'::jsonb;

ALTER TABLE content_types
ADD COLUMN IF NOT EXISTS ui_config JSONB DEFAULT '{}'::jsonb;

-- ============================================================
-- Section 2: Seed essay content type
-- ============================================================

INSERT INTO content_types (slug, name, default_mode, structure_hint, example_type,
    max_words, description, is_builtin, writing_instructions, validation_rules, ui_config)
VALUES (
    'essay',
    'Long-Form Essay',
    'professional',
    'Title -> Central Question -> Thesis -> Body (3-5 sections with evidence) -> Conclusion',
    'essay',
    3000,
    'Intellectually rigorous, stylistically compelling essay',
    TRUE,
    E'WRITING PROCESS (follow in order):\n1. Identify the topic and evaluate the angle using STIRC scoring\n2. Formulate a central question the essay answers\n3. Choose structural framework: argumentative/explanatory/narrative\n4. Load voice guide and relevant patterns from brain\n5. Write the essay following the Five Laws\n6. Self-review against the quality checklist\n\nSTIRC ANGLE SCORING (each 1-5, threshold 18/25):\n- Surprising: Contradicts common assumptions\n- True: Supported by evidence\n- Important: Matters to people\n- Relevant: Connects to current concerns\n- Cool: Inherently interesting\n\nFIVE WRITING LAWS:\n1. Active voice always\n2. Remove needless words\n3. No adverbs\n4. Write simply (4th-7th grade reading level)\n5. First sentence must demand attention',
    '{"min_words": 300, "custom_checks": ["title_required", "substantial_content"]}'::jsonb,
    '{"icon": "pen-tool", "color": "#6366f1", "category": "long-form", "show_framework_selector": true}'::jsonb
) ON CONFLICT (slug) DO NOTHING;

-- ============================================================
-- Section 3: Update existing types with writing_instructions
-- ============================================================

UPDATE content_types SET writing_instructions = E'LINKEDIN RULES:\n1. First line is the hook \u2014 must stop the scroll\n2. Use short paragraphs (1-2 sentences each)\n3. Include a clear CTA or question at the end\n4. No hashtag spam \u2014 3-5 relevant hashtags max\n5. Write conversationally, not corporately',
    validation_rules = '{"min_words": 30}'::jsonb,
    ui_config = '{"icon": "linkedin", "color": "#0077b5", "category": "social"}'::jsonb
WHERE slug = 'linkedin' AND writing_instructions = '';

UPDATE content_types SET writing_instructions = E'EMAIL RULES:\n1. Subject line must be specific and action-oriented\n2. Opening line states purpose \u2014 no fluff\n3. One main ask per email\n4. End with clear next step and timeline\n5. Professional but warm \u2014 not robotic',
    validation_rules = '{"min_words": 50}'::jsonb,
    ui_config = '{"icon": "mail", "color": "#ea580c", "category": "communication"}'::jsonb
WHERE slug = 'email' AND writing_instructions = '';

UPDATE content_types SET writing_instructions = E'LANDING PAGE RULES:\n1. Headline must communicate the core value in under 10 words\n2. Subheadline elaborates the how/what\n3. Problem section uses customer language\n4. Social proof with specific numbers\n5. Single clear CTA \u2014 no competing actions',
    validation_rules = '{"min_words": 200}'::jsonb,
    ui_config = '{"icon": "layout", "color": "#0ea5e9", "category": "marketing"}'::jsonb
WHERE slug = 'landing-page' AND writing_instructions = '';

UPDATE content_types SET writing_instructions = E'COMMENT RULES:\n1. Acknowledge the original content first\n2. Add genuine value or a unique perspective\n3. Keep it concise \u2014 under 3 sentences\n4. Ask a follow-up question if natural\n5. Never be promotional',
    validation_rules = '{"min_words": 10}'::jsonb,
    ui_config = '{"icon": "message-circle", "color": "#22c55e", "category": "social"}'::jsonb
WHERE slug = 'comment' AND writing_instructions = '';

UPDATE content_types SET writing_instructions = E'CASE STUDY RULES:\n1. Lead with the result \u2014 numbers first\n2. Client context must be relatable\n3. Challenge section uses before/after framing\n4. Approach section shows methodology, not just actions\n5. Results MUST be quantified \u2014 no vague claims',
    validation_rules = '{"min_words": 500}'::jsonb,
    ui_config = '{"icon": "bar-chart", "color": "#8b5cf6", "category": "long-form"}'::jsonb
WHERE slug = 'case-study' AND writing_instructions = '';

UPDATE content_types SET writing_instructions = E'PROPOSAL RULES:\n1. Executive summary must standalone \u2014 assume reader skips the rest\n2. Problem section uses client language from discovery\n3. Solution maps directly to stated problems\n4. Deliverables are specific and measurable\n5. Investment section anchors on value, not cost',
    validation_rules = '{"min_words": 800}'::jsonb,
    ui_config = '{"icon": "file-text", "color": "#f59e0b", "category": "business"}'::jsonb
WHERE slug = 'proposal' AND writing_instructions = '';

UPDATE content_types SET writing_instructions = E'ONE-PAGER RULES:\n1. Must be scannable in 60 seconds\n2. Headline sells, body informs\n3. Benefits over features \u2014 max 4 bullets\n4. One piece of social proof\n5. Single CTA with clear next step',
    validation_rules = '{"min_words": 100}'::jsonb,
    ui_config = '{"icon": "file", "color": "#14b8a6", "category": "business"}'::jsonb
WHERE slug = 'one-pager' AND writing_instructions = '';

UPDATE content_types SET writing_instructions = E'PRESENTATION RULES:\n1. Opening hook must earn the next 30 seconds\n2. Max 3-5 key points \u2014 audience remembers 3\n3. Each point needs one supporting story or data point\n4. Transitions between points must be explicit\n5. End with a memorable closing, not just any questions',
    validation_rules = '{"min_words": 200}'::jsonb,
    ui_config = '{"icon": "monitor", "color": "#ec4899", "category": "communication"}'::jsonb
WHERE slug = 'presentation' AND writing_instructions = '';

UPDATE content_types SET writing_instructions = E'INSTAGRAM RULES:\n1. First line is the hook \u2014 visible before more\n2. Tell a micro-story in 2-3 short paragraphs\n3. Use line breaks for readability\n4. CTA should feel natural, not salesy\n5. 5-10 relevant hashtags at the end',
    validation_rules = '{"min_words": 20}'::jsonb,
    ui_config = '{"icon": "instagram", "color": "#e1306c", "category": "social"}'::jsonb
WHERE slug = 'instagram' AND writing_instructions = '';
