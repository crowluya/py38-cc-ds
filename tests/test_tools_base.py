"""
Tests for core/tools/base.py

Python 3.8.10 compatible
"""

import pytest
from claude_code.core.tools.base import (
    Tool,
    ToolCall,
    ToolCategory,
    ToolError,
    ToolParameter,
    ToolPermissionError,
    ToolResult,
    ToolValidationError,
)
from typing import Dict, Any, List


class DummyTool(Tool):
    """A dummy tool for testing."""

    @property
    def name(self) -> str:
        return "dummy"

    @property
    def description(self) -> str:
        return "A dummy tool for testing"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.UTILITY

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="message", type="string", description="Message to echo", required=True),
            ToolParameter(name="count", type="integer", description="Repeat count", required=False, default=1),
        ]

    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        self.validate_arguments(arguments)
        message = arguments.get("message", "")
        count = arguments.get("count", 1)
        output = (message + "\n") * count
        return ToolResult.success_result(self.name, output.strip())


class TestToolParameter:
    """Tests for ToolParameter."""

    def test_basic_parameter(self):
        param = ToolParameter(
            name="file_path",
            type="string",
            description="Path to the file",
            required=True,
        )
        assert param.name == "file_path"
        assert param.type == "string"
        assert param.required is True

    def test_to_json_schema(self):
        param = ToolParameter(
            name="mode",
            type="string",
            description="Operation mode",
            required=False,
            enum=["read", "write"],
            default="read",
        )
        schema = param.to_json_schema()
        assert schema["type"] == "string"
        assert schema["description"] == "Operation mode"
        assert schema["enum"] == ["read", "write"]
        assert schema["default"] == "read"

    def test_optional_parameter(self):
        param = ToolParameter(
            name="limit",
            type="integer",
            description="Max items",
            required=False,
            default=100,
        )
        assert param.required is False
        assert param.default == 100


class TestToolResult:
    """Tests for ToolResult."""

    def test_success_result(self):
        result = ToolResult.success_result("read", "file content here")
        assert result.success is True
        assert result.tool_name == "read"
        assert result.output == "file content here"
        assert result.error is None

    def test_error_result(self):
        result = ToolResult.error_result("write", "Permission denied")
        assert result.success is False
        assert result.tool_name == "write"
        assert result.error == "Permission denied"

    def test_to_dict(self):
        result = ToolResult(
            tool_name="bash",
            success=True,
            output="hello world",
            metadata={"exit_code": 0},
        )
        d = result.to_dict()
        assert d["tool_name"] == "bash"
        assert d["success"] is True
        assert d["output"] == "hello world"
        assert d["metadata"]["exit_code"] == 0

    def test_to_dict_with_error(self):
        result = ToolResult.error_result("edit", "File not found")
        d = result.to_dict()
        assert d["success"] is False
        assert d["error"] == "File not found"


class TestToolCall:
    """Tests for ToolCall."""

    def test_basic_tool_call(self):
        call = ToolCall(
            id="call_123",
            name="read",
            arguments={"file_path": "/tmp/test.txt"},
        )
        assert call.id == "call_123"
        assert call.name == "read"
        assert call.arguments["file_path"] == "/tmp/test.txt"

    def test_to_dict(self):
        call = ToolCall(
            id="call_456",
            name="bash",
            arguments={"command": "ls -la"},
        )
        d = call.to_dict()
        assert d["id"] == "call_456"
        assert d["name"] == "bash"
        assert d["arguments"]["command"] == "ls -la"

    def test_from_dict(self):
        data = {
            "id": "call_789",
            "name": "write",
            "arguments": {"file_path": "/tmp/out.txt", "content": "hello"},
        }
        call = ToolCall.from_dict(data)
        assert call.id == "call_789"
        assert call.name == "write"
        assert call.arguments["content"] == "hello"


class TestToolErrors:
    """Tests for tool error classes."""

    def test_tool_error(self):
        err = ToolError("Something went wrong", tool_name="bash")
        assert str(err) == "Something went wrong"
        assert err.tool_name == "bash"
        assert err.recoverable is True

    def test_tool_permission_error(self):
        err = ToolPermissionError("Access denied", tool_name="write")
        assert err.tool_name == "write"
        assert err.recoverable is False

    def test_tool_validation_error(self):
        err = ToolValidationError(
            "Invalid parameter",
            tool_name="read",
            parameter="file_path",
        )
        assert err.tool_name == "read"
        assert err.parameter == "file_path"
        assert err.recoverable is True


class TestTool:
    """Tests for Tool base class."""

    def test_dummy_tool_properties(self):
        tool = DummyTool()
        assert tool.name == "dummy"
        assert tool.description == "A dummy tool for testing"
        assert tool.category == ToolCategory.UTILITY
        assert len(tool.parameters) == 2

    def test_get_json_schema(self):
        tool = DummyTool()
        schema = tool.get_json_schema()

        assert schema["type"] == "function"
        assert schema["function"]["name"] == "dummy"
        assert schema["function"]["description"] == "A dummy tool for testing"

        params = schema["function"]["parameters"]
        assert params["type"] == "object"
        assert "message" in params["properties"]
        assert "count" in params["properties"]
        assert "message" in params["required"]
        assert "count" not in params["required"]

    def test_validate_arguments_success(self):
        tool = DummyTool()
        # Should not raise
        tool.validate_arguments({"message": "hello"})
        tool.validate_arguments({"message": "hello", "count": 3})

    def test_validate_arguments_missing_required(self):
        tool = DummyTool()
        with pytest.raises(ToolValidationError) as exc_info:
            tool.validate_arguments({})
        assert "message" in str(exc_info.value)

    def test_validate_arguments_wrong_type(self):
        tool = DummyTool()
        with pytest.raises(ToolValidationError) as exc_info:
            tool.validate_arguments({"message": 123})  # Should be string
        assert "string" in str(exc_info.value)

    def test_execute_success(self):
        tool = DummyTool()
        result = tool.execute({"message": "hello"})
        assert result.success is True
        assert result.output == "hello"

    def test_execute_with_count(self):
        tool = DummyTool()
        result = tool.execute({"message": "hi", "count": 3})
        assert result.success is True
        assert result.output == "hi\nhi\nhi"

    def test_str_repr(self):
        tool = DummyTool()
        assert str(tool) == "Tool(dummy)"
        assert "name=dummy" in repr(tool)
        assert "category=utility" in repr(tool)


class TestToolCategory:
    """Tests for ToolCategory enum."""

    def test_categories(self):
        assert ToolCategory.FILE.value == "file"
        assert ToolCategory.SHELL.value == "shell"
        assert ToolCategory.SEARCH.value == "search"
        assert ToolCategory.AGENT.value == "agent"
        assert ToolCategory.UTILITY.value == "utility"


class TestToolWithEnum:
    """Test tool with enum parameter."""

    def test_enum_validation(self):
        class EnumTool(Tool):
            @property
            def name(self) -> str:
                return "enum_tool"

            @property
            def description(self) -> str:
                return "Tool with enum"

            @property
            def parameters(self) -> List[ToolParameter]:
                return [
                    ToolParameter(
                        name="mode",
                        type="string",
                        description="Mode",
                        required=True,
                        enum=["fast", "slow"],
                    ),
                ]

            def execute(self, arguments: Dict[str, Any]) -> ToolResult:
                return ToolResult.success_result(self.name, arguments["mode"])

        tool = EnumTool()

        # Valid enum value
        tool.validate_arguments({"mode": "fast"})

        # Invalid enum value
        with pytest.raises(ToolValidationError) as exc_info:
            tool.validate_arguments({"mode": "invalid"})
        assert "fast" in str(exc_info.value)
        assert "slow" in str(exc_info.value)
