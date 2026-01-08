"""
Directory Loader - Git-aware directory scanning

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)

Scans directories with:
- .gitignore awareness
- Common noise directory filtering (.git, node_modules, __pycache__, etc.)
- Recursive directory traversal
- Directory tree structure generation
"""

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set


@dataclass
class DirectoryEntry:
    """Entry in a directory scan."""

    path: str
    is_file: bool
    is_directory: bool
    size: int = 0

    def __str__(self) -> str:
        if self.is_file:
            return f"{self.path} ({self.size} bytes)"
        return f"{self.path}/"


class GitignoreParser:
    """
    Parser for .gitignore files.

    Supports:
    - Simple patterns (*.log, temp/)
    - Wildcards (*, ?, [])
    - Negation (!pattern)
    - Directory patterns (ending with /)
    """

    # Default noise patterns (always filtered)
    DEFAULT_IGNORE_PATTERNS = [
        ".git",
        ".gitignore",
        ".gitmodules",
        "__pycache__",
        "*.pyc",
        "*.pyo",
        "*.pyd",
        ".pytest_cache",
        ".mypy_cache",
        ".DS_Store",
        "Thumbs.db",
        "node_modules",
        ".venv",
        "venv",
        ".virtualenv",
        "dist",
        "build",
        "*.egg-info",
        ".tox",
        ".coverage",
        "htmlcov",
        "*.log",
    ]

    def __init__(self) -> None:
        """Initialize parser with default ignores."""
        self._patterns: List[str] = list(self.DEFAULT_IGNORE_PATTERNS)
        self._negations: List[str] = []

    def parse_gitignore(self, content: str) -> None:
        """
        Parse .gitignore file content.

        Args:
            content: The text content of .gitignore file
        """
        for line in content.splitlines():
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Handle negation
            if line.startswith("!"):
                self._negations.append(line[1:])
            else:
                self._patterns.append(line)

    def is_ignored(self, path: str, is_directory: bool) -> bool:
        """
        Check if a path should be ignored.

        Args:
            path: Relative path to check (using forward slashes)
            is_directory: Whether the path is a directory

        Returns:
            True if path should be ignored
        """
        # Normalize path to use forward slashes
        normalized_path = path.replace("\\", "/")

        # Check negations first (they override)
        for negation in self._negations:
            if self._match_pattern(negation, normalized_path, is_directory):
                return False

        # Check ignore patterns
        for pattern in self._patterns:
            if self._match_pattern(pattern, normalized_path, is_directory):
                return True

        return False

    def _match_pattern(self, pattern: str, path: str, is_directory: bool) -> bool:
        """
        Match a gitignore pattern against a path.

        Args:
            pattern: Gitignore pattern
            path: Path to check (normalized with forward slashes)
            is_directory: Whether path is a directory

        Returns:
            True if pattern matches
        """
        # Handle directory-only patterns (ending with /)
        if pattern.endswith("/"):
            if not is_directory:
                return False
            pattern = pattern[:-1]

        # Split path into parts
        path_parts = path.split("/")

        # Simple filename pattern (no slash in pattern)
        if "/" not in pattern:
            # Match against any path component
            for part in path_parts:
                if self._wildcard_match(pattern, part):
                    return True
            return False

        # Pattern with slash
        if pattern.startswith("/"):
            # Anchored to root - match from start
            return self._wildcard_match(pattern[1:], path) or self._wildcard_match(
                pattern[1:], "/".join(path_parts)
            )
        else:
            # Match anywhere in path
            # Try matching from different starting points
            for i in range(len(path_parts)):
                subpath = "/".join(path_parts[i:])
                if self._wildcard_match(pattern, subpath):
                    return True

            return False

    def _wildcard_match(self, pattern: str, text: str) -> bool:
        """
        Simple wildcard matching (* and ?).

        Args:
            pattern: Pattern with wildcards
            text: Text to match

        Returns:
            True if text matches pattern
        """
        # Convert glob pattern to regex
        # Escape special regex characters except * and ?
        regex = re.escape(pattern)
        # Replace escaped wildcards with regex equivalents
        regex = regex.replace(r"\*", ".*")
        regex = regex.replace(r"\?", ".")

        # Add anchors
        regex = f"^{regex}$"

        return re.match(regex, text) is not None


class DirectoryLoader:
    """
    Git-aware directory scanner.

    Filters out:
    - Patterns from .gitignore files
    - Common noise directories
    - Nested .gitignore patterns
    """

    def __init__(self) -> None:
        """Initialize directory loader."""
        self._gitignore_cache: Dict[str, GitignoreParser] = {}

    def list_directory(
        self,
        path: str,
        recursive: bool = False,
        base_path: Optional[str] = None,
        gitignore: Optional[GitignoreParser] = None,
    ) -> List[DirectoryEntry]:
        """
        List directory contents with filtering.

        Args:
            path: Directory path to scan
            recursive: Whether to scan recursively
            base_path: Base path for .gitignore resolution
            gitignore: Gitignore parser (created if not provided)

        Returns:
            List of DirectoryEntry objects

        Raises:
            FileNotFoundError: If path doesn't exist
            NotADirectoryError: If path is not a directory
        """
        dir_path = Path(path).resolve()

        if not dir_path.exists():
            raise FileNotFoundError(f"Directory not found: {path}")

        if not dir_path.is_dir():
            raise NotADirectoryError(f"Not a directory: {path}")

        # Initialize gitignore parser
        if gitignore is None:
            gitignore = self._get_gitignore_for_path(path)
            base = base_path or str(dir_path)
        else:
            base = base_path or str(dir_path)

        entries: List[DirectoryEntry] = []

        try:
            for item in dir_path.iterdir():
                entry = self._process_item(
                    item,
                    base,
                    gitignore,
                    recursive,
                )
                if entry:
                    entries.append(entry)

                    # Recurse into subdirectories
                    if recursive and entry.is_directory:
                        # Don't include the directory entry itself when recursing,
                        # only include the files found within it
                        entries.pop()  # Remove the directory entry we just added

                        # Load nested .gitignore if it exists
                        nested_gitignore_path = item / ".gitignore"
                        if nested_gitignore_path.exists():
                            try:
                                content = nested_gitignore_path.read_text(encoding="utf-8")
                                gitignore.parse_gitignore(content)
                            except (OSError, UnicodeDecodeError):
                                pass

                        sub_entries = self.list_directory(
                            str(item),
                            recursive=True,
                            base_path=base,
                            gitignore=gitignore,
                        )
                        entries.extend(sub_entries)

        except PermissionError:
            # Skip directories we can't read
            pass

        return entries

    def _process_item(
        self,
        item: Path,
        base_path: str,
        gitignore: GitignoreParser,
        recursive: bool,
    ) -> Optional[DirectoryEntry]:
        """Process a single filesystem item."""
        try:
            is_dir = item.is_dir()
            is_file = item.is_file()

            # Get relative path from base
            try:
                rel_path = item.relative_to(base_path)
            except ValueError:
                # Item is outside base path, use name only
                rel_path = item.name

            rel_path_str = str(rel_path).replace("\\", "/")

            # Check if ignored
            if gitignore.is_ignored(rel_path_str, is_dir):
                return None

            # Create entry
            size = 0
            if is_file:
                try:
                    size = item.stat().st_size
                except (OSError, PermissionError):
                    size = 0

            return DirectoryEntry(
                path=str(item),
                is_file=is_file,
                is_directory=is_dir,
                size=size,
            )

        except (PermissionError, OSError):
            # Skip items we can't access
            return None

    def _get_gitignore_for_path(self, path: str) -> GitignoreParser:
        """
        Get or create gitignore parser for a path.

        Args:
            path: Directory path

        Returns:
            GitignoreParser with patterns loaded
        """
        abs_path = str(Path(path).resolve())

        if abs_path not in self._gitignore_cache:
            parser = GitignoreParser()
            self._load_gitignore_for_path(abs_path, parser)
            self._gitignore_cache[abs_path] = parser

        return self._gitignore_cache[abs_path]

    def _load_gitignore_for_path(self, path: str, gitignore: GitignoreParser) -> None:
        """
        Load .gitignore files for a path.

        Args:
            path: Directory path
            gitignore: Gitignore parser to populate
        """
        base = Path(path).resolve()

        # Load .gitignore from base path
        gitignore_path = base / ".gitignore"
        if gitignore_path.exists() and gitignore_path.is_file():
            try:
                content = gitignore_path.read_text(encoding="utf-8")
                gitignore.parse_gitignore(content)
            except (OSError, UnicodeDecodeError):
                pass

        # Also check parent directories for repo-wide .gitignore
        parent = base.parent
        while parent != parent.parent:  # Stop at filesystem root
            parent_gitignore = parent / ".gitignore"
            if parent_gitignore.exists() and parent_gitignore.is_file():
                try:
                    content = parent_gitignore.read_text(encoding="utf-8")
                    # Add patterns to beginning (less specific)
                    for line in reversed(content.splitlines()):
                        line = line.strip()
                        if line and not line.startswith("#") and not line.startswith("!"):
                            if line not in gitignore._patterns:
                                gitignore._patterns.insert(0, line)
                        elif line.startswith("!"):
                            if line[1:] not in gitignore._negations:
                                gitignore._negations.insert(0, line[1:])
                except (OSError, UnicodeDecodeError):
                    pass
            else:
                # Stop if we find .git directory (repo root)
                if (parent / ".git").exists():
                    break
            parent = parent.parent

    def get_directory_tree(self, path: str) -> Dict[str, any]:
        """
        Get directory tree structure.

        Args:
            path: Directory path to scan

        Returns:
            Nested dict representing directory structure (relative paths only)
        """
        dir_path = Path(path).resolve()
        entries = self.list_directory(path, recursive=True)

        tree: Dict[str, any] = {}

        for entry in entries:
            self._add_to_tree(tree, entry, dir_path)

        return tree

    def _add_to_tree(self, tree: Dict[str, any], entry: DirectoryEntry, base_path: Path) -> None:
        """
        Add entry to tree structure.

        Args:
            tree: Tree dict to modify
            entry: DirectoryEntry to add
            base_path: Base path for resolving relative paths
        """
        entry_path = Path(entry.path)

        # Get relative path parts
        try:
            rel = entry_path.relative_to(base_path)
        except ValueError:
            # Outside base path, use just the filename
            rel = entry_path

        parts = rel.parts

        current = tree
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                # Leaf node
                if entry.is_directory:
                    if part not in current:
                        current[part] = {}
                else:
                    current[part] = entry.size
            else:
                # Directory node
                if part not in current:
                    current[part] = {}
                current = current[part]  # type: ignore


def list_directory(path: str, recursive: bool = True) -> List[DirectoryEntry]:
    """
    Convenience function to list a directory.

    Args:
        path: Directory path to scan
        recursive: Whether to scan recursively

    Returns:
        List of DirectoryEntry objects
    """
    loader = DirectoryLoader()
    return loader.list_directory(path, recursive=recursive)
