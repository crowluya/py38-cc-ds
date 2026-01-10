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
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Get chat completion response.

        Args:
            messages: List of message dicts
            model: Model name override
            temperature: Temperature override
            max_tokens: Max tokens override
            tools: List of tool definitions in OpenAI format
            tool_choice: Tool choice mode ("auto", "none", or specific tool name)
            **kwargs: Additional parameters

        Returns:
            Response dict with content and optionally tool_calls
        """
        llm = self._settings.llm

        # Build request parameters
        request_params = {
            "model": model or llm.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else llm.temperature,
            "max_tokens": max_tokens if max_tokens is not None else llm.max_tokens,
        }

        # Add tools if provided (OpenAI 0.28.x uses 'functions' parameter)
        if tools:
            # Convert tools format to functions format for openai 0.28.x
            functions = []
            for tool in tools:
                if tool.get("type") == "function":
                    functions.append(tool["function"])
                else:
                    functions.append(tool)
            request_params["functions"] = functions

            if tool_choice:
                if tool_choice == "auto":
                    request_params["function_call"] = "auto"
                elif tool_choice == "none":
                    request_params["function_call"] = "none"
                else:
                    # Specific function name
                    request_params["function_call"] = {"name": tool_choice}

        request_params.update(kwargs)

        try:
            response = openai.ChatCompletion.create(**request_params)

            result = {
                "content": response.choices[0].message.get("content", "") or "",
                "model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
                "finish_reason": response.choices[0].get("finish_reason", "stop"),
            }

            # Extract function call if present (openai 0.28.x format)
            function_call = response.choices[0].message.get("function_call")
            if function_call:
                import json
                result["tool_calls"] = [{
                    "id": f"call_{hash(str(function_call))}",
                    "type": "function",
                    "function": {
                        "name": function_call.get("name", ""),
                        "arguments": function_call.get("arguments", "{}"),
                    },
                }]

            return result

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
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        **kwargs: Any,
    ) -> Iterator[Dict[str, Any]]:
        """
        Get streaming chat completion response.

        Args:
            messages: List of message dicts
            model: Model name override
            temperature: Temperature override
            max_tokens: Max tokens override
            tools: List of tool definitions in OpenAI format
            tool_choice: Tool choice mode
            **kwargs: Additional parameters

        Yields:
            Response chunks with delta content
        """
        llm = self._settings.llm

        # Build request parameters
        request_params = {
            "model": model or llm.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else llm.temperature,
            "max_tokens": max_tokens if max_tokens is not None else llm.max_tokens,
            "stream": True,
        }

        # Add tools if provided (OpenAI 0.28.x uses 'functions' parameter)
        if tools:
            functions = []
            for tool in tools:
                if tool.get("type") == "function":
                    functions.append(tool["function"])
                else:
                    functions.append(tool)
            request_params["functions"] = functions

            if tool_choice:
                if tool_choice == "auto":
                    request_params["function_call"] = "auto"
                elif tool_choice == "none":
                    request_params["function_call"] = "none"
                else:
                    request_params["function_call"] = {"name": tool_choice}

        request_params.update(kwargs)

        try:
            stream = openai.ChatCompletion.create(**request_params)

            for chunk in stream:
                delta = chunk.choices[0].delta
                content = delta.get("content", "")
                if content:
                    yield {"delta": content}

                # Handle function call in streaming (accumulated)
                function_call = delta.get("function_call")
                if function_call:
                    yield {"function_call_delta": function_call}

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
