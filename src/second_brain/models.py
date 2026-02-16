import logging

from pydantic_ai.models import Model

from second_brain.config import BrainConfig

logger = logging.getLogger(__name__)


def get_model(config: BrainConfig) -> Model:
    """Get the best available LLM model with fallback.

    Tries: Anthropic Claude (API key) -> Claude SDK (subscription) -> Ollama (local)
    """
    # Try primary model (Anthropic Claude) — only if API key is set
    if config.anthropic_api_key:
        try:
            from pydantic_ai.models.anthropic import AnthropicModel
            from pydantic_ai.providers.anthropic import AnthropicProvider

            model = AnthropicModel(
                config.primary_model.replace("anthropic:", ""),
                provider=AnthropicProvider(api_key=config.anthropic_api_key),
            )
            logger.info(f"Using primary model: {config.primary_model}")
            return model
        except Exception as e:
            logger.warning(f"Primary model unavailable: {e}")
    else:
        logger.info("No Anthropic API key set, skipping primary model")

    # Try subscription auth (Claude SDK via OAuth token)
    if config.use_subscription:
        try:
            from second_brain.models_sdk import create_sdk_model

            sdk_model = create_sdk_model(config)
            if sdk_model:
                logger.info("Using subscription model: %s", sdk_model.model_name)
                return sdk_model
            else:
                logger.info("Subscription auth not available, trying fallback")
        except Exception as e:
            logger.warning("SDK model creation failed: %s", e)

    # Try fallback (Ollama via OpenAI-compatible API)
    try:
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.ollama import OllamaProvider

        model = OpenAIChatModel(
            config.ollama_model,
            provider=OllamaProvider(
                base_url=f"{config.ollama_base_url}/v1",
                api_key=config.ollama_api_key,
            ),
        )
        logger.info(f"Using fallback model: {config.fallback_model}")
        return model
    except Exception as e:
        logger.error(f"Fallback model also unavailable: {e}")
        raise RuntimeError(
            "No LLM available. Set ANTHROPIC_API_KEY, enable USE_SUBSCRIPTION=true "
            "(requires claude CLI), or start Ollama."
        ) from e
