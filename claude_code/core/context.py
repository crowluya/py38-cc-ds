"""
Context Formatter - File and directory context formatting

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)

Formats file content and directory trees for LLM context:
- File content with path identifier and line ranges
- Directory tree structures
- Content truncation for large files/directories
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from claude_code.interaction.directory_loader import DirectoryLoader, DirectoryEntry


@dataclass
class FileContext:
    """Formatted file context."""

    path: str
    content: str
    line_range: Optional[Tuple[int, int]] = None
    truncated: bool = False

    def format(self, show_line_numbers: bool = False) -> str:
        """
        Format file context as string.

        Args:
            show_line_numbers: Whether to prefix lines with numbers

        Returns:
            Formatted string representation
        """
        lines = []
        lines.append(f"# File: {self.path}")

        if self.line_range:
            lines.append(f"# Lines: {self.line_range[0]}-{self.line_range[1]}")

        if show_line_numbers and self.content:
            numbered_lines = []
            start_line = self.line_range[0] if self.line_range else 1
            for i, line in enumerate(self.content.split("\n")):
                numbered_lines.append(f"{start_line + i}: {line}")
            content_str = "\n".join(numbered_lines)
        else:
            content_str = self.content

        lines.append(content_str)

        if self.truncated:
            lines.append("# ... (content truncated)")

        return "\n".join(lines)

    def __str__(self) -> str:
        """String representation."""
        if self.line_range:
            return f"@{self.path}:{self.line_range[0]}-{self.line_range[1]}"
        return f"@{self.path}"


@dataclass
class DirectoryContext:
    """Formatted directory context."""

    path: str
    files: List[FileContext]
    truncated: bool = False

    def format(self, show_line_numbers: bool = False) -> str:
        """
        Format directory context as string.

        Args:
            show_line_numbers: Whether to show line numbers in files

        Returns:
            Formatted string representation
        """
        if not self.files:
            return f"# Empty directory: {self.path}"

        lines = [f"# Directory: {self.path}"]

        for file_ctx in self.files:
            lines.append(file_ctx.format(show_line_numbers))
            lines.append("")  # Blank line between files

        if self.truncated:
            lines.append("# ... (some files omitted)")

        return "\n".join(lines)

    def __str__(self) -> str:
        """String representation."""
        return f"@{self.path}/ ({len(self.files)} files)"


class ContextFormatter:
    """
    Formatter for file and directory contexts.

    Features:
    - File content loading with UTF-8 encoding
    - Line range extraction
    - Content truncation for large files
    - Directory scanning with gitignore awareness
    - File count limits for directories
    """

    DEFAULT_MAX_CONTENT_LENGTH = 10000  # characters
    DEFAULT_MAX_DIRECTORY_FILES = 100

    def __init__(
        self,
        max_content_length: int = DEFAULT_MAX_CONTENT_LENGTH,
        max_directory_files: int = DEFAULT_MAX_DIRECTORY_FILES,
    ) -> None:
        """
        Initialize context formatter.

        Args:
            max_content_length: Maximum characters for file content
            max_directory_files: Maximum files to include from directory
        """
        self._max_content_length = max_content_length
        self._max_directory_files = max_directory_files
        self._directory_loader = DirectoryLoader()

    def format_file(
        self,
        path: str,
        line_range: Optional[Tuple[int, int]] = None,
        show_line_numbers: bool = False,
    ) -> FileContext:
        """
        Format file as context.

        Args:
            path: File path
            line_range: Optional (start, end) line range (1-based, inclusive)
            show_line_numbers: Whether to include line numbers in output

        Returns:
            FileContext with formatted content

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        file_path = Path(path).resolve()

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        if not file_path.is_file():
            raise ValueError(f"Not a file: {path}")

        # Read file content
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Try with fallback encoding
            content = file_path.read_text(encoding="latin-1")

        # Apply line range if specified
        if line_range:
            lines = content.split("\n")
            start, end = line_range
            # Convert to 0-based indexing
            start_idx = max(0, start - 1)
            end_idx = min(len(lines), end)
            content = "\n".join(lines[start_idx:end_idx])

        # Truncate if necessary
        truncated = False
        if len(content) > self._max_content_length:
            content = content[: self._max_content_length]
            truncated = True

        return FileContext(
            path=str(file_path),
            content=content,
            line_range=line_range,
            truncated=truncated,
        )

    def format_directory(
        self,
        path: str,
        recursive: bool = True,
        include_content: bool = True,
    ) -> DirectoryContext:
        """
        Format directory as context.

        Args:
            path: Directory path
            recursive: Whether to scan recursively
            include_content: Whether to include file contents

        Returns:
            DirectoryContext with formatted files
        """
        dir_path = Path(path).resolve()

        if not dir_path.exists():
            raise FileNotFoundError(f"Directory not found: {path}")

        if not dir_path.is_dir():
            raise ValueError(f"Not a directory: {path}")

        # Scan directory
        entries = self._directory_loader.list_directory(
            path, recursive=recursive
        )

        # Limit number of files
        truncated = False
        if len(entries) > self._max_directory_files:
            entries = entries[: self._max_directory_files]
            truncated = True

        # Format files
        files: List[FileContext] = []
        for entry in entries:
            if entry.is_file and include_content:
                try:
                    file_ctx = self.format_file(str(entry.path))
                    files.append(file_ctx)
                except (OSError, UnicodeDecodeError):
                    # Skip files that can't be read
                    pass

        return DirectoryContext(
            path=str(dir_path),
            files=files,
            truncated=truncated,
        )


class ContextBuilder:
    """
    Builder for aggregating multiple context sources.

    Combines file and directory contexts into a single formatted string.
    """

    def __init__(self) -> None:
        """Initialize context builder."""
        self._contexts: List[object] = []

    def add_file(
        self,
        path: str,
        line_range: Optional[Tuple[int, int]] = None,
    ) -> "ContextBuilder":
        """
        Add file context.

        Args:
            path: File path
            line_range: Optional line range

        Returns:
            Self for chaining
        """
        formatter = ContextFormatter()
        try:
            ctx = formatter.format_file(path, line_range)
            self._contexts.append(ctx)
        except (FileNotFoundError, OSError):
            # Skip files that can't be loaded
            pass
        return self

    def add_directory(
        self,
        path: str,
        recursive: bool = True,
    ) -> "ContextBuilder":
        """
        Add directory context.

        Args:
            path: Directory path
            recursive: Whether to scan recursively

        Returns:
            Self for chaining
        """
        formatter = ContextFormatter()
        try:
            ctx = formatter.format_directory(path, recursive)
            self._contexts.append(ctx)
        except (FileNotFoundError, OSError):
            # Skip directories that can't be loaded
            pass
        return self

    def add_text(self, text: str, label: Optional[str] = None) -> "ContextBuilder":
        """
        Add plain text context.

        Args:
            text: Text content
            label: Optional label for the text

        Returns:
            Self for chaining
        """
        if label:
            self._contexts.append(f"# {label}\n{text}")
        else:
            self._contexts.append(text)
        return self

    def build(self, separator: str = "\n\n---\n\n") -> str:
        """
        Build final context string.

        Args:
            separator: String to insert between contexts

        Returns:
            Combined context string
        """
        parts = []
        for ctx in self._contexts:
            if isinstance(ctx, (FileContext, DirectoryContext)):
                parts.append(ctx.format())
            else:
                parts.append(str(ctx))

        return separator.join(parts)


# Convenience functions
def format_file_context(
    path: str,
    line_range: Optional[Tuple[int, int]] = None,
) -> FileContext:
    """
    Format file as context.

    Args:
        path: File path
        line_range: Optional line range

    Returns:
        FileContext with formatted content
    """
    formatter = ContextFormatter()
    return formatter.format_file(path, line_range)


def format_directory_context(
    path: str,
    recursive: bool = True,
) -> DirectoryContext:
    """
    Format directory as context.

    Args:
        path: Directory path
        recursive: Whether to scan recursively

    Returns:
        DirectoryContext with formatted files
    """
    formatter = ContextFormatter()
    return formatter.format_directory(path, recursive)


# ===== T050: ContextManager =====


class LoadError(Exception):
    """Error raised when loading a file or directory fails."""

    def __init__(self, path: str, reason: str) -> None:
        """
        Initialize LoadError.

        Args:
            path: Path that failed to load
            reason: Reason for failure
        """
        self.path = path
        self.reason = reason
        super().__init__(f"Failed to load '{path}': {reason}")


class ContextManager:
    """
    Manager for loading file and directory contexts.

    Provides a high-level API for loading files and directories
    with proper error handling and configuration.
    """

    DEFAULT_MAX_FILE_SIZE = 100000  # 100 KB
    DEFAULT_MAX_DIRECTORY_FILES = 100

    def __init__(
        self,
        max_file_size: int = DEFAULT_MAX_FILE_SIZE,
        max_directory_files: int = DEFAULT_MAX_DIRECTORY_FILES,
    ) -> None:
        """
        Initialize ContextManager.

        Args:
            max_file_size: Maximum file size in characters
            max_directory_files: Maximum files to load from a directory
        """
        self._max_file_size = max_file_size
        self._max_directory_files = max_directory_files
        self._formatter = ContextFormatter(
            max_content_length=max_file_size,
            max_directory_files=max_directory_files,
        )

    def load_file(
        self,
        path: str,
        line_range: Optional[Tuple[int, int]] = None,
    ) -> FileContext:
        """
        Load a file as context.

        Args:
            path: File path
            line_range: Optional line range (start, end)

        Returns:
            FileContext with file content

        Raises:
            LoadError: If file cannot be loaded
        """
        try:
            return self._formatter.format_file(path, line_range)
        except FileNotFoundError as e:
            raise LoadError(path, "File not found") from e
        except ValueError as e:
            raise LoadError(path, str(e)) from e
        except OSError as e:
            raise LoadError(path, f"OS error: {e}") from e

    def load_directory(
        self,
        path: str,
        recursive: bool = True,
        include_content: bool = True,
    ) -> DirectoryContext:
        """
        Load a directory as context.

        Args:
            path: Directory path
            recursive: Whether to scan recursively
            include_content: Whether to include file contents

        Returns:
            DirectoryContext with directory contents

        Raises:
            LoadError: If directory cannot be loaded
        """
        try:
            return self._formatter.format_directory(
                path, recursive=recursive
            )
        except FileNotFoundError as e:
            raise LoadError(path, "Directory not found") from e
        except ValueError as e:
            raise LoadError(path, str(e)) from e
        except OSError as e:
            raise LoadError(path, f"OS error: {e}") from e

    def load_from_reference(
        self,
        reference: object,
    ) -> object:
        """
        Load context from a parser reference.

        Args:
            reference: FileReference or DirectoryReference from parser

        Returns:
            FileContext or DirectoryContext

        Raises:
            LoadError: If reference cannot be loaded
            ValueError: If reference type is unknown
        """
        from claude_code.interaction.parser import FileReference, DirectoryReference

        if isinstance(reference, FileReference):
            return self.load_file(reference.path, reference.line_range)
        elif isinstance(reference, DirectoryReference):
            return self.load_directory(reference.path, reference.recursive)
        else:
            raise ValueError(f"Unknown reference type: {type(reference)}")
