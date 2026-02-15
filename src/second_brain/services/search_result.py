"""Typed search result for MemoryService."""

from dataclasses import dataclass, field


@dataclass
class SearchResult:
    """Result from MemoryService.search() with optional graph relations."""

    memories: list[dict] = field(default_factory=list)
    relations: list[dict] = field(default_factory=list)
