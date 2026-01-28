"""Exponential backoff retry logic for Lardi-Trans API."""

import asyncio
import time
from typing import Awaitable, Callable, TypeVar

from della.services.larditrans.exceptions import RateLimitedError

T = TypeVar("T")

MAX_RETRIES = 5
BASE_DELAY = 2.0  # seconds
MAX_DELAY = 60.0  # seconds
BACKOFF_FACTOR = 2


def retry_on_rate_limit(fn: Callable[[], T]) -> T:
    """Retry function with exponential backoff when rate limited.

    Args:
        fn: Function to execute that may raise RateLimitedError.

    Returns:
        Result of the function.

    Raises:
        RateLimitedError: If all retries are exhausted.
        Exception: Any other exception from the function.
    """
    delay = BASE_DELAY

    for attempt in range(MAX_RETRIES):
        try:
            return fn()
        except RateLimitedError:
            if attempt == MAX_RETRIES - 1:
                raise

            time.sleep(delay)
            delay = min(delay * BACKOFF_FACTOR, MAX_DELAY)

    raise RateLimitedError()


async def async_retry_on_rate_limit(fn: Callable[[], Awaitable[T]]) -> T:
    """Async retry function with exponential backoff when rate limited.

    Args:
        fn: Async function to execute that may raise RateLimitedError.

    Returns:
        Result of the function.

    Raises:
        RateLimitedError: If all retries are exhausted.
        Exception: Any other exception from the function.
    """
    delay = BASE_DELAY

    for attempt in range(MAX_RETRIES):
        try:
            return await fn()
        except RateLimitedError:
            if attempt == MAX_RETRIES - 1:
                raise

            await asyncio.sleep(delay)
            delay = min(delay * BACKOFF_FACTOR, MAX_DELAY)

    raise RateLimitedError()
