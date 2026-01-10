"""
Glob tool for Claude Code Python MVP

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from claude_code.core.tools.base import (
    Tool,
    ToolCategory,
    ToolParameter,
    ToolResult,
)


class GlobTool(Tool):
    """
    Tool for file pattern matching search.

    Supports:
    - Glob patterns (*, **, ?, [])
    - Recursive search with **
    - Results sorted by modification time
    - Limit on number of results
    - Path security checks
    """

    # Default limit on results
    DEFAULT_LIMIT = 100
    # Maximum limit
    MAX_LIMIT = 1000

    def __init__(self, project_root: Optional[str] = None):
        """
        Initialize Glob tool.

        Args:
            project_root: Optional project root for path security checks
        """
        self._project_root = project_root

    @property
    def name(self) -> str:
        return "Glob"

    @property
    def description(self) -> str:
        return (
            "Fast file pattern matching tool that works with any codebase size. "
            "Supports glob patterns like '**/*.py' or 'src/**/*.ts'. "
            "Returns matching file paths sorted by modification time."
        )

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.SEARCH

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="pattern",
                type="string",
                description="The glob pattern to match files against (e.g., '**/*.py', '*.txt')",
                required=True,
            ),
            ToolParameter(
                name="path",
                type="string",
                description="The directory to search in. Defaults to current working directory.",
                required=False,
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description=f"Maximum number of results to return (default: {GlobTool.DEFAULT_LIMIT}, max: {GlobTool.MAX_LIMIT})",
                required=False,
                default=GlobTool.DEFAULT_LIMIT,
            ),
        ]

    @property
    def requires_permission(self) -> bool:
        return True

    @property
    def is_dangerous(self) -> bool:
        return False  # Read-only operation

    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """
        Execute the glob search.

        Args:
            arguments: Tool arguments containing pattern, path, limit

        Returns:
            ToolResult with matching file paths or error
        """
        self.validate_arguments(arguments)

        pattern = arguments["pattern"]
        search_path = arguments.get("path", os.getcwd())
        limit = arguments.get("limit", self.DEFAULT_LIMIT)

        # Validate pattern
        if not pattern or not pattern.strip():
            return ToolResult.error_result(
                self.name,
                "Pattern cannot be empty",
            )

        # Validate limit
        if limit is not None:
            if limit < 1:
                limit = self.DEFAULT_LIMIT
            elif limit > self.MAX_LIMIT:
                limit = self.MAX_LIMIT

        try:
            path = Path(search_path)

            # Check if path exists
            if not path.exists():
                return ToolResult.error_result(
                    self.name,
                    f"Path not found: {search_path}",
                )

            # Check if path is a directory
            if not path.is_dir():
                return ToolResult.error_result(
                    self.name,
                    f"Not a directory: {search_path}",
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
                        f"Path escapes project root: {search_path}",
                    )

            # Perform glob search
            matches = self._glob_search(path, pattern, limit)

            # Build output
            if not matches:
                return ToolResult.success_result(
                    self.name,
                    f"No matches found for pattern: {pattern}",
                    metadata={
                        "pattern": pattern,
                        "path": str(path),
                        "count": 0,
                        "truncated": False,
                    },
                )

            # Format output
            output_lines = []
            truncated = len(matches) >= limit

            for file_path, mtime in matches:
                # Show relative path if within search path
                try:
                    rel_path = file_path.relative_to(path)
                    output_lines.append(str(rel_path))
                except ValueError:
                    output_lines.append(str(file_path))

            output = "\n".join(output_lines)

            if truncated:
                output += f"\n\n... (showing first {limit} matches, more may exist)"

            return ToolResult.success_result(
                self.name,
                output,
                metadata={
                    "pattern": pattern,
                    "path": str(path),
                    "count": len(matches),
                    "truncated": truncated,
                    "files": [str(f) for f, _ in matches],
                },
            )

        except Exception as e:
            return ToolResult.error_result(
                self.name,
                f"Error during glob search: {str(e)}",
            )

    def _glob_search(
        self,
        path: Path,
        pattern: str,
        limit: int,
    ) -> List[tuple]:
        """
        Perform glob search and return matches sorted by mtime.

        Args:
            path: Directory to search in
            pattern: Glob pattern
            limit: Maximum number of results

        Returns:
            List of (Path, mtime) tuples sorted by mtime (newest first)
        """
        matches = []

        # Use rglob for recursive patterns, glob for non-recursive
        if "**" in pattern:
            iterator = path.rglob(pattern.replace("**/", "").replace("**", "*"))
        else:
            iterator = path.glob(pattern)

        for match in iterator:
            # Skip directories
            if match.is_dir():
                continue

            # Skip hidden files (starting with .)
            if match.name.startswith("."):
                continue

            # Skip hidden directories in path
            try:
                rel_parts = match.relative_to(path).parts
                if any(part.startswith(".") for part in rel_parts[:-1]):
                    continue
            except ValueError:
                pass

            try:
                mtime = match.stat().st_mtime
                matches.append((match, mtime))
            except (OSError, PermissionError):
                # Skip files we can't stat
                continue

            # Early exit if we have enough matches (with buffer for sorting)
            if len(matches) >= limit * 2:
                break

        # Sort by mtime (newest first)
        matches.sort(key=lambda x: x[1], reverse=True)

        # Apply limit
        return matches[:limit]
