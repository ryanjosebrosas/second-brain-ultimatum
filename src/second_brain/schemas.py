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
