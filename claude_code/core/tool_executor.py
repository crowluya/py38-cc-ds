"""
Tool Executor for Claude Code Python MVP

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)

Executes tool calls from LLM responses with:
- Permission checking
- Error handling
- Execution logging
- Callback support
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from claude_code.core.tools.base import (
    Tool,
    ToolCall,
    ToolResult,
    ToolError,
    ToolValidationError,
)
from claude_code.core.tools.registry import ToolRegistry


@dataclass
class ExecutionRecord:
    """Record of a tool execution."""
    tool_call: ToolCall
    result: ToolResult
    timestamp: float = 0.0


class ToolExecutor:
    """
    Executes tool calls from LLM responses.

    Features:
    - Tool lookup from registry
    - Permission/approval checking for dangerous tools
    - Error handling and recovery
    - Execution history logging
    - Callback support for UI updates
    """

    def __init__(
        self,
        registry: ToolRegistry,
        require_approval: bool = False,
        approval_callback: Optional[Callable[[ToolCall], bool]] = None,
        on_tool_start: Optional[Callable[[ToolCall], None]] = None,
        on_tool_complete: Optional[Callable[[ToolCall, ToolResult], None]] = None,
        history_limit: int = 100,
    ):
        """
        Initialize tool executor.

        Args:
            registry: Tool registry to look up tools
            require_approval: Whether to require approval for dangerous tools
            approval_callback: Callback to request approval (returns True if approved)
            on_tool_start: Callback when tool execution starts
            on_tool_complete: Callback when tool execution completes
            history_limit: Maximum number of executions to keep in history
        """
        self._registry = registry
        self._require_approval = require_approval
        self._approval_callback = approval_callback
        self._on_tool_start = on_tool_start
        self._on_tool_complete = on_tool_complete
        self._history_limit = history_limit
        self._history: List[Dict[str, Any]] = []

    def execute(self, tool_call: ToolCall) -> ToolResult:
        """
        Execute a single tool call.

        Args:
            tool_call: The tool call to execute

        Returns:
            ToolResult with execution result
        """
        import time
        start_time = time.time()

        # Notify start callback
        if self._on_tool_start:
            try:
                self._on_tool_start(tool_call)
            except Exception:
                pass  # Don't let callback errors affect execution

        try:
            result = self._execute_internal(tool_call)
        except Exception as e:
            result = ToolResult.error_result(
                tool_call.name,
                f"Unexpected error executing tool: {str(e)}",
            )

        # Record execution
        self._record_execution(tool_call, result, start_time)

        # Notify complete callback
        if self._on_tool_complete:
            try:
                self._on_tool_complete(tool_call, result)
            except Exception:
                pass  # Don't let callback errors affect execution

        return result

    def _execute_internal(self, tool_call: ToolCall) -> ToolResult:
        """
        Internal execution logic.

        Args:
            tool_call: The tool call to execute

        Returns:
            ToolResult with execution result
        """
        # Look up tool
        try:
            tool = self._registry.get(tool_call.name)
        except KeyError:
            return ToolResult.error_result(
                tool_call.name,
                f"Tool not found: {tool_call.name}",
            )

        # Check if tool is enabled
        if not self._registry.is_enabled(tool_call.name):
            return ToolResult.error_result(
                tool_call.name,
                f"Tool is disabled: {tool_call.name}",
            )

        # Check permissions for dangerous tools
        if self._require_approval and tool.is_dangerous:
            if not self._check_approval(tool_call, tool):
                return ToolResult.error_result(
                    tool_call.name,
                    f"Permission denied: Tool execution was not approved",
                )

        # Execute tool
        try:
            result = tool.execute(tool_call.arguments)
            return result
        except ToolValidationError as e:
            return ToolResult.error_result(
                tool_call.name,
                f"Validation error: {str(e)}",
            )
        except ToolError as e:
            return ToolResult.error_result(
                tool_call.name,
                f"Tool error: {str(e)}",
            )
        except Exception as e:
            return ToolResult.error_result(
                tool_call.name,
                f"Error executing tool: {str(e)}",
            )

    def _check_approval(self, tool_call: ToolCall, tool: Tool) -> bool:
        """
        Check if tool execution is approved.

        Args:
            tool_call: The tool call
            tool: The tool to execute

        Returns:
            True if approved, False otherwise
        """
        if not self._approval_callback:
            # No callback means no approval possible
            return False

        try:
            return self._approval_callback(tool_call)
        except Exception:
            # If callback fails, deny by default
            return False

    def _record_execution(
        self,
        tool_call: ToolCall,
        result: ToolResult,
        start_time: float,
    ) -> None:
        """
        Record execution in history.

        Args:
            tool_call: The tool call
            result: The execution result
            start_time: When execution started
        """
        import time

        record = {
            "tool_call": tool_call,
            "result": result,
            "timestamp": start_time,
            "duration": time.time() - start_time,
        }

        self._history.append(record)

        # Trim history if needed
        if len(self._history) > self._history_limit:
            self._history = self._history[-self._history_limit:]

    def execute_all(self, tool_calls: List[ToolCall]) -> List[ToolResult]:
        """
        Execute multiple tool calls sequentially.

        Args:
            tool_calls: List of tool calls to execute

        Returns:
            List of ToolResults in same order as input
        """
        results = []
        for tool_call in tool_calls:
            result = self.execute(tool_call)
            results.append(result)
        return results

    def get_history(self) -> List[Dict[str, Any]]:
        """
        Get execution history.

        Returns:
            List of execution records
        """
        return list(self._history)

    def clear_history(self) -> None:
        """Clear execution history."""
        self._history.clear()

    def get_last_result(self) -> Optional[ToolResult]:
        """
        Get the last execution result.

        Returns:
            Last ToolResult or None if no executions
        """
        if self._history:
            return self._history[-1]["result"]
        return None

    def get_stats(self) -> Dict[str, Any]:
        """
        Get execution statistics.

        Returns:
            Dictionary with execution stats
        """
        if not self._history:
            return {
                "total_executions": 0,
                "successful": 0,
                "failed": 0,
                "tools_used": {},
            }

        successful = sum(1 for r in self._history if r["result"].success)
        failed = len(self._history) - successful

        tools_used: Dict[str, int] = {}
        for record in self._history:
            tool_name = record["tool_call"].name
            tools_used[tool_name] = tools_used.get(tool_name, 0) + 1

        return {
            "total_executions": len(self._history),
            "successful": successful,
            "failed": failed,
            "success_rate": successful / len(self._history) if self._history else 0,
            "tools_used": tools_used,
        }
