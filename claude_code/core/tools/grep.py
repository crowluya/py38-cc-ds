"""
Grep tool for Claude Code Python MVP

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from claude_code.core.tools.base import (
    Tool,
    ToolCategory,
    ToolParameter,
    ToolResult,
)


class GrepTool(Tool):
    """
    Tool for content search using regular expressions.

    Supports:
    - Regex pattern matching
    - Case insensitive search
    - Glob filter for file types
    - Context lines (before/after)
    - Multiple output modes (content, files_with_matches, count)
    - Path security checks
    """

    # Default limit on results
    DEFAULT_LIMIT = 100
    # Maximum limit
    MAX_LIMIT = 1000

    def __init__(self, project_root: Optional[str] = None):
        """
        Initialize Grep tool.

        Args:
            project_root: Optional project root for path security checks
        """
        self._project_root = project_root

    @property
    def name(self) -> str:
        return "Grep"

    @property
    def description(self) -> str:
        return (
            "A powerful search tool for content search using regular expressions. "
            "Supports regex patterns, file type filtering, and context lines. "
            "Output modes: 'content' shows matching lines, 'files_with_matches' shows file paths, 'count' shows match counts."
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
                description="The regular expression pattern to search for",
                required=True,
            ),
            ToolParameter(
                name="path",
                type="string",
                description="File or directory to search in. Defaults to current working directory.",
                required=False,
            ),
            ToolParameter(
                name="glob",
                type="string",
                description="Glob pattern to filter files (e.g., '*.py', '*.{ts,tsx}')",
                required=False,
            ),
            ToolParameter(
                name="case_insensitive",
                type="boolean",
                description="Case insensitive search (default: False)",
                required=False,
                default=False,
            ),
            ToolParameter(
                name="output_mode",
                type="string",
                description="Output mode: 'content', 'files_with_matches', or 'count' (default: 'files_with_matches')",
                required=False,
                default="files_with_matches",
            ),
            ToolParameter(
                name="context_before",
                type="integer",
                description="Number of lines to show before each match (for content mode)",
                required=False,
                default=0,
            ),
            ToolParameter(
                name="context_after",
                type="integer",
                description="Number of lines to show after each match (for content mode)",
                required=False,
                default=0,
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description=f"Maximum number of results (default: {GrepTool.DEFAULT_LIMIT}, max: {GrepTool.MAX_LIMIT})",
                required=False,
                default=GrepTool.DEFAULT_LIMIT,
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
        Execute the grep search.

        Args:
            arguments: Tool arguments

        Returns:
            ToolResult with search results or error
        """
        self.validate_arguments(arguments)

        pattern = arguments["pattern"]
        search_path = arguments.get("path", os.getcwd())
        glob_filter = arguments.get("glob")
        case_insensitive = arguments.get("case_insensitive", False)
        output_mode = arguments.get("output_mode", "files_with_matches")
        context_before = arguments.get("context_before", 0)
        context_after = arguments.get("context_after", 0)
        limit = arguments.get("limit", self.DEFAULT_LIMIT)

        # Validate pattern
        if not pattern:
            return ToolResult.error_result(
                self.name,
                "Pattern cannot be empty",
            )

        # Validate and compile regex
        try:
            flags = re.IGNORECASE if case_insensitive else 0
            regex = re.compile(pattern, flags)
        except re.error as e:
            return ToolResult.error_result(
                self.name,
                f"Invalid regex pattern: {str(e)}",
            )

        # Validate limit
        if limit is not None:
            if limit < 1:
                limit = self.DEFAULT_LIMIT
            elif limit > self.MAX_LIMIT:
                limit = self.MAX_LIMIT

        # Validate context
        context_before = max(0, context_before or 0)
        context_after = max(0, context_after or 0)

        try:
            path = Path(search_path)

            # Check if path exists
            if not path.exists():
                return ToolResult.error_result(
                    self.name,
                    f"Path not found: {search_path}",
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

            # Collect files to search
            if path.is_file():
                files = [path]
            else:
                files = self._collect_files(path, glob_filter)

            # Perform search
            results = self._search_files(
                files,
                regex,
                output_mode,
                context_before,
                context_after,
                limit,
                path,
            )

            # Format output based on mode
            return self._format_results(
                results,
                pattern,
                output_mode,
                str(path),
                limit,
            )

        except Exception as e:
            return ToolResult.error_result(
                self.name,
                f"Error during grep search: {str(e)}",
            )

    def _collect_files(
        self,
        path: Path,
        glob_filter: Optional[str],
    ) -> List[Path]:
        """
        Collect files to search.

        Args:
            path: Directory to search
            glob_filter: Optional glob pattern to filter files

        Returns:
            List of file paths
        """
        files = []

        if glob_filter:
            # Use glob pattern
            if "**" in glob_filter:
                iterator = path.rglob(glob_filter.replace("**/", "").replace("**", "*"))
            else:
                iterator = path.rglob(glob_filter)
        else:
            # Search all files recursively
            iterator = path.rglob("*")

        for file_path in iterator:
            # Skip directories
            if file_path.is_dir():
                continue

            # Skip hidden files and directories
            if file_path.name.startswith("."):
                continue
            try:
                rel_parts = file_path.relative_to(path).parts
                if any(part.startswith(".") for part in rel_parts[:-1]):
                    continue
            except ValueError:
                pass

            # Skip binary files (basic check)
            if self._is_likely_binary(file_path):
                continue

            files.append(file_path)

        return files

    def _is_likely_binary(self, path: Path) -> bool:
        """
        Check if file is likely binary.

        Args:
            path: File path

        Returns:
            True if likely binary
        """
        # Check by extension
        binary_extensions = {
            ".exe", ".dll", ".so", ".dylib", ".bin", ".obj", ".o",
            ".pyc", ".pyo", ".class", ".jar", ".war",
            ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
            ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp",
            ".mp3", ".mp4", ".avi", ".mov", ".mkv", ".wav", ".flac",
            ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
            ".db", ".sqlite", ".sqlite3",
        }
        if path.suffix.lower() in binary_extensions:
            return True

        return False

    def _search_files(
        self,
        files: List[Path],
        regex: re.Pattern,
        output_mode: str,
        context_before: int,
        context_after: int,
        limit: int,
        base_path: Path,
    ) -> List[Dict[str, Any]]:
        """
        Search files for pattern.

        Args:
            files: Files to search
            regex: Compiled regex pattern
            output_mode: Output mode
            context_before: Lines before match
            context_after: Lines after match
            limit: Maximum results
            base_path: Base path for relative paths

        Returns:
            List of match results
        """
        results = []
        total_matches = 0

        for file_path in files:
            if total_matches >= limit:
                break

            try:
                content = file_path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError, OSError):
                continue

            lines = content.splitlines()
            file_matches = []

            for line_num, line in enumerate(lines, 1):
                if regex.search(line):
                    match_info = {
                        "line_num": line_num,
                        "line": line,
                        "context_before": [],
                        "context_after": [],
                    }

                    # Add context if needed
                    if output_mode == "content":
                        # Before context
                        start = max(0, line_num - 1 - context_before)
                        match_info["context_before"] = [
                            (i + 1, lines[i])
                            for i in range(start, line_num - 1)
                        ]
                        # After context
                        end = min(len(lines), line_num + context_after)
                        match_info["context_after"] = [
                            (i + 1, lines[i])
                            for i in range(line_num, end)
                        ]

                    file_matches.append(match_info)
                    total_matches += 1

                    if total_matches >= limit:
                        break

            if file_matches:
                try:
                    rel_path = file_path.relative_to(base_path)
                except ValueError:
                    rel_path = file_path

                results.append({
                    "file": str(rel_path),
                    "abs_path": str(file_path),
                    "matches": file_matches,
                    "match_count": len(file_matches),
                })

        return results

    def _format_results(
        self,
        results: List[Dict[str, Any]],
        pattern: str,
        output_mode: str,
        search_path: str,
        limit: int,
    ) -> ToolResult:
        """
        Format search results based on output mode.

        Args:
            results: Search results
            pattern: Search pattern
            output_mode: Output mode
            search_path: Search path
            limit: Result limit

        Returns:
            Formatted ToolResult
        """
        total_matches = sum(r["match_count"] for r in results)
        total_files = len(results)

        if total_matches == 0:
            return ToolResult.success_result(
                self.name,
                f"No matches found for pattern: {pattern}",
                metadata={
                    "pattern": pattern,
                    "path": search_path,
                    "match_count": 0,
                    "file_count": 0,
                },
            )

        output_lines = []

        if output_mode == "count":
            output_lines.append(f"Found {total_matches} matches in {total_files} files")
            for r in results:
                output_lines.append(f"  {r['file']}: {r['match_count']}")

        elif output_mode == "files_with_matches":
            for r in results:
                output_lines.append(r["file"])

        else:  # content
            for r in results:
                output_lines.append(f"\n{r['file']}:")
                for match in r["matches"]:
                    # Show context before
                    for ctx_num, ctx_line in match["context_before"]:
                        output_lines.append(f"  {ctx_num}-  {ctx_line}")
                    # Show match
                    output_lines.append(f"  {match['line_num']}:  {match['line']}")
                    # Show context after
                    for ctx_num, ctx_line in match["context_after"]:
                        output_lines.append(f"  {ctx_num}-  {ctx_line}")

        output = "\n".join(output_lines)

        return ToolResult.success_result(
            self.name,
            output,
            metadata={
                "pattern": pattern,
                "path": search_path,
                "match_count": total_matches,
                "file_count": total_files,
                "output_mode": output_mode,
                "files": [r["file"] for r in results],
            },
        )
