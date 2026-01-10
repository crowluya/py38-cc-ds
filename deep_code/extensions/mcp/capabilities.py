"""
MCP Capabilities - Tools, Resources, and Prompts Discovery

Python 3.8.10 compatible
Implements capability discovery for MCP servers.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class MCPTool:
    """MCP tool definition."""

    name: str
    description: str
    inputSchema: Dict[str, Any]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPTool":
        """Create from dictionary."""
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            inputSchema=data.get("inputSchema", {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.inputSchema,
        }


@dataclass
class MCPResource:
    """MCP resource definition."""

    uri: str
    name: str
    description: Optional[str] = None
    mimeType: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPResource":
        """Create from dictionary."""
        return cls(
            uri=data["uri"],
            name=data["name"],
            description=data.get("description"),
            mimeType=data.get("mimeType"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "uri": self.uri,
            "name": self.name,
        }
        if self.description:
            result["description"] = self.description
        if self.mimeType:
            result["mimeType"] = self.mimeType
        return result


@dataclass
class MCPPrompt:
    """MCP prompt definition."""

    name: str
    description: Optional[str] = None
    arguments: Optional[List[Dict[str, Any]]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPPrompt":
        """Create from dictionary."""
        return cls(
            name=data["name"],
            description=data.get("description"),
            arguments=data.get("arguments"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {"name": self.name}
        if self.description:
            result["description"] = self.description
        if self.arguments:
            result["arguments"] = self.arguments
        return result


class CapabilityCache:
    """
    Cache for MCP server capabilities.
    
    Stores tools, resources, and prompts with automatic refresh support.
    """

    def __init__(self) -> None:
        """Initialize capability cache."""
        self._tools: Dict[str, MCPTool] = {}
        self._resources: Dict[str, MCPResource] = {}
        self._prompts: Dict[str, MCPPrompt] = {}

    def update_tools(self, tools: List[Dict[str, Any]]) -> None:
        """
        Update tools cache.

        Args:
            tools: List of tool definitions
        """
        self._tools.clear()
        for tool_data in tools:
            tool = MCPTool.from_dict(tool_data)
            self._tools[tool.name] = tool

    def update_resources(self, resources: List[Dict[str, Any]]) -> None:
        """
        Update resources cache.

        Args:
            resources: List of resource definitions
        """
        self._resources.clear()
        for resource_data in resources:
            resource = MCPResource.from_dict(resource_data)
            self._resources[resource.uri] = resource

    def update_prompts(self, prompts: List[Dict[str, Any]]) -> None:
        """
        Update prompts cache.

        Args:
            prompts: List of prompt definitions
        """
        self._prompts.clear()
        for prompt_data in prompts:
            prompt = MCPPrompt.from_dict(prompt_data)
            self._prompts[prompt.name] = prompt

    def get_tool(self, name: str) -> Optional[MCPTool]:
        """Get tool by name."""
        return self._tools.get(name)

    def get_resource(self, uri: str) -> Optional[MCPResource]:
        """Get resource by URI."""
        return self._resources.get(uri)

    def get_prompt(self, name: str) -> Optional[MCPPrompt]:
        """Get prompt by name."""
        return self._prompts.get(name)

    def list_tools(self) -> List[MCPTool]:
        """List all tools."""
        return list(self._tools.values())

    def list_resources(self) -> List[MCPResource]:
        """List all resources."""
        return list(self._resources.values())

    def list_prompts(self) -> List[MCPPrompt]:
        """List all prompts."""
        return list(self._prompts.values())

    def clear(self) -> None:
        """Clear all cached capabilities."""
        self._tools.clear()
        self._resources.clear()
        self._prompts.clear()
