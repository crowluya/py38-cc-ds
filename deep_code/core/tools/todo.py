"""
TodoWrite tool for DeepCode

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)

Provides task list management for tracking progress during conversations.
"""

from typing import Any, Dict, List, Optional

from deep_code.core.tools.base import (
    Tool,
    ToolCategory,
    ToolParameter,
    ToolResult,
)


# Valid todo statuses
VALID_STATUSES = {"pending", "in_progress", "completed"}


class TodoSession:
    """
    Session storage for todo items.

    Allows sharing todo state between multiple tool instances.
    """

    def __init__(self):
        self._todos: List[Dict[str, Any]] = []

    def get_todos(self) -> List[Dict[str, Any]]:
        """Get all todos."""
        return list(self._todos)

    def set_todos(self, todos: List[Dict[str, Any]]) -> None:
        """Set all todos (replaces existing)."""
        self._todos = list(todos)

    def clear(self) -> None:
        """Clear all todos."""
        self._todos = []


class TodoWriteTool(Tool):
    """
    Tool for managing a task list during conversations.

    Features:
    - Add/update/remove todo items
    - Track status: pending, in_progress, completed
    - Format todos for display
    - Share state via session
    """

    def __init__(self, session: Optional[TodoSession] = None):
        """
        Initialize TodoWrite tool.

        Args:
            session: Optional session for sharing state between instances
        """
        self._session = session or TodoSession()

    @property
    def name(self) -> str:
        return "TodoWrite"

    @property
    def description(self) -> str:
        return (
            "Manage a structured task list for tracking progress. "
            "Use this tool to create, update, and track tasks during complex operations. "
            "Each todo has: content (task description), status (pending/in_progress/completed), "
            "and activeForm (present continuous form shown during execution)."
        )

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.UTILITY

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="todos",
                type="array",
                description=(
                    "The updated todo list. Each item must have: "
                    "content (string, task description), "
                    "status (string, one of: pending, in_progress, completed), "
                    "activeForm (string, present continuous form)"
                ),
                required=True,
            ),
        ]

    @property
    def requires_permission(self) -> bool:
        return False

    @property
    def is_dangerous(self) -> bool:
        return False

    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """
        Execute the TodoWrite tool.

        Args:
            arguments: Tool arguments containing 'todos' list

        Returns:
            ToolResult with success/failure status
        """
        self.validate_arguments(arguments)

        todos = arguments.get("todos", [])

        # Validate todos format
        if not isinstance(todos, list):
            return ToolResult.error_result(
                self.name,
                "todos must be a list",
            )

        # Validate each todo item
        validated_todos = []
        for i, todo in enumerate(todos):
            if not isinstance(todo, dict):
                return ToolResult.error_result(
                    self.name,
                    f"Todo item {i} must be an object",
                )

            # Check required fields
            content = todo.get("content")
            status = todo.get("status")
            active_form = todo.get("activeForm")

            if not content or not isinstance(content, str):
                return ToolResult.error_result(
                    self.name,
                    f"Todo item {i} missing required field 'content' (string)",
                )

            if not status or not isinstance(status, str):
                return ToolResult.error_result(
                    self.name,
                    f"Todo item {i} missing required field 'status' (string)",
                )

            if not active_form or not isinstance(active_form, str):
                return ToolResult.error_result(
                    self.name,
                    f"Todo item {i} missing required field 'activeForm' (string)",
                )

            # Validate status
            if status not in VALID_STATUSES:
                return ToolResult.error_result(
                    self.name,
                    f"Todo item {i} has invalid status '{status}'. "
                    f"Must be one of: {', '.join(sorted(VALID_STATUSES))}",
                )

            validated_todos.append({
                "content": content,
                "status": status,
                "activeForm": active_form,
            })

        # Update session
        self._session.set_todos(validated_todos)

        # Format output
        output = self.format_todos()

        return ToolResult.success_result(
            self.name,
            output,
            metadata={
                "todo_count": len(validated_todos),
                "pending": len([t for t in validated_todos if t["status"] == "pending"]),
                "in_progress": len([t for t in validated_todos if t["status"] == "in_progress"]),
                "completed": len([t for t in validated_todos if t["status"] == "completed"]),
            },
        )

    def get_todos(self) -> List[Dict[str, Any]]:
        """
        Get all todos.

        Returns:
            List of todo items
        """
        return self._session.get_todos()

    def get_todos_by_status(self, status: str) -> List[Dict[str, Any]]:
        """
        Get todos filtered by status.

        Args:
            status: Status to filter by

        Returns:
            List of matching todo items
        """
        return [t for t in self._session.get_todos() if t.get("status") == status]

    def format_todos(self) -> str:
        """
        Format todos for display.

        Returns:
            Formatted string representation of todos
        """
        todos = self._session.get_todos()

        if not todos:
            return "No todos in list."

        lines = []
        for i, todo in enumerate(todos, 1):
            status = todo.get("status", "pending")
            content = todo.get("content", "")

            # Status indicator
            if status == "completed":
                indicator = "[x]"
            elif status == "in_progress":
                indicator = "[~]"
            else:
                indicator = "[ ]"

            lines.append(f"{i}. {indicator} {content}")

        return "\n".join(lines)

    def get_json_schema(self) -> Dict[str, Any]:
        """
        Get JSON schema for the tool.

        Returns:
            JSON schema dictionary
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "todos": {
                            "type": "array",
                            "description": "The updated todo list",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "content": {
                                        "type": "string",
                                        "description": "Task description",
                                        "minLength": 1,
                                    },
                                    "status": {
                                        "type": "string",
                                        "enum": ["pending", "in_progress", "completed"],
                                        "description": "Task status",
                                    },
                                    "activeForm": {
                                        "type": "string",
                                        "description": "Present continuous form shown during execution",
                                        "minLength": 1,
                                    },
                                },
                                "required": ["content", "status", "activeForm"],
                            },
                        },
                    },
                    "required": ["todos"],
                },
            },
        }
