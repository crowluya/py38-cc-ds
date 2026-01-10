"""
Agent Loop - Complete conversation loop implementation (T021)

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)

Provides:
- Complete conversation loop with LLM
- Tool execution integration
- Streaming support
- Callback hooks for UI integration
- Error handling and recovery
"""

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Iterator, List, Optional, Union

from deep_code.core.tools.base import ToolCall, ToolResult
from deep_code.core.tools.registry import ToolRegistry


# Logger for this module
logger = logging.getLogger(__name__)


class AgentLoopError(Exception):
    """Base exception for agent loop errors."""

    def __init__(self, message: str, cause: Optional[Exception] = None):
        super().__init__(message)
        self.cause = cause


class MessageRole(Enum):
    """Message role in conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    """A message in the conversation history."""
    role: MessageRole
    content: str
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for LLM API."""
        result: Dict[str, Any] = {
            "role": self.role.value,
            "content": self.content,
        }
        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id
        if self.tool_calls:
            result["tool_calls"] = self.tool_calls
        if self.name:
            result["name"] = self.name
        return result


@dataclass
class TurnResult:
    """Result of a conversation turn."""
    content: str
    finish_reason: str
    tool_calls: Optional[List[ToolCall]] = None
    raw_response: Optional[Any] = None

    @property
    def has_tool_calls(self) -> bool:
        """Check if this turn has tool calls."""
        return self.tool_calls is not None and len(self.tool_calls) > 0


@dataclass
class AgentLoopConfig:
    """Configuration for AgentLoop."""
    llm_client: Any
    tool_registry: Optional[ToolRegistry] = None
    system_prompt: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7
    max_tool_rounds: int = 10
    stream: bool = False

    # Callbacks
    on_stream_chunk: Optional[Callable[[Dict[str, Any]], None]] = None
    on_tool_start: Optional[Callable[[str, Dict[str, Any]], None]] = None
    on_tool_end: Optional[Callable[[str, ToolResult], None]] = None
    on_turn_start: Optional[Callable[[], None]] = None
    on_turn_end: Optional[Callable[[TurnResult], None]] = None


class AgentLoop:
    """
    Complete agent conversation loop.

    Manages:
    - Conversation history
    - LLM calls
    - Tool execution
    - Streaming responses
    - Callbacks for UI integration
    """

    def __init__(self, config: AgentLoopConfig) -> None:
        """
        Initialize AgentLoop.

        Args:
            config: Loop configuration
        """
        self._config = config
        self._history: List[Message] = []
        self._tool_registry = config.tool_registry

        logger.debug("AgentLoop initialized with config: max_tokens=%d, temperature=%.2f",
                     config.max_tokens, config.temperature)

    def run_turn(self, user_input: str) -> TurnResult:
        """
        Run a single conversation turn.

        Args:
            user_input: User message

        Returns:
            TurnResult with response

        Raises:
            AgentLoopError: If an error occurs
        """
        logger.info("Starting turn with input: %s...", user_input[:50])

        # Notify turn start
        if self._config.on_turn_start:
            try:
                self._config.on_turn_start()
            except Exception as e:
                logger.warning("on_turn_start callback failed: %s", e)

        # Add user message to history
        self._add_message(MessageRole.USER, user_input)

        try:
            # Run tool loop
            result = self._run_tool_loop()

            # Notify turn end
            if self._config.on_turn_end:
                try:
                    self._config.on_turn_end(result)
                except Exception as e:
                    logger.warning("on_turn_end callback failed: %s", e)

            logger.info("Turn completed with finish_reason: %s", result.finish_reason)
            return result

        except Exception as e:
            logger.error("Turn failed with error: %s", e)
            raise AgentLoopError(f"Turn failed: {str(e)}", cause=e)

    def run_turn_stream(self, user_input: str) -> Iterator[Dict[str, Any]]:
        """
        Run a conversation turn with streaming.

        Args:
            user_input: User message

        Yields:
            Response chunks

        Raises:
            AgentLoopError: If an error occurs
        """
        logger.info("Starting streaming turn")

        # Add user message to history
        self._add_message(MessageRole.USER, user_input)

        try:
            # Get streaming response
            messages = self._build_messages()
            kwargs = self._build_llm_kwargs()

            stream = self._config.llm_client.chat_completion_stream(
                messages=messages,
                **kwargs
            )

            content_parts = []

            for chunk in stream:
                # Extract delta content
                if isinstance(chunk, dict):
                    delta = chunk.get("delta", "")
                else:
                    delta = getattr(chunk, "delta", "")

                if delta:
                    content_parts.append(delta)

                # Notify callback
                if self._config.on_stream_chunk:
                    try:
                        self._config.on_stream_chunk(chunk)
                    except Exception as e:
                        logger.warning("on_stream_chunk callback failed: %s", e)

                yield chunk

            # Add assistant message to history
            full_content = "".join(content_parts)
            self._add_message(MessageRole.ASSISTANT, full_content)

        except Exception as e:
            logger.error("Streaming turn failed: %s", e)
            raise AgentLoopError(f"Streaming failed: {str(e)}", cause=e)

    def _run_tool_loop(self) -> TurnResult:
        """
        Run the tool execution loop.

        Returns:
            Final TurnResult
        """
        tool_round = 0
        max_rounds = self._config.max_tool_rounds

        while tool_round < max_rounds:
            logger.debug("Tool loop round %d/%d", tool_round + 1, max_rounds)

            # Call LLM
            result = self._call_llm()

            # Check if we have tool calls
            if not result.has_tool_calls:
                # No tool calls, add response and return
                self._add_message(MessageRole.ASSISTANT, result.content)
                return result

            # Add assistant message with tool calls
            self._add_assistant_with_tool_calls(result)

            # Execute tool calls
            for tool_call in result.tool_calls:
                tool_result = self._execute_tool(tool_call)
                self._add_tool_result(tool_call, tool_result)

            tool_round += 1

        # Max rounds reached, get final response without tools
        logger.warning("Max tool rounds (%d) reached", max_rounds)
        result = self._call_llm()
        self._add_message(MessageRole.ASSISTANT, result.content)
        return result

    def _call_llm(self) -> TurnResult:
        """
        Call the LLM.

        Returns:
            TurnResult with response
        """
        messages = self._build_messages()
        kwargs = self._build_llm_kwargs()

        # Add tools if registry is available
        if self._tool_registry:
            tools = self._tool_registry.get_tools_schema(include_disabled=False)
            if tools:
                kwargs["tools"] = tools

        logger.debug("Calling LLM with %d messages", len(messages))

        response = self._config.llm_client.chat_completion(
            messages=messages,
            **kwargs
        )

        return self._parse_response(response)

    def _parse_response(self, response: Any) -> TurnResult:
        """
        Parse LLM response into TurnResult.

        Args:
            response: Raw LLM response

        Returns:
            Parsed TurnResult
        """
        # Extract fields from response (dict or object)
        if isinstance(response, dict):
            content = response.get("content", "") or ""
            finish_reason = response.get("finish_reason", "stop")
            tool_calls_data = response.get("tool_calls")
        else:
            content = getattr(response, "content", "") or ""
            finish_reason = getattr(response, "finish_reason", "stop")
            tool_calls_data = getattr(response, "tool_calls", None)

        # Parse tool calls
        tool_calls = None
        if tool_calls_data:
            tool_calls = self._parse_tool_calls(tool_calls_data)

        return TurnResult(
            content=content,
            finish_reason=finish_reason,
            tool_calls=tool_calls,
            raw_response=response,
        )

    def _parse_tool_calls(self, raw_tools: Any) -> List[ToolCall]:
        """
        Parse tool calls from LLM response.

        Args:
            raw_tools: Raw tool calls data

        Returns:
            List of ToolCall objects
        """
        if not raw_tools:
            return []

        tool_calls = []

        items = raw_tools if isinstance(raw_tools, list) else [raw_tools]

        for raw in items:
            tool_call = self._parse_single_tool_call(raw)
            if tool_call:
                tool_calls.append(tool_call)

        return tool_calls

    def _parse_single_tool_call(self, raw: Any) -> Optional[ToolCall]:
        """
        Parse a single tool call.

        Args:
            raw: Raw tool call data

        Returns:
            ToolCall or None
        """
        if isinstance(raw, dict):
            call_id = raw.get("id", "")
            name = raw.get("name", "")
            arguments = raw.get("arguments", {})
        else:
            call_id = getattr(raw, "id", "")
            name = getattr(raw, "name", "")
            arguments = getattr(raw, "arguments", {})

        if not name:
            return None

        # Handle JSON string arguments
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                arguments = {}

        return ToolCall(
            id=call_id,
            name=name,
            arguments=arguments if isinstance(arguments, dict) else {},
        )

    def _execute_tool(self, tool_call: ToolCall) -> ToolResult:
        """
        Execute a tool call.

        Args:
            tool_call: Tool call to execute

        Returns:
            ToolResult
        """
        logger.info("Executing tool: %s", tool_call.name)

        # Notify tool start
        if self._config.on_tool_start:
            try:
                self._config.on_tool_start(tool_call.name, tool_call.arguments)
            except Exception as e:
                logger.warning("on_tool_start callback failed: %s", e)

        try:
            # Get tool from registry
            if not self._tool_registry:
                result = ToolResult.error_result(
                    tool_call.name,
                    "No tool registry configured",
                )
            elif not self._tool_registry.has(tool_call.name):
                result = ToolResult.error_result(
                    tool_call.name,
                    f"Unknown tool: {tool_call.name}",
                )
            else:
                tool = self._tool_registry.get(tool_call.name)
                result = tool.execute(tool_call.arguments)

        except Exception as e:
            logger.error("Tool execution failed: %s", e)
            result = ToolResult.error_result(
                tool_call.name,
                f"Tool execution failed: {str(e)}",
            )

        # Notify tool end
        if self._config.on_tool_end:
            try:
                self._config.on_tool_end(tool_call.name, result)
            except Exception as e:
                logger.warning("on_tool_end callback failed: %s", e)

        logger.info("Tool %s completed: success=%s", tool_call.name, result.success)
        return result

    def _build_messages(self) -> List[Dict[str, Any]]:
        """
        Build messages list for LLM.

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
            messages.append(msg.to_dict())

        return messages

    def _build_llm_kwargs(self) -> Dict[str, Any]:
        """
        Build kwargs for LLM call.

        Returns:
            Kwargs dictionary
        """
        return {
            "max_tokens": self._config.max_tokens,
            "temperature": self._config.temperature,
        }

    def _add_message(self, role: MessageRole, content: str) -> None:
        """
        Add a message to history.

        Args:
            role: Message role
            content: Message content
        """
        self._history.append(Message(role=role, content=content))

    def _add_assistant_with_tool_calls(self, result: TurnResult) -> None:
        """
        Add assistant message with tool calls to history.

        Args:
            result: Turn result with tool calls
        """
        tool_calls_data = None
        if result.tool_calls:
            tool_calls_data = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments),
                    },
                }
                for tc in result.tool_calls
            ]

        self._history.append(Message(
            role=MessageRole.ASSISTANT,
            content=result.content or "",
            tool_calls=tool_calls_data,
        ))

    def _add_tool_result(self, tool_call: ToolCall, result: ToolResult) -> None:
        """
        Add tool result to history.

        Args:
            tool_call: The tool call
            result: The tool result
        """
        content = result.output
        if result.error:
            content = f"Error: {result.error}\n{content}" if content else f"Error: {result.error}"

        self._history.append(Message(
            role=MessageRole.TOOL,
            content=content,
            tool_call_id=tool_call.id,
            name=tool_call.name,
        ))

    def get_history(self) -> List[Message]:
        """
        Get conversation history.

        Returns:
            List of messages
        """
        return list(self._history)

    def reset(self) -> None:
        """Reset conversation history."""
        self._history = []
        logger.info("Conversation history reset")

    @property
    def config(self) -> AgentLoopConfig:
        """Get configuration."""
        return self._config


def create_agent_loop(
    llm_client: Any,
    tool_registry: Optional[ToolRegistry] = None,
    system_prompt: Optional[str] = None,
    **kwargs: Any,
) -> AgentLoop:
    """
    Convenience function to create an AgentLoop.

    Args:
        llm_client: LLM client instance
        tool_registry: Optional tool registry
        system_prompt: Optional system prompt
        **kwargs: Additional config options

    Returns:
        Configured AgentLoop
    """
    config = AgentLoopConfig(
        llm_client=llm_client,
        tool_registry=tool_registry,
        system_prompt=system_prompt,
        **kwargs,
    )
    return AgentLoop(config)
