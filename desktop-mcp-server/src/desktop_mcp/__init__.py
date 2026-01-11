"""
Desktop MCP Server

Python 3.8.10 compatible
Provides desktop automation tools via MCP protocol.
"""

from desktop_mcp.server import MCPServer, run_server

__version__ = "0.1.0"
__all__ = ["MCPServer", "run_server"]
