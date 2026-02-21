"""Retry utility with exponential backoff for transient failures."""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    wait_random_exponential,
)

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_attempts: int = 3
    min_wait: float = 1.0
    max_wait: float = 10.0
    retry_on: tuple[type[Exception], ...] = field(
        default_factory=lambda: (ConnectionError, TimeoutError, OSError)
    )


DEFAULT_RETRY = RetryConfig()


@dataclass
class Mem0RetryConfig(RetryConfig):
    """Retry config with jitter for Mem0 cloud API."""

    # Override wait strategy to use jitter (avoids thundering herd)
    use_jitter: bool = True


MEM0_RETRY_CONFIG = Mem0RetryConfig(
    max_attempts=3,
    min_wait=1.0,
    max_wait=10.0,
    retry_on=(ConnectionError, TimeoutError, OSError),
    use_jitter=True,
)


def create_retry_decorator(config: RetryConfig | None = None):
    """Create a tenacity retry decorator from config.

    Args:
        config: Retry configuration. Defaults to DEFAULT_RETRY.

    Returns:
        A tenacity retry decorator with before_sleep_log for observability.
    """
    cfg = config or DEFAULT_RETRY
    wait_strategy = (
        wait_random_exponential(multiplier=1, max=cfg.max_wait)
        if getattr(cfg, "use_jitter", False)
        else wait_exponential(multiplier=1, min=cfg.min_wait, max=cfg.max_wait)
    )
    return retry(
        stop=stop_after_attempt(cfg.max_attempts),
        wait=wait_strategy,
        retry=retry_if_exception_type(cfg.retry_on),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


# Mem0-specific retry decorator with jitter and observable logging
_MEM0_RETRY = create_retry_decorator(MEM0_RETRY_CONFIG)


@dataclass
class GraphitiAdapterRetryConfig(RetryConfig):
    """Retry config for GraphitiMemoryAdapter (matches Mem0 pattern).

    Uses shorter backoff (0.5-4s vs 1-10s) since Graphiti is typically self-hosted
    with faster recovery. No jitter since there's no thundering herd concern.
    """

    use_jitter: bool = False


GRAPHITI_ADAPTER_RETRY_CONFIG = GraphitiAdapterRetryConfig(
    max_attempts=3,
    min_wait=0.5,
    max_wait=4.0,
    retry_on=(ConnectionError, TimeoutError, OSError),
    use_jitter=False,
)

# GraphitiMemoryAdapter retry decorator (for async method wrapping)
_GRAPHITI_ADAPTER_RETRY = create_retry_decorator(GRAPHITI_ADAPTER_RETRY_CONFIG)


async def async_retry(func: Callable[..., Any], *args: Any, config: RetryConfig | None = None, **kwargs: Any) -> Any:
    """Run a sync function in a thread with retry on transient failures."""
    cfg = config or DEFAULT_RETRY

    @retry(
        stop=stop_after_attempt(cfg.max_attempts),
        wait=wait_exponential(multiplier=1, min=cfg.min_wait, max=cfg.max_wait),
        retry=retry_if_exception_type(cfg.retry_on),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _call():
        return func(*args, **kwargs)

    return await asyncio.to_thread(_call)
