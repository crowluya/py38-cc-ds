"""
Tool base classes and types for Claude Code Python MVP

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class ToolCategory(Enum):
    """Tool category for grouping."""
    FILE = "file"           # Read, Write, Edit, Glob
    SHELL = "shell"         # Bash
    SEARCH = "search"       # Grep, Glob
    AGENT = "agent"         # Task, subagents
    UTILITY = "utility"     # Todo, etc.


@dataclass
class ToolParameter:
    """Definition of a tool parameter."""
    name: str
    type: str  # "string", "integer", "boolean", "array", "object"
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[str]] = None  # Allowed values

    def to_json_schema(self) -> Dict[str, Any]:
        """Convert to JSON Schema format."""
        schema: Dict[str, Any] = {
            "type": self.type,
            "description": self.description,
        }
        if self.enum:
            schema["enum"] = self.enum
        if self.default is not None:
            schema["default"] = self.default
        return schema


@dataclass
class ToolResult:
    """Result of a tool execution."""
    tool_name: str
    success: bool
    output: str
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "tool_name": self.tool_name,
            "success": self.success,
            "output": self.output,
        }
        if self.error:
            result["error"] = self.error
        if self.metadata:
            result["metadata"] = self.metadata
        return result

    @classmethod
    def success_result(cls, tool_name: str, output: str, metadata: Optional[Dict[str, Any]] = None) -> "ToolResult":
        """Create a success result."""
        return cls(tool_name=tool_name, success=True, output=output, metadata=metadata)

    @classmethod
    def error_result(cls, tool_name: str, error: str, output: str = "") -> "ToolResult":
        """Create an error result."""
        return cls(tool_name=tool_name, success=False, output=output, error=error)


@dataclass
class ToolCall:
    """A tool call from the LLM."""
    id: str                          # Unique call ID
    name: str                        # Tool name
    arguments: Dict[str, Any]        # Tool arguments

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "arguments": self.arguments,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolCall":
        """Create from dictionary."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            arguments=data.get("arguments", {}),
        )


class ToolError(Exception):
    """Base exception for tool errors."""

    def __init__(self, message: str, tool_name: str = "", recoverable: bool = True):
        super().__init__(message)
        self.tool_name = tool_name
        self.recoverable = recoverable


class ToolPermissionError(ToolError):
    """Permission denied for tool execution."""

    def __init__(self, message: str, tool_name: str = ""):
        super().__init__(message, tool_name, recoverable=False)


class ToolValidationError(ToolError):
    """Invalid tool parameters."""

    def __init__(self, message: str, tool_name: str = "", parameter: str = ""):
        super().__init__(message, tool_name, recoverable=True)
        self.parameter = parameter


class Tool(ABC):
    """
    Abstract base class for all tools.

    Tools are the primary way the LLM interacts with the system.
    Each tool has a name, description, parameters, and an execute method.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name (used in tool calls)."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description (shown to LLM)."""
        pass

    @property
    def category(self) -> ToolCategory:
        """Tool category for grouping."""
        return ToolCategory.UTILITY

    @property
    def parameters(self) -> List[ToolParameter]:
        """Tool parameters."""
        return []

    @property
    def requires_permission(self) -> bool:
        """Whether this tool requires permission check."""
        return True

    @property
    def is_dangerous(self) -> bool:
        """Whether this tool is potentially dangerous."""
        return False

    def get_json_schema(self) -> Dict[str, Any]:
        """
        Get OpenAI-compatible function schema.

        Returns:
            JSON Schema for the tool
        """
        properties = {}
        required = []

        for param in self.parameters:
            properties[param.name] = param.to_json_schema()
            if param.required:
                required.append(param.name)

        schema: Dict[str, Any] = {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                },
            },
        }

        if required:
            schema["function"]["parameters"]["required"] = required

        return schema

    def validate_arguments(self, arguments: Dict[str, Any]) -> None:
        """
        Validate tool arguments.

        Args:
            arguments: Arguments to validate

        Raises:
            ToolValidationError: If validation fails
        """
        for param in self.parameters:
            if param.required and param.name not in arguments:
                raise ToolValidationError(
                    f"Missing required parameter: {param.name}",
                    tool_name=self.name,
                    parameter=param.name,
                )

            if param.name in arguments:
                value = arguments[param.name]
                # Type checking
                if param.type == "string" and not isinstance(value, str):
                    raise ToolValidationError(
                        f"Parameter {param.name} must be a string",
                        tool_name=self.name,
                        parameter=param.name,
                    )
                elif param.type == "integer" and not isinstance(value, int):
                    raise ToolValidationError(
                        f"Parameter {param.name} must be an integer",
                        tool_name=self.name,
                        parameter=param.name,
                    )
                elif param.type == "boolean" and not isinstance(value, bool):
                    raise ToolValidationError(
                        f"Parameter {param.name} must be a boolean",
                        tool_name=self.name,
                        parameter=param.name,
                    )

                # Enum checking
                if param.enum and value not in param.enum:
                    raise ToolValidationError(
                        f"Parameter {param.name} must be one of: {param.enum}",
                        tool_name=self.name,
                        parameter=param.name,
                    )

    @abstractmethod
    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """
        Execute the tool with given arguments.

        Args:
            arguments: Tool arguments

        Returns:
            ToolResult with execution result
        """
        pass

    def __str__(self) -> str:
        """String representation."""
        return f"Tool({self.name})"

    def __repr__(self) -> str:
        """Repr representation."""
        return f"<Tool name={self.name} category={self.category.value}>"
