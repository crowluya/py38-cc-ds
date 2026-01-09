"""
LLM module for Claude Code Python MVP.

Provides abstract client interface and implementations.
"""

from typing import Any, Dict, Iterator, List, Optional

from claude_code.config.settings import Settings
from claude_code.llm.client import (
    LLMClient,
    LLMConfigError,
    LLMAPIError,
    LLMTimeoutError,
)
from claude_code.llm.factory import LLMClientFactory, create_llm_client

# Try to import and register OpenAI client
try:
    from claude_code.llm.openai_client import OpenAIClient
    LLMClientFactory.register_client("openai", OpenAIClient)
except ImportError:
    pass

# Import and register Requests client (always available)
from claude_code.llm.requests_client import RequestsClient
LLMClientFactory.register_client("requests", RequestsClient)

__all__ = [
    # Base
    "LLMClient",
    "LLMConfigError",
    "LLMAPIError",
    "LLMTimeoutError",
    # Factory
    "LLMClientFactory",
    "create_llm_client",
    # Clients
    "OpenAIClient",
    "RequestsClient",
]
