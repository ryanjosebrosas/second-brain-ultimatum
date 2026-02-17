"""Retry utility with exponential backoff for transient failures."""

import asyncio
import logging
from dataclasses import dataclass, field

from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
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


async def async_retry(func, *args, config: RetryConfig | None = None, **kwargs):
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
