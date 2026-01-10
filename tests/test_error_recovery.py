"""
Tests for Error Recovery Mechanism (T026)

Python 3.8.10 compatible
"""

import pytest
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, MagicMock, patch


class TestErrorClassification:
    """Tests for error classification."""

    def test_classify_network_error(self):
        """Test classifying network errors."""
        from deep_code.core.error_recovery import classify_error, ErrorCategory

        error = ConnectionError("Connection refused")
        category = classify_error(error)

        assert category == ErrorCategory.NETWORK

    def test_classify_timeout_error(self):
        """Test classifying timeout errors."""
        from deep_code.core.error_recovery import classify_error, ErrorCategory

        error = TimeoutError("Request timed out")
        category = classify_error(error)

        assert category == ErrorCategory.TIMEOUT

    def test_classify_rate_limit_error(self):
        """Test classifying rate limit errors."""
        from deep_code.core.error_recovery import classify_error, ErrorCategory

        error = Exception("Rate limit exceeded")
        category = classify_error(error)

        assert category == ErrorCategory.RATE_LIMIT

    def test_classify_auth_error(self):
        """Test classifying authentication errors."""
        from deep_code.core.error_recovery import classify_error, ErrorCategory

        error = PermissionError("Access denied")
        category = classify_error(error)

        assert category == ErrorCategory.AUTH

    def test_classify_validation_error(self):
        """Test classifying validation errors."""
        from deep_code.core.error_recovery import classify_error, ErrorCategory

        error = ValueError("Invalid input")
        category = classify_error(error)

        assert category == ErrorCategory.VALIDATION

    def test_classify_unknown_error(self):
        """Test classifying unknown errors."""
        from deep_code.core.error_recovery import classify_error, ErrorCategory

        error = RuntimeError("Something went wrong")
        category = classify_error(error)

        assert category == ErrorCategory.UNKNOWN


class TestRecoveryStrategy:
    """Tests for recovery strategies."""

    def test_get_strategy_for_network(self):
        """Test getting strategy for network errors."""
        from deep_code.core.error_recovery import (
            get_recovery_strategy,
            ErrorCategory,
            RecoveryAction,
        )

        strategy = get_recovery_strategy(ErrorCategory.NETWORK)

        assert strategy.action == RecoveryAction.RETRY
        assert strategy.max_retries > 0

    def test_get_strategy_for_timeout(self):
        """Test getting strategy for timeout errors."""
        from deep_code.core.error_recovery import (
            get_recovery_strategy,
            ErrorCategory,
            RecoveryAction,
        )

        strategy = get_recovery_strategy(ErrorCategory.TIMEOUT)

        assert strategy.action == RecoveryAction.RETRY

    def test_get_strategy_for_rate_limit(self):
        """Test getting strategy for rate limit errors."""
        from deep_code.core.error_recovery import (
            get_recovery_strategy,
            ErrorCategory,
            RecoveryAction,
        )

        strategy = get_recovery_strategy(ErrorCategory.RATE_LIMIT)

        assert strategy.action == RecoveryAction.BACKOFF
        assert strategy.backoff_multiplier > 1

    def test_get_strategy_for_auth(self):
        """Test getting strategy for auth errors."""
        from deep_code.core.error_recovery import (
            get_recovery_strategy,
            ErrorCategory,
            RecoveryAction,
        )

        strategy = get_recovery_strategy(ErrorCategory.AUTH)

        assert strategy.action == RecoveryAction.FAIL

    def test_get_strategy_for_validation(self):
        """Test getting strategy for validation errors."""
        from deep_code.core.error_recovery import (
            get_recovery_strategy,
            ErrorCategory,
            RecoveryAction,
        )

        strategy = get_recovery_strategy(ErrorCategory.VALIDATION)

        assert strategy.action == RecoveryAction.FAIL


class TestErrorRecoveryManager:
    """Tests for ErrorRecoveryManager."""

    def test_manager_creation(self):
        """Test creating recovery manager."""
        from deep_code.core.error_recovery import ErrorRecoveryManager

        manager = ErrorRecoveryManager()

        assert manager is not None

    def test_manager_with_config(self):
        """Test manager with custom config."""
        from deep_code.core.error_recovery import (
            ErrorRecoveryManager,
            RecoveryConfig,
        )

        config = RecoveryConfig(max_retries=5, base_delay=2.0)
        manager = ErrorRecoveryManager(config=config)

        assert manager.config.max_retries == 5
        assert manager.config.base_delay == 2.0

    def test_handle_recoverable_error(self):
        """Test handling recoverable error."""
        from deep_code.core.error_recovery import ErrorRecoveryManager

        manager = ErrorRecoveryManager()
        error = ConnectionError("Connection refused")

        result = manager.handle_error(error)

        assert result.should_retry is True
        assert result.delay > 0

    def test_handle_non_recoverable_error(self):
        """Test handling non-recoverable error."""
        from deep_code.core.error_recovery import ErrorRecoveryManager

        manager = ErrorRecoveryManager()
        error = PermissionError("Access denied")

        result = manager.handle_error(error)

        assert result.should_retry is False

    def test_max_retries_exceeded(self):
        """Test max retries exceeded."""
        from deep_code.core.error_recovery import (
            ErrorRecoveryManager,
            RecoveryConfig,
        )

        config = RecoveryConfig(max_retries=2)
        manager = ErrorRecoveryManager(config=config)
        error = ConnectionError("Connection refused")

        # Simulate multiple failures
        for _ in range(3):
            result = manager.handle_error(error)

        assert result.should_retry is False
        assert result.retries_exhausted is True


class TestRecoveryContext:
    """Tests for recovery context."""

    def test_context_tracks_attempts(self):
        """Test context tracks retry attempts."""
        from deep_code.core.error_recovery import RecoveryContext

        context = RecoveryContext()

        context.record_attempt()
        context.record_attempt()

        assert context.attempt_count == 2

    def test_context_tracks_errors(self):
        """Test context tracks errors."""
        from deep_code.core.error_recovery import RecoveryContext

        context = RecoveryContext()
        error = ValueError("Test error")

        context.record_error(error)

        assert len(context.errors) == 1
        assert context.last_error == error

    def test_context_reset(self):
        """Test context reset."""
        from deep_code.core.error_recovery import RecoveryContext

        context = RecoveryContext()
        context.record_attempt()
        context.record_error(ValueError("Test"))

        context.reset()

        assert context.attempt_count == 0
        assert len(context.errors) == 0


class TestRecoveryCallbacks:
    """Tests for recovery callbacks."""

    def test_on_error_callback(self):
        """Test on_error callback is called."""
        from deep_code.core.error_recovery import ErrorRecoveryManager

        errors_received = []

        def on_error(error, category):
            errors_received.append((error, category))

        manager = ErrorRecoveryManager(on_error=on_error)
        error = ConnectionError("Test")

        manager.handle_error(error)

        assert len(errors_received) == 1

    def test_on_retry_callback(self):
        """Test on_retry callback is called."""
        from deep_code.core.error_recovery import ErrorRecoveryManager

        retries = []

        def on_retry(attempt, delay):
            retries.append((attempt, delay))

        manager = ErrorRecoveryManager(on_retry=on_retry)
        error = ConnectionError("Test")

        manager.handle_error(error)

        assert len(retries) == 1

    def test_on_recovery_callback(self):
        """Test on_recovery callback is called."""
        from deep_code.core.error_recovery import ErrorRecoveryManager

        recoveries = []

        def on_recovery():
            recoveries.append(True)

        manager = ErrorRecoveryManager(on_recovery=on_recovery)

        manager.mark_recovered()

        assert len(recoveries) == 1


class TestCircuitBreaker:
    """Tests for circuit breaker pattern."""

    def test_circuit_starts_closed(self):
        """Test circuit starts in closed state."""
        from deep_code.core.error_recovery import CircuitBreaker, CircuitState

        breaker = CircuitBreaker()

        assert breaker.state == CircuitState.CLOSED

    def test_circuit_opens_on_failures(self):
        """Test circuit opens after threshold failures."""
        from deep_code.core.error_recovery import CircuitBreaker, CircuitState

        breaker = CircuitBreaker(failure_threshold=3)

        for _ in range(3):
            breaker.record_failure()

        assert breaker.state == CircuitState.OPEN

    def test_circuit_allows_when_closed(self):
        """Test circuit allows requests when closed."""
        from deep_code.core.error_recovery import CircuitBreaker

        breaker = CircuitBreaker()

        assert breaker.allow_request() is True

    def test_circuit_blocks_when_open(self):
        """Test circuit blocks requests when open."""
        from deep_code.core.error_recovery import CircuitBreaker

        breaker = CircuitBreaker(failure_threshold=1)
        breaker.record_failure()

        assert breaker.allow_request() is False

    def test_circuit_half_open_after_timeout(self):
        """Test circuit becomes half-open after timeout."""
        from deep_code.core.error_recovery import CircuitBreaker, CircuitState

        breaker = CircuitBreaker(failure_threshold=1, reset_timeout=0.01)
        breaker.record_failure()

        import time
        time.sleep(0.02)

        # Should transition to half-open on next check
        breaker.allow_request()

        assert breaker.state == CircuitState.HALF_OPEN

    def test_circuit_closes_on_success(self):
        """Test circuit closes on success in half-open state."""
        from deep_code.core.error_recovery import CircuitBreaker, CircuitState

        breaker = CircuitBreaker(failure_threshold=1, reset_timeout=0.01)
        breaker.record_failure()

        import time
        time.sleep(0.02)

        breaker.allow_request()  # Transition to half-open
        breaker.record_success()

        assert breaker.state == CircuitState.CLOSED


class TestFallbackHandler:
    """Tests for fallback handling."""

    def test_fallback_on_error(self):
        """Test fallback is called on error."""
        from deep_code.core.error_recovery import with_fallback

        def main_func():
            raise ValueError("Main failed")

        def fallback_func():
            return "fallback result"

        result = with_fallback(main_func, fallback_func)

        assert result == "fallback result"

    def test_no_fallback_on_success(self):
        """Test fallback is not called on success."""
        from deep_code.core.error_recovery import with_fallback

        def main_func():
            return "main result"

        def fallback_func():
            return "fallback result"

        result = with_fallback(main_func, fallback_func)

        assert result == "main result"

    def test_fallback_with_error_info(self):
        """Test fallback receives error info."""
        from deep_code.core.error_recovery import with_fallback

        received_error = []

        def main_func():
            raise ValueError("Test error")

        def fallback_func(error=None):
            received_error.append(error)
            return "fallback"

        with_fallback(main_func, fallback_func, pass_error=True)

        assert len(received_error) == 1
        assert isinstance(received_error[0], ValueError)


class TestGracefulDegradation:
    """Tests for graceful degradation."""

    def test_degradation_levels(self):
        """Test degradation levels."""
        from deep_code.core.error_recovery import (
            DegradationManager,
            DegradationLevel,
        )

        manager = DegradationManager()

        assert manager.level == DegradationLevel.NORMAL

    def test_degrade_on_errors(self):
        """Test degradation on repeated errors."""
        from deep_code.core.error_recovery import (
            DegradationManager,
            DegradationLevel,
        )

        manager = DegradationManager(error_threshold=2)

        manager.record_error()
        manager.record_error()

        assert manager.level == DegradationLevel.DEGRADED

    def test_recover_on_success(self):
        """Test recovery on success."""
        from deep_code.core.error_recovery import (
            DegradationManager,
            DegradationLevel,
        )

        manager = DegradationManager(error_threshold=1, recovery_threshold=2)
        manager.record_error()  # Degrade

        manager.record_success()
        manager.record_success()

        assert manager.level == DegradationLevel.NORMAL

    def test_get_available_features(self):
        """Test getting available features at degradation level."""
        from deep_code.core.error_recovery import (
            DegradationManager,
            DegradationLevel,
        )

        manager = DegradationManager()

        features = manager.get_available_features()

        assert "streaming" in features
        assert "tools" in features


class TestErrorRecoveryIntegration:
    """Integration tests for error recovery."""

    def test_recovery_with_agent_loop(self):
        """Test error recovery with agent loop."""
        from deep_code.core.error_recovery import (
            ErrorRecoveryManager,
            RecoveryConfig,
        )

        config = RecoveryConfig(max_retries=3, base_delay=0.01)
        manager = ErrorRecoveryManager(config=config)

        # Simulate agent loop with errors
        attempts = 0
        success = False

        while attempts < 5:
            try:
                if attempts < 2:
                    raise ConnectionError("Simulated failure")
                success = True
                manager.mark_recovered()
                break
            except ConnectionError as e:
                result = manager.handle_error(e)
                if not result.should_retry:
                    break
                attempts += 1

        assert success is True
        assert attempts == 2

    def test_circuit_breaker_with_recovery(self):
        """Test circuit breaker with recovery manager."""
        from deep_code.core.error_recovery import (
            CircuitBreaker,
            ErrorRecoveryManager,
        )

        breaker = CircuitBreaker(failure_threshold=2)
        manager = ErrorRecoveryManager()

        # Record failures
        for _ in range(2):
            breaker.record_failure()

        # Circuit should be open
        assert breaker.allow_request() is False

        # Error should not be retried when circuit is open
        error = ConnectionError("Test")
        result = manager.handle_error(error, circuit_breaker=breaker)

        assert result.circuit_open is True
