"""Pydantic output models for Second Brain agent responses."""

from typing import Literal

from pydantic import BaseModel, Field

ConfidenceLevel = Literal["LOW", "MEDIUM", "HIGH"]


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

    answer: str = Field(description="The contextual response")
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


class CreateResult(BaseModel):
    """Output from the CreateAgent."""

    draft: str = Field(description="The drafted content")
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
    notes: str = Field(default="", description="Notes for the human editor")


class DimensionScore(BaseModel):
    """A single dimension's review score."""

    dimension: str = Field(description="Review dimension name (e.g., Messaging, Brand Voice)")
    score: int = Field(description="Score 1-10 for this dimension")
    status: str = Field(description="Status: pass, warning, or issue")
    strengths: list[str] = Field(default_factory=list, description="What's done well")
    suggestions: list[str] = Field(default_factory=list, description="Improvement suggestions")
    issues: list[str] = Field(default_factory=list, description="Must-fix problems")


class ReviewDimensionConfig(BaseModel):
    """Per-content-type configuration for a review dimension."""

    name: str = Field(description="Dimension name matching REVIEW_DIMENSIONS (e.g., 'Messaging')")
    weight: float = Field(default=1.0, description="Relative weight for scoring (0.5=half, 1.0=normal, 1.5=extra)")
    enabled: bool = Field(default=True, description="Whether this dimension applies to this content type")


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
        description="Event type: pattern_created, pattern_reinforced, "
        "confidence_upgraded, experience_recorded"
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


class ReviewHistoryEntry(BaseModel):
    """A stored review result for quality trending."""

    review_date: str = Field(
        default="",
        description="Date of review (YYYY-MM-DD). Empty = server default.",
    )
    content_type: str = Field(default="", description="Content type reviewed")
    overall_score: float = Field(description="Overall review score 1-10")
    verdict: str = Field(description="READY TO SEND, NEEDS REVISION, or MAJOR REWORK")
    dimension_scores: list[dict] = Field(
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
    ),
    "email": ContentTypeConfig(
        name="Professional Email",
        default_mode="professional",
        structure_hint="Subject -> Opening -> Body -> Closing -> Next Steps",
        example_type="email",
        max_words=500,
        description="Client or prospect email",
        is_builtin=True,
    ),
    "landing-page": ContentTypeConfig(
        name="Landing Page",
        default_mode="professional",
        structure_hint="Headline -> Subhead -> Problem -> Solution -> Proof -> CTA",
        example_type="landing-page",
        max_words=1000,
        description="Homepage or landing page copy",
        is_builtin=True,
    ),
    "comment": ContentTypeConfig(
        name="Comment/Reply",
        default_mode="casual",
        structure_hint="Acknowledgment -> Insight/Value -> Question (optional)",
        example_type="comment",
        max_words=150,
        description="Social media comment or reply",
        is_builtin=True,
    ),
    "case-study": ContentTypeConfig(
        name="Case Study",
        default_mode="professional",
        structure_hint="Client Context -> Challenge -> Approach -> Results (quantified) -> Key Takeaways",
        example_type="case-study",
        max_words=1500,
        description="Client success story with measurable results",
        is_builtin=True,
    ),
    "proposal": ContentTypeConfig(
        name="Sales Proposal",
        default_mode="professional",
        structure_hint="Executive Summary -> Problem -> Proposed Solution -> Deliverables -> Timeline -> Investment -> Next Steps",
        example_type="proposal",
        max_words=2000,
        description="Sales or project proposal with scope and pricing",
        is_builtin=True,
    ),
    "one-pager": ContentTypeConfig(
        name="One-Pager",
        default_mode="professional",
        structure_hint="Headline -> Problem (1-2 sentences) -> Solution -> Key Benefits (3-4) -> Social Proof -> CTA",
        example_type="one-pager",
        max_words=500,
        description="Compact executive summary or overview document",
        is_builtin=True,
    ),
    "presentation": ContentTypeConfig(
        name="Presentation Script",
        default_mode="professional",
        structure_hint="Opening Hook -> Key Points (3-5) -> Supporting Data -> Audience Messaging -> Call to Action",
        example_type="presentation",
        max_words=800,
        description="Presentation talking points and script (not slide text)",
        is_builtin=True,
    ),
    "instagram": ContentTypeConfig(
        name="Instagram Post",
        default_mode="casual",
        structure_hint="Hook (first line, attention-grabbing) -> Story/Value (2-3 short paragraphs) -> CTA -> Hashtags",
        example_type="instagram",
        max_words=200,
        description="Instagram caption with hook, story, and hashtags",
        is_builtin=True,
    ),
}


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
    )
