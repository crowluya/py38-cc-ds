"""
LLM Client Abstract Base Class

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Iterator


class LLMClient(ABC):
    """
    Abstract base class for LLM clients.

    Defines the interface for LLM chat completions with support for:
    - OpenAI-compatible APIs
    - Streaming responses
    - Tool/Function calling
    - DeepSeek R1 70B internal network support
    """

    @abstractmethod
    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Get chat completion response.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model name (uses default if None)
            temperature: Sampling temperature (0.0 - 2.0)
            max_tokens: Maximum tokens to generate
            tools: List of tool definitions in OpenAI format
            tool_choice: Tool choice mode ("auto", "none", or specific tool name)
            **kwargs: Additional model-specific parameters

        Returns:
            Response dict with at least 'content' field, and optionally 'tool_calls'
        """
        pass

    @abstractmethod
    def chat_completion_stream(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        **kwargs: Any,
    ) -> Iterator[Dict[str, Any]]:
        """
        Get streaming chat completion response.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model name (uses default if None)
            temperature: Sampling temperature (0.0 - 2.0)
            max_tokens: Maximum tokens to generate
            tools: List of tool definitions in OpenAI format
            tool_choice: Tool choice mode ("auto", "none", or specific tool name)
            **kwargs: Additional model-specific parameters

        Yields:
            Response chunks with 'delta' content or 'tool_calls'
        """
        pass

    @abstractmethod
    def get_model(self) -> str:
        """
        Get the default model name.

        Returns:
            Model identifier string
        """
        pass

    def supports_streaming(self) -> bool:
        """
        Check if client supports streaming responses.

        Returns:
            True if streaming is supported
        """
        return True

    def supports_tools(self) -> bool:
        """
        Check if client supports tool/function calling.

        Returns:
            True if tools are supported
        """
        return True

    @abstractmethod
    def validate_config(self) -> bool:
        """
        Validate client configuration.

        Returns:
            True if configuration is valid
        """
        pass

    def format_messages(
        self,
        messages: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Format messages for the LLM API.

        Args:
            messages: Raw message list

        Returns:
            Formatted message list
        """
        # Default: just pass through
        return messages

    def format_tool_result_message(
        self,
        tool_call_id: str,
        tool_name: str,
        content: str,
    ) -> Dict[str, Any]:
        """
        Format a tool result message for the LLM API.

        Args:
            tool_call_id: ID of the tool call
            tool_name: Name of the tool
            content: Tool execution result

        Returns:
            Formatted message dict
        """
        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": tool_name,
            "content": content,
        }


class LLMClientError(Exception):
    """Base exception for LLM client errors."""

    pass


class LLMConfigError(LLMClientError):
    """Exception raised for configuration errors."""

    pass


class LLMAPIError(LLMClientError):
    """Exception raised for API call errors."""

    pass


class LLMTimeoutError(LLMClientError):
    """Exception raised for timeout errors."""

    pass
