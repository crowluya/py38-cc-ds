"""
Read tool for Claude Code Python MVP

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)
"""

import base64
import mimetypes
from pathlib import Path
from typing import Any, Dict, List, Optional

from claude_code.core.tools.base import (
    Tool,
    ToolCategory,
    ToolParameter,
    ToolResult,
    ToolError,
)


class ReadTool(Tool):
    """
    Tool for reading file contents.

    Supports:
    - Text files with line number display
    - Binary files (returns base64)
    - Image files (returns base64 with mime type)
    - Line range selection (offset/limit)
    - Path security checks
    """

    def __init__(self, project_root: Optional[str] = None):
        """
        Initialize Read tool.

        Args:
            project_root: Optional project root for path security checks
        """
        self._project_root = project_root

    @property
    def name(self) -> str:
        return "Read"

    @property
    def description(self) -> str:
        return (
            "Reads a file from the local filesystem. "
            "Returns file contents with line numbers for text files. "
            "For images and binary files, returns base64 encoded content."
        )

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FILE

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="file_path",
                type="string",
                description="The absolute path to the file to read",
                required=True,
            ),
            ToolParameter(
                name="offset",
                type="integer",
                description="The line number to start reading from (1-based). Only for text files.",
                required=False,
                default=1,
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description="The number of lines to read. Only for text files.",
                required=False,
                default=2000,
            ),
        ]

    @property
    def requires_permission(self) -> bool:
        return True

    @property
    def is_dangerous(self) -> bool:
        return False

    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """
        Execute the read operation.

        Args:
            arguments: Tool arguments containing file_path, offset, limit

        Returns:
            ToolResult with file contents or error
        """
        self.validate_arguments(arguments)

        file_path = arguments["file_path"]
        offset = arguments.get("offset", 1)
        limit = arguments.get("limit", 2000)

        # Validate offset and limit
        if offset < 1:
            offset = 1
        if limit < 1:
            limit = 1
        if limit > 10000:
            limit = 10000  # Cap at 10000 lines

        try:
            path = Path(file_path)

            # Check if file exists
            if not path.exists():
                return ToolResult.error_result(
                    self.name,
                    f"File not found: {file_path}",
                )

            # Check if it's a file (not directory)
            if not path.is_file():
                return ToolResult.error_result(
                    self.name,
                    f"Not a file: {file_path}",
                )

            # Security check: prevent path traversal
            if self._project_root:
                try:
                    resolved = path.resolve()
                    root = Path(self._project_root).resolve()
                    resolved.relative_to(root)
                except ValueError:
                    return ToolResult.error_result(
                        self.name,
                        f"Path escapes project root: {file_path}",
                    )

            # Determine file type
            mime_type, _ = mimetypes.guess_type(str(path))

            # Check if it's an image
            if mime_type and mime_type.startswith("image/"):
                return self._read_image(path, mime_type)

            # Check if it's a binary file
            if self._is_binary(path):
                return self._read_binary(path)

            # Read as text file
            return self._read_text(path, offset, limit)

        except PermissionError:
            return ToolResult.error_result(
                self.name,
                f"Permission denied: {file_path}",
            )
        except Exception as e:
            return ToolResult.error_result(
                self.name,
                f"Error reading file: {str(e)}",
            )

    def _read_text(self, path: Path, offset: int, limit: int) -> ToolResult:
        """Read text file with line numbers."""
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Try with latin-1 as fallback
            try:
                content = path.read_text(encoding="latin-1")
            except Exception:
                return self._read_binary(path)

        lines = content.splitlines()
        total_lines = len(lines)

        # Apply offset and limit (1-based indexing)
        start_idx = offset - 1
        end_idx = start_idx + limit

        if start_idx >= total_lines:
            return ToolResult.success_result(
                self.name,
                f"(File has {total_lines} lines, offset {offset} is beyond end)",
                metadata={"total_lines": total_lines, "file_path": str(path)},
            )

        selected_lines = lines[start_idx:end_idx]

        # Format with line numbers (cat -n style)
        formatted_lines = []
        for i, line in enumerate(selected_lines, start=offset):
            # Truncate long lines
            if len(line) > 2000:
                line = line[:2000] + "... (truncated)"
            formatted_lines.append(f"{i:6d}\t{line}")

        output = "\n".join(formatted_lines)

        # Add truncation notice if needed
        if end_idx < total_lines:
            remaining = total_lines - end_idx
            output += f"\n\n... ({remaining} more lines)"

        return ToolResult.success_result(
            self.name,
            output,
            metadata={
                "total_lines": total_lines,
                "shown_lines": len(selected_lines),
                "offset": offset,
                "limit": limit,
                "file_path": str(path),
            },
        )

    def _read_image(self, path: Path, mime_type: str) -> ToolResult:
        """Read image file as base64."""
        try:
            data = path.read_bytes()
            b64 = base64.b64encode(data).decode("ascii")

            return ToolResult.success_result(
                self.name,
                f"[Image: {mime_type}, {len(data)} bytes]\ndata:{mime_type};base64,{b64[:100]}...",
                metadata={
                    "type": "image",
                    "mime_type": mime_type,
                    "size": len(data),
                    "base64": b64,
                    "file_path": str(path),
                },
            )
        except Exception as e:
            return ToolResult.error_result(
                self.name,
                f"Error reading image: {str(e)}",
            )

    def _read_binary(self, path: Path) -> ToolResult:
        """Read binary file as base64."""
        try:
            data = path.read_bytes()
            b64 = base64.b64encode(data).decode("ascii")

            return ToolResult.success_result(
                self.name,
                f"[Binary file: {len(data)} bytes]\nbase64:{b64[:100]}...",
                metadata={
                    "type": "binary",
                    "size": len(data),
                    "base64": b64,
                    "file_path": str(path),
                },
            )
        except Exception as e:
            return ToolResult.error_result(
                self.name,
                f"Error reading binary file: {str(e)}",
            )

    def _is_binary(self, path: Path, sample_size: int = 8192) -> bool:
        """
        Check if file is binary by looking for null bytes.

        Args:
            path: File path
            sample_size: Number of bytes to sample

        Returns:
            True if file appears to be binary
        """
        try:
            with open(path, "rb") as f:
                chunk = f.read(sample_size)
                # Check for null bytes (common in binary files)
                if b"\x00" in chunk:
                    return True
                # Check for high ratio of non-text bytes
                text_chars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)) - {0x7f})
                non_text = sum(1 for byte in chunk if byte not in text_chars)
                if len(chunk) > 0 and non_text / len(chunk) > 0.3:
                    return True
            return False
        except Exception:
            return False
