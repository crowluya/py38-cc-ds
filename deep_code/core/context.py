"""
Context Formatter - File and directory context formatting

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)

Formats file content and directory trees for LLM context:
- File content with path identifier and line ranges
- Directory tree structures
- Content truncation for large files/directories
- Permission checking for file operations (T071)
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from deep_code.interaction.directory_loader import DirectoryLoader, DirectoryEntry

# Optional type hints for permission system
try:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from deep_code.security.permissions import (
            PermissionManager,
            ApprovalCallback,
        )
except ImportError:
    pass


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

    T071: Optional permission checking for file operations.
    """

    DEFAULT_MAX_FILE_SIZE = 100000  # 100 KB
    DEFAULT_MAX_DIRECTORY_FILES = 100

    def __init__(
        self,
        max_file_size: int = DEFAULT_MAX_FILE_SIZE,
        max_directory_files: int = DEFAULT_MAX_DIRECTORY_FILES,
        permission_manager: Optional[Any] = None,
        approval_callback: Optional[Callable] = None,
    ) -> None:
        """
        Initialize ContextManager.

        Args:
            max_file_size: Maximum file size in characters
            max_directory_files: Maximum files to load from a directory
            permission_manager: Optional PermissionManager for checking file permissions
            approval_callback: Optional callback for ASK permissions
        """
        self._max_file_size = max_file_size
        self._max_directory_files = max_directory_files
        self._permission_manager = permission_manager
        self._approval_callback = approval_callback
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
            LoadError: If file cannot be loaded or permission denied
        """
        # T071: Check read permission
        if self._permission_manager is not None:
            if not self._check_file_permission(path, for_read=True):
                raise LoadError(path, "Permission denied: File read not permitted")

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
        # T071: Check read permission for directory
        if self._permission_manager is not None:
            if not self._check_file_permission(path, for_read=True):
                raise LoadError(path, "Permission denied: Directory read not permitted")

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

    def _check_file_permission(
        self,
        path: str,
        for_read: bool = True,
    ) -> bool:
        """
        Check if file operation is permitted.

        Args:
            path: File path to check
            for_read: True for read operation, False for write

        Returns:
            True if permitted, False otherwise
        """
        # Lazy import to avoid circular dependency
        from deep_code.security.permissions import (
            PermissionApprover,
            PermissionDomain,
        )

        # Determine domain based on operation
        domain = PermissionDomain.FILE_READ if for_read else PermissionDomain.FILE_WRITE

        # Create approver with callback if provided
        approver = PermissionApprover(
            self._permission_manager,
            approval_callback=self._approval_callback,
        )

        # Check permission
        permission = approver.request_permission(
            domain=domain,
            target=path,
        )

        return permission.granted

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
        from deep_code.interaction.parser import FileReference, DirectoryReference

        if isinstance(reference, FileReference):
            return self.load_file(reference.path, reference.line_range)
        elif isinstance(reference, DirectoryReference):
            return self.load_directory(reference.path, reference.recursive)
        else:
            raise ValueError(f"Unknown reference type: {type(reference)}")


# ===== T051: LongTermMemory =====


class LongTermMemory:
    """
    Long-term memory for persistent project context.

    Auto-discovers and loads long-term memory files like:
    - CLAUDE.md (project operations manual)
    - AGENTS.md (cross-agent standards)
    - constitution.md (engineering principles)

    Handles missing files gracefully without crashing.
    """

    DEFAULT_MEMORY_FILES = [
        "CLAUDE.md",
        "AGENTS.md",
        "constitution.md",
    ]

    def __init__(self, custom_files: Optional[List[str]] = None) -> None:
        """
        Initialize LongTermMemory.

        Args:
            custom_files: Optional list of custom memory file names to load
        """
        self._memory_files = custom_files or list(self.DEFAULT_MEMORY_FILES)
        self._context_manager = ContextManager()
        self.files: Dict[str, FileContext] = {}

    def load_from_directory(self, directory: str) -> None:
        """
        Load memory files from a directory.

        Args:
            directory: Directory path to scan for memory files
        """
        dir_path = Path(directory)

        for filename in self._memory_files:
            file_path = dir_path / filename
            if file_path.exists() and file_path.is_file():
                try:
                    file_ctx = self._context_manager.load_file(str(file_path))
                    self.files[filename] = file_ctx
                except (LoadError, OSError):
                    # Skip files that can't be loaded
                    pass

    @property
    def is_empty(self) -> bool:
        """Check if no memory files are loaded."""
        return len(self.files) == 0

    def get_file_names(self) -> List[str]:
        """
        Get list of loaded file names.

        Returns:
            List of file names that were successfully loaded
        """
        return list(self.files.keys())

    def has_file(self, filename: str) -> bool:
        """
        Check if a specific file is loaded.

        Args:
            filename: Name of the file to check

        Returns:
            True if file is loaded
        """
        return filename in self.files

    def get_file(self, filename: str) -> Optional[FileContext]:
        """
        Get a specific loaded file.

        Args:
            filename: Name of the file to get

        Returns:
            FileContext if found, None otherwise
        """
        return self.files.get(filename)

    def get_formatted_content(self) -> str:
        """
        Get all loaded memory files formatted as a single string.

        Returns:
            Formatted content from all loaded files
        """
        if not self.files:
            return "# No long-term memory files loaded"

        parts = []
        for filename in sorted(self.files.keys()):
            file_ctx = self.files[filename]
            parts.append(f"# {filename}")
            parts.append(file_ctx.format())
            parts.append("")  # Blank line between files

        return "\n".join(parts)

    def get_status_message(self) -> str:
        """
        Get a status message about loaded memory files.

        Returns:
            Human-readable status message
        """
        if not self.files:
            return "No long-term memory files found."

        loaded = ", ".join(sorted(self.files.keys()))
        return f"Loaded {len(self.files)} long-term memory file(s): {loaded}"

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.

        Returns:
            Dictionary with files data
        """
        return {
            "files": {
                name: ctx.to_dict() if hasattr(ctx, "to_dict") else {
                    "path": ctx.path,
                    "content": ctx.content,
                }
                for name, ctx in self.files.items()
            },
            "count": len(self.files),
        }

    def load_from_directory(
        self,
        directory: str,
        resolve_imports: bool = False,
    ) -> None:
        """
        Load memory files from a directory.

        Args:
            directory: Directory path to scan for memory files
            resolve_imports: Whether to resolve @ import syntax
        """
        dir_path = Path(directory)

        for filename in self._memory_files:
            file_path = dir_path / filename
            if file_path.exists() and file_path.is_file():
                try:
                    if resolve_imports:
                        # Use ModularLoader to resolve imports
                        loader = ModularLoader()
                        content = loader.load_with_imports(str(file_path), base_dir=directory)
                        # Create FileContext with resolved content
                        self.files[filename] = FileContext(
                            path=str(file_path),
                            content=content,
                            line_range=None,
                            truncated=False,
                        )
                    else:
                        file_ctx = self._context_manager.load_file(str(file_path))
                        self.files[filename] = file_ctx
                except (LoadError, OSError):
                    # Skip files that can't be loaded
                    pass


# ===== T052: Modular imports with @ syntax =====


class CircularImportError(Exception):
    """Error raised when circular imports are detected."""

    def __init__(self, import_path: List[str]) -> None:
        """
        Initialize CircularImportError.

        Args:
            import_path: List of file paths showing the circular import chain
        """
        self.import_path = import_path
        path_str = " -> ".join(import_path)
        super().__init__(f"Circular import detected: {path_str}")


class ModularLoader:
    """
    Loader for files with modular @ import syntax.

    Supports:
    - @file.md - Import entire file
    - @file.md:1-10 - Import file with line range
    - @dir/ - Import all files in directory
    - Recursive imports with circular reference detection
    """

    DEFAULT_MAX_IMPORT_DEPTH = 50
    IMPORT_PATTERN = re.compile(r"@([^\s\n]+)")

    def __init__(self, max_import_depth: int = DEFAULT_MAX_IMPORT_DEPTH) -> None:
        """
        Initialize ModularLoader.

        Args:
            max_import_depth: Maximum depth for recursive imports
        """
        self._max_import_depth = max_import_depth
        self._imported_files: List[str] = []

    def load_with_imports(
        self,
        file_path: str,
        base_dir: Optional[str] = None,
        current_depth: int = 0,
        import_chain: Optional[List[str]] = None,
    ) -> str:
        """
        Load a file and resolve @ import statements.

        Args:
            file_path: Path to the file to load
            base_dir: Base directory for resolving relative imports
            current_depth: Current import depth (for recursion)
            import_chain: Chain of imported files (for circular detection)

        Returns:
            File content with @ imports resolved

        Raises:
            CircularImportError: If circular imports are detected
            LoadError: If file cannot be loaded
        """
        if import_chain is None:
            import_chain = []

        # Resolve the file path for comparison
        try:
            resolved_path = str(Path(file_path).resolve())
        except OSError:
            resolved_path = file_path

        base = base_dir or str(Path(file_path).parent)

        # Check for circular imports (before reading file)
        if resolved_path in import_chain:
            # Circular import detected
            full_chain = import_chain + [resolved_path]
            raise CircularImportError(full_chain)

        # Check max depth
        if current_depth >= self._max_import_depth:
            return f"\n\n[Import depth limit reached]\n\n"

        # Track imported file
        if resolved_path not in self._imported_files:
            self._imported_files.append(resolved_path)

        # Read file content
        try:
            content = Path(file_path).read_text(encoding="utf-8")
        except FileNotFoundError:
            return f"\n\n[File not found: {file_path}]\n\n"
        except UnicodeDecodeError:
            try:
                content = Path(file_path).read_text(encoding="latin-1")
            except Exception:
                return f"\n\n[Cannot read file: {file_path}]\n\n"

        # Process @ imports
        new_chain = import_chain + [resolved_path]
        result = self._process_imports(content, base, current_depth + 1, new_chain)

        return result

    def _process_imports(
        self,
        content: str,
        base_dir: str,
        current_depth: int,
        import_chain: List[str],
    ) -> str:
        """
        Process @ import statements in content.

        Args:
            content: File content
            base_dir: Base directory for resolving imports
            current_depth: Current import depth
            import_chain: Chain of imported files

        Returns:
            Content with @ imports resolved
        """
        lines = []
        base_path = Path(base_dir)

        for line in content.split("\n"):
            # Check for @ import
            match = self.IMPORT_PATTERN.search(line)
            if match:
                import_ref = match.group(1)

                # Parse the import reference
                imported_content = self._resolve_import(
                    import_ref,
                    base_path,
                    current_depth,
                    import_chain,
                )

                # Replace the @import line with the imported content
                if imported_content:
                    lines.append(imported_content)
            else:
                lines.append(line)

        return "\n".join(lines)

    def _resolve_import(
        self,
        import_ref: str,
        base_path: Path,
        current_depth: int,
        import_chain: List[str],
    ) -> str:
        """
        Resolve a single @ import reference.

        Args:
            import_ref: Import reference (e.g., "file.md", "file.md:1-10", "dir/")
            base_path: Base directory for resolving paths
            current_depth: Current import depth
            import_chain: Chain of imported files

        Returns:
            Resolved import content
        """
        # Check if it's a directory import (ends with /)
        if import_ref.endswith("/"):
            return self._import_directory(import_ref, base_path, current_depth, import_chain)

        # Check if it has a line range
        range_match = re.search(r":(\d+)-(\d+)", import_ref)
        line_range = None
        if range_match:
            line_range = (int(range_match.group(1)), int(range_match.group(2)))
            import_ref = import_ref[:range_match.start()]

        # Resolve the import path
        import_path = base_path / import_ref

        if not import_path.exists():
            return f"\n\n[Import not found: {import_ref}]\n\n"

        if import_path.is_dir():
            return self._import_directory(
                import_ref + "/",
                base_path,
                current_depth,
                import_chain,
            )

        # Import the file
        return self._import_file(
            str(import_path),
            base_path,
            current_depth,
            import_chain,
            line_range,
        )

    def _import_file(
        self,
        file_path: str,
        base_path: Path,
        current_depth: int,
        import_chain: List[str],
        line_range: Optional[Tuple[int, int]] = None,
    ) -> str:
        """
        Import a file with optional line range.

        Args:
            file_path: Path to file
            base_path: Base directory
            current_depth: Current import depth
            import_chain: Chain of imported files
            line_range: Optional line range

        Returns:
            File content (with line range applied if specified)
        """
        # Load file with recursive import processing
        content = self.load_with_imports(
            file_path,
            base_dir=str(base_path),
            current_depth=current_depth,
            import_chain=import_chain,
        )

        # Apply line range if specified (after imports are resolved)
        if line_range:
            lines = content.split("\n")
            start, end = line_range
            start_idx = max(0, start - 1)
            end_idx = min(len(lines), end)
            content = "\n".join(lines[start_idx:end_idx])

        return content

    def _import_directory(
        self,
        dir_ref: str,
        base_path: Path,
        current_depth: int,
        import_chain: List[str],
    ) -> str:
        """
        Import all files in a directory.

        Args:
            dir_ref: Directory reference (e.g., "docs/")
            base_path: Base directory
            current_depth: Current import depth
            import_chain: Chain of imported files

        Returns:
            Combined content from all files in directory
        """
        dir_path = base_path / dir_ref.rstrip("/")

        if not dir_path.exists() or not dir_path.is_dir():
            return f"\n\n[Directory not found: {dir_ref}]\n\n"

        # Use DirectoryLoader to list files
        loader = DirectoryLoader()
        try:
            entries = loader.list_directory(str(dir_path), recursive=True)
        except OSError:
            return f"\n\n[Cannot read directory: {dir_ref}]\n\n"

        # Sort and combine file contents
        parts = []
        for entry in sorted(entries, key=lambda e: e.path):
            if entry.is_file:
                file_content = self._import_file(
                    entry.path,
                    dir_path,
                    current_depth,
                    import_chain,
                )
                parts.append(file_content)

        return "\n\n".join(parts)

    def get_imported_files(self) -> List[str]:
        """
        Get list of files that were imported.

        Returns:
            List of file paths
        """
        return list(self._imported_files)

    def reset(self) -> None:
        """Reset the imported files tracker."""
        self._imported_files = []
