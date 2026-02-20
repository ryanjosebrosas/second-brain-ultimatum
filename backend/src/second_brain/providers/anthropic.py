"""Anthropic provider -- Claude models via API key or subscription auth."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic_ai.models import Model

from second_brain.providers import BaseProvider, register_provider

if TYPE_CHECKING:
    from second_brain.config import BrainConfig

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseProvider):
    """Anthropic Claude provider (API key auth)."""

    def __init__(self, api_key: str, use_subscription: bool = False, config: "BrainConfig | None" = None):
        self._api_key = api_key
        self._use_subscription = use_subscription
        self._config = config

    def validate_config(self) -> bool:
        if not self._api_key and not self._use_subscription:
            raise ValueError(
                "Anthropic provider requires ANTHROPIC_API_KEY or USE_SUBSCRIPTION=true. "
                "Get an API key at https://console.anthropic.com/"
            )
        return True

    def build_model(self, model_name: str) -> Model:
        # Try subscription auth first if enabled
        if self._use_subscription and self._config:
            try:
                from second_brain.models_sdk import create_sdk_model
                sdk_model = create_sdk_model(self._config)
                if sdk_model:
                    logger.info("Using Anthropic subscription model: %s", sdk_model.model_name)
                    return sdk_model
            except Exception as e:
                logger.warning("Subscription auth failed, falling back to API key: %s", e)

        if not self._api_key:
            raise ValueError(
                "Subscription auth unavailable and no ANTHROPIC_API_KEY set. "
                "Either authenticate Claude CLI or provide an API key."
            )

        from pydantic_ai.models.anthropic import AnthropicModel
        from pydantic_ai.providers.anthropic import AnthropicProvider as PydanticAnthropicProvider

        # Strip 'anthropic:' prefix if present
        clean_name = model_name.replace("anthropic:", "")
        model = AnthropicModel(
            clean_name,
            provider=PydanticAnthropicProvider(api_key=self._api_key),
        )
        logger.info("Using Anthropic model: %s", clean_name)
        return model

    @classmethod
    def from_config(cls, config: BrainConfig) -> AnthropicProvider:
        return cls(
            api_key=config.anthropic_api_key or "",
            use_subscription=config.use_subscription,
            config=config,
        )


register_provider("anthropic", AnthropicProvider)
