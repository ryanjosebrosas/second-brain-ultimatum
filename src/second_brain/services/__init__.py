"""Second Brain services — memory and storage backends."""

from second_brain.services.memory import MemoryService
from second_brain.services.search_result import SearchResult
from second_brain.services.storage import StorageService

# Lazy import: graphiti-core is optional
try:
    from second_brain.services.graphiti import GraphitiService
except ImportError:
    GraphitiService = None

__all__ = ["GraphitiService", "MemoryService", "SearchResult", "StorageService"]
