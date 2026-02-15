"""Pydantic output models for Second Brain agent responses."""

from pydantic import BaseModel, Field


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
    confidence: str = Field(
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
    confidence: str = Field(
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
