"""Provider registry and base class for LLM providers.

All providers inherit from BaseProvider and register via PROVIDER_REGISTRY.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from pydantic_ai.models import Model

if TYPE_CHECKING:
    from second_brain.config import BrainConfig

logger = logging.getLogger(__name__)


class BaseProvider(ABC):
    """Abstract base for LLM providers."""

    @abstractmethod
    def build_model(self, model_name: str) -> Model:
        """Build and return a pydantic-ai Model instance."""

    @abstractmethod
    def validate_config(self) -> bool:
        """Validate provider config is present/valid. Raise ValueError if not."""

    @classmethod
    @abstractmethod
    def from_config(cls, config: BrainConfig) -> BaseProvider:
        """Factory -- instantiate provider from BrainConfig."""


# Registry maps provider name -> class
PROVIDER_REGISTRY: dict[str, type[BaseProvider]] = {}


def register_provider(name: str, cls: type[BaseProvider]) -> None:
    """Register a provider class under a name."""
    PROVIDER_REGISTRY[name] = cls


def get_provider_class(name: str) -> type[BaseProvider]:
    """Look up a provider class by name.

    Raises ValueError if the provider is not registered.
    """
    if name not in PROVIDER_REGISTRY:
        available = ", ".join(sorted(PROVIDER_REGISTRY.keys()))
        raise ValueError(
            f"Unknown model provider: {name!r}. "
            f"Available providers: {available}"
        )
    return PROVIDER_REGISTRY[name]


# Import providers to trigger registration
def _register_all() -> None:
    """Import all provider modules to populate the registry."""
    from second_brain.providers.anthropic import AnthropicProvider  # noqa: F401
    from second_brain.providers.ollama import OllamaLocalProvider, OllamaCloudProvider  # noqa: F401
    from second_brain.providers.openai import OpenAIProvider  # noqa: F401
    from second_brain.providers.groq import GroqProvider  # noqa: F401


_register_all()

__all__ = [
    "BaseProvider",
    "PROVIDER_REGISTRY",
    "register_provider",
    "get_provider_class",
]
