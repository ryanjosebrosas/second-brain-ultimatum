"""Second Brain services — memory and storage backends."""

from second_brain.services.embeddings import EmbeddingService
from second_brain.services.health import HealthService
from second_brain.services.memory import MemoryService
from second_brain.services.search_result import SearchResult
from second_brain.services.storage import ContentTypeRegistry, StorageService

# Lazy import: graphiti-core is optional
try:
    from second_brain.services.graphiti import GraphitiService
except ImportError:
    GraphitiService = None

__all__ = [
    "ContentTypeRegistry",
    "EmbeddingService",
    "GraphitiService",
    "HealthService",
    "MemoryService",
    "SearchResult",
    "StorageService",
]
