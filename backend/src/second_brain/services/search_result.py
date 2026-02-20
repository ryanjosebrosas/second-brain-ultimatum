"""Typed search result for MemoryService."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SearchResult:
    """Result from MemoryService.search() with optional graph relations."""

    memories: list[dict[str, Any]] = field(default_factory=list)
    relations: list[dict[str, Any]] = field(default_factory=list)
    search_filters: dict[str, Any] = field(default_factory=dict)
