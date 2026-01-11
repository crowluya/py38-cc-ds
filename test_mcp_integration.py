#!/usr/bin/env python3
"""
Integration test for DeepCode MCP client with real MCP server.

Tests the full flow:
1. Start test MCP server as subprocess
2. Connect via stdio transport
3. Initialize handshake
4. List tools
5. Call tools
6. Shutdown
"""

import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from deep_code.extensions.mcp.protocol import MCPRequest, MCPResponse
from deep_code.extensions.mcp.transport_stdio import StdioTransport
from deep_code.extensions.mcp.client import MCPClient


def test_mcp_integration():
    """Test MCP client with real server."""
    print("=" * 60)
    print("DeepCode MCP Integration Test")
    print("=" * 60)

    # Path to test server
    server_script = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "test_mcp_server.py"
    )
    python_path = sys.executable

    print(f"\n1. Starting MCP server...")
    print(f"   Python: {python_path}")
    print(f"   Server: {server_script}")

    # Create transport
    transport = StdioTransport(
        command=python_path,
        args=[server_script],
    )

    try:
        # Start transport
        transport.start()
        print("   Server started successfully!")

        # Create client
        client = MCPClient(transport)

        # Test initialize
        print(f"\n2. Testing initialize...")
        init_result = client.initialize()
        print(f"   Protocol version: {init_result.get('protocolVersion', 'unknown')}")
        print(f"   Server: {init_result.get('serverInfo', {}).get('name', 'unknown')}")
        print("   Initialize OK!")

        # Test tools/list
        print(f"\n3. Testing tools/list...")
        tools = client.list_tools()
        print(f"   Found {len(tools)} tools:")
        for tool in tools:
            print(f"   - {tool.get('name')}: {tool.get('description')}")
        print("   Tools list OK!")

        # Test tools/call - echo
        print(f"\n4. Testing tools/call (echo)...")
        echo_result = client.call_tool("echo", {"message": "Hello DeepCode!"})
        print(f"   Result: {echo_result}")
        print("   Echo tool OK!")

        # Test tools/call - add
        print(f"\n5. Testing tools/call (add)...")
        add_result = client.call_tool("add", {"a": 10, "b": 32})
        print(f"   Result: {add_result}")
        print("   Add tool OK!")

        # Test shutdown
        print(f"\n6. Testing shutdown...")
        client.shutdown()
        print("   Shutdown OK!")

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n   ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup
        try:
            transport.stop()
        except:
            pass


if __name__ == "__main__":
    success = test_mcp_integration()
    sys.exit(0 if success else 1)
