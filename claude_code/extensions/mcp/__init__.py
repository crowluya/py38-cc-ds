"""
MCP (Model Context Protocol) framework for Claude Code Python MVP

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)

Provides:
- MCP protocol parsing (JSON-RPC 2.0)
- Tool server connection (stdio transport)
- Dynamic tool registration
- Configuration file support
"""

from claude_code.extensions.mcp.protocol import MCPProtocol, MCPResponse, parse_tool_definition
from claude_code.extensions.mcp.client import MCPClient, MCPError
from claude_code.extensions.mcp.config import MCPConfig
from claude_code.extensions.mcp.manager import MCPManager
from claude_code.extensions.mcp.tools import MCPToolWrapper

__all__ = [
    "MCPProtocol",
    "MCPResponse",
    "parse_tool_definition",
    "MCPClient",
    "MCPError",
    "MCPConfig",
    "MCPManager",
    "MCPToolWrapper",
]
