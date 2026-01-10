"""
Token Statistics Module (CMD-011 to CMD-013)

Python 3.8.10 compatible
Provides token counting and cost estimation.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional


# Model pricing (per 1M tokens)
MODEL_PRICING: Dict[str, Dict[str, float]] = {
    # DeepSeek models
    "deepseek-r1-70b": {"input": 0.14, "output": 0.28},
    "deepseek-chat": {"input": 0.14, "output": 0.28},
    "deepseek-coder": {"input": 0.14, "output": 0.28},
    # OpenAI models
    "gpt-4": {"input": 30.0, "output": 60.0},
    "gpt-4-turbo": {"input": 10.0, "output": 30.0},
    "gpt-4o": {"input": 2.5, "output": 10.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.6},
    "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
    # Claude models
    "claude-3-opus": {"input": 15.0, "output": 75.0},
    "claude-3-sonnet": {"input": 3.0, "output": 15.0},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
    # Default for unknown models
    "default": {"input": 1.0, "output": 2.0},
}


@dataclass
class TokenUsage:
    """Token usage for a single request."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def __post_init__(self) -> None:
        if self.total_tokens == 0:
            self.total_tokens = self.prompt_tokens + self.completion_tokens


@dataclass
class TokenStats:
    """Accumulated token statistics."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    request_count: int = 0
    model: str = "default"
    custom_pricing: Optional[Dict[str, float]] = None

    def add(self, usage: TokenUsage) -> None:
        """Add token usage from a request."""
        self.prompt_tokens += usage.prompt_tokens
        self.completion_tokens += usage.completion_tokens
        self.total_tokens += usage.total_tokens
        self.request_count += 1

    def add_tokens(self, prompt: int, completion: int) -> None:
        """Add token counts directly."""
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.total_tokens += prompt + completion
        self.request_count += 1

    def get_pricing(self) -> Dict[str, float]:
        """Get pricing for the current model."""
        if self.custom_pricing:
            return self.custom_pricing

        # Try exact match
        if self.model in MODEL_PRICING:
            return MODEL_PRICING[self.model]

        # Try prefix match
        model_lower = self.model.lower()
        for key in MODEL_PRICING:
            if model_lower.startswith(key.lower()):
                return MODEL_PRICING[key]

        return MODEL_PRICING["default"]

    def calculate_cost(self) -> float:
        """Calculate estimated cost in USD."""
        pricing = self.get_pricing()
        input_cost = (self.prompt_tokens / 1_000_000) * pricing["input"]
        output_cost = (self.completion_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost

    def format_stats(self, show_cost: bool = True) -> str:
        """Format statistics for display."""
        parts = [
            f"{self.prompt_tokens} in",
            f"{self.completion_tokens} out",
        ]

        if show_cost:
            cost = self.calculate_cost()
            if cost < 0.01:
                parts.append(f"${cost:.6f}")
            elif cost < 1.0:
                parts.append(f"${cost:.4f}")
            else:
                parts.append(f"${cost:.2f}")

        return f"[tokens: {' / '.join(parts)}]"

    def format_summary(self) -> str:
        """Format full summary for display."""
        cost = self.calculate_cost()
        lines = [
            f"Token Usage Summary",
            f"  Model: {self.model}",
            f"  Requests: {self.request_count}",
            f"  Input tokens: {self.prompt_tokens:,}",
            f"  Output tokens: {self.completion_tokens:,}",
            f"  Total tokens: {self.total_tokens:,}",
            f"  Estimated cost: ${cost:.4f}",
        ]
        return "\n".join(lines)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "request_count": self.request_count,
            "model": self.model,
            "estimated_cost": self.calculate_cost(),
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "TokenStats":
        """Create from dictionary."""
        return cls(
            prompt_tokens=data.get("prompt_tokens", 0),
            completion_tokens=data.get("completion_tokens", 0),
            total_tokens=data.get("total_tokens", 0),
            request_count=data.get("request_count", 0),
            model=data.get("model", "default"),
        )


def estimate_tokens(text: str) -> int:
    """Estimate token count for text."""
    if not text:
        return 0
    char_count = len(text)
    code_indicators = ["{", "}", "(", ")", "[", "]", ";", "def ", "class ", "function "]
    is_code = any(ind in text for ind in code_indicators)
    if is_code:
        return max(1, char_count // 3)
    else:
        return max(1, char_count // 4)


def format_token_display(
    prompt_tokens: int,
    completion_tokens: int,
    model: str = "default",
    show_cost: bool = True,
) -> str:
    """Format token usage for inline display."""
    stats = TokenStats(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        model=model,
    )
    return stats.format_stats(show_cost=show_cost)


# Global stats tracker for session
_session_stats: Optional[TokenStats] = None


def get_session_stats() -> TokenStats:
    """Get or create session stats tracker."""
    global _session_stats
    if _session_stats is None:
        _session_stats = TokenStats()
    return _session_stats


def reset_session_stats() -> None:
    """Reset session stats."""
    global _session_stats
    _session_stats = TokenStats()


def record_usage(prompt_tokens: int, completion_tokens: int, model: str = "default") -> TokenStats:
    """Record token usage for the session."""
    stats = get_session_stats()
    stats.model = model
    stats.add_tokens(prompt_tokens, completion_tokens)
    return stats
