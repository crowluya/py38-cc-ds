"""
Edit tool for DeepCode

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


class EditTool(Tool):
    """
    Tool for editing file contents using string replacement.

    Supports:
    - Exact string replacement (old_string -> new_string)
    - Replace all occurrences with replace_all parameter
    - Uniqueness check (old_string must be unique unless replace_all)
    - Path security checks
    """

    def __init__(self, project_root: Optional[str] = None):
        """
        Initialize Edit tool.

        Args:
            project_root: Optional project root for path security checks
        """
        self._project_root = project_root

    @property
    def name(self) -> str:
        return "Edit"

    @property
    def description(self) -> str:
        return (
            "Performs exact string replacements in files. "
            "The old_string must be unique in the file unless replace_all is True. "
            "Use this for precise edits to existing files."
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
                description="The absolute path to the file to modify",
                required=True,
            ),
            ToolParameter(
                name="old_string",
                type="string",
                description="The text to replace (must be unique unless replace_all is True)",
                required=True,
            ),
            ToolParameter(
                name="new_string",
                type="string",
                description="The text to replace it with (must be different from old_string)",
                required=True,
            ),
            ToolParameter(
                name="replace_all",
                type="boolean",
                description="Replace all occurrences of old_string (default: False)",
                required=False,
                default=False,
            ),
        ]

    @property
    def requires_permission(self) -> bool:
        return True

    @property
    def is_dangerous(self) -> bool:
        return True  # Editing files is potentially dangerous

    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """
        Execute the edit operation.

        Args:
            arguments: Tool arguments containing file_path, old_string, new_string, replace_all

        Returns:
            ToolResult with success/error status
        """
        self.validate_arguments(arguments)

        file_path = arguments["file_path"]
        old_string = arguments["old_string"]
        new_string = arguments["new_string"]
        replace_all = arguments.get("replace_all", False)

        # Validate old_string is not empty
        if not old_string:
            return ToolResult.error_result(
                self.name,
                "old_string cannot be empty",
            )

        # Validate old_string != new_string
        if old_string == new_string:
            return ToolResult.error_result(
                self.name,
                "old_string and new_string must be different",
            )

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

            # Read file content
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                # Try with latin-1 as fallback
                try:
                    content = path.read_text(encoding="latin-1")
                except Exception as e:
                    return ToolResult.error_result(
                        self.name,
                        f"Cannot read file encoding: {str(e)}",
                    )

            # Count occurrences
            count = content.count(old_string)

            if count == 0:
                return ToolResult.error_result(
                    self.name,
                    f"old_string not found in file: {file_path}",
                )

            if count > 1 and not replace_all:
                return ToolResult.error_result(
                    self.name,
                    f"old_string is not unique in file (found {count} times). "
                    f"Use replace_all=True to replace all occurrences, "
                    f"or provide more context to make old_string unique.",
                )

            # Perform replacement
            if replace_all:
                new_content = content.replace(old_string, new_string)
                replacements = count
            else:
                new_content = content.replace(old_string, new_string, 1)
                replacements = 1

            # Write back
            path.write_text(new_content, encoding="utf-8")

            # Build success message
            if replacements == 1:
                msg = f"Replaced 1 occurrence in {file_path}"
            else:
                msg = f"Replaced {replacements} occurrences in {file_path}"

            return ToolResult.success_result(
                self.name,
                msg,
                metadata={
                    "file_path": str(path),
                    "replacements": replacements,
                    "old_string_length": len(old_string),
                    "new_string_length": len(new_string),
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
                f"OS error editing file: {str(e)}",
            )
        except Exception as e:
            return ToolResult.error_result(
                self.name,
                f"Error editing file: {str(e)}",
            )
