"""
Auto Retry Mechanism (T029)

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)

Provides:
- Exponential backoff retry logic
- Configurable retry parameters
- Retry decorator and context manager
- Retryable LLM client wrapper
- Callbacks for retry events
"""

import functools
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator, List, Optional, Tuple, Type, Union


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: float = 0.0  # Random jitter factor (0-1)
    total_timeout: Optional[float] = None  # Total timeout in seconds


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """
    Calculate delay for retry attempt using exponential backoff.

    Args:
        attempt: Retry attempt number (0-based)
        config: Retry configuration

    Returns:
        Delay in seconds
    """
    # Exponential backoff: base_delay * exponential_base^attempt
    delay = config.base_delay * (config.exponential_base ** attempt)

    # Cap at max_delay
    delay = min(delay, config.max_delay)

    # Add jitter if configured
    if config.jitter > 0:
        jitter_range = delay * config.jitter
        delay = delay + random.uniform(-jitter_range, jitter_range)
        delay = max(0, delay)  # Ensure non-negative

    return delay


def retry(
    config: RetryConfig,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[int, Exception, float], None]] = None,
    should_retry: Optional[Callable[[Exception], bool]] = None,
) -> Callable:
    """
    Retry decorator with exponential backoff.

    Args:
        config: Retry configuration
        exceptions: Tuple of exception types to retry on
        on_retry: Callback called on each retry (attempt, exception, delay)
        should_retry: Optional callback to determine if should retry

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            last_exception: Optional[Exception] = None

            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    # Check if we should retry
                    if should_retry is not None and not should_retry(e):
                        raise

                    # Check if max retries reached
                    if attempt >= config.max_retries:
                        raise

                    # Check total timeout
                    if config.total_timeout is not None:
                        elapsed = time.time() - start_time
                        if elapsed >= config.total_timeout:
                            raise

                    # Calculate delay
                    delay = calculate_delay(attempt, config)

                    # Check if delay would exceed timeout
                    if config.total_timeout is not None:
                        elapsed = time.time() - start_time
                        remaining = config.total_timeout - elapsed
                        if delay > remaining:
                            raise

                    # Call on_retry callback
                    if on_retry is not None:
                        on_retry(attempt, e, delay)

                    # Wait before retry
                    time.sleep(delay)

            # Should not reach here, but just in case
            if last_exception is not None:
                raise last_exception

        return wrapper
    return decorator


class RetryAttempt:
    """Represents a retry attempt in context manager."""

    def __init__(self) -> None:
        self._should_retry = False
        self._exception: Optional[Exception] = None

    def retry(self, exception: Exception) -> None:
        """
        Signal that this attempt should be retried.

        Args:
            exception: Exception that caused the retry
        """
        self._should_retry = True
        self._exception = exception

    @property
    def should_retry(self) -> bool:
        """Check if should retry."""
        return self._should_retry

    @property
    def exception(self) -> Optional[Exception]:
        """Get the exception."""
        return self._exception


def retry_context(config: RetryConfig) -> Iterator[RetryAttempt]:
    """
    Context manager for retry logic.

    Args:
        config: Retry configuration

    Yields:
        RetryAttempt for each attempt

    Example:
        for attempt in retry_context(config):
            try:
                result = do_something()
                break
            except Exception as e:
                attempt.retry(e)
    """
    start_time = time.time()

    for attempt_num in range(config.max_retries + 1):
        attempt = RetryAttempt()
        yield attempt

        if not attempt.should_retry:
            return

        # Check if max retries reached
        if attempt_num >= config.max_retries:
            if attempt.exception:
                raise attempt.exception
            return

        # Check total timeout
        if config.total_timeout is not None:
            elapsed = time.time() - start_time
            if elapsed >= config.total_timeout:
                if attempt.exception:
                    raise attempt.exception
                return

        # Calculate and apply delay
        delay = calculate_delay(attempt_num, config)
        time.sleep(delay)


class RetryableLLMClient:
    """
    LLM client wrapper with automatic retry.

    Wraps an LLM client and adds retry logic for transient failures.
    """

    def __init__(
        self,
        client: Any,
        config: Optional[RetryConfig] = None,
        on_retry: Optional[Callable[[int, Exception, float], None]] = None,
    ) -> None:
        """
        Initialize retryable client.

        Args:
            client: Underlying LLM client
            config: Retry configuration
            on_retry: Callback for retry events
        """
        self._client = client
        self._config = config or RetryConfig()
        self._on_retry = on_retry

    def chat_completion(
        self,
        messages: List[Any],
        **kwargs: Any,
    ) -> Any:
        """
        Get chat completion with retry.

        Args:
            messages: Chat messages
            **kwargs: Additional arguments

        Returns:
            Chat completion response
        """
        @retry(
            self._config,
            on_retry=self._on_retry,
        )
        def _call() -> Any:
            return self._client.chat_completion(messages=messages, **kwargs)

        return _call()

    def chat_completion_stream(
        self,
        messages: List[Any],
        **kwargs: Any,
    ) -> Iterator[Any]:
        """
        Get streaming chat completion with retry.

        Note: Retry only applies to initial connection, not mid-stream.

        Args:
            messages: Chat messages
            **kwargs: Additional arguments

        Yields:
            Response chunks
        """
        @retry(
            self._config,
            on_retry=self._on_retry,
        )
        def _call() -> Iterator[Any]:
            return self._client.chat_completion_stream(messages=messages, **kwargs)

        return _call()

    def get_model(self) -> str:
        """Get model name from underlying client."""
        return self._client.get_model()

    def validate_config(self) -> bool:
        """Validate configuration of underlying client."""
        return self._client.validate_config()

    def supports_streaming(self) -> bool:
        """Check if streaming is supported."""
        return self._client.supports_streaming()

    def supports_tools(self) -> bool:
        """Check if tools are supported."""
        return self._client.supports_tools()


def create_retryable_client(
    client: Any,
    max_retries: int = 3,
    base_delay: float = 1.0,
    **kwargs: Any,
) -> RetryableLLMClient:
    """
    Create a retryable LLM client.

    Args:
        client: Underlying LLM client
        max_retries: Maximum retry attempts
        base_delay: Base delay between retries
        **kwargs: Additional retry config options

    Returns:
        RetryableLLMClient instance
    """
    config = RetryConfig(
        max_retries=max_retries,
        base_delay=base_delay,
        **kwargs,
    )
    return RetryableLLMClient(client, config)
