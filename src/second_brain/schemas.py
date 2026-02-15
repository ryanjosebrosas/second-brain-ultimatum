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


CONTENT_TYPES: dict[str, ContentTypeConfig] = {
    "linkedin": ContentTypeConfig(
        name="LinkedIn Post",
        default_mode="casual",
        structure_hint="Hook -> Body (2-3 paragraphs) -> CTA/Question",
        example_type="linkedin",
        max_words=300,
        description="LinkedIn feed post",
    ),
    "email": ContentTypeConfig(
        name="Professional Email",
        default_mode="professional",
        structure_hint="Subject -> Opening -> Body -> Closing -> Next Steps",
        example_type="email",
        max_words=500,
        description="Client or prospect email",
    ),
    "landing-page": ContentTypeConfig(
        name="Landing Page",
        default_mode="professional",
        structure_hint="Headline -> Subhead -> Problem -> Solution -> Proof -> CTA",
        example_type="landing-page",
        max_words=1000,
        description="Homepage or landing page copy",
    ),
    "comment": ContentTypeConfig(
        name="Comment/Reply",
        default_mode="casual",
        structure_hint="Acknowledgment -> Insight/Value -> Question (optional)",
        example_type="comment",
        max_words=150,
        description="Social media comment or reply",
    ),
}
