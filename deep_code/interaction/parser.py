"""
Interaction Parser - @file and !command syntax

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)

Parses user input for:
- @file: Inject file content
- @dir/: Inject directory tree (ends with /)
- !command: Execute shell command
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Union


@dataclass
class FileReference:
    """Reference to a file to inject into context."""

    path: str
    line_range: Optional[tuple] = None  # (start, end) inclusive

    def __str__(self) -> str:
        if self.line_range:
            return f"@{self.path}:{self.line_range[0]}-{self.line_range[1]}"
        return f"@{self.path}"


@dataclass
class DirectoryReference:
    """Reference to a directory to inject into context."""

    path: str
    recursive: bool = True

    def __str__(self) -> str:
        return f"@{self.path}/"


@dataclass
class CommandReference:
    """Reference to a shell command to execute."""

    command: str

    def __str__(self) -> str:
        return f"!{self.command}"


@dataclass
class ParsedInput:
    """Result of parsing user input."""

    raw_input: str
    prompt: str
    file_refs: List[FileReference]
    directory_refs: List[DirectoryReference]
    command_refs: List[CommandReference]

    def has_references(self) -> bool:
        """Check if any references are present."""
        return bool(
            self.file_refs or self.directory_refs or self.command_refs
        )

    def get_all_references(self) -> List[Union[FileReference, DirectoryReference, CommandReference]]:
        """Get all references in order."""
        refs: List[Union[FileReference, DirectoryReference, CommandReference]] = []
        refs.extend(self.file_refs)
        refs.extend(self.directory_refs)
        refs.extend(self.command_refs)
        return refs


class Parser:
    """
    Parser for @file, @dir/, and !command syntax.

    Grammar:
    - @file.path[:start-end] - File reference with optional line range
    - @dir/path/ - Directory reference (ends with /)
    - !command - Shell command to execute (at end or standalone)
    """

    def __init__(self) -> None:
        """Initialize parser."""
        pass

    def parse(self, input_text: str) -> ParsedInput:
        """
        Parse user input for references.

        Args:
            input_text: Raw user input

        Returns:
            ParsedInput with extracted references
        """
        raw = input_text
        file_refs: List[FileReference] = []
        directory_refs: List[DirectoryReference] = []
        command_refs: List[CommandReference] = []

        # Find all @... references
        at_pattern = re.compile(r"@[^\s]+")
        refs_to_remove: List[tuple] = []

        for match in at_pattern.finditer(raw):
            ref_text = match.group(0)  # e.g., "@path/", "@file", "@file:10-20"
            start, end = match.start(), match.end()

            # Check if it's a command reference
            if ref_text.startswith("!"):
                command_refs.append(CommandReference(ref_text[1:]))
                refs_to_remove.append((start, end))
                continue

            # Check if ends with / -> directory
            if ref_text.endswith("/"):
                path = ref_text[1:-1]  # Remove @ and trailing /
                directory_refs.append(DirectoryReference(path, recursive=True))
                refs_to_remove.append((start, end))
                continue

            # Check if has line range @file:start-end
            range_match = re.search(r":(\d+)-(\d+)", ref_text)
            if range_match:
                path = ref_text[1:range_match.start()]
                line_range = (int(range_match.group(1)), int(range_match.group(2)))
                file_refs.append(FileReference(path, line_range))
                refs_to_remove.append((start, end))
                continue

            # Otherwise it's a simple file reference
            path = ref_text[1:]
            file_refs.append(FileReference(path))
            refs_to_remove.append((start, end))

        # Extract command at end if not already processed
        if not command_refs:
            command_match = re.search(r"!\s*(.+)$", raw)
            if command_match:
                command = command_match.group(1).strip()
                if command:
                    command_refs.append(CommandReference(command))
                    refs_to_remove.append((command_match.start(), len(raw)))
                    raw = raw[:command_match.start()]

        # Remove all references from prompt
        prompt = raw
        for start, end in sorted(refs_to_remove, reverse=True):
            prompt = prompt[:start] + prompt[end:]

        prompt = " ".join(prompt.split())  # Normalize whitespace

        return ParsedInput(
            raw_input=input_text,
            prompt=prompt,
            file_refs=file_refs,
            directory_refs=directory_refs,
            command_refs=command_refs,
        )

    def is_command_only(self, input_text: str) -> bool:
        """
        Check if input is a command-only (starts with !).

        Args:
            input_text: Raw user input

        Returns:
            True if input starts with !
        """
        return input_text.strip().startswith("!")

    def extract_line_range(self, input_text: str) -> Optional[tuple]:
        """
        Extract line range from input text.

        Args:
            input_text: Text containing line range like ":10-20"

        Returns:
            Tuple of (start, end) or None
        """
        match = re.search(r":(\d+)-(\d+)", input_text)
        if match:
            return (int(match.group(1)), int(match.group(2)))
        return None


def parse_input(input_text: str) -> ParsedInput:
    """
    Convenience function to parse user input.

    Args:
        input_text: Raw user input

    Returns:
        ParsedInput with extracted references
    """
    parser = Parser()
    return parser.parse(input_text)
