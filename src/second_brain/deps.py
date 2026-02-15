from dataclasses import dataclass
from typing import TYPE_CHECKING

from second_brain.config import BrainConfig

if TYPE_CHECKING:
    from second_brain.services.memory import MemoryService
    from second_brain.services.storage import StorageService


@dataclass
class BrainDeps:
    """Dependencies injected into all Second Brain agents."""

    config: BrainConfig
    memory_service: "MemoryService"
    storage_service: "StorageService"
