"""
OpenAI Client Implementation

Python 3.8.10 compatible
Uses openai==0.28.1 (last version supporting Python 3.8)
Supports DeepSeek R1 70B internal network endpoints
"""

from typing import Any, Dict, Iterator, List, Optional

import openai
from claude_code.config.settings import Settings
from claude_code.llm.client import LLMClient, LLMConfigError


class OpenAIClient(LLMClient):
    """
    OpenAI-compatible LLM client.

    Supports:
    - OpenAI API
    - DeepSeek R1 70B (OpenAI-compatible)
    - Custom base URLs for internal networks
    - Streaming responses
    """

    def __init__(self, settings: Settings):
        """
        Initialize OpenAI client.

        Args:
            settings: Settings instance with LLM configuration
        """
        self._settings = settings
        self._configure_client()

    def _configure_client(self) -> None:
        """Configure the OpenAI client from settings."""
        llm = self._settings.llm

        # Set API key
        if llm.api_key:
            openai.api_key = llm.api_key

        # Set base URL (for DeepSeek internal endpoint)
        if llm.api_base:
            openai.api_base = llm.api_base

        # Set timeout
        openai.timeout = llm.timeout

    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Get chat completion response.

        Args:
            messages: List of message dicts
            model: Model name override
            temperature: Temperature override
            max_tokens: Max tokens override
            **kwargs: Additional parameters

        Returns:
            Response dict with content
        """
        llm = self._settings.llm

        try:
            response = openai.ChatCompletion.create(
                model=model or llm.model,
                messages=messages,
                temperature=temperature if temperature is not None else llm.temperature,
                max_tokens=max_tokens if max_tokens is not None else llm.max_tokens,
                **kwargs,
            )

            return {
                "content": response.choices[0].message["content"],
                "model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
            }
        except openai.error.APIError as e:
            raise LLMAPIError(f"OpenAI API error: {e}")
        except openai.error.Timeout as e:
            raise LLMTimeoutError(f"OpenAI timeout: {e}")

    def chat_completion_stream(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> Iterator[Dict[str, Any]]:
        """
        Get streaming chat completion response.

        Args:
            messages: List of message dicts
            model: Model name override
            temperature: Temperature override
            max_tokens: Max tokens override
            **kwargs: Additional parameters

        Yields:
            Response chunks with delta content
        """
        llm = self._settings.llm

        try:
            stream = openai.ChatCompletion.create(
                model=model or llm.model,
                messages=messages,
                temperature=temperature if temperature is not None else llm.temperature,
                max_tokens=max_tokens if max_tokens is not None else llm.max_tokens,
                stream=True,
                **kwargs,
            )

            for chunk in stream:
                delta = chunk.choices[0].delta
                content = delta.get("content", "")
                if content:
                    yield {"delta": content}

        except openai.error.APIError as e:
            raise LLMAPIError(f"OpenAI API error: {e}")
        except openai.error.Timeout as e:
            raise LLMTimeoutError(f"OpenAI timeout: {e}")

    def get_model(self) -> str:
        """Get the default model name."""
        return self._settings.llm.model

    def supports_streaming(self) -> bool:
        """OpenAI client supports streaming."""
        return True

    def supports_tools(self) -> bool:
        """OpenAI client supports function calling."""
        return True

    def validate_config(self) -> bool:
        """Validate client configuration."""
        llm = self._settings.llm

        # Check API key
        if not llm.api_key:
            return False

        return True
