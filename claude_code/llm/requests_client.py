"""
Requests Client Implementation (OpenAI-compatible)

Python 3.8.10 compatible
Uses requests==2.28.2 for HTTP calls
Fallback client when openai library is unavailable
"""

import json
import time
from typing import Any, Dict, Iterator, List, Optional

import requests
from claude_code.config.settings import Settings
from claude_code.llm.client import LLMClient, LLMConfigError, LLMAPIError, LLMTimeoutError


class RequestsClient(LLMClient):
    """
    OpenAI-compatible LLM client using requests library.

    Supports:
    - DeepSeek R1 70B (OpenAI-compatible)
    - Custom base URLs for internal networks
    - Streaming responses (SSE parsing)
    - Retry logic with exponential backoff
    """

    def __init__(self, settings: Settings):
        """
        Initialize Requests client.

        Args:
            settings: Settings instance with LLM configuration
        """
        self._settings = settings
        self._session = requests.Session()
        self._configure_session()

    def _configure_session(self) -> None:
        """Configure the requests session from settings."""
        llm = self._settings.llm

        # Set headers
        headers = {
            "Content-Type": "application/json",
        }
        if llm.api_key:
            headers["Authorization"] = f"Bearer {llm.api_key}"

        self._session.headers.update(headers)

        # Configure SSL verification
        self._session.verify = llm.verify_ssl
        if llm.ca_cert:
            self._session.verify = llm.ca_cert

    def _get_api_url(self) -> str:
        """Get the full API URL for chat completions."""
        llm = self._settings.llm
        base_url = llm.api_base or "https://api.openai.com/v1"
        return f"{base_url.rstrip('/')}/chat/completions"

    def _do_request(
        self,
        payload: Dict[str, Any],
        stream: bool = False,
    ) -> requests.Response:
        """
        Perform HTTP request with retry logic.

        Args:
            payload: Request payload
            stream: Whether to stream response

        Returns:
            Response object
        """
        llm = self._settings.llm
        max_retries = 3
        base_delay = 1.0

        for attempt in range(max_retries):
            try:
                response = self._session.post(
                    self._get_api_url(),
                    json=payload,
                    stream=stream,
                    timeout=llm.timeout,
                )

                # Check for HTTP errors
                if response.status_code >= 400:
                    error_msg = f"API error: {response.status_code}"
                    try:
                        error_detail = response.json()
                        error_msg += f" - {error_detail.get('error', {}).get('message', 'Unknown error')}"
                    except (json.JSONDecodeError, KeyError):
                        pass
                    raise LLMAPIError(error_msg)

                return response

            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    time.sleep(base_delay * (2 ** attempt))
                    continue
                raise LLMTimeoutError(f"Request timeout after {max_retries} retries")

            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    time.sleep(base_delay * (2 ** attempt))
                    continue
                raise LLMAPIError(f"Request failed: {e}")

        raise LLMAPIError("Max retries exceeded")

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

        payload = {
            "model": model or llm.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else llm.temperature,
            "max_tokens": max_tokens if max_tokens is not None else llm.max_tokens,
        }

        # Add tools if provided
        if tools:
            # Try modern 'tools' format first, fall back to 'functions' for compatibility
            payload["tools"] = tools
            if tool_choice:
                if tool_choice in ("auto", "none"):
                    payload["tool_choice"] = tool_choice
                else:
                    payload["tool_choice"] = {"type": "function", "function": {"name": tool_choice}}

        payload.update(kwargs)

        response = self._do_request(payload, stream=False)
        data = response.json()

        result = {
            "content": data["choices"][0]["message"].get("content", "") or "",
            "model": data.get("model", llm.model),
            "usage": {
                "prompt_tokens": data.get("usage", {}).get("prompt_tokens", 0),
                "completion_tokens": data.get("usage", {}).get("completion_tokens", 0),
                "total_tokens": data.get("usage", {}).get("total_tokens", 0),
            },
            "finish_reason": data["choices"][0].get("finish_reason", "stop"),
        }

        # Extract tool_calls if present (modern format)
        tool_calls = data["choices"][0]["message"].get("tool_calls")
        if tool_calls:
            result["tool_calls"] = tool_calls

        # Extract function_call if present (legacy format)
        function_call = data["choices"][0]["message"].get("function_call")
        if function_call and not tool_calls:
            result["tool_calls"] = [{
                "id": f"call_{hash(str(function_call))}",
                "type": "function",
                "function": {
                    "name": function_call.get("name", ""),
                    "arguments": function_call.get("arguments", "{}"),
                },
            }]

        return result

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

        payload = {
            "model": model or llm.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else llm.temperature,
            "max_tokens": max_tokens if max_tokens is not None else llm.max_tokens,
            "stream": True,
        }

        # Add tools if provided
        if tools:
            payload["tools"] = tools
            if tool_choice:
                if tool_choice in ("auto", "none"):
                    payload["tool_choice"] = tool_choice
                else:
                    payload["tool_choice"] = {"type": "function", "function": {"name": tool_choice}}

        payload.update(kwargs)

        response = self._do_request(payload, stream=True)

        for line in response.iter_lines():
            if not line:
                continue

            line = line.decode("utf-8")

            # SSE format: "data: {...}"
            if not line.startswith("data: "):
                continue

            data_str = line[6:]  # Remove "data: " prefix

            # Skip [DONE] marker
            if data_str.strip() == "[DONE]":
                break

            try:
                data = json.loads(data_str)
                delta = data["choices"][0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    yield {"delta": content}

                # Handle tool_calls in streaming
                tool_calls = delta.get("tool_calls")
                if tool_calls:
                    yield {"tool_calls_delta": tool_calls}

            except (json.JSONDecodeError, KeyError):
                continue

    def get_model(self) -> str:
        """Get the default model name."""
        return self._settings.llm.model

    def supports_streaming(self) -> bool:
        """Requests client supports streaming."""
        return True

    def supports_tools(self) -> bool:
        """Requests client supports function calling."""
        return True

    def validate_config(self) -> bool:
        """Validate client configuration."""
        llm = self._settings.llm

        # Check API key
        if not llm.api_key:
            return False

        # Check base URL
        if not llm.api_base:
            return False

        return True

    def close(self) -> None:
        """Close the session."""
        self._session.close()
