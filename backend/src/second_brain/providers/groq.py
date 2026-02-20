"""Groq provider -- fast inference via OpenAI-compatible API."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic_ai.models import Model

from second_brain.providers import BaseProvider, register_provider

if TYPE_CHECKING:
    from second_brain.config import BrainConfig

logger = logging.getLogger(__name__)

DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"


class GroqProvider(BaseProvider):
    """Groq provider -- OpenAI-compatible fast inference."""

    def __init__(self, api_key: str, model: str = DEFAULT_GROQ_MODEL):
        self._api_key = api_key
        self._model = model

    def validate_config(self) -> bool:
        if not self._api_key:
            raise ValueError(
                "Groq provider requires GROQ_API_KEY. "
                "Get one at https://console.groq.com/"
            )
        return True

    def build_model(self, model_name: str) -> Model:
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider

        name = model_name or self._model
        model = OpenAIChatModel(
            name,
            provider=OpenAIProvider(
                base_url=GROQ_BASE_URL,
                api_key=self._api_key,
            ),
        )
        logger.info("Using Groq model: %s", name)
        return model

    @classmethod
    def from_config(cls, config: BrainConfig) -> GroqProvider:
        return cls(
            api_key=config.groq_api_key or "",
            model=config.groq_model_name,
        )


register_provider("groq", GroqProvider)
