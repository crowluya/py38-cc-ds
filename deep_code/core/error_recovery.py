"""
Error Recovery Mechanism (T026)

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)

Provides:
- Error classification by type
- Recovery strategies per error category
- Circuit breaker pattern
- Graceful degradation
- Fallback handling
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type


class ErrorCategory(Enum):
    """Categories of errors for recovery handling."""
    NETWORK = "network"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    AUTH = "auth"
    VALIDATION = "validation"
    RESOURCE = "resource"
    UNKNOWN = "unknown"


class RecoveryAction(Enum):
    """Actions to take for error recovery."""
    RETRY = "retry"
    BACKOFF = "backoff"
    FAIL = "fail"
    FALLBACK = "fallback"


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class DegradationLevel(Enum):
    """Degradation levels for graceful degradation."""
    NORMAL = "normal"
    DEGRADED = "degraded"
    MINIMAL = "minimal"


# Error classification patterns
_NETWORK_ERRORS: Tuple[Type[Exception], ...] = (
    ConnectionError,
    ConnectionRefusedError,
    ConnectionResetError,
    BrokenPipeError,
)

_TIMEOUT_ERRORS: Tuple[Type[Exception], ...] = (
    TimeoutError,
)

_AUTH_ERRORS: Tuple[Type[Exception], ...] = (
    PermissionError,
)

_VALIDATION_ERRORS: Tuple[Type[Exception], ...] = (
    ValueError,
    TypeError,
    KeyError,
)

# Error message patterns for classification
_RATE_LIMIT_PATTERNS = [
    "rate limit",
    "too many requests",
    "throttl",
    "quota exceeded",
]

_AUTH_PATTERNS = [
    "unauthorized",
    "forbidden",
    "access denied",
    "authentication",
    "invalid api key",
    "invalid token",
]


def classify_error(error: Exception) -> ErrorCategory:
    """
    Classify an error into a category.

    Args:
        error: Exception to classify

    Returns:
        ErrorCategory
    """
    # Check by exception type
    if isinstance(error, _NETWORK_ERRORS):
        return ErrorCategory.NETWORK

    if isinstance(error, _TIMEOUT_ERRORS):
        return ErrorCategory.TIMEOUT

    if isinstance(error, _AUTH_ERRORS):
        return ErrorCategory.AUTH

    if isinstance(error, _VALIDATION_ERRORS):
        # Check message for rate limit patterns first
        error_msg = str(error).lower()
        for pattern in _RATE_LIMIT_PATTERNS:
            if pattern in error_msg:
                return ErrorCategory.RATE_LIMIT
        return ErrorCategory.VALIDATION

    # Check error message for patterns
    error_msg = str(error).lower()

    for pattern in _RATE_LIMIT_PATTERNS:
        if pattern in error_msg:
            return ErrorCategory.RATE_LIMIT

    for pattern in _AUTH_PATTERNS:
        if pattern in error_msg:
            return ErrorCategory.AUTH

    return ErrorCategory.UNKNOWN


@dataclass
class RecoveryStrategy:
    """Strategy for recovering from an error."""
    action: RecoveryAction
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: float = 0.1


# Default strategies per error category
_DEFAULT_STRATEGIES: Dict[ErrorCategory, RecoveryStrategy] = {
    ErrorCategory.NETWORK: RecoveryStrategy(
        action=RecoveryAction.RETRY,
        max_retries=3,
        base_delay=1.0,
    ),
    ErrorCategory.TIMEOUT: RecoveryStrategy(
        action=RecoveryAction.RETRY,
        max_retries=2,
        base_delay=2.0,
    ),
    ErrorCategory.RATE_LIMIT: RecoveryStrategy(
        action=RecoveryAction.BACKOFF,
        max_retries=5,
        base_delay=5.0,
        backoff_multiplier=2.0,
    ),
    ErrorCategory.AUTH: RecoveryStrategy(
        action=RecoveryAction.FAIL,
        max_retries=0,
    ),
    ErrorCategory.VALIDATION: RecoveryStrategy(
        action=RecoveryAction.FAIL,
        max_retries=0,
    ),
    ErrorCategory.RESOURCE: RecoveryStrategy(
        action=RecoveryAction.RETRY,
        max_retries=2,
        base_delay=1.0,
    ),
    ErrorCategory.UNKNOWN: RecoveryStrategy(
        action=RecoveryAction.RETRY,
        max_retries=1,
        base_delay=1.0,
    ),
}


def get_recovery_strategy(category: ErrorCategory) -> RecoveryStrategy:
    """
    Get recovery strategy for an error category.

    Args:
        category: Error category

    Returns:
        RecoveryStrategy
    """
    return _DEFAULT_STRATEGIES.get(
        category,
        _DEFAULT_STRATEGIES[ErrorCategory.UNKNOWN],
    )


@dataclass
class RecoveryConfig:
    """Configuration for error recovery."""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: float = 0.1
    custom_strategies: Dict[ErrorCategory, RecoveryStrategy] = field(
        default_factory=dict
    )


@dataclass
class RecoveryResult:
    """Result of error recovery handling."""
    should_retry: bool
    delay: float = 0.0
    retries_exhausted: bool = False
    circuit_open: bool = False
    category: Optional[ErrorCategory] = None
    message: str = ""


class RecoveryContext:
    """Context for tracking recovery state."""

    def __init__(self) -> None:
        """Initialize recovery context."""
        self._attempt_count = 0
        self._errors: List[Exception] = []
        self._start_time: Optional[float] = None

    def record_attempt(self) -> None:
        """Record a retry attempt."""
        if self._start_time is None:
            self._start_time = time.time()
        self._attempt_count += 1

    def record_error(self, error: Exception) -> None:
        """Record an error."""
        self._errors.append(error)

    def reset(self) -> None:
        """Reset the context."""
        self._attempt_count = 0
        self._errors = []
        self._start_time = None

    @property
    def attempt_count(self) -> int:
        """Get attempt count."""
        return self._attempt_count

    @property
    def errors(self) -> List[Exception]:
        """Get recorded errors."""
        return list(self._errors)

    @property
    def last_error(self) -> Optional[Exception]:
        """Get last error."""
        return self._errors[-1] if self._errors else None

    @property
    def elapsed_time(self) -> float:
        """Get elapsed time since first attempt."""
        if self._start_time is None:
            return 0.0
        return time.time() - self._start_time


class ErrorRecoveryManager:
    """
    Manager for error recovery.

    Handles error classification, strategy selection, and recovery coordination.
    """

    def __init__(
        self,
        config: Optional[RecoveryConfig] = None,
        on_error: Optional[Callable[[Exception, ErrorCategory], None]] = None,
        on_retry: Optional[Callable[[int, float], None]] = None,
        on_recovery: Optional[Callable[[], None]] = None,
    ) -> None:
        """
        Initialize recovery manager.

        Args:
            config: Recovery configuration
            on_error: Callback when error occurs
            on_retry: Callback when retry is scheduled
            on_recovery: Callback when recovery succeeds
        """
        self._config = config or RecoveryConfig()
        self._on_error = on_error
        self._on_retry = on_retry
        self._on_recovery = on_recovery
        self._context = RecoveryContext()

    @property
    def config(self) -> RecoveryConfig:
        """Get configuration."""
        return self._config

    def handle_error(
        self,
        error: Exception,
        circuit_breaker: Optional["CircuitBreaker"] = None,
    ) -> RecoveryResult:
        """
        Handle an error and determine recovery action.

        Args:
            error: Exception that occurred
            circuit_breaker: Optional circuit breaker

        Returns:
            RecoveryResult with recovery decision
        """
        # Classify error
        category = classify_error(error)

        # Record error
        self._context.record_error(error)
        self._context.record_attempt()

        # Notify callback
        if self._on_error:
            try:
                self._on_error(error, category)
            except Exception:
                pass

        # Check circuit breaker
        if circuit_breaker and not circuit_breaker.allow_request():
            return RecoveryResult(
                should_retry=False,
                circuit_open=True,
                category=category,
                message="Circuit breaker is open",
            )

        # Get strategy
        strategy = self._config.custom_strategies.get(
            category,
            get_recovery_strategy(category),
        )

        # Check if should retry
        if strategy.action == RecoveryAction.FAIL:
            return RecoveryResult(
                should_retry=False,
                category=category,
                message=f"Error category {category.value} is not recoverable",
            )

        # Check max retries
        max_retries = min(strategy.max_retries, self._config.max_retries)
        if self._context.attempt_count > max_retries:
            return RecoveryResult(
                should_retry=False,
                retries_exhausted=True,
                category=category,
                message=f"Max retries ({max_retries}) exceeded",
            )

        # Calculate delay
        attempt = self._context.attempt_count - 1
        delay = self._calculate_delay(attempt, strategy)

        # Notify retry callback
        if self._on_retry:
            try:
                self._on_retry(self._context.attempt_count, delay)
            except Exception:
                pass

        return RecoveryResult(
            should_retry=True,
            delay=delay,
            category=category,
            message=f"Retry {self._context.attempt_count}/{max_retries}",
        )

    def _calculate_delay(
        self,
        attempt: int,
        strategy: RecoveryStrategy,
    ) -> float:
        """Calculate delay for retry attempt."""
        import random

        delay = strategy.base_delay * (strategy.backoff_multiplier ** attempt)
        delay = min(delay, strategy.max_delay)

        # Add jitter
        if strategy.jitter > 0:
            jitter_range = delay * strategy.jitter
            delay = delay + random.uniform(-jitter_range, jitter_range)
            delay = max(0, delay)

        return delay

    def mark_recovered(self) -> None:
        """Mark that recovery was successful."""
        self._context.reset()

        if self._on_recovery:
            try:
                self._on_recovery()
            except Exception:
                pass

    def reset(self) -> None:
        """Reset the manager state."""
        self._context.reset()


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.

    Prevents repeated calls to a failing service.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout: float = 30.0,
        success_threshold: int = 1,
    ) -> None:
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Failures before opening circuit
            reset_timeout: Seconds before trying half-open
            success_threshold: Successes needed to close circuit
        """
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._success_threshold = success_threshold

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None

    @property
    def state(self) -> CircuitState:
        """Get current state."""
        return self._state

    def allow_request(self) -> bool:
        """
        Check if request should be allowed.

        Returns:
            True if request is allowed
        """
        if self._state == CircuitState.CLOSED:
            return True

        if self._state == CircuitState.OPEN:
            # Check if timeout has passed
            if self._last_failure_time is not None:
                elapsed = time.time() - self._last_failure_time
                if elapsed >= self._reset_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._success_count = 0
                    return True
            return False

        # Half-open: allow limited requests
        return True

    def record_success(self) -> None:
        """Record a successful request."""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self._success_threshold:
                self._state = CircuitState.CLOSED
                self._failure_count = 0

        elif self._state == CircuitState.CLOSED:
            # Reset failure count on success
            self._failure_count = 0

    def record_failure(self) -> None:
        """Record a failed request."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            # Immediately open on failure in half-open
            self._state = CircuitState.OPEN

        elif self._state == CircuitState.CLOSED:
            if self._failure_count >= self._failure_threshold:
                self._state = CircuitState.OPEN

    def reset(self) -> None:
        """Reset circuit breaker."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None


def with_fallback(
    main_func: Callable[[], Any],
    fallback_func: Callable[..., Any],
    pass_error: bool = False,
) -> Any:
    """
    Execute function with fallback on error.

    Args:
        main_func: Main function to execute
        fallback_func: Fallback function if main fails
        pass_error: Whether to pass error to fallback

    Returns:
        Result from main or fallback function
    """
    try:
        return main_func()
    except Exception as e:
        if pass_error:
            return fallback_func(error=e)
        return fallback_func()


class DegradationManager:
    """
    Manager for graceful degradation.

    Tracks system health and adjusts available features.
    """

    # Features available at each degradation level
    _LEVEL_FEATURES: Dict[DegradationLevel, Set[str]] = {
        DegradationLevel.NORMAL: {
            "streaming",
            "tools",
            "context",
            "history",
            "formatting",
        },
        DegradationLevel.DEGRADED: {
            "tools",
            "context",
            "history",
        },
        DegradationLevel.MINIMAL: {
            "context",
        },
    }

    def __init__(
        self,
        error_threshold: int = 5,
        recovery_threshold: int = 3,
    ) -> None:
        """
        Initialize degradation manager.

        Args:
            error_threshold: Errors before degrading
            recovery_threshold: Successes before recovering
        """
        self._error_threshold = error_threshold
        self._recovery_threshold = recovery_threshold
        self._level = DegradationLevel.NORMAL
        self._error_count = 0
        self._success_count = 0

    @property
    def level(self) -> DegradationLevel:
        """Get current degradation level."""
        return self._level

    def record_error(self) -> None:
        """Record an error."""
        self._error_count += 1
        self._success_count = 0

        if self._error_count >= self._error_threshold:
            self._degrade()

    def record_success(self) -> None:
        """Record a success."""
        self._success_count += 1

        if self._success_count >= self._recovery_threshold:
            self._recover()

    def _degrade(self) -> None:
        """Degrade to next level."""
        if self._level == DegradationLevel.NORMAL:
            self._level = DegradationLevel.DEGRADED
        elif self._level == DegradationLevel.DEGRADED:
            self._level = DegradationLevel.MINIMAL
        self._error_count = 0

    def _recover(self) -> None:
        """Recover to previous level."""
        if self._level == DegradationLevel.MINIMAL:
            self._level = DegradationLevel.DEGRADED
        elif self._level == DegradationLevel.DEGRADED:
            self._level = DegradationLevel.NORMAL
        self._success_count = 0

    def get_available_features(self) -> Set[str]:
        """
        Get features available at current level.

        Returns:
            Set of available feature names
        """
        return self._LEVEL_FEATURES.get(self._level, set())

    def is_feature_available(self, feature: str) -> bool:
        """
        Check if a feature is available.

        Args:
            feature: Feature name

        Returns:
            True if feature is available
        """
        return feature in self.get_available_features()

    def reset(self) -> None:
        """Reset to normal level."""
        self._level = DegradationLevel.NORMAL
        self._error_count = 0
        self._success_count = 0
