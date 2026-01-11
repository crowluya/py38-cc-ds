"""
Tests for MCP (Model Context Protocol) framework

Python 3.8.10 compatible
Tests for MCP-001 through MCP-020 implementations.
"""

import pytest
import json
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path


class TestMCPProtocol:
    """Tests for MCP protocol message types (MCP-001)."""

    def test_create_request(self):
        """Test creating a JSON-RPC request."""
        from deep_code.extensions.mcp.protocol import MCPRequest, create_request

        request = create_request("tools/list", {})

        assert request.jsonrpc == "2.0"
        assert request.method == "tools/list"
        assert request.id is not None
        assert request.params == {}

    def test_create_request_with_params(self):
        """Test creating a request with parameters."""
        from deep_code.extensions.mcp.protocol import create_request

        request = create_request("tools/call", {
            "name": "read_file",
            "arguments": {"path": "/tmp/test.txt"}
        })

        assert request.method == "tools/call"
        assert request.params["name"] == "read_file"
        assert request.params["arguments"]["path"] == "/tmp/test.txt"

    def test_request_to_dict(self):
        """Test converting request to dictionary."""
        from deep_code.extensions.mcp.protocol import MCPRequest

        request = MCPRequest(method="test", params={"key": "value"}, id=1)
        data = request.to_dict()

        assert data["jsonrpc"] == "2.0"
        assert data["method"] == "test"
        assert data["id"] == 1
        assert data["params"] == {"key": "value"}

    def test_request_from_dict(self):
        """Test creating request from dictionary."""
        from deep_code.extensions.mcp.protocol import MCPRequest

        data = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }
        request = MCPRequest.from_dict(data)

        assert request.method == "tools/list"
        assert request.id == 1


class TestMCPResponse:
    """Tests for MCPResponse data class."""

    def test_success_response(self):
        """Test creating a success response."""
        from deep_code.extensions.mcp.protocol import MCPResponse

        response = MCPResponse(id=1, result={"key": "value"})

        assert response.id == 1
        assert response.result == {"key": "value"}
        assert response.error is None
        assert response.is_error is False

    def test_error_response(self):
        """Test creating an error response."""
        from deep_code.extensions.mcp.protocol import MCPResponse

        response = MCPResponse(
            id=1,
            error={"code": -32600, "message": "Invalid Request"}
        )

        assert response.id == 1
        assert response.error is not None
        assert response.is_error is True

    def test_response_to_dict(self):
        """Test converting response to dictionary."""
        from deep_code.extensions.mcp.protocol import MCPResponse

        response = MCPResponse(id=1, result={"tools": []})
        data = response.to_dict()

        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 1
        assert data["result"] == {"tools": []}

    def test_response_from_dict(self):
        """Test creating response from dictionary."""
        from deep_code.extensions.mcp.protocol import MCPResponse

        data = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"tools": [{"name": "test_tool"}]}
        }
        response = MCPResponse.from_dict(data)

        assert response.id == 1
        assert response.result == {"tools": [{"name": "test_tool"}]}


class TestMCPNotification:
    """Tests for MCPNotification."""

    def test_create_notification(self):
        """Test creating a notification."""
        from deep_code.extensions.mcp.protocol import create_notification

        notification = create_notification(
            "notifications/tools/list_changed",
            {}
        )

        assert notification.method == "notifications/tools/list_changed"
        assert notification.jsonrpc == "2.0"

    def test_notification_no_id(self):
        """Test that notifications have no id."""
        from deep_code.extensions.mcp.protocol import MCPNotification

        notification = MCPNotification(method="test")
        data = notification.to_dict()

        assert "id" not in data


class TestMCPMessageEncoding:
    """Tests for message encoding/decoding."""

    def test_encode_message(self):
        """Test encoding message to JSON."""
        from deep_code.extensions.mcp.protocol import MCPRequest, encode_message

        request = MCPRequest(method="test", id=1)
        encoded = encode_message(request)

        assert isinstance(encoded, str)
        data = json.loads(encoded)
        assert data["method"] == "test"

    def test_decode_request(self):
        """Test decoding a request."""
        from deep_code.extensions.mcp.protocol import decode_message, MCPRequest

        data = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list"
        })
        message = decode_message(data)

        assert isinstance(message, MCPRequest)
        assert message.method == "tools/list"

    def test_decode_response(self):
        """Test decoding a response."""
        from deep_code.extensions.mcp.protocol import decode_message, MCPResponse

        data = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"tools": []}
        })
        message = decode_message(data)

        assert isinstance(message, MCPResponse)
        assert message.result == {"tools": []}

    def test_decode_notification(self):
        """Test decoding a notification."""
        from deep_code.extensions.mcp.protocol import decode_message, MCPNotification

        data = json.dumps({
            "jsonrpc": "2.0",
            "method": "notifications/tools/list_changed"
        })
        message = decode_message(data)

        assert isinstance(message, MCPNotification)


class TestMCPToolWrapper:
    """Tests for MCP tool wrapper (MCP-013)."""

    def test_create_wrapper_tool(self):
        """Test creating a wrapper tool from MCP definition."""
        from deep_code.extensions.mcp.tools import MCPToolWrapper

        mcp_tool_def = {
            "name": "mcp_read_file",
            "description": "Read file via MCP",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"}
                },
                "required": ["path"]
            }
        }

        mock_client = Mock()
        wrapper = MCPToolWrapper(
            tool_definition=mcp_tool_def,
            mcp_client=mock_client,
            server_name="test-server"
        )

        assert wrapper.name == "mcp__test-server__mcp_read_file"
        assert "Read file via MCP" in wrapper.description

    def test_wrapper_tool_execute(self):
        """Test executing a wrapper tool."""
        from deep_code.extensions.mcp.tools import MCPToolWrapper

        mcp_tool_def = {
            "name": "test_tool",
            "description": "Test tool"
        }

        mock_client = Mock()
        mock_client.call_tool.return_value = {"result": "success"}

        wrapper = MCPToolWrapper(
            tool_definition=mcp_tool_def,
            mcp_client=mock_client,
            server_name="server"
        )

        result = wrapper.execute({"arg1": "value1"})

        assert result.success is True
        mock_client.call_tool.assert_called_once_with("test_tool", {"arg1": "value1"})

    def test_wrapper_tool_execute_error(self):
        """Test wrapper tool execution error handling."""
        from deep_code.extensions.mcp.tools import MCPToolWrapper

        mcp_tool_def = {
            "name": "failing_tool",
            "description": "A tool that fails"
        }

        mock_client = Mock()
        mock_client.call_tool.side_effect = RuntimeError("Tool execution failed")

        wrapper = MCPToolWrapper(
            tool_definition=mcp_tool_def,
            mcp_client=mock_client,
            server_name="server"
        )

        result = wrapper.execute({})

        assert result.success is False
        assert "failed" in result.error.lower()

    def test_wrapper_tool_json_schema(self):
        """Test wrapper tool JSON schema generation."""
        from deep_code.extensions.mcp.tools import MCPToolWrapper

        mcp_tool_def = {
            "name": "schema_tool",
            "description": "Tool with schema",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "param1": {"type": "string", "description": "First param"}
                },
                "required": ["param1"]
            }
        }

        mock_client = Mock()
        wrapper = MCPToolWrapper(
            tool_definition=mcp_tool_def,
            mcp_client=mock_client,
            server_name="test"
        )

        schema = wrapper.get_json_schema()

        assert schema["type"] == "function"
        assert "param1" in schema["function"]["parameters"]["properties"]


class TestMCPToolRouter:
    """Tests for MCP tool router (MCP-014)."""

    def test_router_register(self):
        """Test registering a tool."""
        from deep_code.extensions.mcp.tools import MCPToolWrapper, MCPToolRouter

        router = MCPToolRouter()
        mock_client = Mock()
        wrapper = MCPToolWrapper(
            tool_definition={"name": "test", "description": "Test"},
            mcp_client=mock_client,
            server_name="server"
        )

        router.register(wrapper)

        assert len(router) == 1
        assert wrapper.name in router

    def test_router_get(self):
        """Test getting a tool by name."""
        from deep_code.extensions.mcp.tools import MCPToolWrapper, MCPToolRouter

        router = MCPToolRouter()
        mock_client = Mock()
        wrapper = MCPToolWrapper(
            tool_definition={"name": "test", "description": "Test"},
            mcp_client=mock_client,
            server_name="server"
        )
        router.register(wrapper)

        found = router.get(wrapper.name)
        assert found is wrapper

        # Also find by original name
        found_by_original = router.get("test")
        assert found_by_original is wrapper

    def test_router_call(self):
        """Test calling a tool through router."""
        from deep_code.extensions.mcp.tools import MCPToolWrapper, MCPToolRouter

        router = MCPToolRouter()
        mock_client = Mock()
        mock_client.call_tool.return_value = "result"

        wrapper = MCPToolWrapper(
            tool_definition={"name": "test", "description": "Test"},
            mcp_client=mock_client,
            server_name="server"
        )
        router.register(wrapper)

        result = router.call(wrapper.name, {"arg": "value"})

        assert result.success is True

    def test_router_clear(self):
        """Test clearing all tools."""
        from deep_code.extensions.mcp.tools import MCPToolWrapper, MCPToolRouter

        router = MCPToolRouter()
        mock_client = Mock()
        wrapper = MCPToolWrapper(
            tool_definition={"name": "test", "description": "Test"},
            mcp_client=mock_client,
            server_name="server"
        )
        router.register(wrapper)

        router.clear()

        assert len(router) == 0


class TestJSONSchemaValidation:
    """Tests for JSON Schema validation (MCP-013)."""

    def test_validate_string(self):
        """Test validating string type."""
        from deep_code.extensions.mcp.tools import validate_json_schema

        schema = {"type": "string"}
        errors = validate_json_schema("hello", schema)
        assert len(errors) == 0

        errors = validate_json_schema(123, schema)
        assert len(errors) > 0

    def test_validate_object(self):
        """Test validating object type."""
        from deep_code.extensions.mcp.tools import validate_json_schema

        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"}
            },
            "required": ["name"]
        }

        errors = validate_json_schema({"name": "test"}, schema)
        assert len(errors) == 0

        errors = validate_json_schema({}, schema)
        assert len(errors) > 0  # Missing required

    def test_validate_array(self):
        """Test validating array type."""
        from deep_code.extensions.mcp.tools import validate_json_schema

        schema = {
            "type": "array",
            "items": {"type": "string"}
        }

        errors = validate_json_schema(["a", "b"], schema)
        assert len(errors) == 0

        errors = validate_json_schema([1, 2], schema)
        assert len(errors) > 0


class TestOutputTruncation:
    """Tests for output truncation (MCP-014)."""

    def test_truncate_short_output(self):
        """Test that short output is not truncated."""
        from deep_code.extensions.mcp.tools import truncate_output

        output = "short output"
        result = truncate_output(output, limit=100)

        assert result == output

    def test_truncate_long_output(self):
        """Test that long output is truncated."""
        from deep_code.extensions.mcp.tools import truncate_output

        output = "x" * 200
        result = truncate_output(output, limit=100)

        assert len(result) < len(output)
        assert "truncated" in result.lower()


class TestMCPConfig:
    """Tests for MCP configuration (MCP-010, MCP-011)."""

    def test_server_config_from_dict(self):
        """Test creating server config from dictionary."""
        from deep_code.extensions.mcp.config import MCPServerConfig

        config = MCPServerConfig.from_dict("test", {
            "command": "npx",
            "args": ["-y", "server"],
            "env": {"KEY": "value"}
        })

        assert config.name == "test"
        assert config.command == "npx"
        assert config.args == ["-y", "server"]
        assert config.env == {"KEY": "value"}

    def test_server_config_http(self):
        """Test HTTP server config."""
        from deep_code.extensions.mcp.config import MCPServerConfig

        config = MCPServerConfig.from_dict("api", {
            "type": "http",
            "url": "https://api.example.com/mcp",
            "headers": {"Authorization": "Bearer token"}
        })

        assert config.transport_type == "http"
        assert config.url == "https://api.example.com/mcp"

    def test_mcp_config_from_dict(self):
        """Test loading MCPConfig from dictionary."""
        from deep_code.extensions.mcp.config import MCPConfig

        config_dict = {
            "mcpServers": {
                "filesystem": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
                },
                "github": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-github"],
                    "env": {"GITHUB_TOKEN": "xxx"}
                }
            }
        }

        config = MCPConfig.from_dict(config_dict)

        assert len(config) == 2
        assert "filesystem" in config.list_servers()
        assert "github" in config.list_servers()

    def test_mcp_config_empty(self):
        """Test loading empty config."""
        from deep_code.extensions.mcp.config import MCPConfig

        config = MCPConfig.from_dict({})

        assert len(config) == 0

    def test_get_server_config(self):
        """Test getting server configuration."""
        from deep_code.extensions.mcp.config import MCPConfig

        config_dict = {
            "mcpServers": {
                "test": {
                    "command": "python",
                    "args": ["-m", "test_server"]
                }
            }
        }

        config = MCPConfig.from_dict(config_dict)
        server_config = config.get_server("test")

        assert server_config is not None
        assert server_config.command == "python"

    def test_get_nonexistent_server(self):
        """Test getting non-existent server config."""
        from deep_code.extensions.mcp.config import MCPConfig

        config = MCPConfig.from_dict({})
        server_config = config.get_server("nonexistent")

        assert server_config is None


class TestEnvVarExpansion:
    """Tests for environment variable expansion (MCP-010)."""

    def test_expand_simple_var(self):
        """Test expanding simple variable."""
        from deep_code.extensions.mcp.config import expand_env_vars
        import os

        os.environ["TEST_VAR"] = "test_value"
        result = expand_env_vars("${TEST_VAR}")

        assert result == "test_value"

    def test_expand_with_default(self):
        """Test expanding with default value."""
        from deep_code.extensions.mcp.config import expand_env_vars
        import os

        # Ensure var doesn't exist
        os.environ.pop("NONEXISTENT_VAR", None)
        result = expand_env_vars("${NONEXISTENT_VAR:-default}")

        assert result == "default"

    def test_expand_in_string(self):
        """Test expanding variable in string."""
        from deep_code.extensions.mcp.config import expand_env_vars
        import os

        os.environ["PREFIX"] = "hello"
        result = expand_env_vars("${PREFIX}_world")

        assert result == "hello_world"


class TestMCPManager:
    """Tests for MCP manager (MCP-012)."""

    def test_manager_initialization(self):
        """Test manager initialization."""
        from deep_code.extensions.mcp.manager import MCPManager

        manager = MCPManager()

        assert len(manager) == 0

    def test_manager_add_server(self):
        """Test adding a server to manager."""
        from deep_code.extensions.mcp.manager import MCPManager
        from deep_code.extensions.mcp.config import MCPServerConfig

        manager = MCPManager()
        config = MCPServerConfig(name="test", command="echo")
        manager.add_server(config)

        assert "test" in manager
        assert len(manager) == 1

    def test_manager_remove_server(self):
        """Test removing a server from manager."""
        from deep_code.extensions.mcp.manager import MCPManager
        from deep_code.extensions.mcp.config import MCPServerConfig

        manager = MCPManager()
        config = MCPServerConfig(name="test", command="echo")
        manager.add_server(config)
        manager.remove_server("test")

        assert "test" not in manager

    def test_manager_list_servers(self):
        """Test listing servers."""
        from deep_code.extensions.mcp.manager import MCPManager
        from deep_code.extensions.mcp.config import MCPServerConfig

        manager = MCPManager()
        manager.add_server(MCPServerConfig(name="server1", command="cmd1"))
        manager.add_server(MCPServerConfig(name="server2", command="cmd2"))

        servers = manager.list_servers()

        assert "server1" in servers
        assert "server2" in servers

    def test_manager_get_status(self):
        """Test getting server status."""
        from deep_code.extensions.mcp.manager import MCPManager, ServerStatus
        from deep_code.extensions.mcp.config import MCPServerConfig

        manager = MCPManager()
        manager.add_server(MCPServerConfig(name="test", command="echo"))

        status = manager.get_status("test")

        assert status == ServerStatus.DISCONNECTED


class TestMCPResources:
    """Tests for MCP resource references (MCP-015)."""

    def test_parse_resource_reference(self):
        """Test parsing resource reference."""
        from deep_code.extensions.mcp.resources import ResourceReference

        ref = ResourceReference.parse("@mcp:notion:project-notes")

        assert ref is not None
        assert ref.server_name == "notion"
        assert ref.resource_uri == "project-notes"

    def test_find_resource_references(self):
        """Test finding multiple references in text."""
        from deep_code.extensions.mcp.resources import find_resource_references

        text = "Check @mcp:notion:notes and @mcp:github:issues"
        refs = find_resource_references(text)

        assert len(refs) == 2
        assert refs[0].server_name == "notion"
        assert refs[1].server_name == "github"

    def test_resource_content_format(self):
        """Test formatting resource content."""
        from deep_code.extensions.mcp.resources import ResourceContent

        content = ResourceContent(
            uri="file:///test.txt",
            name="test.txt",
            content="Hello world",
            mime_type="text/plain",
            server_name="filesystem"
        )

        formatted = content.to_context_string()

        assert "test.txt" in formatted
        assert "Hello world" in formatted


class TestMCPIntegration:
    """Integration tests for MCP framework."""

    def test_tool_naming_convention(self):
        """Test that MCP tools follow naming convention: mcp__server__toolname."""
        from deep_code.extensions.mcp.tools import MCPToolWrapper

        wrapper = MCPToolWrapper(
            tool_definition={"name": "read", "description": "Read"},
            mcp_client=Mock(),
            server_name="filesystem"
        )

        assert wrapper.name == "mcp__filesystem__read"

    def test_tool_category(self):
        """Test that MCP tools have correct category."""
        from deep_code.extensions.mcp.tools import MCPToolWrapper
        from deep_code.core.tools.base import ToolCategory

        wrapper = MCPToolWrapper(
            tool_definition={"name": "test", "description": "Test"},
            mcp_client=Mock(),
            server_name="server"
        )

        assert wrapper.category == ToolCategory.MCP

    def test_manager_context_manager(self):
        """Test manager as context manager."""
        from deep_code.extensions.mcp.manager import MCPManager

        with MCPManager() as manager:
            assert manager is not None

    def test_resource_resolver_caching(self):
        """Test resource resolver caching."""
        from deep_code.extensions.mcp.resources import ResourceResolver
        from deep_code.extensions.mcp.manager import MCPManager

        manager = MCPManager()
        resolver = ResourceResolver(manager)

        # Cache should be empty initially
        assert len(resolver._cache) == 0

        # Clear cache should work
        resolver.clear_cache()
        assert len(resolver._cache) == 0
