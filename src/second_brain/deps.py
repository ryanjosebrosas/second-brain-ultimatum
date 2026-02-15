from dataclasses import dataclass
from typing import TYPE_CHECKING

from second_brain.config import BrainConfig

if TYPE_CHECKING:
    from second_brain.services.graphiti import GraphitiService
    from second_brain.services.memory import MemoryService
    from second_brain.services.storage import ContentTypeRegistry, StorageService


@dataclass
class BrainDeps:
    """Dependencies injected into all Second Brain agents."""

    config: BrainConfig
    memory_service: "MemoryService"
    storage_service: "StorageService"
    graphiti_service: "GraphitiService | None" = None
    content_type_registry: "ContentTypeRegistry | None" = None

    def get_content_type_registry(self) -> "ContentTypeRegistry":
        """Get or create the content type registry."""
        if self.content_type_registry is None:
            from second_brain.services.storage import ContentTypeRegistry
            self.content_type_registry = ContentTypeRegistry(self.storage_service)
        return self.content_type_registry
