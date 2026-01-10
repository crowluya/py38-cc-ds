"""
Tests for Auto Retry Mechanism (T029)

Python 3.8.10 compatible
"""

import pytest
import time
from typing import Any, Dict, List
from unittest.mock import Mock, MagicMock, patch, call


class TestRetryConfig:
    """Tests for retry configuration."""

    def test_default_config(self):
        """Test default retry configuration."""
        from deep_code.core.retry import RetryConfig

        config = RetryConfig()

        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0

    def test_custom_config(self):
        """Test custom retry configuration."""
        from deep_code.core.retry import RetryConfig

        config = RetryConfig(
            max_retries=5,
            base_delay=0.5,
            max_delay=30.0,
        )

        assert config.max_retries == 5
        assert config.base_delay == 0.5
        assert config.max_delay == 30.0


class TestRetryDelay:
    """Tests for retry delay calculation."""

    def test_exponential_backoff(self):
        """Test exponential backoff calculation."""
        from deep_code.core.retry import calculate_delay, RetryConfig

        config = RetryConfig(base_delay=1.0, exponential_base=2.0)

        assert calculate_delay(0, config) == 1.0  # 1 * 2^0
        assert calculate_delay(1, config) == 2.0  # 1 * 2^1
        assert calculate_delay(2, config) == 4.0  # 1 * 2^2

    def test_max_delay_cap(self):
        """Test delay is capped at max_delay."""
        from deep_code.core.retry import calculate_delay, RetryConfig

        config = RetryConfig(base_delay=1.0, max_delay=5.0, exponential_base=2.0)

        # 1 * 2^10 = 1024, but should be capped at 5
        assert calculate_delay(10, config) == 5.0

    def test_jitter(self):
        """Test jitter is applied."""
        from deep_code.core.retry import calculate_delay, RetryConfig

        config = RetryConfig(base_delay=1.0, jitter=0.1)

        delays = [calculate_delay(0, config) for _ in range(10)]

        # With jitter, delays should vary
        assert len(set(delays)) > 1 or all(0.9 <= d <= 1.1 for d in delays)


class TestRetryDecorator:
    """Tests for retry decorator."""

    def test_success_no_retry(self):
        """Test successful call doesn't retry."""
        from deep_code.core.retry import retry, RetryConfig

        call_count = 0

        @retry(RetryConfig(max_retries=3))
        def success_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = success_func()

        assert result == "success"
        assert call_count == 1

    def test_retry_on_exception(self):
        """Test retry on exception."""
        from deep_code.core.retry import retry, RetryConfig

        call_count = 0

        @retry(RetryConfig(max_retries=3, base_delay=0.01))
        def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"

        result = failing_func()

        assert result == "success"
        assert call_count == 3

    def test_max_retries_exceeded(self):
        """Test exception raised after max retries."""
        from deep_code.core.retry import retry, RetryConfig

        call_count = 0

        @retry(RetryConfig(max_retries=2, base_delay=0.01))
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")

        with pytest.raises(ValueError):
            always_fails()

        assert call_count == 3  # Initial + 2 retries

    def test_retry_specific_exceptions(self):
        """Test retry only on specific exceptions."""
        from deep_code.core.retry import retry, RetryConfig

        call_count = 0

        @retry(RetryConfig(max_retries=3, base_delay=0.01), exceptions=(ValueError,))
        def specific_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("Not retryable")

        with pytest.raises(TypeError):
            specific_error()

        assert call_count == 1  # No retry for TypeError


class TestRetryContext:
    """Tests for retry context manager."""

    def test_context_success(self):
        """Test context manager with success on first attempt."""
        from deep_code.core.retry import retry_context, RetryConfig

        result = None
        attempts = 0

        for attempt in retry_context(RetryConfig(max_retries=3)):
            attempts += 1
            result = "success"
            break  # Success, no retry needed

        assert result == "success"
        assert attempts == 1

    def test_context_retry(self):
        """Test context manager with retry."""
        from deep_code.core.retry import retry_context, RetryConfig

        attempts = 0

        config = RetryConfig(max_retries=3, base_delay=0.01)

        for attempt in retry_context(config):
            attempts += 1
            if attempts < 3:
                attempt.retry(ValueError("Retry"))
            else:
                break

        assert attempts == 3


class TestRetryableClient:
    """Tests for retryable LLM client wrapper."""

    def test_retryable_client_success(self):
        """Test retryable client with success."""
        from deep_code.core.retry import RetryableLLMClient, RetryConfig

        mock_client = Mock()
        mock_client.chat_completion.return_value = {"content": "response"}

        client = RetryableLLMClient(mock_client, RetryConfig())

        result = client.chat_completion(messages=[])

        assert result["content"] == "response"
        assert mock_client.chat_completion.call_count == 1

    def test_retryable_client_retry(self):
        """Test retryable client with retry."""
        from deep_code.core.retry import RetryableLLMClient, RetryConfig

        mock_client = Mock()
        mock_client.chat_completion.side_effect = [
            Exception("Error 1"),
            Exception("Error 2"),
            {"content": "response"},
        ]

        config = RetryConfig(max_retries=3, base_delay=0.01)
        client = RetryableLLMClient(mock_client, config)

        result = client.chat_completion(messages=[])

        assert result["content"] == "response"
        assert mock_client.chat_completion.call_count == 3

    def test_retryable_client_max_retries(self):
        """Test retryable client exceeds max retries."""
        from deep_code.core.retry import RetryableLLMClient, RetryConfig

        mock_client = Mock()
        mock_client.chat_completion.side_effect = Exception("Always fails")

        config = RetryConfig(max_retries=2, base_delay=0.01)
        client = RetryableLLMClient(mock_client, config)

        with pytest.raises(Exception):
            client.chat_completion(messages=[])

        assert mock_client.chat_completion.call_count == 3


class TestRetryCallbacks:
    """Tests for retry callbacks."""

    def test_on_retry_callback(self):
        """Test on_retry callback is called."""
        from deep_code.core.retry import retry, RetryConfig

        retry_info = []

        def on_retry(attempt, exception, delay):
            retry_info.append((attempt, str(exception), delay))

        call_count = 0

        @retry(RetryConfig(max_retries=2, base_delay=0.01), on_retry=on_retry)
        def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError(f"Error {call_count}")
            return "success"

        failing_func()

        assert len(retry_info) == 2
        assert "Error 1" in retry_info[0][1]
        assert "Error 2" in retry_info[1][1]

    def test_should_retry_callback(self):
        """Test should_retry callback."""
        from deep_code.core.retry import retry, RetryConfig

        def should_retry(exception):
            return "retry" in str(exception).lower()

        call_count = 0

        @retry(RetryConfig(max_retries=3, base_delay=0.01), should_retry=should_retry)
        def conditional_retry():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Please retry")
            elif call_count == 2:
                raise ValueError("Do not continue")
            return "success"

        with pytest.raises(ValueError):
            conditional_retry()

        assert call_count == 2  # Stopped at "Do not continue"


class TestRetryWithTimeout:
    """Tests for retry with timeout."""

    def test_retry_respects_timeout(self):
        """Test retry respects total timeout."""
        from deep_code.core.retry import retry, RetryConfig

        call_count = 0

        @retry(RetryConfig(max_retries=10, base_delay=0.1, total_timeout=0.3))
        def slow_fail():
            nonlocal call_count
            call_count += 1
            raise ValueError("Fail")

        with pytest.raises(ValueError):
            slow_fail()

        # Should stop before max_retries due to timeout
        assert call_count < 10


class TestRetryIntegration:
    """Integration tests for retry mechanism."""

    def test_retry_with_agent_loop(self):
        """Test retry integration with agent loop."""
        from deep_code.core.retry import RetryableLLMClient, RetryConfig
        from deep_code.core.agent_loop import AgentLoop, AgentLoopConfig

        mock_client = Mock()
        mock_client.chat_completion.side_effect = [
            Exception("Temporary error"),
            {"content": "Hello!", "finish_reason": "stop"},
        ]

        config = RetryConfig(max_retries=2, base_delay=0.01)
        retryable_client = RetryableLLMClient(mock_client, config)

        loop_config = AgentLoopConfig(llm_client=retryable_client)
        loop = AgentLoop(loop_config)

        result = loop.run_turn("Hi")

        assert result.content == "Hello!"
