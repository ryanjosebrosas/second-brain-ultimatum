"""Request body models for the FastAPI REST API.

These are INPUT schemas only — output schemas live in second_brain.schemas.
"""

from typing import Literal

from pydantic import BaseModel, Field


# --- Agent request models ---

class RecallRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=10000)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=10000)


class LearnRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    category: str = Field(default="general")


class CreateContentRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=10000)
    content_type: str = Field(default="linkedin")


class ReviewContentRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    content_type: str | None = Field(default=None)


class CoachingRequest(BaseModel):
    request: str = Field(..., min_length=1, max_length=10000)
    session_type: str = Field(default="morning")


class PrioritizeRequest(BaseModel):
    tasks: str = Field(..., min_length=1, max_length=10000)


class EmailRequest(BaseModel):
    request: str = Field(..., min_length=1, max_length=10000)


class SpecialistRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=10000)


class PipelineRequest(BaseModel):
    request: str = Field(..., min_length=1, max_length=10000)
    steps: str = Field(default="")


class ClarityRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)


class SynthesizeRequest(BaseModel):
    findings: str = Field(..., min_length=1, max_length=10000)


class TemplateRequest(BaseModel):
    deliverable: str = Field(..., min_length=1, max_length=10000)


# --- Memory request models ---

class VectorSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=10000)
    table: Literal["memory_content", "patterns", "examples", "knowledge_repo"] = Field(
        default="memory_content"
    )
    limit: int = Field(default=10, ge=1, le=100)


class MultimodalSearchRequest(BaseModel):
    query: str = Field(default="")
    image_url: str = Field(default="")
    table: Literal["memory_content", "patterns", "examples", "knowledge_repo"] = Field(
        default="memory_content"
    )
    limit: int = Field(default=10, ge=1, le=100)


class IngestExampleRequest(BaseModel):
    content_type: str = Field(..., min_length=1, max_length=200)
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1, max_length=10000)
    notes: str | None = Field(default=None)


class IngestKnowledgeRequest(BaseModel):
    category: str = Field(..., min_length=1, max_length=200)
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1, max_length=10000)
    tags: str | None = Field(default=None)


class LearnImageRequest(BaseModel):
    image_url: str = Field(..., min_length=1)
    context: str = Field(default="")
    category: str = Field(default="visual")


class LearnDocumentRequest(BaseModel):
    document_url: str = Field(..., min_length=1)
    document_type: str = Field(default="pdf")
    context: str = Field(default="")
    category: str = Field(default="document")


class LearnVideoRequest(BaseModel):
    video_url: str = Field(..., min_length=1)
    context: str = Field(default="")
    category: str = Field(default="video")


# --- Project request models ---

class CreateProjectRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    category: str = Field(default="content")
    description: str | None = Field(default=None)


class UpdateProjectRequest(BaseModel):
    name: str | None = Field(default=None)
    description: str | None = Field(default=None)
    category: str | None = Field(default=None)


class AdvanceProjectRequest(BaseModel):
    target_stage: str | None = Field(default=None)


class AddArtifactRequest(BaseModel):
    artifact_type: str = Field(..., min_length=1)
    title: str | None = Field(default=None)
    content: str | None = Field(default=None)


class ManageContentTypeRequest(BaseModel):
    action: str = Field(..., description="'add' or 'remove'")
    slug: str = Field(..., min_length=1, max_length=100)
    name: str = Field(default="")
    default_mode: str = Field(default="professional")
    structure_hint: str = Field(default="")
    max_words: int = Field(default=500, ge=1)
    description: str = Field(default="")


# --- Template request models ---

class CreateTemplateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    content_type: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1, max_length=50000)
    description: str = Field(default="")
    structure_hint: str = Field(default="")
    when_to_use: str = Field(default="")
    when_not_to_use: str = Field(default="")
    customization_guide: str = Field(default="")
    tags: list[str] = Field(default_factory=list)
    source_deliverable: str = Field(default="")
    ai_generated: bool = Field(default=False)


class UpdateTemplateRequest(BaseModel):
    name: str | None = Field(default=None)
    content_type: str | None = Field(default=None)
    body: str | None = Field(default=None)
    description: str | None = Field(default=None)
    structure_hint: str | None = Field(default=None)
    when_to_use: str | None = Field(default=None)
    when_not_to_use: str | None = Field(default=None)
    customization_guide: str | None = Field(default=None)
    tags: list[str] | None = Field(default=None)


class DeconstructRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=50000)
    content_type: str = Field(default="", description="Optional hint for content type detection")


# --- Graph request models ---

class GraphSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=10000)
    limit: int = Field(default=10, ge=1, le=100)
