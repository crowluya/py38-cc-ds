"""
Help System (T028)

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)

Provides:
- Help topic registry
- Formatted help output
- Tool and command help
- Contextual help
- Search functionality
"""

import sys
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, TextIO


@dataclass
class HelpTopic:
    """A help topic."""
    name: str
    title: str
    content: str
    examples: List[str] = field(default_factory=list)
    related: List[str] = field(default_factory=list)
    category: str = "general"


class HelpRegistry:
    """Registry for help topics."""

    def __init__(self) -> None:
        """Initialize registry."""
        self._topics: Dict[str, HelpTopic] = {}

    def register(
        self,
        name: str,
        title: str,
        content: str,
        examples: Optional[List[str]] = None,
        related: Optional[List[str]] = None,
        category: str = "general",
    ) -> None:
        """
        Register a help topic.

        Args:
            name: Topic name
            title: Topic title
            content: Topic content
            examples: Usage examples
            related: Related topics
            category: Topic category
        """
        self._topics[name] = HelpTopic(
            name=name,
            title=title,
            content=content,
            examples=examples or [],
            related=related or [],
            category=category,
        )

    def has(self, name: str) -> bool:
        """Check if topic exists."""
        return name in self._topics

    def get(self, name: str) -> Optional[HelpTopic]:
        """Get a topic by name."""
        return self._topics.get(name)

    def list_topics(self) -> List[str]:
        """List all topic names."""
        return list(self._topics.keys())

    def get_by_category(self, category: str) -> List[HelpTopic]:
        """Get topics by category."""
        return [t for t in self._topics.values() if t.category == category]

    def search(self, query: str) -> List[HelpTopic]:
        """
        Search topics.

        Args:
            query: Search query

        Returns:
            Matching topics
        """
        query_lower = query.lower()
        results = []

        for topic in self._topics.values():
            if (
                query_lower in topic.name.lower() or
                query_lower in topic.title.lower() or
                query_lower in topic.content.lower()
            ):
                results.append(topic)

        return results


class HelpFormatter:
    """Formatter for help output."""

    def __init__(self, use_color: bool = False, width: int = 80) -> None:
        """
        Initialize formatter.

        Args:
            use_color: Use ANSI colors
            width: Output width
        """
        self._use_color = use_color
        self._width = width

    def format_topic(self, topic: HelpTopic) -> str:
        """
        Format a help topic.

        Args:
            topic: Topic to format

        Returns:
            Formatted string
        """
        lines = []

        # Title
        title = topic.title
        if self._use_color:
            title = f"\033[1m{title}\033[0m"
        lines.append(title)
        lines.append("=" * len(topic.title))
        lines.append("")

        # Content
        lines.append(topic.content)
        lines.append("")

        # Examples
        if topic.examples:
            lines.append("Examples:")
            for example in topic.examples:
                lines.append(f"  {example}")
            lines.append("")

        # Related
        if topic.related:
            related_str = ", ".join(topic.related)
            lines.append(f"Related: {related_str}")
            lines.append("")

        return "\n".join(lines)

    def format_topic_list(self, topics: List[HelpTopic]) -> str:
        """
        Format a list of topics.

        Args:
            topics: Topics to format

        Returns:
            Formatted string
        """
        lines = ["Available Topics:", ""]

        for topic in topics:
            lines.append(f"  {topic.name:15} - {topic.title}")

        lines.append("")
        lines.append("Use '/help <topic>' for more information.")

        return "\n".join(lines)


# Global help registry
_global_registry = HelpRegistry()


def _init_default_topics() -> None:
    """Initialize default help topics."""
    # Commands
    _global_registry.register(
        "commands",
        "Available Commands",
        """DeepCode supports the following slash commands:

/help [topic]  - Show help (this message)
/clear         - Clear conversation history
/history       - Show command history
/reset         - Reset the session
/exit          - Exit DeepCode

You can also type 'exit', 'quit', or 'q' to exit.""",
        examples=["/help", "/help commands", "/clear"],
        related=["tools", "shortcuts"],
        category="commands",
    )

    # Tools
    _global_registry.register(
        "tools",
        "Available Tools",
        """DeepCode provides the following tools:

Read     - Read file contents
Write    - Write content to files
Edit     - Edit existing files
Glob     - Find files by pattern
Grep     - Search file contents
Bash     - Execute shell commands
Task     - Manage tasks
Todo     - Track todo items

Tools are automatically invoked by the AI assistant based on your requests.""",
        examples=["Read the file config.json", "Search for 'TODO' in all Python files"],
        related=["commands", "examples"],
        category="tools",
    )

    # Read tool
    _global_registry.register(
        "read",
        "Read Tool",
        """The Read tool reads file contents.

Usage: Automatically invoked when you ask to read or view a file.

Parameters:
  file_path  - Path to the file to read
  offset     - Line number to start from (optional)
  limit      - Number of lines to read (optional)

The tool supports text files, images (via OCR), and binary files.""",
        examples=[
            "Read the file src/main.py",
            "Show me the first 50 lines of config.json",
        ],
        related=["write", "edit", "tools"],
        category="tools",
    )

    # Write tool
    _global_registry.register(
        "write",
        "Write Tool",
        """The Write tool creates or overwrites files.

Usage: Automatically invoked when you ask to create or write a file.

Parameters:
  file_path  - Path to the file to write
  content    - Content to write

Warning: This will overwrite existing files without confirmation.""",
        examples=[
            "Create a new file called hello.py with a hello world program",
            "Write the configuration to config.json",
        ],
        related=["read", "edit", "tools"],
        category="tools",
    )

    # Edit tool
    _global_registry.register(
        "edit",
        "Edit Tool",
        """The Edit tool modifies existing files.

Usage: Automatically invoked when you ask to edit or modify a file.

Parameters:
  file_path   - Path to the file to edit
  old_string  - Text to find and replace
  new_string  - Replacement text

The tool performs exact string matching for replacements.""",
        examples=[
            "Change the function name from 'foo' to 'bar' in utils.py",
            "Fix the typo in README.md",
        ],
        related=["read", "write", "tools"],
        category="tools",
    )

    # Shortcuts
    _global_registry.register(
        "shortcuts",
        "Keyboard Shortcuts",
        """Keyboard shortcuts in DeepCode:

Ctrl+C  - Cancel current input / Interrupt
Ctrl+D  - Exit DeepCode
Up/Down - Navigate command history (if supported)

In multiline mode:
  Lines ending with : or \\ continue on the next line
  Empty line submits the input""",
        related=["commands"],
        category="general",
    )

    # Examples
    _global_registry.register(
        "examples",
        "Usage Examples",
        """Common usage examples:

1. Reading files:
   "Read the file src/main.py"
   "Show me the contents of package.json"

2. Writing files:
   "Create a Python script that prints hello world"
   "Write a README.md for this project"

3. Editing files:
   "Fix the bug in line 42 of utils.py"
   "Rename the function 'old_name' to 'new_name'"

4. Searching:
   "Find all files containing 'TODO'"
   "Search for the definition of MyClass"

5. Running commands:
   "Run the tests"
   "Install the dependencies" """,
        related=["tools", "commands"],
        category="general",
    )

    # Help
    _global_registry.register(
        "help",
        "Help System",
        """The help system provides information about DeepCode features.

Usage:
  /help           - Show general help
  /help <topic>   - Show help for a specific topic
  /help search <query> - Search help topics

Available topics: commands, tools, shortcuts, examples""",
        examples=["/help", "/help tools", "/help read"],
        category="general",
    )


# Initialize default topics
_init_default_topics()


class HelpCommand:
    """Handler for help commands."""

    def __init__(
        self,
        output: Optional[TextIO] = None,
        registry: Optional[HelpRegistry] = None,
        use_color: bool = False,
    ) -> None:
        """
        Initialize help command.

        Args:
            output: Output stream
            registry: Help registry
            use_color: Use colors
        """
        self._output = output or sys.stdout
        self._registry = registry or _global_registry
        self._formatter = HelpFormatter(use_color=use_color)

    def show_help(self, topic: Optional[str] = None) -> None:
        """
        Show help.

        Args:
            topic: Optional topic name
        """
        if topic is None:
            self._show_general_help()
        elif topic == "search":
            self._output.write("Usage: /help search <query>\n")
        else:
            self._show_topic_help(topic)

    def _show_general_help(self) -> None:
        """Show general help."""
        lines = [
            "DeepCode Help",
            "=============",
            "",
            "DeepCode is an AI-powered coding assistant.",
            "",
            "Quick Start:",
            "  - Type your request in natural language",
            "  - Use /help <topic> for specific help",
            "  - Use /exit to quit",
            "",
            "Topics: commands, tools, shortcuts, examples",
            "",
            "Type '/help <topic>' for more information.",
            "",
        ]
        self._output.write("\n".join(lines))

    def _show_topic_help(self, topic: str) -> None:
        """Show help for a topic."""
        help_topic = self._registry.get(topic)

        if help_topic is None:
            self._output.write(f"Help topic '{topic}' not found.\n")
            self._output.write("Available topics: " + ", ".join(self._registry.list_topics()) + "\n")
            return

        formatted = self._formatter.format_topic(help_topic)
        self._output.write(formatted)

    def search(self, query: str) -> List[HelpTopic]:
        """
        Search help topics.

        Args:
            query: Search query

        Returns:
            Matching topics
        """
        return self._registry.search(query)


# Tool help database
_TOOL_HELP: Dict[str, str] = {
    "Read": "Read file contents. Supports text files, images (OCR), and binary files.",
    "Write": "Write content to files. Creates new files or overwrites existing ones.",
    "Edit": "Edit existing files by replacing text patterns.",
    "Glob": "Find files matching glob patterns (e.g., **/*.py).",
    "Grep": "Search file contents using regular expressions.",
    "Bash": "Execute shell commands.",
    "Task": "Manage and track tasks.",
    "Todo": "Track todo items and progress.",
}

# Command help database
_COMMAND_HELP: Dict[str, str] = {
    "help": "Show help information. Usage: /help [topic]",
    "clear": "Clear conversation history.",
    "history": "Show command history.",
    "reset": "Reset the session.",
    "exit": "Exit DeepCode.",
    "quit": "Exit DeepCode (alias for /exit).",
}


def get_tool_help(tool_name: str) -> Optional[str]:
    """
    Get help for a tool.

    Args:
        tool_name: Tool name

    Returns:
        Help text or None
    """
    # Check exact match
    if tool_name in _TOOL_HELP:
        return _TOOL_HELP[tool_name]

    # Check case-insensitive
    for name, help_text in _TOOL_HELP.items():
        if name.lower() == tool_name.lower():
            return help_text

    # Check registry
    topic = _global_registry.get(tool_name.lower())
    if topic:
        return topic.content

    return None


def list_tools_help() -> Dict[str, str]:
    """
    List all tools help.

    Returns:
        Dictionary of tool name to help text
    """
    return dict(_TOOL_HELP)


def get_command_help(command: str) -> Optional[str]:
    """
    Get help for a command.

    Args:
        command: Command name

    Returns:
        Help text or None
    """
    return _COMMAND_HELP.get(command.lower())


def list_commands_help() -> Dict[str, str]:
    """
    List all commands help.

    Returns:
        Dictionary of command name to help text
    """
    return dict(_COMMAND_HELP)


def get_quick_reference() -> str:
    """
    Get quick reference.

    Returns:
        Quick reference text
    """
    lines = [
        "DeepCode Quick Reference",
        "========================",
        "",
        "Commands:",
        "  /help     - Show help",
        "  /clear    - Clear history",
        "  /exit     - Exit",
        "",
        "Tools:",
        "  Read, Write, Edit, Glob, Grep, Bash, Task, Todo",
        "",
        "Shortcuts:",
        "  Ctrl+C - Cancel",
        "  Ctrl+D - Exit",
        "",
    ]
    return "\n".join(lines)


def get_contextual_help(context: str, message: str) -> str:
    """
    Get contextual help based on situation.

    Args:
        context: Context type (error, tool_error, etc.)
        message: Context message

    Returns:
        Contextual help text
    """
    if context == "error":
        if "connection" in message.lower():
            return "Connection error. Check your network and try again."
        if "timeout" in message.lower():
            return "Request timed out. The server may be busy. Try again later."
        if "permission" in message.lower():
            return "Permission denied. Check file permissions."
        return "An error occurred. Use /help for assistance."

    if context == "tool_error":
        if "not found" in message.lower():
            return "File or resource not found. Check the path and try again."
        if "Read" in message:
            return "Error reading file. Ensure the file exists and is readable."
        if "Write" in message:
            return "Error writing file. Check permissions and disk space."
        return "Tool error. Check your input and try again."

    return "Use /help for assistance."


def search_help(query: str) -> List[HelpTopic]:
    """
    Search help topics.

    Args:
        query: Search query

    Returns:
        Matching topics
    """
    return _global_registry.search(query)


def get_examples(topic: str) -> List[str]:
    """
    Get examples for a topic.

    Args:
        topic: Topic name

    Returns:
        List of examples
    """
    help_topic = _global_registry.get(topic.lower())
    if help_topic:
        return help_topic.examples
    return []


def register_help_topic(
    name: str,
    title: str,
    content: str,
    **kwargs: Any,
) -> None:
    """
    Register a custom help topic.

    Args:
        name: Topic name
        title: Topic title
        content: Topic content
        **kwargs: Additional options
    """
    _global_registry.register(name, title, content, **kwargs)
