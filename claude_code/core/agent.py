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

from claude_code.core.context import ContextManager, LoadError
from claude_code.core.executor import CommandExecutor


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


# ===== T060-T061: Agent Engine =====


class ToolType(Enum):
    """Type of tool call."""

    SHELL = "shell"
    READ_FILE = "read_file"
    READ_DIRECTORY = "read_directory"


@dataclass
class ToolCall:
    """A tool call requested by the LLM."""

    tool_type: ToolType
    command: str
    arguments: Dict[str, Any]
    call_id: str = ""

    def __str__(self) -> str:
        """String representation."""
        return f"{self.tool_type.value}:{self.command}"


@dataclass
class ConversationTurn:
    """Result of a conversation turn."""

    content: str
    finish_reason: str
    tool_calls: Optional[List[ToolCall]] = None
    raw_response: Optional[Any] = None

    @property
    def has_tools(self) -> bool:
        """Check if this turn has tool calls."""
        return self.tool_calls is not None and len(self.tool_calls) > 0


@dataclass
class AgentConfig:
    """Configuration for Agent."""

    llm_client: Any
    max_tokens: int = 4096
    temperature: float = 0.7
    system_prompt: Optional[str] = None
    stream: bool = False


class Agent:
    """
    Agent for managing conversation loops and tool orchestration.

    Features:
    - Message history management
    - LLM integration
    - Tool execution (shell, file read, directory read)
    - Context injection
    - Streaming support
    """

    def __init__(self, config: AgentConfig) -> None:
        """
        Initialize Agent.

        Args:
            config: Agent configuration
        """
        self._config = config
        self._history: List[Message] = []
        self._context_manager = ContextManager()
        self._command_executor = CommandExecutor()

    def process(self, user_input: str) -> ConversationTurn:
        """
        Process a user input through the conversation loop.

        Args:
            user_input: User message or command

        Returns:
            ConversationTurn with response
        """
        # Add user message to history
        self._add_user_message(user_input)

        # Call LLM
        if self._config.stream:
            turn = self._call_llm_stream()
        else:
            turn = self._call_llm()

        # Handle tool calls
        if turn.has_tools:
            turn = self._handle_tool_calls(turn)

        # Add assistant response to history
        self._add_assistant_message(turn.content, turn.tool_calls)

        return turn

    def inject_context(self, context: str) -> None:
        """
        Inject context into the conversation.

        Args:
            context: Context string (e.g., @file.txt or directory content)
        """
        # Add as a system message or user message with context
        self._add_system_message(context)

    def reset(self) -> None:
        """Reset conversation history."""
        self._history = []

    def get_history(self) -> List[Message]:
        """Get conversation history."""
        return list(self._history)

    def _call_llm(self) -> ConversationTurn:
        """
        Call LLM without streaming.

        Returns:
            ConversationTurn with response
        """
        messages = self._format_messages_for_llm()

        kwargs = {
            "max_tokens": self._config.max_tokens,
            "temperature": self._config.temperature,
        }

        response = self._config.llm_client.chat_completion(
            messages=messages,
            **kwargs
        )

        # Extract content from response (dict or object)
        if isinstance(response, dict):
            content = response.get("content", "")
            finish_reason = response.get("finish_reason", "stop")
        else:
            content = getattr(response, "content", "")
            finish_reason = getattr(response, "finish_reason", "stop")

        # Extract tool calls if present
        tool_calls = None
        tool_calls_data = None
        if isinstance(response, dict):
            tool_calls_data = response.get("tool_calls")
        elif hasattr(response, "tool_calls"):
            tool_calls_data = response.tool_calls

        if tool_calls_data:
            tool_calls = self._parse_tool_calls(tool_calls_data)

        return ConversationTurn(
            content=content,
            finish_reason=finish_reason,
            tool_calls=tool_calls,
            raw_response=response,
        )

    def _call_llm_stream(self) -> ConversationTurn:
        """
        Call LLM with streaming.

        Returns:
            ConversationTurn with accumulated response
        """
        messages = self._format_messages_for_llm()

        chunks = self._config.llm_client.chat_completion_stream(
            messages=messages,
            max_tokens=self._config.max_tokens,
            temperature=self._config.temperature,
        )

        content_parts = []
        for chunk in chunks:
            # Handle both dict and object chunks
            if isinstance(chunk, dict):
                delta = chunk.get("delta", "")
                content_parts.append(delta)
            elif hasattr(chunk, "content"):
                content_parts.append(chunk.content)

        content = "".join(content_parts)

        return ConversationTurn(
            content=content,
            finish_reason="stop",
            tool_calls=None,  # Streaming doesn't support tools in MVP
        )

    def _handle_tool_calls(self, turn: ConversationTurn) -> ConversationTurn:
        """
        Execute tool calls and get follow-up response.

        Args:
            turn: Turn with tool calls

        Returns:
            Final ConversationTurn after tool execution
        """
        if not turn.has_tools:
            return turn

        tool_results = []

        for tool_call in turn.tool_calls:
            result = self._execute_tool(tool_call)
            tool_results.append(result)

        # Add tool results to history
        for result in tool_results:
            self._add_tool_message(result)

        # Get follow-up response from LLM
        return self._call_llm()

    def _execute_tool(self, tool_call: ToolCall) -> ToolResult:
        """
        Execute a single tool call.

        Args:
            tool_call: Tool call to execute

        Returns:
            ToolResult with execution result
        """
        try:
            if tool_call.tool_type == ToolType.SHELL:
                return self._execute_shell(tool_call)
            elif tool_call.tool_type == ToolType.READ_FILE:
                return self._execute_read_file(tool_call)
            elif tool_call.tool_type == ToolType.READ_DIRECTORY:
                return self._execute_read_directory(tool_call)
            else:
                return ToolResult(
                    tool_id=tool_call.call_id,
                    name=tool_call.tool_type.value,
                    output=f"Unknown tool type: {tool_call.tool_type.value}",
                    success=False,
                )
        except Exception as e:
            return ToolResult(
                tool_id=tool_call.call_id,
                name=tool_call.tool_type.value,
                output=f"Error: {str(e)}",
                success=False,
            )

    def _execute_shell(self, tool_call: ToolCall) -> ToolResult:
        """Execute shell command."""
        result = self._command_executor.execute(tool_call.command)

        return ToolResult(
            tool_id=tool_call.call_id,
            name=ToolType.SHELL.value,
            output=result.combined_output(),
            success=result.success,
            error_output=result.stderr,
        )

    def _execute_read_file(self, tool_call: ToolCall) -> ToolResult:
        """Execute file read."""
        try:
            file_ctx = self._context_manager.load_file(tool_call.command)
            return ToolResult(
                tool_id=tool_call.call_id,
                name=ToolType.READ_FILE.value,
                output=file_ctx.content,
                success=True,
            )
        except LoadError as e:
            return ToolResult(
                tool_id=tool_call.call_id,
                name=ToolType.READ_FILE.value,
                output=f"Failed to load file: {e.reason}",
                success=False,
            )

    def _execute_read_directory(self, tool_call: ToolCall) -> ToolResult:
        """Execute directory read."""
        recursive = tool_call.arguments.get("recursive", True)

        try:
            dir_ctx = self._context_manager.load_directory(
                tool_call.command,
                recursive=recursive
            )

            # Format directory contents
            output = dir_ctx.format()

            return ToolResult(
                tool_id=tool_call.call_id,
                name=ToolType.READ_DIRECTORY.value,
                output=output,
                success=True,
            )
        except LoadError as e:
            return ToolResult(
                tool_id=tool_call.call_id,
                name=ToolType.READ_DIRECTORY.value,
                output=f"Failed to load directory: {e.reason}",
                success=False,
            )

    def _parse_tool_calls(self, raw_tools: Any) -> List[ToolCall]:
        """
        Parse tool calls from LLM response.

        Args:
            raw_tools: Raw tool calls from LLM

        Returns:
            List of ToolCall objects
        """
        # Handle different formats from different LLMs
        if isinstance(raw_tools, list):
            # Check if already ToolCall objects
            if raw_tools and all(isinstance(t, ToolCall) for t in raw_tools):
                return raw_tools
            return [self._parse_single_tool(t) for t in raw_tools]
        elif isinstance(raw_tools, dict):
            return [self._parse_single_tool(raw_tools)]
        elif isinstance(raw_tools, ToolCall):
            return [raw_tools]
        return []

    def _parse_single_tool(self, raw: Any) -> ToolCall:
        """Parse a single tool call from raw format."""
        # Extract common fields
        tool_type_str = getattr(raw, "type", raw.get("type", "shell")) if isinstance(raw, dict) else getattr(raw, "type", "shell")

        # Map to ToolType
        try:
            tool_type = ToolType(tool_type_str.lower())
        except ValueError:
            tool_type = ToolType.SHELL

        command = getattr(raw, "command", raw.get("command", "")) if isinstance(raw, dict) else getattr(raw, "command", "")
        arguments = getattr(raw, "arguments", raw.get("arguments", {})) if isinstance(raw, dict) else getattr(raw, "arguments", {})
        call_id = getattr(raw, "id", raw.get("id", "")) if isinstance(raw, dict) else getattr(raw, "id", "")

        return ToolCall(
            tool_type=tool_type,
            command=command,
            arguments=arguments if isinstance(arguments, dict) else {},
            call_id=call_id,
        )

    def _format_messages_for_llm(self) -> List[Dict[str, Any]]:
        """
        Format message history for LLM.

        Returns:
            List of message dictionaries
        """
        messages = []

        # Add system prompt if configured
        if self._config.system_prompt:
            messages.append({
                "role": "system",
                "content": self._config.system_prompt,
            })

        # Add conversation history
        for msg in self._history:
            messages.append(msg.format_for_llm())

        return messages

    def _add_user_message(self, content: str) -> None:
        """Add user message to history."""
        self._history.append(Message(role=MessageRole.USER, content=content))

    def _add_assistant_message(
        self,
        content: str,
        tool_result: Optional[ToolResult] = None,
    ) -> None:
        """Add assistant message to history."""
        self._history.append(
            Message(role=MessageRole.ASSISTANT, content=content, tool_result=tool_result)
        )

    def _add_system_message(self, content: str) -> None:
        """Add system message to history."""
        self._history.append(Message(role=MessageRole.SYSTEM, content=content))

    def _add_tool_message(self, tool_result: ToolResult) -> None:
        """Add tool result message to history."""
        self._history.append(
            Message(
                role=MessageRole.TOOL,
                content="",
                tool_result=tool_result,
            )
        )


def create_agent(
    llm_client: Any,
    system_prompt: Optional[str] = None,
    max_tokens: int = 4096,
    temperature: float = 0.7,
) -> Agent:
    """
    Convenience function to create an Agent.

    Args:
        llm_client: LLM client instance
        system_prompt: Optional system prompt
        max_tokens: Maximum tokens for generation
        temperature: Sampling temperature

    Returns:
        Configured Agent instance
    """
    config = AgentConfig(
        llm_client=llm_client,
        system_prompt=system_prompt,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return Agent(config)
