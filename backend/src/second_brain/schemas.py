"""Pydantic output models for Second Brain agent responses."""

from typing import Any, Literal

from pydantic import BaseModel, Field

ConfidenceLevel = Literal["LOW", "MEDIUM", "HIGH"]


class MultimodalContentBlock(BaseModel):
    """A single multimodal content block for Mem0 ingestion."""

    type: Literal["image_url", "pdf_url", "mdx_url", "text"] = Field(
        description="Content type: image_url, pdf_url, mdx_url, or text"
    )
    url: str | None = Field(
        default=None,
        description="URL or base64 data URI for the content (for image/pdf/mdx types)",
    )
    text: str | None = Field(
        default=None,
        description="Text content (for text type only)",
    )


class MultimodalLearnResult(BaseModel):
    """Output from multimodal learn MCP tools."""

    content_type: str = Field(description="Type of content ingested: image, document, video")
    source: str = Field(description="Source URL or 'base64' for inline content")
    memory_stored: bool = Field(default=False, description="Whether Mem0 memory was created")
    memory_id: str = Field(default="", description="Mem0 memory ID if stored")
    embedding_stored: bool = Field(
        default=False, description="Whether vector embedding was stored"
    )
    context: str = Field(default="", description="User-provided context about the content")
    summary: str = Field(default="", description="Processing summary")


class Relation(BaseModel):
    """A graph relationship between entities."""

    source: str = Field(description="Source entity name")
    relationship: str = Field(description="Relationship type (e.g., uses, includes)")
    target: str = Field(description="Target entity name")


class MemoryMatch(BaseModel):
    """A single memory search result."""

    content: str = Field(description="The memory content")
    source: str = Field(default="", description="Source file or category")
    relevance: str = Field(default="MEDIUM", description="HIGH/MEDIUM/LOW relevance")


class RecallResult(BaseModel):
    """Output from the RecallAgent."""

    query: str = Field(description="The original search query")
    matches: list[MemoryMatch] = Field(
        default_factory=list,
        description="Ranked memory matches",
    )
    patterns: list[str] = Field(
        default_factory=list,
        description="Related pattern names from registry",
    )
    relations: list[Relation] = Field(
        default_factory=list,
        description="Entity relationships from graph memory",
    )
    summary: str = Field(
        default="",
        description="Brief summary of what was found",
    )


class AskResult(BaseModel):
    """Output from the AskAgent."""

    answer: str = Field(
        description=(
            "The COMPLETE response to the user's request. If they asked a question, "
            "provide the full answer. If they asked you to write or draft something, "
            "include the FULL written text — NOT a summary or description of what you would write."
        )
    )
    context_used: list[str] = Field(
        default_factory=list,
        description="Brain context files/memories referenced",
    )
    patterns_applied: list[str] = Field(
        default_factory=list,
        description="Patterns applied in the response",
    )
    relations: list[Relation] = Field(
        default_factory=list,
        description="Entity relationships from graph memory",
    )
    confidence: ConfidenceLevel = Field(
        default="MEDIUM",
        description="Confidence in the response: HIGH/MEDIUM/LOW",
    )
    next_action: str = Field(
        default="",
        description="Suggested next command (e.g., '/plan' for complex tasks)",
    )


class PatternExtract(BaseModel):
    """A single pattern extracted from work session input."""

    name: str = Field(description="Short descriptive name for the pattern")
    topic: str = Field(
        description="Category: Messaging, Content, Process, Positioning, or custom"
    )
    confidence: ConfidenceLevel = Field(
        default="LOW",
        description="LOW for new patterns, MEDIUM if reinforcing existing (2+ uses), HIGH if proven (5+ uses)",
    )
    pattern_text: str = Field(
        description="What the pattern is — the actionable insight"
    )
    evidence: list[str] = Field(
        default_factory=list,
        description="Evidence supporting this pattern from the input",
    )
    anti_patterns: list[str] = Field(
        default_factory=list,
        description="What NOT to do — common mistakes related to this pattern",
    )
    context: str = Field(
        default="",
        description="When to apply this pattern",
    )
    is_reinforcement: bool = Field(
        default=False,
        description="True if this reinforces an existing pattern rather than creating a new one",
    )
    existing_pattern_name: str = Field(
        default="",
        description="Name of existing pattern being reinforced, if is_reinforcement is True",
    )
    applicable_content_types: list[str] | None = Field(
        default=None,
        description="Content type slugs this pattern applies to (e.g., ['linkedin', 'email']). "
        "None means the pattern is universal and applies to all content types.",
    )


class LearnResult(BaseModel):
    """Output from the LearnAgent."""

    input_summary: str = Field(
        description="Brief summary of what was provided as input"
    )
    patterns_extracted: list[PatternExtract] = Field(
        default_factory=list,
        description="New or reinforced patterns extracted",
    )
    insights: list[str] = Field(
        default_factory=list,
        description="Key insights that don't fit a pattern structure",
    )
    experience_recorded: bool = Field(
        default=False,
        description="Whether an experience entry was created",
    )
    experience_category: str = Field(
        default="",
        description="Category of the experience (content, prospects, clients)",
    )
    storage_summary: str = Field(
        default="",
        description="Summary of what was stored and where",
    )
    patterns_new: int = Field(
        default=0,
        description="Count of new patterns created",
    )
    patterns_reinforced: int = Field(
        default=0,
        description="Count of existing patterns reinforced",
    )


class ReviewDimensionConfig(BaseModel):
    """Per-content-type configuration for a review dimension."""

    name: str = Field(description="Dimension name matching REVIEW_DIMENSIONS (e.g., 'Messaging')")
    weight: float = Field(default=1.0, description="Relative weight for scoring (0.5=half, 1.0=normal, 1.5=extra)")
    enabled: bool = Field(default=True, description="Whether this dimension applies to this content type")


class ContentTypeConfig(BaseModel):
    """Configuration for a content type in the registry."""

    name: str
    default_mode: str
    structure_hint: str
    example_type: str
    max_words: int = 0
    description: str = ""
    review_dimensions: list[ReviewDimensionConfig] | None = Field(
        default=None,
        description="Per-dimension review config. None = all dimensions with equal weight.",
    )
    is_builtin: bool = Field(
        default=False,
        description="True for seed types that ship with the system.",
    )
    writing_instructions: str = Field(
        default="",
        description="Type-specific writing rules and protocols injected into agent instructions "
        "at runtime. Example: STIRC scoring protocol for essays, hook/CTA rules for LinkedIn.",
    )
    validation_rules: dict[str, Any] = Field(
        default_factory=dict,
        description="Type-specific validation rules applied by validate_draft tool. "
        "Keys: min_words (int), required_sections (list[str]), custom_checks (list[str]).",
    )
    ui_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Frontend UI metadata. Keys: icon (str), color (str), category (str), "
        "input_placeholder (str), show_framework_selector (bool).",
    )


class CreateResult(BaseModel):
    """Output from the CreateAgent."""

    draft: str = Field(
        description=(
            "The COMPLETE written text of the content — the actual post, email, article, "
            "or document itself. This must be the full publishable draft, NOT a summary, "
            "description, or explanation of what was written. "
            "Example: for a LinkedIn post, this is the actual post text the user will copy and paste."
        )
    )
    content_type: str = Field(description="Content type used (e.g., linkedin, email)")
    mode: str = Field(
        description="Communication mode: casual, professional, or formal"
    )
    voice_elements: list[str] = Field(
        default_factory=list,
        description="Voice/tone elements applied in the draft",
    )
    patterns_applied: list[str] = Field(
        default_factory=list,
        description="Brain patterns applied",
    )
    examples_referenced: list[str] = Field(
        default_factory=list,
        description="Example titles that informed the draft",
    )
    word_count: int = Field(default=0, description="Word count of the draft")
    notes: str = Field(
        default="",
        description=(
            "Editorial notes for the human reviewer — suggestions about what to polish, "
            "verify, or adjust. Meta-commentary about the draft goes here, NOT in the draft field."
        ),
    )


class DimensionScore(BaseModel):
    """A single dimension's review score."""

    dimension: str = Field(description="Review dimension name (e.g., Messaging, Brand Voice)")
    score: int = Field(description="Score 1-10 for this dimension")
    status: str = Field(description="Status: pass, warning, or issue")
    strengths: list[str] = Field(default_factory=list, description="What's done well")
    suggestions: list[str] = Field(default_factory=list, description="Improvement suggestions")
    issues: list[str] = Field(default_factory=list, description="Must-fix problems")


class ReviewResult(BaseModel):
    """Aggregate scorecard from a full 6-dimension review."""

    scores: list[DimensionScore] = Field(description="Per-dimension scores")
    overall_score: float = Field(description="Average score across all dimensions (1-10)")
    verdict: str = Field(description="READY TO SEND, NEEDS REVISION, or MAJOR REWORK")
    summary: str = Field(default="", description="2-3 sentence overall assessment")
    top_strengths: list[str] = Field(default_factory=list, description="Top 3 strengths across all dimensions")
    critical_issues: list[str] = Field(default_factory=list, description="Must-fix issues across all dimensions")
    next_steps: list[str] = Field(default_factory=list, description="Recommended next actions")


class GrowthEvent(BaseModel):
    """A single brain growth event for the growth log."""

    event_type: str = Field(
        description="Type of growth event: pattern_created, pattern_reinforced, "
        "pattern_graduated, confidence_upgraded, confidence_downgraded, "
        "experience_added, memory_consolidated, content_reviewed, "
        "project_created, project_completed, milestone_reached, example_promoted"
    )
    event_date: str = Field(
        default="",
        description="Date of event (YYYY-MM-DD). Empty = server default.",
    )
    pattern_name: str = Field(default="", description="Pattern name if applicable")
    pattern_topic: str = Field(default="", description="Pattern topic if applicable")
    details: dict = Field(
        default_factory=dict,
        description="Event-specific details (JSON)",
    )


class ReviewDimensionEntry(BaseModel):
    """A single dimension score stored in review history."""

    dimension: str = Field(description="Review dimension name (e.g., Messaging, Brand Voice)")
    score: int = Field(description="Score 1-10 for this dimension")
    status: str = Field(default="pass", description="pass, warning, or issue")
    strengths: list[str] = Field(default_factory=list, description="Strengths noted")
    issues: list[str] = Field(default_factory=list, description="Issues found")


class ReviewHistoryEntry(BaseModel):
    """A stored review result for quality trending."""

    review_date: str = Field(
        default="",
        description="Date of review (YYYY-MM-DD). Empty = server default.",
    )
    content_type: str = Field(default="", description="Content type reviewed")
    overall_score: float = Field(description="Overall review score 1-10")
    verdict: str = Field(description="READY TO SEND, NEEDS REVISION, or MAJOR REWORK")
    dimension_scores: list[ReviewDimensionEntry] = Field(
        default_factory=list,
        description="Per-dimension scores as dicts",
    )
    top_strengths: list[str] = Field(default_factory=list)
    critical_issues: list[str] = Field(default_factory=list)
    content_preview: str = Field(
        default="",
        description="First 200 chars of reviewed content",
    )


class ConfidenceTransition(BaseModel):
    """A confidence level change event."""

    transition_date: str = Field(
        default="",
        description="Date of transition (YYYY-MM-DD). Empty = server default.",
    )
    pattern_name: str = Field(description="Pattern that changed confidence")
    pattern_topic: str = Field(default="", description="Pattern topic")
    from_confidence: str = Field(description="Previous confidence: NEW, LOW, MEDIUM, HIGH")
    to_confidence: str = Field(description="New confidence: LOW, MEDIUM, HIGH")
    use_count: int = Field(default=1, description="Use count at time of transition")
    reason: str = Field(default="", description="Why the transition happened")


# --- Project Lifecycle ---

ProjectStage = Literal["planning", "executing", "reviewing", "learning", "complete", "archived"]

ArtifactType = Literal["plan", "research", "output", "review", "learnings"]


class ProjectArtifact(BaseModel):
    """A single artifact within a project lifecycle."""

    artifact_type: ArtifactType = Field(
        description="Type of artifact: plan, research, output, review, or learnings"
    )
    title: str | None = Field(default=None, description="Artifact title")
    content: str | None = Field(default=None, description="Artifact content text")
    metadata: dict = Field(
        default_factory=dict, description="Additional artifact metadata"
    )


class ProjectResult(BaseModel):
    """Result of a project lifecycle operation."""

    project_id: str = Field(description="UUID of the project")
    name: str = Field(description="Project name")
    lifecycle_stage: ProjectStage = Field(description="Current lifecycle stage")
    category: str = Field(default="content", description="Project category")
    artifacts: list[ProjectArtifact] = Field(
        default_factory=list, description="Project artifacts"
    )
    review_score: float | None = Field(
        default=None, description="Final review score if reviewed"
    )
    patterns_extracted: list[str] = Field(
        default_factory=list, description="Pattern names extracted"
    )
    patterns_upgraded: list[str] = Field(
        default_factory=list, description="Pattern names upgraded"
    )
    message: str = Field(default="", description="Status message")


# --- Quality Trending ---


class DimensionBreakdown(BaseModel):
    """Score breakdown for a single review dimension over time."""

    dimension: str = Field(description="Dimension name (e.g. 'Messaging')")
    avg_score: float = Field(description="Average score for this dimension")
    trend: str = Field(
        default="stable", description="Score trend: improving/stable/declining"
    )
    review_count: int = Field(
        default=0, description="Number of reviews with this dimension scored"
    )


class QualityTrend(BaseModel):
    """Quality metrics trending data."""

    period_days: int = Field(description="Trend period in days")
    total_reviews: int = Field(default=0, description="Total reviews in period")
    avg_score: float = Field(default=0.0, description="Average overall score")
    score_trend: str = Field(
        default="stable",
        description="Overall trend: improving/stable/declining",
    )
    by_dimension: list[DimensionBreakdown] = Field(
        default_factory=list, description="Per-dimension breakdowns"
    )
    by_content_type: dict[str, float] = Field(
        default_factory=dict, description="Avg score per content type"
    )
    recurring_issues: list[str] = Field(
        default_factory=list,
        description="Issues appearing in 3+ reviews",
    )
    excellence_count: int = Field(
        default=0, description="Reviews scoring 9+"
    )
    needs_work_count: int = Field(
        default=0, description="Reviews scoring below 6"
    )


# --- Brain Growth Milestones ---

BrainLevel = Literal["EMPTY", "FOUNDATION", "GROWTH", "COMPOUND", "EXPERT"]


class BrainMilestone(BaseModel):
    """A brain growth milestone with completion status."""

    name: str = Field(description="Milestone name")
    description: str = Field(description="What this milestone requires")
    completed: bool = Field(
        default=False, description="Whether milestone is achieved"
    )
    completed_date: str | None = Field(
        default=None, description="ISO date when completed"
    )


class BrainGrowthStatus(BaseModel):
    """Overall brain growth level and milestone progress."""

    level: BrainLevel = Field(description="Current brain level")
    level_description: str = Field(description="Human-readable level meaning")
    milestones: list[BrainMilestone] = Field(
        default_factory=list, description="All milestones with status"
    )
    next_milestone: str | None = Field(
        default=None, description="Next unachieved milestone"
    )
    patterns_total: int = Field(default=0, description="Total pattern count")
    high_confidence_count: int = Field(
        default=0, description="HIGH confidence patterns"
    )
    experiences_total: int = Field(default=0, description="Total experiences")
    avg_review_score: float = Field(default=0.0, description="Average review score")


# --- Pattern Registry ---


class PatternRegistryEntry(BaseModel):
    """A pattern entry for the registry view."""

    id: str | None = Field(default=None, description="Pattern UUID from database")
    name: str = Field(description="Pattern name")
    topic: str = Field(description="Pattern topic/category")
    confidence: ConfidenceLevel = Field(description="Current confidence level")
    use_count: int = Field(
        default=0, description="Number of times used/reinforced"
    )
    date_added: str = Field(description="ISO date when first created")
    date_updated: str = Field(description="ISO date of last update")
    consecutive_failures: int = Field(
        default=0,
        description="Consecutive review failures below score 6",
    )
    is_stale: bool = Field(
        default=False, description="Not reinforced in 30+ days"
    )
    applicable_content_types: list[str] = Field(
        default_factory=list,
        description="Content types this applies to",
    )


class MemoryContentRow(BaseModel):
    """A memory content entry from the memory_content table.

    Used for structured storage of categorized memory content
    (e.g., brand voice rules, audience profiles, product positioning).
    """

    category: str = Field(description="Category name (e.g., voice, audience, product)")
    subcategory: str = Field(
        default="general",
        description="Sub-category for further grouping within a category",
    )
    content: str = Field(description="The memory content text")
    source: str = Field(default="", description="Source file or origin of this content")
    last_updated: str = Field(
        default="",
        description="ISO date string of last update (YYYY-MM-DD)",
    )


# --- Setup/Onboarding ---


class SetupStep(BaseModel):
    """A single setup step in the brain setup checklist."""

    category: str = Field(description="Memory category name (e.g., voice, audience)")
    label: str = Field(description="Human-readable label for this setup step")
    complete: bool = Field(default=False, description="Whether this step is complete")
    memory_count: int = Field(default=0, description="Number of memories in this category")


class SetupStatus(BaseModel):
    """Brain setup/onboarding completion status."""

    is_complete: bool = Field(
        default=False, description="Whether all setup steps are done"
    )
    steps: list[SetupStep] = Field(
        default_factory=list,
        description="Setup steps with completion status",
    )
    missing_categories: list[str] = Field(
        default_factory=list,
        description="Memory categories not yet populated",
    )
    total_memory_entries: int = Field(
        default=0, description="Total memory_content rows"
    )
    has_patterns: bool = Field(
        default=False, description="Whether any patterns exist"
    )
    has_examples: bool = Field(
        default=False, description="Whether any examples exist"
    )


class GrowthSummary(BaseModel):
    """Aggregated growth metrics for reporting."""

    period_days: int = Field(description="Number of days in the reporting period")
    patterns_created: int = Field(default=0)
    patterns_reinforced: int = Field(default=0)
    confidence_upgrades: int = Field(default=0)
    experiences_recorded: int = Field(default=0)
    reviews_completed: int = Field(default=0)
    avg_review_score: float = Field(default=0.0)
    review_score_trend: str = Field(
        default="stable",
        description="improving, stable, or declining",
    )
    stale_patterns: list[str] = Field(
        default_factory=list,
        description="Pattern names not reinforced in 30+ days",
    )
    top_patterns: list[str] = Field(
        default_factory=list,
        description="Most reinforced patterns in the period",
    )
    brain_level: str = Field(
        default="EMPTY", description="Current brain growth level"
    )
    milestones_completed: int = Field(
        default=0, description="Number of milestones achieved"
    )
    quality_trend: QualityTrend | None = Field(
        default=None,
        description="Quality trend for the period — None if no reviews in period",
    )


REVIEW_DIMENSIONS: list[dict[str, str]] = [
    {
        "name": "Messaging",
        "focus": "Message clarity and impact",
        "checks": "Clear key message, compelling value proposition, specific CTA, logical flow, no jargon",
    },
    {
        "name": "Positioning",
        "focus": "Market positioning and differentiation",
        "checks": "Differentiators highlighted, aligns with company positioning, competitive advantages clear, target audience alignment",
    },
    {
        "name": "Quality",
        "focus": "Completeness and professionalism",
        "checks": "All sections present, no placeholder text, consistent formatting, appropriate length, professional presentation",
    },
    {
        "name": "Data Accuracy",
        "focus": "Factual accuracy and claims",
        "checks": "Statistics accurate, claims have evidence, no contradictions, company info correct",
    },
    {
        "name": "Brand Voice",
        "focus": "Voice and tone consistency",
        "checks": "Tone matches voice guide, language consistent, personality comes through, matches winning examples",
    },
    {
        "name": "Competitive",
        "focus": "Competitive positioning",
        "checks": "Handles likely objections, doesn't oversell, unique value clear, avoids competitor traps",
    },
]

# Default review dimension configs (all enabled, weight 1.0)
# Used when a content type has review_dimensions=None
DEFAULT_REVIEW_DIMENSIONS: list[ReviewDimensionConfig] = [
    ReviewDimensionConfig(name=dim["name"], weight=1.0, enabled=True)
    for dim in REVIEW_DIMENSIONS
]


DEFAULT_CONTENT_TYPES: dict[str, ContentTypeConfig] = {
    "linkedin": ContentTypeConfig(
        name="LinkedIn Post",
        default_mode="casual",
        structure_hint="Hook -> Body (2-3 paragraphs) -> CTA/Question",
        example_type="linkedin",
        max_words=300,
        description="LinkedIn feed post",
        is_builtin=True,
        writing_instructions=(
            "LINKEDIN RULES:\n"
            "1. First line is the hook — must stop the scroll\n"
            "2. Use short paragraphs (1-2 sentences each)\n"
            "3. Include a clear CTA or question at the end\n"
            "4. No hashtag spam — 3-5 relevant hashtags max\n"
            "5. Write conversationally, not corporately"
        ),
        validation_rules={"min_words": 30},
        ui_config={"icon": "linkedin", "color": "#0077b5", "category": "social"},
    ),
    "email": ContentTypeConfig(
        name="Professional Email",
        default_mode="professional",
        structure_hint="Subject -> Opening -> Body -> Closing -> Next Steps",
        example_type="email",
        max_words=500,
        description="Client or prospect email",
        is_builtin=True,
        writing_instructions=(
            "EMAIL RULES:\n"
            "1. Subject line must be specific and action-oriented\n"
            "2. Opening line states purpose — no fluff\n"
            "3. One main ask per email\n"
            "4. End with clear next step and timeline\n"
            "5. Professional but warm — not robotic"
        ),
        validation_rules={"min_words": 50},
        ui_config={"icon": "mail", "color": "#ea580c", "category": "communication"},
    ),
    "landing-page": ContentTypeConfig(
        name="Landing Page",
        default_mode="professional",
        structure_hint="Headline -> Subhead -> Problem -> Solution -> Proof -> CTA",
        example_type="landing-page",
        max_words=1000,
        description="Homepage or landing page copy",
        is_builtin=True,
        writing_instructions=(
            "LANDING PAGE RULES:\n"
            "1. Headline must communicate the core value in under 10 words\n"
            "2. Subheadline elaborates the how/what\n"
            "3. Problem section uses customer language\n"
            "4. Social proof with specific numbers\n"
            "5. Single clear CTA — no competing actions"
        ),
        validation_rules={"min_words": 200},
        ui_config={"icon": "layout", "color": "#0ea5e9", "category": "marketing"},
    ),
    "comment": ContentTypeConfig(
        name="Comment/Reply",
        default_mode="casual",
        structure_hint="Acknowledgment -> Insight/Value -> Question (optional)",
        example_type="comment",
        max_words=150,
        description="Social media comment or reply",
        is_builtin=True,
        writing_instructions=(
            "COMMENT RULES:\n"
            "1. Acknowledge the original content first\n"
            "2. Add genuine value or a unique perspective\n"
            "3. Keep it concise — under 3 sentences\n"
            "4. Ask a follow-up question if natural\n"
            "5. Never be promotional"
        ),
        validation_rules={"min_words": 10},
        ui_config={"icon": "message-circle", "color": "#22c55e", "category": "social"},
    ),
    "case-study": ContentTypeConfig(
        name="Case Study",
        default_mode="professional",
        structure_hint="Client Context -> Challenge -> Approach -> Results (quantified) -> Key Takeaways",
        example_type="case-study",
        max_words=1500,
        description="Client success story with measurable results",
        is_builtin=True,
        writing_instructions=(
            "CASE STUDY RULES:\n"
            "1. Lead with the result — numbers first\n"
            "2. Client context must be relatable\n"
            "3. Challenge section uses before/after framing\n"
            "4. Approach section shows methodology, not just actions\n"
            "5. Results MUST be quantified — no vague claims"
        ),
        validation_rules={"min_words": 500},
        ui_config={"icon": "bar-chart", "color": "#8b5cf6", "category": "long-form"},
    ),
    "proposal": ContentTypeConfig(
        name="Sales Proposal",
        default_mode="professional",
        structure_hint="Executive Summary -> Problem -> Proposed Solution -> Deliverables -> Timeline -> Investment -> Next Steps",
        example_type="proposal",
        max_words=2000,
        description="Sales or project proposal with scope and pricing",
        is_builtin=True,
        writing_instructions=(
            "PROPOSAL RULES:\n"
            "1. Executive summary must standalone — assume reader skips the rest\n"
            "2. Problem section uses client language from discovery\n"
            "3. Solution maps directly to stated problems\n"
            "4. Deliverables are specific and measurable\n"
            "5. Investment section anchors on value, not cost"
        ),
        validation_rules={"min_words": 800},
        ui_config={"icon": "file-text", "color": "#f59e0b", "category": "business"},
    ),
    "one-pager": ContentTypeConfig(
        name="One-Pager",
        default_mode="professional",
        structure_hint="Headline -> Problem (1-2 sentences) -> Solution -> Key Benefits (3-4) -> Social Proof -> CTA",
        example_type="one-pager",
        max_words=500,
        description="Compact executive summary or overview document",
        is_builtin=True,
        writing_instructions=(
            "ONE-PAGER RULES:\n"
            "1. Must be scannable in 60 seconds\n"
            "2. Headline sells, body informs\n"
            "3. Benefits over features — max 4 bullets\n"
            "4. One piece of social proof\n"
            "5. Single CTA with clear next step"
        ),
        validation_rules={"min_words": 100},
        ui_config={"icon": "file", "color": "#14b8a6", "category": "business"},
    ),
    "presentation": ContentTypeConfig(
        name="Presentation Script",
        default_mode="professional",
        structure_hint="Opening Hook -> Key Points (3-5) -> Supporting Data -> Audience Messaging -> Call to Action",
        example_type="presentation",
        max_words=800,
        description="Presentation talking points and script (not slide text)",
        is_builtin=True,
        writing_instructions=(
            "PRESENTATION RULES:\n"
            "1. Opening hook must earn the next 30 seconds\n"
            "2. Max 3-5 key points — audience remembers 3\n"
            "3. Each point needs one supporting story or data point\n"
            "4. Transitions between points must be explicit\n"
            "5. End with a memorable closing, not just 'any questions?'"
        ),
        validation_rules={"min_words": 200},
        ui_config={"icon": "monitor", "color": "#ec4899", "category": "communication"},
    ),
    "instagram": ContentTypeConfig(
        name="Instagram Post",
        default_mode="casual",
        structure_hint="Hook (first line, attention-grabbing) -> Story/Value (2-3 short paragraphs) -> CTA -> Hashtags",
        example_type="instagram",
        max_words=200,
        description="Instagram caption with hook, story, and hashtags",
        is_builtin=True,
        writing_instructions=(
            "INSTAGRAM RULES:\n"
            "1. First line is the hook — visible before 'more'\n"
            "2. Tell a micro-story in 2-3 short paragraphs\n"
            "3. Use line breaks for readability\n"
            "4. CTA should feel natural, not salesy\n"
            "5. 5-10 relevant hashtags at the end"
        ),
        validation_rules={"min_words": 20},
        ui_config={"icon": "instagram", "color": "#e1306c", "category": "social"},
    ),
    "essay": ContentTypeConfig(
        name="Long-Form Essay",
        default_mode="professional",
        structure_hint="Title -> Central Question -> Thesis -> Body (3-5 sections with evidence) -> Conclusion",
        example_type="essay",
        max_words=3000,
        description="Intellectually rigorous, stylistically compelling essay",
        is_builtin=True,
        writing_instructions=(
            "WRITING PROCESS (follow in order):\n"
            "1. Identify the topic and evaluate the angle using STIRC scoring\n"
            "2. Formulate a central question the essay answers\n"
            "3. Choose structural framework: argumentative/explanatory/narrative\n"
            "4. Load voice guide and relevant patterns from brain\n"
            "5. Write the essay following the Five Laws\n"
            "6. Self-review against the quality checklist\n\n"
            "STIRC ANGLE SCORING (each 1-5, threshold 18/25):\n"
            "- Surprising: Contradicts common assumptions\n"
            "- True: Supported by evidence\n"
            "- Important: Matters to people\n"
            "- Relevant: Connects to current concerns\n"
            "- Cool: Inherently interesting\n\n"
            "FIVE WRITING LAWS:\n"
            "1. Active voice always (object then action)\n"
            "2. Remove needless words — every word earns its place\n"
            "3. No adverbs — strong verbs don't need modification\n"
            "4. Write simply — 4th-7th grade reading level\n"
            "5. First sentence must demand attention\n\n"
            "AI PATTERNS TO AVOID: em dashes for drama, 'Here's the thing:', "
            "'Let me explain why', Three. Word. Sentences., fake enthusiasm "
            "(amazing, incredible), rhetorical questions as transitions, 'In conclusion'."
        ),
        validation_rules={
            "min_words": 300,
            "required_sections": [],
            "custom_checks": ["title_required", "substantial_content"],
        },
        ui_config={
            "icon": "pen-tool",
            "color": "#6366f1",
            "category": "long-form",
            "input_placeholder": "What topic should the essay explore?",
            "show_framework_selector": True,
        },
    ),
}


# --- Chief of Staff / Orchestration ---

AgentRoute = Literal[
    "recall", "ask", "learn", "create", "review",
    "clarity", "synthesizer", "template_builder",
    "coach", "pmo", "email", "specialist",
    "pipeline",
]


class RoutingDecision(BaseModel):
    """Output from the Chief of Staff routing agent."""

    target_agent: AgentRoute = Field(description="Agent to route the request to")
    reasoning: str = Field(description="Why this agent was selected")
    context_to_inject: list[str] = Field(
        default_factory=list,
        description="Memory categories or files to load as context for the target agent",
    )
    pipeline_steps: list[AgentRoute] = Field(
        default_factory=list,
        description="If pipeline mode, ordered list of agents to chain. Empty for single agent.",
    )
    confidence: ConfidenceLevel = Field(default="MEDIUM", description="Routing confidence")


# --- Content Pipeline Agents ---


class ClarityFinding(BaseModel):
    """A single clarity issue found in content."""

    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = Field(description="Issue severity")
    location: str = Field(description="Where in the content the issue appears")
    issue: str = Field(description="Description of the clarity problem")
    suggestion: str = Field(description="Specific improvement suggestion")
    pattern: str = Field(default="", description="Pattern category: jargon, complexity, density, abstract")


class ClarityResult(BaseModel):
    """Output from the Clarity Maximizer agent."""

    findings: list[ClarityFinding] = Field(default_factory=list, description="Clarity issues found")
    overall_readability: str = Field(
        default="MEDIUM",
        description="Overall readability: HIGH (clear), MEDIUM (some issues), LOW (major barriers)",
    )
    summary: str = Field(default="", description="2-3 sentence readability assessment")
    critical_count: int = Field(default=0, description="Number of CRITICAL findings")


class SynthesizerTheme(BaseModel):
    """A consolidated improvement theme from the Feedback Synthesizer."""

    title: str = Field(description="Theme title (e.g., 'Strengthen Value Proposition')")
    priority: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = Field(description="Priority level")
    findings_consolidated: list[str] = Field(
        default_factory=list,
        description="Original finding descriptions merged into this theme",
    )
    action: str = Field(description="Specific implementation steps")
    effort_minutes: int = Field(default=30, description="Estimated implementation time in minutes")
    dependencies: list[str] = Field(
        default_factory=list,
        description="Theme titles that must be completed before this one",
    )
    owner: str = Field(default="user", description="Who should execute this action")


class SynthesizerResult(BaseModel):
    """Output from the Feedback Synthesizer agent."""

    themes: list[SynthesizerTheme] = Field(default_factory=list, description="Consolidated improvement themes")
    total_findings_input: int = Field(default=0, description="Total individual findings received")
    total_themes_output: int = Field(default=0, description="Number of consolidated themes")
    implementation_hours: float = Field(default=0.0, description="Total estimated hours")
    summary: str = Field(default="", description="Executive summary of improvement plan")
    parallel_opportunities: list[str] = Field(
        default_factory=list,
        description="Themes that can be worked on simultaneously",
    )


class TemplateOpportunity(BaseModel):
    """A reusable template opportunity identified by the Template Builder."""

    name: str = Field(description="Template name")
    source_deliverable: str = Field(description="What deliverable inspired this template")
    structure: str = Field(description="The reusable structure/framework")
    when_to_use: str = Field(description="Scenarios where this template applies")
    customization_guide: str = Field(default="", description="What to customize vs keep standard")
    estimated_time_savings: str = Field(default="", description="Time saved per use")


class TemplateBuilderResult(BaseModel):
    """Output from the Template Builder agent."""

    opportunities: list[TemplateOpportunity] = Field(
        default_factory=list, description="Template opportunities identified"
    )
    templates_created: int = Field(default=0, description="Number of new templates created")
    patterns_captured: list[str] = Field(
        default_factory=list, description="Pattern names captured as templates"
    )
    summary: str = Field(default="", description="Summary of template analysis")


# --- Operations & Advisory Agents ---


class CoachPriority(BaseModel):
    """A single priority item in a coaching session."""

    title: str = Field(description="Priority title or goal for this session")
    urgency: str = Field(default="medium", description="Urgency level: high/medium/low")
    status: str = Field(default="pending", description="pending/in-progress/done")
    notes: str = Field(default="", description="Additional context or blockers")


class TimeBlock(BaseModel):
    """A scheduled time block in a coaching session plan."""

    time: str = Field(description="Time range (e.g., '9:00-10:00 AM')")
    activity: str = Field(description="Planned activity for this block")
    priority: str = Field(default="", description="Associated priority title if any")
    energy_level: str = Field(default="medium", description="Required energy: high/medium/low")


class CoachSession(BaseModel):
    """Output from the Daily Accountability Coach."""

    session_type: Literal["morning", "evening", "check_in", "intervention"] = Field(
        description="Type of coaching session"
    )
    priorities: list[CoachPriority] = Field(
        default_factory=list,
        description="Prioritized tasks with scores and rationale",
    )
    time_blocks: list[TimeBlock] = Field(
        default_factory=list,
        description="Suggested time blocks with start/end and task assignment",
    )
    energy_assessment: str = Field(default="", description="User energy level and recommendation")
    coaching_notes: str = Field(default="", description="Coaching observations and suggestions")
    next_action: str = Field(default="", description="Immediate next step for the user")
    therapeutic_level: int = Field(
        default=1,
        description="Therapeutic depth level used (1=surface, 2=pattern, 3=core, 4=identity)",
    )


class PriorityScore(BaseModel):
    """A single task with PMO priority scoring."""

    task_name: str = Field(description="Task or project name")
    total_score: float = Field(description="Composite priority score 0-100")
    urgency: float = Field(default=0, description="Urgency score (35% weight)")
    impact: float = Field(default=0, description="Impact score (25% weight)")
    effort: float = Field(default=0, description="Effort score (15% weight, inverted)")
    alignment: float = Field(default=0, description="Strategic alignment (15% weight)")
    momentum: float = Field(default=0, description="Momentum score (10% weight)")
    category: str = Field(default="backlog", description="today_focus/this_week/backlog")
    rationale: str = Field(default="", description="Why this scored the way it did")


class PMOResult(BaseModel):
    """Output from the PMO Advisor agent."""

    scored_tasks: list[PriorityScore] = Field(default_factory=list, description="Scored and ranked tasks")
    today_focus: list[str] = Field(default_factory=list, description="Tasks for today (score >= 75)")
    this_week: list[str] = Field(default_factory=list, description="Tasks for this week (score >= 60)")
    quick_wins: list[str] = Field(default_factory=list, description="Tasks under 30 minutes")
    recommended_sequence: list[str] = Field(
        default_factory=list, description="Optimal execution order"
    )
    coaching_message: str = Field(default="", description="Conversational coaching guidance")
    capacity_hours: float = Field(default=8.0, description="Available focused hours estimated")


class EmailAction(BaseModel):
    """Output from the Email Agent."""

    action_type: Literal["send", "draft", "search", "organize"] = Field(
        description="What email action was performed"
    )
    subject: str = Field(default="", description="Email subject line")
    body: str = Field(default="", description="Email body content")
    recipients: list[str] = Field(default_factory=list, description="Email recipients")
    voice_elements: list[str] = Field(default_factory=list, description="Brand voice elements applied")
    template_used: str = Field(default="", description="Template name if one was used")
    status: str = Field(default="draft", description="sent/draft/searched/organized")
    notes: str = Field(default="", description="Notes for user review before sending")


class SpecialistAnswer(BaseModel):
    """Output from the Claude Code Specialist agent."""

    answer: str = Field(description="The verified answer with source citations")
    confidence_level: Literal["VERIFIED", "LIKELY", "UNCERTAIN"] = Field(
        description="Confidence: VERIFIED (from source), LIKELY (inferred), UNCERTAIN (needs verification)"
    )
    sources: list[str] = Field(default_factory=list, description="File paths or URLs cited")
    related_topics: list[str] = Field(default_factory=list, description="Related topics to explore")


# --- Brain Growth Milestone Definitions ---

BRAIN_MILESTONES = [
    {"name": "first_pattern", "description": "Extract your first pattern", "requires": {"min_patterns": 1}},
    {"name": "five_patterns", "description": "Accumulate 5 patterns", "requires": {"min_patterns": 5}},
    {"name": "first_medium", "description": "Achieve first MEDIUM confidence pattern", "requires": {"min_medium": 1}},
    {"name": "first_high", "description": "Achieve first HIGH confidence pattern", "requires": {"min_high": 1}},
    {"name": "ten_experiences", "description": "Complete 10 experiences", "requires": {"min_experiences": 10}},
    {"name": "consistent_quality", "description": "Average review score 8+", "requires": {"min_avg_score": 8.0}},
    {"name": "twenty_patterns", "description": "Accumulate 20 patterns", "requires": {"min_patterns": 20}},
    {"name": "five_high", "description": "Have 5 HIGH confidence patterns", "requires": {"min_high": 5}},
    {"name": "compound_returns", "description": "20+ experiences with 9+ avg score", "requires": {"min_experiences": 20, "min_avg_score": 9.0}},
]

BRAIN_LEVEL_THRESHOLDS = {
    "EMPTY": {"min_patterns": 0, "min_experiences": 0},
    "FOUNDATION": {"min_patterns": 1, "min_experiences": 0},
    "GROWTH": {"min_patterns": 5, "min_medium": 1},
    "COMPOUND": {"min_patterns": 10, "min_high": 1, "min_experiences": 10},
    "EXPERT": {"min_patterns": 20, "min_high": 5, "min_experiences": 20, "min_avg_score": 9.0},
}

QUALITY_GATE_SCORE = 8.0  # Minimum review score for example promotion
CONFIDENCE_DOWNGRADE_THRESHOLD = 6.0  # Score below which consecutive failures count
CONFIDENCE_DOWNGRADE_CONSECUTIVE = 2  # Consecutive failures before downgrade


# --- Vault Ingestion Models ---


class VaultFileMetadata(BaseModel):
    """Metadata extracted from a vault file's path and frontmatter."""

    file_path: str = Field(description="Absolute path to the source file")
    relative_path: str = Field(description="Path relative to vault root")
    user_id: str = Field(description="Mem0 user_id scope (uttam, robert, luke, or brainforge)")
    category: str = Field(description="Content category (voice, patterns, examples, transcript, etc.)")
    content_type: str | None = Field(default=None, description="Content format (linkedin, email, playbook, etc.)")
    client: str | None = Field(default=None, description="Client name if client-scoped content")
    author: str | None = Field(default=None, description="Author name if attributable")
    title: str = Field(description="Derived or extracted title")
    file_hash: str = Field(description="SHA-256 hash of file content for change detection")


class VaultFileContent(BaseModel):
    """Parsed content from a vault file."""

    metadata: VaultFileMetadata = Field(description="File metadata")
    body: str = Field(description="Main content body (markdown text)")
    frontmatter: dict = Field(default_factory=dict, description="Parsed frontmatter key-value pairs")
    is_transcript: bool = Field(default=False, description="Whether this file contains a WEBVTT transcript")


class TranscriptHeader(BaseModel):
    """Metadata from a transcript file's header block."""

    meeting_title: str = Field(default="", description="Meeting title from header")
    meeting_date: str = Field(default="", description="Meeting date from header")
    participants: list[str] = Field(default_factory=list, description="Meeting participants")


class TranscriptSummary(BaseModel):
    """AI-generated summary of a meeting transcript."""

    title: str = Field(description="Inferred title for this transcript")
    summary: str = Field(description="2-4 sentence summary of the main discussion")
    key_points: list[str] = Field(description="3-7 key takeaways")
    key_quotes: list[str] = Field(default_factory=list, description="Notable verbatim quotes with speaker attribution")
    speakers: list[str] = Field(default_factory=list, description="Speaker names identified")
    topics: list[str] = Field(default_factory=list, description="Main topics covered")
    action_items: list[str] = Field(default_factory=list, description="Action items or decisions made")


class IngestionResult(BaseModel):
    """Result of a vault ingestion run."""

    total_files: int = Field(default=0, description="Total files discovered")
    ingested: int = Field(default=0, description="Files successfully ingested")
    skipped: int = Field(default=0, description="Files skipped (already ingested, stub files, etc.)")
    errors: int = Field(default=0, description="Files that failed to ingest")
    transcripts_summarized: int = Field(default=0, description="Transcripts summarized by AI")
    by_user: dict[str, int] = Field(default_factory=dict, description="Counts per user_id")
    by_category: dict[str, int] = Field(default_factory=dict, description="Counts per category")
    error_files: list[str] = Field(default_factory=list, description="Paths of files that failed")


def content_type_from_row(row: dict) -> ContentTypeConfig:
    """Convert a Supabase content_types row to a ContentTypeConfig."""
    dims = row.get("review_dimensions")
    review_dims = None
    if dims and isinstance(dims, list):
        review_dims = [ReviewDimensionConfig(**d) for d in dims]
    return ContentTypeConfig(
        name=row["name"],
        default_mode=row.get("default_mode", "professional"),
        structure_hint=row.get("structure_hint", ""),
        example_type=row.get("example_type", row.get("slug", "")),
        max_words=row.get("max_words", 0),
        description=row.get("description", ""),
        review_dimensions=review_dims,
        is_builtin=row.get("is_builtin", False),
        writing_instructions=row.get("writing_instructions") or "",
        validation_rules=row.get("validation_rules") or {},
        ui_config=row.get("ui_config") or {},
    )
