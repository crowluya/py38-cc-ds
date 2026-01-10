"""
Tests for LLM Client Tool Use support (T003)

Python 3.8.10 compatible
"""

import json
import pytest
from typing import Any, Dict, Iterator, List, Optional
from unittest.mock import MagicMock, patch

from deep_code.llm.client import LLMClient


class MockToolClient(LLMClient):
    """Mock client for testing tool use."""

    def __init__(self, tool_response: Optional[Dict[str, Any]] = None):
        self._tool_response = tool_response
        self._last_tools = None
        self._last_tool_choice = None

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
        # Store for inspection
        self._last_tools = tools
        self._last_tool_choice = tool_choice

        if self._tool_response:
            return self._tool_response

        # Default response without tools
        return {
            "content": "Hello!",
            "model": "test-model",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "finish_reason": "stop",
        }

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
        self._last_tools = tools
        self._last_tool_choice = tool_choice
        yield {"delta": "Hello"}
        yield {"delta": " World"}

    def get_model(self) -> str:
        return "test-model"

    def validate_config(self) -> bool:
        return True


class TestLLMClientToolUse:
    """Tests for tool use in LLM clients."""

    def test_chat_completion_accepts_tools(self):
        """Test that chat_completion accepts tools parameter."""
        client = MockToolClient()
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read a file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string", "description": "Path to file"},
                        },
                        "required": ["file_path"],
                    },
                },
            }
        ]

        result = client.chat_completion(
            messages=[{"role": "user", "content": "Read test.txt"}],
            tools=tools,
            tool_choice="auto",
        )

        assert client._last_tools == tools
        assert client._last_tool_choice == "auto"
        assert "content" in result

    def test_chat_completion_returns_tool_calls(self):
        """Test that chat_completion can return tool_calls."""
        tool_response = {
            "content": "",
            "model": "test-model",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "finish_reason": "tool_calls",
            "tool_calls": [
                {
                    "id": "call_123",
                    "type": "function",
                    "function": {
                        "name": "read_file",
                        "arguments": '{"file_path": "test.txt"}',
                    },
                }
            ],
        }

        client = MockToolClient(tool_response=tool_response)
        result = client.chat_completion(
            messages=[{"role": "user", "content": "Read test.txt"}],
            tools=[{"type": "function", "function": {"name": "read_file"}}],
        )

        assert "tool_calls" in result
        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["function"]["name"] == "read_file"

    def test_tool_choice_auto(self):
        """Test tool_choice='auto'."""
        client = MockToolClient()
        client.chat_completion(
            messages=[{"role": "user", "content": "Hello"}],
            tools=[{"type": "function", "function": {"name": "test"}}],
            tool_choice="auto",
        )
        assert client._last_tool_choice == "auto"

    def test_tool_choice_none(self):
        """Test tool_choice='none'."""
        client = MockToolClient()
        client.chat_completion(
            messages=[{"role": "user", "content": "Hello"}],
            tools=[{"type": "function", "function": {"name": "test"}}],
            tool_choice="none",
        )
        assert client._last_tool_choice == "none"

    def test_tool_choice_specific(self):
        """Test tool_choice with specific function name."""
        client = MockToolClient()
        client.chat_completion(
            messages=[{"role": "user", "content": "Hello"}],
            tools=[{"type": "function", "function": {"name": "read_file"}}],
            tool_choice="read_file",
        )
        assert client._last_tool_choice == "read_file"

    def test_stream_accepts_tools(self):
        """Test that chat_completion_stream accepts tools parameter."""
        client = MockToolClient()
        tools = [{"type": "function", "function": {"name": "test"}}]

        chunks = list(client.chat_completion_stream(
            messages=[{"role": "user", "content": "Hello"}],
            tools=tools,
            tool_choice="auto",
        ))

        assert client._last_tools == tools
        assert client._last_tool_choice == "auto"
        assert len(chunks) == 2

    def test_format_tool_result_message(self):
        """Test format_tool_result_message helper."""
        client = MockToolClient()
        msg = client.format_tool_result_message(
            tool_call_id="call_123",
            tool_name="read_file",
            content="File content here",
        )

        assert msg["role"] == "tool"
        assert msg["tool_call_id"] == "call_123"
        assert msg["name"] == "read_file"
        assert msg["content"] == "File content here"

    def test_no_tools_still_works(self):
        """Test that calls without tools still work."""
        client = MockToolClient()
        result = client.chat_completion(
            messages=[{"role": "user", "content": "Hello"}],
        )

        assert client._last_tools is None
        assert client._last_tool_choice is None
        assert result["content"] == "Hello!"


class TestToolCallParsing:
    """Tests for parsing tool calls from responses."""

    def test_parse_tool_call_arguments(self):
        """Test parsing JSON arguments from tool call."""
        tool_call = {
            "id": "call_123",
            "type": "function",
            "function": {
                "name": "read_file",
                "arguments": '{"file_path": "/tmp/test.txt", "encoding": "utf-8"}',
            },
        }

        args = json.loads(tool_call["function"]["arguments"])
        assert args["file_path"] == "/tmp/test.txt"
        assert args["encoding"] == "utf-8"

    def test_parse_multiple_tool_calls(self):
        """Test parsing multiple tool calls."""
        tool_calls = [
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "read_file", "arguments": '{"file_path": "a.txt"}'},
            },
            {
                "id": "call_2",
                "type": "function",
                "function": {"name": "read_file", "arguments": '{"file_path": "b.txt"}'},
            },
        ]

        assert len(tool_calls) == 2
        assert tool_calls[0]["function"]["name"] == "read_file"
        assert tool_calls[1]["function"]["name"] == "read_file"

        args1 = json.loads(tool_calls[0]["function"]["arguments"])
        args2 = json.loads(tool_calls[1]["function"]["arguments"])
        assert args1["file_path"] == "a.txt"
        assert args2["file_path"] == "b.txt"


class TestToolSchemaFormat:
    """Tests for tool schema format."""

    def test_openai_tool_format(self):
        """Test OpenAI tool format."""
        tool = {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read the contents of a file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "The path to the file to read",
                        },
                        "offset": {
                            "type": "integer",
                            "description": "Line number to start reading from",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Number of lines to read",
                        },
                    },
                    "required": ["file_path"],
                },
            },
        }

        assert tool["type"] == "function"
        assert tool["function"]["name"] == "read_file"
        assert "file_path" in tool["function"]["parameters"]["properties"]
        assert "file_path" in tool["function"]["parameters"]["required"]

    def test_multiple_tools_schema(self):
        """Test multiple tools schema."""
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read a file",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "Write a file",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "bash",
                    "description": "Execute shell command",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
        ]

        assert len(tools) == 3
        names = [t["function"]["name"] for t in tools]
        assert "read_file" in names
        assert "write_file" in names
        assert "bash" in names
