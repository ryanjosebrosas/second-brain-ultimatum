"""Shared configuration for the Streamlit frontend."""

import os
from typing import Any
from urllib.parse import urlparse

# --- API Connection ---
_FASTAPI_URL_RAW = os.getenv("SECOND_BRAIN_API_URL", "http://localhost:8001")
_parsed = urlparse(_FASTAPI_URL_RAW)
if _parsed.scheme not in ("http", "https") or not _parsed.netloc:
    raise ValueError(
        f"Invalid SECOND_BRAIN_API_URL: {_FASTAPI_URL_RAW!r}. "
        "Must be a valid http:// or https:// URL."
    )
FASTAPI_URL: str = _FASTAPI_URL_RAW
API_BASE: str = FASTAPI_URL + "/api"

# --- Agent Definitions ---
# Each agent maps to a POST endpoint. Keys match the API route names.
# input_field: the field name in the request body schema
# extra_fields: additional optional fields the agent accepts
AGENTS = {
    "recall": {
        "name": "Recall",
        "icon": ":material/search:",
        "description": "Search memory for relevant context, patterns, and past experiences",
        "endpoint": "/recall",
        "input_field": "query",
        "input_label": "What do you want to recall?",
        "extra_fields": {},
    },
    "ask": {
        "name": "Ask",
        "icon": ":material/question_answer:",
        "description": "Ask the Second Brain a question",
        "endpoint": "/ask",
        "input_field": "question",
        "input_label": "What's your question?",
        "extra_fields": {},
    },
    "learn": {
        "name": "Learn",
        "icon": ":material/school:",
        "description": "Extract patterns and learnings from content",
        "endpoint": "/learn",
        "input_field": "content",
        "input_label": "Paste your work session or content to learn from",
        "extra_fields": {
            "category": {"type": "text", "default": "general", "label": "Category"},
        },
    },
    "create": {
        "name": "Create",
        "icon": ":material/edit:",
        "description": "Draft content in your voice using brain knowledge",
        "endpoint": "/create",
        "input_field": "prompt",
        "input_label": "What content do you want to create?",
        "extra_fields": {
            "content_type": {"type": "select", "default": "linkedin", "label": "Content Type"},
        },
    },
    "review": {
        "name": "Review",
        "icon": ":material/rate_review:",
        "description": "Review content quality with adaptive dimension scoring",
        "endpoint": "/review",
        "input_field": "content",
        "input_label": "Paste content to review",
        "extra_fields": {
            "content_type": {"type": "select", "default": None, "label": "Content Type (optional)"},
        },
    },
    "coaching": {
        "name": "Coach",
        "icon": ":material/fitness_center:",
        "description": "Get daily accountability coaching",
        "endpoint": "/coaching",
        "input_field": "request",
        "input_label": "What do you need coaching on?",
        "extra_fields": {
            "session_type": {"type": "select_fixed", "default": "morning", "label": "Session Type",
                            "options": ["morning", "midday", "evening", "weekly"]},
        },
    },
    "prioritize": {
        "name": "Prioritize",
        "icon": ":material/sort:",
        "description": "Score and prioritize tasks using PMO methodology",
        "endpoint": "/prioritize",
        "input_field": "tasks",
        "input_label": "List your tasks (one per line or comma-separated)",
        "extra_fields": {},
    },
    "email": {
        "name": "Email",
        "icon": ":material/mail:",
        "description": "Compose emails with brand voice",
        "endpoint": "/email",
        "input_field": "request",
        "input_label": "Describe the email you need",
        "extra_fields": {},
    },
    "specialist": {
        "name": "Specialist",
        "icon": ":material/code:",
        "description": "Ask about Claude Code or Pydantic AI",
        "endpoint": "/specialist",
        "input_field": "question",
        "input_label": "What's your technical question?",
        "extra_fields": {},
    },
    "pipeline": {
        "name": "Pipeline",
        "icon": ":material/route:",
        "description": "Run a multi-agent pipeline",
        "endpoint": "/pipeline",
        "input_field": "request",
        "input_label": "Describe what you need (agents will be routed automatically)",
        "extra_fields": {
            "steps": {"type": "text", "default": "", "label": "Steps (comma-separated, or leave empty for auto-routing)"},
        },
    },
    "clarity": {
        "name": "Clarity",
        "icon": ":material/visibility:",
        "description": "Analyze content for clarity and readability",
        "endpoint": "/clarity",
        "input_field": "content",
        "input_label": "Paste content to analyze",
        "extra_fields": {},
    },
    "synthesize": {
        "name": "Synthesize",
        "icon": ":material/merge:",
        "description": "Consolidate review findings into actionable themes",
        "endpoint": "/synthesize",
        "input_field": "findings",
        "input_label": "Paste review findings to synthesize",
        "extra_fields": {},
    },
    "templates": {
        "name": "Templates",
        "icon": ":material/dashboard_customize:",
        "description": "Analyze a deliverable for reusable template opportunities",
        "endpoint": "/templates",
        "input_field": "deliverable",
        "input_label": "Describe or paste the deliverable to analyze",
        "extra_fields": {},
    },
}

# --- Memory Table Definitions ---
MEMORY_TABLES = {
    "patterns": {
        "name": "Patterns",
        "icon": ":material/pattern:",
        "endpoint": "/search/patterns",
        "filters": {
            "topic": {"type": "text", "label": "Topic"},
            "confidence": {"type": "select_fixed", "label": "Confidence",
                          "options": ["", "HIGH", "MEDIUM", "LOW"]},
            "keyword": {"type": "text", "label": "Keyword"},
        },
        "display_fields": ["name", "pattern_text", "topic", "confidence", "use_count"],
    },
    "examples": {
        "name": "Examples",
        "icon": ":material/article:",
        "endpoint": "/search/examples",
        "filters": {
            "content_type": {"type": "text", "label": "Content Type"},
        },
        "display_fields": ["title", "content", "content_type"],
    },
    "knowledge": {
        "name": "Knowledge",
        "icon": ":material/menu_book:",
        "endpoint": "/search/knowledge",
        "filters": {
            "category": {"type": "text", "label": "Category"},
        },
        "display_fields": ["title", "content", "category", "tags"],
    },
    "experiences": {
        "name": "Experiences",
        "icon": ":material/work:",
        "endpoint": "/search/experiences",
        "filters": {
            "category": {"type": "text", "label": "Category"},
        },
        "display_fields": ["title", "description", "category", "impact"],
    },
}

# Explicit mapping from plural table keys to singular API delete names.
# Do NOT use rstrip("s") — it's fragile for irregular plurals.
DELETE_TABLE_MAP: dict[str, str] = {
    "patterns": "pattern",
    "examples": "example",
    "knowledge": "knowledge",
    "experiences": "experience",
}

# Offline fallback when /content-types API is unreachable.
# Keep in sync with backend ContentTypeRegistry.
DEFAULT_CONTENT_TYPES: list[str] = [
    "linkedin", "email", "landing-page", "comment", "case-study",
    "proposal", "one-pager", "presentation", "instagram", "essay",
]

# Category display order and labels
CONTENT_TYPE_CATEGORIES: dict[str, str] = {
    "social": "Social Media",
    "communication": "Communication",
    "marketing": "Marketing",
    "business": "Business",
    "long-form": "Long-Form Writing",
}

# Knowledge categories for the ingest form
KNOWLEDGE_CATEGORIES: list[str] = [
    "audience", "product", "competitors", "industry",
    "process", "values", "style-voice", "general",
]


def group_content_types_by_category(
    content_types: dict[str, Any],
) -> dict[str, list[tuple[str, str]]]:
    """Group content types by their ui_config.category.

    Returns: {"Social Media": [("linkedin", "LinkedIn Post"), ...], ...}
    Uncategorized types go under "Other".
    """
    groups: dict[str, list[tuple[str, str]]] = {}
    for slug, ct in content_types.items():
        ui = ct.get("ui_config", {}) if isinstance(ct, dict) else {}
        raw_category = ui.get("category", "other")
        display_category = CONTENT_TYPE_CATEGORIES.get(raw_category, raw_category.title())
        name = ct.get("name", slug) if isinstance(ct, dict) else slug
        groups.setdefault(display_category, []).append((slug, name))

    # Sort groups by CONTENT_TYPE_CATEGORIES order, then alphabetically within
    ordered: dict[str, list[tuple[str, str]]] = {}
    for raw_key, display_label in CONTENT_TYPE_CATEGORIES.items():
        if display_label in groups:
            ordered[display_label] = sorted(groups.pop(display_label), key=lambda x: x[1])
    # Append any remaining categories not in the predefined order
    for label in sorted(groups.keys()):
        ordered[label] = sorted(groups[label], key=lambda x: x[1])
    return ordered
