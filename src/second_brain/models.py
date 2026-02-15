import logging

from pydantic_ai.models import Model

from second_brain.config import BrainConfig

logger = logging.getLogger(__name__)


def get_model(config: BrainConfig) -> Model:
    """Get the best available LLM model with fallback.

    Tries: Anthropic Claude -> Ollama (local)
    """
    # Try primary model (Anthropic Claude)
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

    # Try fallback (Ollama via OpenAI-compatible API)
    try:
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.ollama import OllamaProvider

        model = OpenAIChatModel(
            config.ollama_model,
            provider=OllamaProvider(
                base_url=f"{config.ollama_base_url}/v1",
            ),
        )
        logger.info(f"Using fallback model: {config.fallback_model}")
        return model
    except Exception as e:
        logger.error(f"Fallback model also unavailable: {e}")
        raise RuntimeError(
            "No LLM available. Set ANTHROPIC_API_KEY or start Ollama."
        ) from e
