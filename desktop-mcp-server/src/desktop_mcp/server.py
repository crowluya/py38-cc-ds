"""
MCP Server implementation for desktop automation.

Provides tools for screenshot, OCR, and input control via MCP protocol.
"""

import base64
import json
import sys
from typing import Dict, Any, List, Optional, Callable

from desktop_mcp.platform_base import get_platform, PlatformBase


class MCPServer:
    """
    MCP Server that exposes desktop automation tools.

    Communicates via stdio using JSON-RPC 2.0 protocol.
    """

    def __init__(self, platform: Optional[PlatformBase] = None):
        """
        Initialize MCP server.

        Args:
            platform: Platform implementation. Auto-detected if None.
        """
        self._platform = platform
        self._tools = self._register_tools()
        self._initialized = False

    @property
    def platform(self) -> PlatformBase:
        """Lazy-load platform to avoid import errors during testing."""
        if self._platform is None:
            self._platform = get_platform()
        return self._platform

    def _register_tools(self) -> Dict[str, Dict[str, Any]]:
        """Register all available tools."""
        return {
            "screenshot": {
                "description": "Capture screenshot of screen or region. Returns base64 PNG.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer", "description": "X coordinate of region"},
                        "y": {"type": "integer", "description": "Y coordinate of region"},
                        "width": {"type": "integer", "description": "Width of region"},
                        "height": {"type": "integer", "description": "Height of region"}
                    }
                },
                "handler": self._tool_screenshot
            },
            "ocr_screen": {
                "description": "OCR the screen or region. Returns text with positions.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer", "description": "X coordinate of region"},
                        "y": {"type": "integer", "description": "Y coordinate of region"},
                        "width": {"type": "integer", "description": "Width of region"},
                        "height": {"type": "integer", "description": "Height of region"},
                        "lang": {"type": "string", "description": "OCR language (default: eng)", "default": "eng"}
                    }
                },
                "handler": self._tool_ocr_screen
            },
            "find_text": {
                "description": "Find text on screen and return center coordinates.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Text to find"},
                        "x": {"type": "integer", "description": "X coordinate of search region"},
                        "y": {"type": "integer", "description": "Y coordinate of search region"},
                        "width": {"type": "integer", "description": "Width of search region"},
                        "height": {"type": "integer", "description": "Height of search region"},
                        "lang": {"type": "string", "description": "OCR language (default: eng)", "default": "eng"}
                    },
                    "required": ["text"]
                },
                "handler": self._tool_find_text
            },
            "click": {
                "description": "Click at coordinates.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer", "description": "X coordinate"},
                        "y": {"type": "integer", "description": "Y coordinate"},
                        "button": {"type": "string", "enum": ["left", "right", "middle"], "default": "left"}
                    },
                    "required": ["x", "y"]
                },
                "handler": self._tool_click
            },
            "double_click": {
                "description": "Double click at coordinates.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer", "description": "X coordinate"},
                        "y": {"type": "integer", "description": "Y coordinate"}
                    },
                    "required": ["x", "y"]
                },
                "handler": self._tool_double_click
            },
            "right_click": {
                "description": "Right click at coordinates.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer", "description": "X coordinate"},
                        "y": {"type": "integer", "description": "Y coordinate"}
                    },
                    "required": ["x", "y"]
                },
                "handler": self._tool_right_click
            },
            "move_mouse": {
                "description": "Move mouse to coordinates.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer", "description": "X coordinate"},
                        "y": {"type": "integer", "description": "Y coordinate"}
                    },
                    "required": ["x", "y"]
                },
                "handler": self._tool_move_mouse
            },
            "drag": {
                "description": "Drag from start to end coordinates.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "start_x": {"type": "integer", "description": "Start X coordinate"},
                        "start_y": {"type": "integer", "description": "Start Y coordinate"},
                        "end_x": {"type": "integer", "description": "End X coordinate"},
                        "end_y": {"type": "integer", "description": "End Y coordinate"},
                        "duration": {"type": "number", "description": "Drag duration in seconds", "default": 0.5}
                    },
                    "required": ["start_x", "start_y", "end_x", "end_y"]
                },
                "handler": self._tool_drag
            },
            "type_text": {
                "description": "Type text string.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Text to type"},
                        "interval": {"type": "number", "description": "Delay between keystrokes", "default": 0.0}
                    },
                    "required": ["text"]
                },
                "handler": self._tool_type_text
            },
            "hotkey": {
                "description": "Press keyboard shortcut (e.g., ctrl+c, cmd+v).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "keys": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Key names (e.g., ['ctrl', 'c'])"
                        }
                    },
                    "required": ["keys"]
                },
                "handler": self._tool_hotkey
            },
            "scroll": {
                "description": "Scroll mouse wheel.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "clicks": {"type": "integer", "description": "Scroll clicks (positive=up, negative=down)"},
                        "x": {"type": "integer", "description": "X coordinate to scroll at"},
                        "y": {"type": "integer", "description": "Y coordinate to scroll at"}
                    },
                    "required": ["clicks"]
                },
                "handler": self._tool_scroll
            },
            "get_screen_size": {
                "description": "Get screen dimensions.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                },
                "handler": self._tool_get_screen_size
            },
            "get_mouse_position": {
                "description": "Get current mouse position.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                },
                "handler": self._tool_get_mouse_position
            }
        }

    # Tool handlers
    def _tool_screenshot(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle screenshot tool."""
        region = None
        if all(k in args for k in ("x", "y", "width", "height")):
            region = (args["x"], args["y"], args["width"], args["height"])

        img_bytes = self.platform.screenshot(region)
        img_base64 = base64.b64encode(img_bytes).decode("utf-8")

        return {
            "type": "image",
            "data": img_base64,
            "mimeType": "image/png"
        }

    def _tool_ocr_screen(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle OCR tool."""
        region = None
        if all(k in args for k in ("x", "y", "width", "height")):
            region = (args["x"], args["y"], args["width"], args["height"])

        lang = args.get("lang", "eng")
        results = self.platform.ocr(region=region, lang=lang)

        return {
            "results": results,
            "count": len(results)
        }

    def _tool_find_text(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle find_text tool."""
        text = args["text"]
        region = None
        if all(k in args for k in ("x", "y", "width", "height")):
            region = (args["x"], args["y"], args["width"], args["height"])

        lang = args.get("lang", "eng")
        result = self.platform.find_text(text, region=region, lang=lang)

        if result:
            return {"found": True, "x": result[0], "y": result[1]}
        else:
            return {"found": False, "x": None, "y": None}

    def _tool_click(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle click tool."""
        self.platform.click(args["x"], args["y"], args.get("button", "left"))
        return {"success": True}

    def _tool_double_click(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle double_click tool."""
        self.platform.double_click(args["x"], args["y"])
        return {"success": True}

    def _tool_right_click(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle right_click tool."""
        self.platform.click(args["x"], args["y"], "right")
        return {"success": True}

    def _tool_move_mouse(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle move_mouse tool."""
        self.platform.move_mouse(args["x"], args["y"])
        return {"success": True}

    def _tool_drag(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle drag tool."""
        self.platform.drag(
            args["start_x"],
            args["start_y"],
            args["end_x"],
            args["end_y"],
            args.get("duration", 0.5)
        )
        return {"success": True}

    def _tool_type_text(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle type_text tool."""
        self.platform.type_text(args["text"], args.get("interval", 0.0))
        return {"success": True}

    def _tool_hotkey(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle hotkey tool."""
        self.platform.hotkey(*args["keys"])
        return {"success": True}

    def _tool_scroll(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle scroll tool."""
        self.platform.scroll(
            args["clicks"],
            args.get("x"),
            args.get("y")
        )
        return {"success": True}

    def _tool_get_screen_size(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get_screen_size tool."""
        width, height = self.platform.get_screen_size()
        return {"width": width, "height": height}

    def _tool_get_mouse_position(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get_mouse_position tool."""
        x, y = self.platform.get_mouse_position()
        return {"x": x, "y": y}

    # MCP Protocol handlers
    def handle_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Handle incoming MCP message.

        Args:
            message: JSON-RPC 2.0 message.

        Returns:
            Response message or None for notifications.
        """
        method = message.get("method", "")
        msg_id = message.get("id")
        params = message.get("params", {})

        # Handle different methods
        if method == "initialize":
            return self._handle_initialize(msg_id, params)
        elif method == "initialized":
            return None  # Notification, no response
        elif method == "tools/list":
            return self._handle_tools_list(msg_id)
        elif method == "tools/call":
            return self._handle_tools_call(msg_id, params)
        elif method == "ping":
            return self._make_response(msg_id, {})
        else:
            return self._make_error(msg_id, -32601, f"Method not found: {method}")

    def _handle_initialize(self, msg_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request."""
        self._initialized = True
        return self._make_response(msg_id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "desktop-mcp-server",
                "version": "0.1.0"
            }
        })

    def _handle_tools_list(self, msg_id: Any) -> Dict[str, Any]:
        """Handle tools/list request."""
        tools = []
        for name, tool in self._tools.items():
            tools.append({
                "name": name,
                "description": tool["description"],
                "inputSchema": tool["inputSchema"]
            })
        return self._make_response(msg_id, {"tools": tools})

    def _handle_tools_call(self, msg_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request."""
        tool_name = params.get("name", "")
        tool_args = params.get("arguments", {})

        if tool_name not in self._tools:
            return self._make_error(msg_id, -32602, f"Unknown tool: {tool_name}")

        try:
            handler = self._tools[tool_name]["handler"]
            result = handler(tool_args)
            return self._make_response(msg_id, {
                "content": [
                    {"type": "text", "text": json.dumps(result, ensure_ascii=False)}
                ]
            })
        except Exception as e:
            return self._make_response(msg_id, {
                "content": [
                    {"type": "text", "text": json.dumps({"error": str(e)})}
                ],
                "isError": True
            })

    def _make_response(self, msg_id: Any, result: Any) -> Dict[str, Any]:
        """Create JSON-RPC response."""
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": result
        }

    def _make_error(self, msg_id: Any, code: int, message: str) -> Dict[str, Any]:
        """Create JSON-RPC error response."""
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {
                "code": code,
                "message": message
            }
        }


def run_server():
    """Run MCP server on stdio."""
    server = MCPServer()

    # Read from stdin, write to stdout
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            message = json.loads(line)
            response = server.handle_message(message)
            if response:
                print(json.dumps(response), flush=True)
        except json.JSONDecodeError:
            error = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": "Parse error"
                }
            }
            print(json.dumps(error), flush=True)
