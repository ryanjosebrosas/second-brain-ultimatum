"""OpenAI provider -- GPT models via API key."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic_ai.models import Model

from second_brain.providers import BaseProvider, register_provider

if TYPE_CHECKING:
    from second_brain.config import BrainConfig

logger = logging.getLogger(__name__)

# Default model if user doesn't specify one
DEFAULT_OPENAI_MODEL = "gpt-4o"


class OpenAIProvider(BaseProvider):
    """OpenAI provider -- GPT models via API key."""

    def __init__(self, api_key: str, model: str = DEFAULT_OPENAI_MODEL):
        self._api_key = api_key
        self._model = model

    def validate_config(self) -> bool:
        if not self._api_key:
            raise ValueError(
                "OpenAI provider requires OPENAI_API_KEY. "
                "Get one at https://platform.openai.com/api-keys"
            )
        return True

    def build_model(self, model_name: str) -> Model:
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider as PydanticOpenAIProvider

        name = model_name or self._model
        model = OpenAIChatModel(
            name,
            provider=PydanticOpenAIProvider(api_key=self._api_key),
        )
        logger.info("Using OpenAI model: %s", name)
        return model

    @classmethod
    def from_config(cls, config: BrainConfig) -> OpenAIProvider:
        return cls(
            api_key=config.openai_api_key or "",
            model=config.openai_model_name,
        )


register_provider("openai", OpenAIProvider)
