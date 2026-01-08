"""
Agent - Message history and tool result management

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)

Handles:
- Message history for conversation
- Tool result formatting
- Command output injection into context
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class MessageRole(Enum):
    """Message role in conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


@dataclass
class ToolResult:
    """Result of a tool/command execution."""

    tool_id: str
    name: str
    output: str
    success: bool
    error_output: str = ""

    def get_combined_output(self) -> str:
        """
        Get combined output (stdout + stderr).

        Returns:
            Combined output string
        """
        parts = []
        if self.output:
            parts.append(self.output)
        if self.error_output:
            parts.append(f"Error: {self.error_output}")
        return "\n".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "output": self.output,
            "success": self.success,
            "error_output": self.error_output,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolResult":
        """Create from dictionary."""
        return cls(
            tool_id=data.get("tool_id", ""),
            name=data.get("name", ""),
            output=data.get("output", ""),
            success=data.get("success", True),
            error_output=data.get("error_output", ""),
        )

    def __str__(self) -> str:
        """String representation."""
        status = "success" if self.success else "failed"
        return f"ToolResult({self.name}, {status})"


@dataclass
class Message:
    """Message in conversation history."""

    role: MessageRole
    content: str
    tool_result: Optional[ToolResult] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "role": self.role.value,
            "content": self.content,
            "tool_result": self.tool_result.to_dict() if self.tool_result else None,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create from dictionary."""
        tool_result_data = data.get("tool_result")
        tool_result = ToolResult.from_dict(tool_result_data) if tool_result_data else None

        return cls(
            role=MessageRole(data["role"]),
            content=data["content"],
            tool_result=tool_result,
            metadata=data.get("metadata"),
        )

    def format_for_llm(self) -> Dict[str, Any]:
        """
        Format message for LLM API.

        Returns:
            Dictionary in LLM-compatible format
        """
        formatted: Dict[str, Any] = {
            "role": self.role.value,
            "content": self.content,
        }

        if self.tool_result:
            formatted["tool_result"] = self.tool_result.to_dict()

        return formatted

    def __str__(self) -> str:
        """String representation."""
        if self.tool_result:
            return f"{self.role.value}: {self.content} (tool: {self.tool_result.name})"
        return f"{self.role.value}: {self.content}"


@dataclass
class CommandOutputContext:
    """
    Context from command execution output.

    Wraps command execution results for injection into conversation.
    """

    command: str
    return_code: int
    stdout: str
    stderr: str
    timed_out: bool = False

    @property
    def success(self) -> bool:
        """Check if command succeeded."""
        return self.return_code == 0 and not self.timed_out

    def to_message(self) -> Message:
        """
        Convert to a tool result message.

        Returns:
            Message with tool result
        """
        # Format output for the tool result
        output_parts = []
        output_parts.append(f"$ {self.command}")

        if self.stdout:
            output_parts.append(self.stdout.rstrip())

        if self.stderr:
            output_parts.append(f"[stderr] {self.stderr.rstrip()}")

        if not self.success:
            output_parts.append(f"[Exit code: {self.return_code}]")
        elif self.timed_out:
            output_parts.append("[Timed out]")

        combined_output = "\n".join(output_parts)

        tool_result = ToolResult(
            tool_id=f"cmd_{hash(self.command)}",
            name="shell",
            output=combined_output,
            success=self.success,
            error_output=self.stderr if self.return_code != 0 else "",
        )

        return Message(
            role=MessageRole.TOOL,
            content="",  # Tool results use the tool_result field
            tool_result=tool_result,
        )

    def format(self) -> str:
        """
        Format as human-readable string.

        Returns:
            Formatted command output
        """
        lines = [
            f"Command: {self.command}",
            f"Exit code: {self.return_code}",
        ]

        if self.stdout:
            lines.append("Output:")
            lines.append(self.stdout.rstrip())

        if self.stderr:
            lines.append("Errors:")
            lines.append(self.stderr.rstrip())

        if self.timed_out:
            lines.append("(Command timed out)")

        return "\n".join(lines)

    def __str__(self) -> str:
        """String representation."""
        return self.format()


def inject_command_output(
    history: List[Message],
    command_output: CommandOutputContext,
) -> List[Message]:
    """
    Inject command output into conversation history.

    Args:
        history: Current message history
        command_output: Command execution result

    Returns:
        New history with tool result message appended
    """
    # Create a copy of history to avoid mutation
    new_history = list(history)

    # Convert command output to tool message
    tool_message = command_output.to_message()

    # Append to history
    new_history.append(tool_message)

    return new_history


def create_history() -> List[Message]:
    """
    Create a new conversation history.

    Returns:
        Empty message list
    """
    return []


def add_user_message(
    history: List[Message],
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> List[Message]:
    """
    Add a user message to history.

    Args:
        history: Current message history
        content: Message content
        metadata: Optional metadata

    Returns:
        New history with user message appended
    """
    new_history = list(history)
    new_history.append(
        Message(role=MessageRole.USER, content=content, metadata=metadata)
    )
    return new_history


def add_assistant_message(
    history: List[Message],
    content: str,
    tool_result: Optional[ToolResult] = None,
) -> List[Message]:
    """
    Add an assistant message to history.

    Args:
        history: Current message history
        content: Message content
        tool_result: Optional tool result

    Returns:
        New history with assistant message appended
    """
    new_history = list(history)
    new_history.append(
        Message(role=MessageRole.ASSISTANT, content=content, tool_result=tool_result)
    )
    return new_history


def serialize_history(history: List[Message]) -> List[Dict[str, Any]]:
    """
    Serialize history to list of dictionaries.

    Args:
        history: Message history

    Returns:
        List of serialized messages
    """
    return [msg.to_dict() for msg in history]


def deserialize_history(data: List[Dict[str, Any]]) -> List[Message]:
    """
    Deserialize history from list of dictionaries.

    Args:
        data: Serialized message data

    Returns:
        List of Message objects
    """
    return [Message.from_dict(item) for item in data]
