"""
Tests for CLI Tool Display (T012)

Python 3.8.10 compatible
"""

import pytest
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, MagicMock, patch

from deep_code.cli.models import ToolBlock
from deep_code.core.tools.base import ToolCall, ToolResult


class TestToolBlock:
    """Tests for ToolBlock rendering."""

    def test_tool_block_success(self):
        """Test rendering successful tool block."""
        block = ToolBlock(
            title="Read(test.py)",
            body="def hello():\n    pass",
            ok=True,
        )
        rendered = block.render()

        assert "●" in rendered
        assert "Read(test.py)" in rendered
        assert "def hello():" in rendered

    def test_tool_block_failure(self):
        """Test rendering failed tool block."""
        block = ToolBlock(
            title="Write(test.py)",
            body="Permission denied",
            ok=False,
        )
        rendered = block.render()

        assert "●" in rendered
        assert "Write(test.py)" in rendered
        assert "Permission denied" in rendered

    def test_tool_block_collapsed(self):
        """Test collapsed tool block with many lines."""
        long_body = "\n".join([f"line {i}" for i in range(50)])
        block = ToolBlock(
            title="Read(large.py)",
            body=long_body,
            ok=True,
            expanded=False,
            max_lines=12,
        )
        rendered = block.render()

        # Should show truncation message
        assert "Ctrl+O to expand" in rendered or "lines" in rendered

    def test_tool_block_expanded(self):
        """Test expanded tool block shows all lines."""
        long_body = "\n".join([f"line {i}" for i in range(50)])
        block = ToolBlock(
            title="Read(large.py)",
            body=long_body,
            ok=True,
            expanded=True,
            max_lines=12,
        )
        rendered = block.render()

        # Should show all lines
        assert "line 49" in rendered

    def test_tool_block_empty_body(self):
        """Test tool block with empty body."""
        block = ToolBlock(
            title="Write(test.py)",
            body="",
            ok=True,
        )
        rendered = block.render()

        assert "Write(test.py)" in rendered


class TestToolCallFormatting:
    """Tests for formatting tool calls for display."""

    def test_format_tool_call_read(self):
        """Test formatting Read tool call."""
        from deep_code.cli.tool_display import format_tool_call_title

        tool_call = ToolCall(
            id="call_1",
            name="Read",
            arguments={"file_path": "/path/to/file.py"},
        )

        title = format_tool_call_title(tool_call)
        assert "Read" in title
        assert "file.py" in title

    def test_format_tool_call_write(self):
        """Test formatting Write tool call."""
        from deep_code.cli.tool_display import format_tool_call_title

        tool_call = ToolCall(
            id="call_2",
            name="Write",
            arguments={"file_path": "/path/to/output.txt", "content": "hello"},
        )

        title = format_tool_call_title(tool_call)
        assert "Write" in title
        assert "output.txt" in title

    def test_format_tool_call_bash(self):
        """Test formatting Bash tool call."""
        from deep_code.cli.tool_display import format_tool_call_title

        tool_call = ToolCall(
            id="call_3",
            name="Bash",
            arguments={"command": "ls -la"},
        )

        title = format_tool_call_title(tool_call)
        assert "Bash" in title
        assert "ls -la" in title

    def test_format_tool_call_glob(self):
        """Test formatting Glob tool call."""
        from deep_code.cli.tool_display import format_tool_call_title

        tool_call = ToolCall(
            id="call_4",
            name="Glob",
            arguments={"pattern": "**/*.py"},
        )

        title = format_tool_call_title(tool_call)
        assert "Glob" in title
        assert "*.py" in title

    def test_format_tool_call_grep(self):
        """Test formatting Grep tool call."""
        from deep_code.cli.tool_display import format_tool_call_title

        tool_call = ToolCall(
            id="call_5",
            name="Grep",
            arguments={"pattern": "def test_"},
        )

        title = format_tool_call_title(tool_call)
        assert "Grep" in title
        assert "def test_" in title

    def test_format_tool_call_edit(self):
        """Test formatting Edit tool call."""
        from deep_code.cli.tool_display import format_tool_call_title

        tool_call = ToolCall(
            id="call_6",
            name="Edit",
            arguments={
                "file_path": "/path/to/file.py",
                "old_string": "foo",
                "new_string": "bar",
            },
        )

        title = format_tool_call_title(tool_call)
        assert "Edit" in title
        assert "file.py" in title


class TestToolResultFormatting:
    """Tests for formatting tool results for display."""

    def test_format_tool_result_success(self):
        """Test formatting successful tool result."""
        from deep_code.cli.tool_display import format_tool_result_body

        result = ToolResult.success_result(
            "Read",
            "def hello():\n    print('Hello')",
        )

        body = format_tool_result_body(result)
        assert "def hello():" in body

    def test_format_tool_result_error(self):
        """Test formatting error tool result."""
        from deep_code.cli.tool_display import format_tool_result_body

        result = ToolResult.error_result(
            "Write",
            "Permission denied: /etc/passwd",
        )

        body = format_tool_result_body(result)
        assert "Permission denied" in body

    def test_format_tool_result_truncated(self):
        """Test formatting long tool result."""
        from deep_code.cli.tool_display import format_tool_result_body

        long_output = "x" * 10000
        result = ToolResult.success_result("Read", long_output)

        body = format_tool_result_body(result, max_length=1000)
        assert len(body) <= 1100  # Allow some overhead for truncation message


class TestToolBlockCreation:
    """Tests for creating ToolBlock from tool calls and results."""

    def test_create_tool_block_from_call_and_result(self):
        """Test creating ToolBlock from tool call and result."""
        from deep_code.cli.tool_display import create_tool_block

        tool_call = ToolCall(
            id="call_1",
            name="Read",
            arguments={"file_path": "/path/to/file.py"},
        )
        result = ToolResult.success_result(
            "Read",
            "def hello():\n    pass",
        )

        block = create_tool_block(tool_call, result)

        assert isinstance(block, ToolBlock)
        assert "Read" in block.title
        assert block.ok is True
        assert "def hello():" in block.body

    def test_create_tool_block_from_failed_result(self):
        """Test creating ToolBlock from failed result."""
        from deep_code.cli.tool_display import create_tool_block

        tool_call = ToolCall(
            id="call_1",
            name="Write",
            arguments={"file_path": "/etc/passwd", "content": "test"},
        )
        result = ToolResult.error_result(
            "Write",
            "Permission denied",
        )

        block = create_tool_block(tool_call, result)

        assert isinstance(block, ToolBlock)
        assert block.ok is False
        assert "Permission denied" in block.body


class TestToolDisplayCallback:
    """Tests for tool display callback integration."""

    def test_on_tool_call_callback(self):
        """Test that on_tool_call callback creates proper display."""
        from deep_code.cli.tool_display import create_tool_block

        displayed_blocks = []

        def on_tool_call(tool_call: ToolCall, result: ToolResult):
            block = create_tool_block(tool_call, result)
            displayed_blocks.append(block)

        # Simulate tool calls
        tool_call = ToolCall(
            id="call_1",
            name="Glob",
            arguments={"pattern": "*.py"},
        )
        result = ToolResult.success_result(
            "Glob",
            "file1.py\nfile2.py\nfile3.py",
        )

        on_tool_call(tool_call, result)

        assert len(displayed_blocks) == 1
        assert "Glob" in displayed_blocks[0].title
        assert displayed_blocks[0].ok is True


class TestToolDisplayIntegration:
    """Integration tests for tool display with Agent."""

    def test_agent_with_tool_display_callback(self):
        """Test agent integration with tool display callback."""
        from deep_code.core.agent import Agent, AgentConfig
        from deep_code.core.tools.registry import ToolRegistry
        from deep_code.core.tools.base import Tool, ToolCategory, ToolParameter
        from deep_code.cli.tool_display import create_tool_block

        class MockTool(Tool):
            @property
            def name(self) -> str:
                return "MockTool"

            @property
            def description(self) -> str:
                return "Mock tool"

            @property
            def category(self) -> ToolCategory:
                return ToolCategory.OTHER

            @property
            def parameters(self) -> list:
                return []

            @property
            def requires_permission(self) -> bool:
                return False

            @property
            def is_dangerous(self) -> bool:
                return False

            def execute(self, arguments: dict) -> ToolResult:
                return ToolResult.success_result(self.name, "Mock output")

        class MockLLMClient:
            def __init__(self):
                self._call_count = 0

            def chat_completion(self, messages, **kwargs):
                self._call_count += 1
                if self._call_count == 1:
                    return {
                        "content": "",
                        "finish_reason": "tool_calls",
                        "tool_calls": [
                            {"id": "call_1", "name": "MockTool", "arguments": {}}
                        ],
                    }
                return {
                    "content": "Done",
                    "finish_reason": "stop",
                    "tool_calls": None,
                }

        displayed_blocks = []

        def on_tool_call(tool_call: ToolCall, result: ToolResult):
            block = create_tool_block(tool_call, result)
            displayed_blocks.append(block)

        registry = ToolRegistry()
        registry.register(MockTool())

        config = AgentConfig(
            llm_client=MockLLMClient(),
            tool_registry=registry,
            on_tool_call=on_tool_call,
        )
        agent = Agent(config)

        turn = agent.process("Run the mock tool")

        assert len(displayed_blocks) == 1
        assert "MockTool" in displayed_blocks[0].title
