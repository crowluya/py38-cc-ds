"""
Write tool for DeepCode

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from deep_code.core.tools.base import (
    Tool,
    ToolCategory,
    ToolParameter,
    ToolResult,
)


class WriteTool(Tool):
    """
    Tool for writing file contents.

    Supports:
    - Creating new files
    - Overwriting existing files
    - Auto-creating parent directories
    - Path security checks
    """

    def __init__(self, project_root: Optional[str] = None):
        """
        Initialize Write tool.

        Args:
            project_root: Optional project root for path security checks
        """
        self._project_root = project_root

    @property
    def name(self) -> str:
        return "Write"

    @property
    def description(self) -> str:
        return (
            "Writes content to a file on the local filesystem. "
            "Creates parent directories if they don't exist. "
            "Will overwrite existing files."
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
                description="The absolute path to the file to write",
                required=True,
            ),
            ToolParameter(
                name="content",
                type="string",
                description="The content to write to the file",
                required=True,
            ),
        ]

    @property
    def requires_permission(self) -> bool:
        return True

    @property
    def is_dangerous(self) -> bool:
        return True  # Writing files is potentially dangerous

    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """
        Execute the write operation.

        Args:
            arguments: Tool arguments containing file_path and content

        Returns:
            ToolResult with success/error status
        """
        self.validate_arguments(arguments)

        file_path = arguments["file_path"]
        content = arguments["content"]

        try:
            path = Path(file_path)

            # Security check: prevent path traversal
            if self._project_root:
                try:
                    # Resolve the path (handles ..)
                    resolved = path.resolve()
                    root = Path(self._project_root).resolve()
                    resolved.relative_to(root)
                except ValueError:
                    return ToolResult.error_result(
                        self.name,
                        f"Path escapes project root: {file_path}",
                    )

            # Check if path is a directory
            if path.exists() and path.is_dir():
                return ToolResult.error_result(
                    self.name,
                    f"Cannot write to directory: {file_path}",
                )

            # Create parent directories if needed
            parent = path.parent
            if not parent.exists():
                parent.mkdir(parents=True, exist_ok=True)

            # Check if file exists (for reporting)
            existed = path.exists()

            # Write the file
            path.write_text(content, encoding="utf-8")

            # Build success message
            if existed:
                msg = f"Overwrote {file_path}"
            else:
                msg = f"Created {file_path}"

            # Count lines for metadata
            line_count = len(content.splitlines())

            return ToolResult.success_result(
                self.name,
                msg,
                metadata={
                    "file_path": str(path),
                    "bytes_written": len(content.encode("utf-8")),
                    "lines": line_count,
                    "created": not existed,
                    "overwritten": existed,
                },
            )

        except PermissionError:
            return ToolResult.error_result(
                self.name,
                f"Permission denied: {file_path}",
            )
        except OSError as e:
            return ToolResult.error_result(
                self.name,
                f"OS error writing file: {str(e)}",
            )
        except Exception as e:
            return ToolResult.error_result(
                self.name,
                f"Error writing file: {str(e)}",
            )
