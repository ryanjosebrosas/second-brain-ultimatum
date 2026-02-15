import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from second_brain.config import BrainConfig

if TYPE_CHECKING:
    from second_brain.services.graphiti import GraphitiService
    from second_brain.services.memory import MemoryService
    from second_brain.services.storage import ContentTypeRegistry, StorageService

logger = logging.getLogger(__name__)


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


def create_deps(config: BrainConfig | None = None) -> BrainDeps:
    """Create BrainDeps with all services initialized.

    Args:
        config: Optional config override. Defaults to loading from .env.
    """
    from second_brain.services.memory import MemoryService
    from second_brain.services.storage import StorageService

    if config is None:
        config = BrainConfig()

    graphiti = None
    # New path: graphiti_enabled flag (independent of Mem0 graph)
    if config.graphiti_enabled:
        try:
            from second_brain.services.graphiti import GraphitiService
            graphiti = GraphitiService(config)
        except ImportError:
            logger.warning(
                "graphiti-core not installed. Install with: pip install -e '.[graphiti]'"
            )
    # Legacy path: graph_provider="graphiti" (backwards compat)
    elif config.graph_provider == "graphiti":
        try:
            from second_brain.services.graphiti import GraphitiService
            graphiti = GraphitiService(config)
        except ImportError:
            logger.warning(
                "graphiti-core not installed. Install with: pip install -e '.[graphiti]'"
            )

    return BrainDeps(
        config=config,
        memory_service=MemoryService(config),
        storage_service=StorageService(config),
        graphiti_service=graphiti,
    )
