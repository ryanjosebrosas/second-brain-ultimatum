"""Model factory -- provider-based LLM selection with fallback chains.

Uses the provider registry pattern: config.model_provider selects the primary
provider, config.model_fallback_chain lists fallback providers tried in order.
"""

import logging

from pydantic_ai.models import Model

from second_brain.config import BrainConfig

logger = logging.getLogger(__name__)


def get_model(config: BrainConfig) -> Model:
    """Get the best available LLM model using provider registry + fallback chain.

    Tries the primary provider first, then each fallback in order.
    Raises RuntimeError if all providers fail with diagnostic details.
    """
    from second_brain.providers import get_provider_class

    # Build list of providers to try: primary + fallbacks
    providers_to_try = [config.model_provider] + config.fallback_chain_list
    errors: list[tuple[str, str]] = []

    for provider_name in providers_to_try:
        try:
            provider_cls = get_provider_class(provider_name)
            provider = provider_cls.from_config(config)
            provider.validate_config()
            model = provider.build_model(config.model_name or "")
            if providers_to_try.index(provider_name) > 0:
                logger.info(
                    "Primary provider unavailable, using fallback: %s",
                    provider_name,
                )
            return model
        except Exception as e:
            reason = str(e)
            errors.append((provider_name, reason))
            logger.warning("Provider %s failed: %s", provider_name, reason)

    # All providers failed -- build diagnostic message
    tried = ", ".join(f"{name} ({reason})" for name, reason in errors)
    raise RuntimeError(
        f"No LLM available. Tried: {tried}. "
        "Set MODEL_PROVIDER and ensure the required API key/service is available. "
        "Supported providers: anthropic, ollama-local, ollama-cloud, openai, groq."
    )
