#!/usr/bin/env python3
"""
Test external MCP servers with DeepCode MCP client.

Tests:
1. @modelcontextprotocol/server-filesystem
2. @modelcontextprotocol/server-memory
3. @modelcontextprotocol/server-fetch
"""

import sys
import os
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from deep_code.extensions.mcp.transport_stdio import StdioTransport
from deep_code.extensions.mcp.client import MCPClient


def test_filesystem_server():
    """Test filesystem MCP server."""
    print("\n" + "=" * 60)
    print("TEST 1: @modelcontextprotocol/server-filesystem")
    print("=" * 60)

    # Create temp directory for testing
    test_dir = tempfile.mkdtemp(prefix="mcp_test_")
    print(f"\nTest directory: {test_dir}")

    transport = StdioTransport(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", test_dir],
    )

    try:
        print("\n1. Starting server...")
        transport.start()
        time.sleep(2)  # Wait for npx to download and start
        print("   Server started!")

        client = MCPClient(transport, default_timeout=60.0)  # Longer timeout for npx

        print("\n2. Initialize...")
        init_result = client.initialize()
        server_name = init_result.get("serverInfo", {}).get("name", "unknown")
        print(f"   Server: {server_name}")

        print("\n3. List tools...")
        tools = client.list_tools()
        print(f"   Found {len(tools)} tools:")
        for tool in tools:
            print(f"   - {tool.get('name')}")

        print("\n4. Test write_file...")
        write_result = client.call_tool("write_file", {
            "path": os.path.join(test_dir, "hello.txt"),
            "content": "Hello from DeepCode MCP!"
        })
        print(f"   Result: {write_result}")

        print("\n5. Test read_file...")
        read_result = client.call_tool("read_file", {
            "path": os.path.join(test_dir, "hello.txt")
        })
        print(f"   Result: {read_result}")

        print("\n6. Test list_directory...")
        list_result = client.call_tool("list_directory", {
            "path": test_dir
        })
        print(f"   Result: {list_result}")

        print("\n7. Shutdown...")
        client.shutdown()
        print("   Done!")

        print("\n✅ filesystem server test PASSED!")
        return True

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        transport.stop()
        # Cleanup
        import shutil
        try:
            shutil.rmtree(test_dir)
        except:
            pass


def test_memory_server():
    """Test memory MCP server."""
    print("\n" + "=" * 60)
    print("TEST 2: @modelcontextprotocol/server-memory")
    print("=" * 60)

    transport = StdioTransport(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-memory"],
    )

    try:
        print("\n1. Starting server...")
        transport.start()
        time.sleep(2)
        print("   Server started!")

        client = MCPClient(transport, default_timeout=60.0)

        print("\n2. Initialize...")
        init_result = client.initialize()
        server_name = init_result.get("serverInfo", {}).get("name", "unknown")
        print(f"   Server: {server_name}")

        print("\n3. List tools...")
        tools = client.list_tools()
        print(f"   Found {len(tools)} tools:")
        for tool in tools:
            print(f"   - {tool.get('name')}")

        print("\n4. Test create_entities...")
        create_result = client.call_tool("create_entities", {
            "entities": [
                {
                    "name": "DeepCode",
                    "entityType": "project",
                    "observations": ["AI coding assistant", "Python 3.8 compatible"]
                }
            ]
        })
        print(f"   Result: {create_result}")

        print("\n5. Test read_graph...")
        read_result = client.call_tool("read_graph", {})
        print(f"   Result: {read_result}")

        print("\n6. Shutdown...")
        client.shutdown()
        print("   Done!")

        print("\n✅ memory server test PASSED!")
        return True

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        transport.stop()


def test_fetch_server():
    """Test fetch MCP server."""
    print("\n" + "=" * 60)
    print("TEST 3: @modelcontextprotocol/server-fetch")
    print("=" * 60)

    transport = StdioTransport(
        command="npx",
        args=["-y", "mcp-fetch-server"],
    )

    try:
        print("\n1. Starting server...")
        transport.start()
        time.sleep(2)
        print("   Server started!")

        client = MCPClient(transport, default_timeout=60.0)

        print("\n2. Initialize...")
        init_result = client.initialize()
        server_name = init_result.get("serverInfo", {}).get("name", "unknown")
        print(f"   Server: {server_name}")

        print("\n3. List tools...")
        tools = client.list_tools()
        print(f"   Found {len(tools)} tools:")
        for tool in tools:
            print(f"   - {tool.get('name')}")

        print("\n4. Test fetch (httpbin.org)...")
        fetch_result = client.call_tool("fetch", {
            "url": "https://httpbin.org/get"
        })
        # Truncate long result
        result_str = str(fetch_result)
        if len(result_str) > 200:
            result_str = result_str[:200] + "..."
        print(f"   Result: {result_str}")

        print("\n5. Shutdown...")
        client.shutdown()
        print("   Done!")

        print("\n✅ fetch server test PASSED!")
        return True

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        transport.stop()


def main():
    """Run all tests."""
    print("=" * 60)
    print("DeepCode MCP External Server Tests")
    print("=" * 60)

    results = {}

    # Test 1: filesystem
    results["filesystem"] = test_filesystem_server()

    # Test 2: memory
    results["memory"] = test_memory_server()

    # Test 3: fetch
    results["fetch"] = test_fetch_server()

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {name}: {status}")

    all_passed = all(results.values())
    print("\n" + ("ALL TESTS PASSED!" if all_passed else "SOME TESTS FAILED"))
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
