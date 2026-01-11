"""
Tests for desktop-mcp-server.

These tests mock the platform dependencies to allow testing without
actual screen capture or input control.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List, Optional, Tuple

# Test the server without importing platform-specific modules
import sys
sys.modules['pyautogui'] = MagicMock()
sys.modules['pytesseract'] = MagicMock()
sys.modules['PIL'] = MagicMock()
sys.modules['PIL.Image'] = MagicMock()
sys.modules['PIL.ImageGrab'] = MagicMock()


class MockPlatform:
    """Mock platform for testing."""

    def __init__(self):
        self.screenshot_data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        self.ocr_results = [
            {"text": "Hello", "x": 10, "y": 20, "width": 50, "height": 15, "confidence": 95},
            {"text": "World", "x": 70, "y": 20, "width": 50, "height": 15, "confidence": 90}
        ]
        self.screen_size = (1920, 1080)
        self.mouse_position = (500, 300)
        self.clicks = []
        self.typed_text = []
        self.hotkeys = []
        self.scrolls = []
        self.moves = []
        self.drags = []

    def screenshot(self, region: Optional[Tuple[int, int, int, int]] = None) -> bytes:
        return self.screenshot_data

    def ocr(
        self,
        image_data: Optional[bytes] = None,
        region: Optional[Tuple[int, int, int, int]] = None,
        lang: str = "eng"
    ) -> List[Dict[str, Any]]:
        return self.ocr_results

    def find_text(
        self,
        text: str,
        region: Optional[Tuple[int, int, int, int]] = None,
        lang: str = "eng"
    ) -> Optional[Tuple[int, int]]:
        text_lower = text.lower()
        for item in self.ocr_results:
            if text_lower == item["text"].lower():
                return (item["x"] + item["width"] // 2, item["y"] + item["height"] // 2)
        return None

    def click(self, x: int, y: int, button: str = "left") -> None:
        self.clicks.append({"x": x, "y": y, "button": button, "type": "single"})

    def double_click(self, x: int, y: int) -> None:
        self.clicks.append({"x": x, "y": y, "button": "left", "type": "double"})

    def move_mouse(self, x: int, y: int) -> None:
        self.moves.append({"x": x, "y": y})
        self.mouse_position = (x, y)

    def drag(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration: float = 0.5
    ) -> None:
        self.drags.append({
            "start_x": start_x, "start_y": start_y,
            "end_x": end_x, "end_y": end_y,
            "duration": duration
        })

    def type_text(self, text: str, interval: float = 0.0) -> None:
        self.typed_text.append({"text": text, "interval": interval})

    def hotkey(self, *keys: str) -> None:
        self.hotkeys.append(list(keys))

    def scroll(self, clicks: int, x: Optional[int] = None, y: Optional[int] = None) -> None:
        self.scrolls.append({"clicks": clicks, "x": x, "y": y})

    def get_screen_size(self) -> Tuple[int, int]:
        return self.screen_size

    def get_mouse_position(self) -> Tuple[int, int]:
        return self.mouse_position


class TestMCPServer:
    """Test MCP server protocol handling."""

    @pytest.fixture
    def server(self):
        """Create server with mock platform."""
        from desktop_mcp.server import MCPServer
        mock_platform = MockPlatform()
        return MCPServer(platform=mock_platform), mock_platform

    def test_initialize(self, server):
        """Test initialize request."""
        srv, _ = server
        response = srv.handle_message({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"}
            }
        })

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        assert response["result"]["protocolVersion"] == "2024-11-05"
        assert "tools" in response["result"]["capabilities"]

    def test_initialized_notification(self, server):
        """Test initialized notification returns None."""
        srv, _ = server
        response = srv.handle_message({
            "jsonrpc": "2.0",
            "method": "initialized"
        })
        assert response is None

    def test_tools_list(self, server):
        """Test tools/list request."""
        srv, _ = server
        response = srv.handle_message({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list"
        })

        assert response["id"] == 2
        tools = response["result"]["tools"]
        tool_names = [t["name"] for t in tools]

        # Check all expected tools are present
        expected_tools = [
            "screenshot", "ocr_screen", "find_text",
            "click", "double_click", "right_click",
            "move_mouse", "drag", "type_text", "hotkey",
            "scroll", "get_screen_size", "get_mouse_position"
        ]
        for name in expected_tools:
            assert name in tool_names, f"Missing tool: {name}"

    def test_tool_screenshot(self, server):
        """Test screenshot tool."""
        srv, _ = server
        response = srv.handle_message({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "screenshot",
                "arguments": {}
            }
        })

        assert response["id"] == 3
        content = response["result"]["content"]
        assert len(content) == 1
        result = json.loads(content[0]["text"])
        assert result["type"] == "image"
        assert result["mimeType"] == "image/png"
        assert "data" in result

    def test_tool_screenshot_with_region(self, server):
        """Test screenshot tool with region."""
        srv, _ = server
        response = srv.handle_message({
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "screenshot",
                "arguments": {"x": 0, "y": 0, "width": 100, "height": 100}
            }
        })

        assert "result" in response
        result = json.loads(response["result"]["content"][0]["text"])
        assert result["type"] == "image"

    def test_tool_ocr_screen(self, server):
        """Test OCR tool."""
        srv, _ = server
        response = srv.handle_message({
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "ocr_screen",
                "arguments": {}
            }
        })

        result = json.loads(response["result"]["content"][0]["text"])
        assert result["count"] == 2
        assert len(result["results"]) == 2
        assert result["results"][0]["text"] == "Hello"

    def test_tool_find_text_found(self, server):
        """Test find_text tool when text is found."""
        srv, _ = server
        response = srv.handle_message({
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "find_text",
                "arguments": {"text": "Hello"}
            }
        })

        result = json.loads(response["result"]["content"][0]["text"])
        assert result["found"] is True
        assert result["x"] == 35  # 10 + 50/2
        assert result["y"] == 27  # 20 + 15/2

    def test_tool_find_text_not_found(self, server):
        """Test find_text tool when text is not found."""
        srv, _ = server
        response = srv.handle_message({
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {
                "name": "find_text",
                "arguments": {"text": "NotFound"}
            }
        })

        result = json.loads(response["result"]["content"][0]["text"])
        assert result["found"] is False

    def test_tool_click(self, server):
        """Test click tool."""
        srv, platform = server
        response = srv.handle_message({
            "jsonrpc": "2.0",
            "id": 8,
            "method": "tools/call",
            "params": {
                "name": "click",
                "arguments": {"x": 100, "y": 200}
            }
        })

        result = json.loads(response["result"]["content"][0]["text"])
        assert result["success"] is True
        assert len(platform.clicks) == 1
        assert platform.clicks[0] == {"x": 100, "y": 200, "button": "left", "type": "single"}

    def test_tool_double_click(self, server):
        """Test double_click tool."""
        srv, platform = server
        response = srv.handle_message({
            "jsonrpc": "2.0",
            "id": 9,
            "method": "tools/call",
            "params": {
                "name": "double_click",
                "arguments": {"x": 150, "y": 250}
            }
        })

        result = json.loads(response["result"]["content"][0]["text"])
        assert result["success"] is True
        assert platform.clicks[0]["type"] == "double"

    def test_tool_type_text(self, server):
        """Test type_text tool."""
        srv, platform = server
        response = srv.handle_message({
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {
                "name": "type_text",
                "arguments": {"text": "Hello World"}
            }
        })

        result = json.loads(response["result"]["content"][0]["text"])
        assert result["success"] is True
        assert platform.typed_text[0]["text"] == "Hello World"

    def test_tool_hotkey(self, server):
        """Test hotkey tool."""
        srv, platform = server
        response = srv.handle_message({
            "jsonrpc": "2.0",
            "id": 11,
            "method": "tools/call",
            "params": {
                "name": "hotkey",
                "arguments": {"keys": ["ctrl", "c"]}
            }
        })

        result = json.loads(response["result"]["content"][0]["text"])
        assert result["success"] is True
        assert platform.hotkeys[0] == ["ctrl", "c"]

    def test_tool_scroll(self, server):
        """Test scroll tool."""
        srv, platform = server
        response = srv.handle_message({
            "jsonrpc": "2.0",
            "id": 12,
            "method": "tools/call",
            "params": {
                "name": "scroll",
                "arguments": {"clicks": -3}
            }
        })

        result = json.loads(response["result"]["content"][0]["text"])
        assert result["success"] is True
        assert platform.scrolls[0]["clicks"] == -3

    def test_tool_get_screen_size(self, server):
        """Test get_screen_size tool."""
        srv, _ = server
        response = srv.handle_message({
            "jsonrpc": "2.0",
            "id": 13,
            "method": "tools/call",
            "params": {
                "name": "get_screen_size",
                "arguments": {}
            }
        })

        result = json.loads(response["result"]["content"][0]["text"])
        assert result["width"] == 1920
        assert result["height"] == 1080

    def test_tool_get_mouse_position(self, server):
        """Test get_mouse_position tool."""
        srv, _ = server
        response = srv.handle_message({
            "jsonrpc": "2.0",
            "id": 14,
            "method": "tools/call",
            "params": {
                "name": "get_mouse_position",
                "arguments": {}
            }
        })

        result = json.loads(response["result"]["content"][0]["text"])
        assert result["x"] == 500
        assert result["y"] == 300

    def test_tool_drag(self, server):
        """Test drag tool."""
        srv, platform = server
        response = srv.handle_message({
            "jsonrpc": "2.0",
            "id": 15,
            "method": "tools/call",
            "params": {
                "name": "drag",
                "arguments": {
                    "start_x": 100, "start_y": 100,
                    "end_x": 200, "end_y": 200
                }
            }
        })

        result = json.loads(response["result"]["content"][0]["text"])
        assert result["success"] is True
        assert platform.drags[0]["start_x"] == 100
        assert platform.drags[0]["end_x"] == 200

    def test_unknown_tool(self, server):
        """Test calling unknown tool."""
        srv, _ = server
        response = srv.handle_message({
            "jsonrpc": "2.0",
            "id": 16,
            "method": "tools/call",
            "params": {
                "name": "unknown_tool",
                "arguments": {}
            }
        })

        assert "error" in response
        assert response["error"]["code"] == -32602

    def test_unknown_method(self, server):
        """Test unknown method."""
        srv, _ = server
        response = srv.handle_message({
            "jsonrpc": "2.0",
            "id": 17,
            "method": "unknown/method"
        })

        assert "error" in response
        assert response["error"]["code"] == -32601

    def test_ping(self, server):
        """Test ping method."""
        srv, _ = server
        response = srv.handle_message({
            "jsonrpc": "2.0",
            "id": 18,
            "method": "ping"
        })

        assert response["id"] == 18
        assert response["result"] == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
