"""Ollama provider -- local and cloud modes via OpenAI-compatible API."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic_ai.models import Model

from second_brain.providers import BaseProvider, register_provider

if TYPE_CHECKING:
    from second_brain.config import BrainConfig

logger = logging.getLogger(__name__)


class OllamaLocalProvider(BaseProvider):
    """Ollama local provider -- connects to self-hosted Ollama server."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.1:8b"):
        self._base_url = base_url
        self._model = model

    def validate_config(self) -> bool:
        if not self._base_url:
            raise ValueError(
                "Ollama local provider requires OLLAMA_BASE_URL. "
                "Default: http://localhost:11434"
            )
        return True

    def build_model(self, model_name: str) -> Model:
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.ollama import OllamaProvider

        name = model_name or self._model
        model = OpenAIChatModel(
            name,
            provider=OllamaProvider(
                base_url=f"{self._base_url}/v1",
            ),
        )
        logger.info("Using Ollama local model: %s at %s", name, self._base_url)
        return model

    @classmethod
    def from_config(cls, config: BrainConfig) -> OllamaLocalProvider:
        return cls(
            base_url=config.ollama_base_url,
            model=config.ollama_model,
        )


class OllamaCloudProvider(BaseProvider):
    """Ollama cloud provider -- connects to hosted Ollama with API key."""

    def __init__(self, base_url: str, api_key: str | None = None, model: str = "llama3.1:8b"):
        self._base_url = base_url
        self._api_key = api_key
        self._model = model

    def validate_config(self) -> bool:
        if not self._base_url:
            raise ValueError(
                "Ollama cloud provider requires OLLAMA_BASE_URL "
                "(your hosted Ollama endpoint)."
            )
        if not self._api_key:
            raise ValueError(
                "Ollama cloud provider requires OLLAMA_API_KEY "
                "for authenticated access."
            )
        return True

    def build_model(self, model_name: str) -> Model:
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.ollama import OllamaProvider

        name = model_name or self._model
        model = OpenAIChatModel(
            name,
            provider=OllamaProvider(
                base_url=f"{self._base_url}/v1",
                api_key=self._api_key,
            ),
        )
        logger.info("Using Ollama cloud model: %s at %s", name, self._base_url)
        return model

    @classmethod
    def from_config(cls, config: BrainConfig) -> OllamaCloudProvider:
        return cls(
            base_url=config.ollama_base_url,
            api_key=config.ollama_api_key,
            model=config.ollama_model,
        )


register_provider("ollama-local", OllamaLocalProvider)
register_provider("ollama-cloud", OllamaCloudProvider)
