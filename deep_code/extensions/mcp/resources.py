"""
MCP Resource Reference Support

Python 3.8.10 compatible
Implements MCP-015: Resource reference syntax parsing and content injection.

Supports @mcp:server:resource syntax for referencing MCP resources.
"""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from deep_code.extensions.mcp.manager import MCPManager


# Resource reference pattern: @mcp:server_name:resource_uri
# Examples:
#   @mcp:notion:project-notes
#   @mcp:filesystem:file:///path/to/file.txt
#   @mcp:github:repo/owner/issues
MCP_RESOURCE_PATTERN = re.compile(
    r"@mcp:([a-zA-Z0-9_-]+):([^\s]+)"
)


@dataclass
class ResourceReference:
    """Parsed MCP resource reference."""

    server_name: str
    resource_uri: str
    original_text: str

    @classmethod
    def parse(cls, text: str) -> Optional["ResourceReference"]:
        """
        Parse a resource reference from text.

        Args:
            text: Text that may contain a resource reference

        Returns:
            ResourceReference or None if not a valid reference
        """
        match = MCP_RESOURCE_PATTERN.match(text)
        if match:
            return cls(
                server_name=match.group(1),
                resource_uri=match.group(2),
                original_text=match.group(0),
            )
        return None


@dataclass
class ResourceContent:
    """Content loaded from an MCP resource."""

    uri: str
    name: str
    content: str
    mime_type: Optional[str] = None
    server_name: Optional[str] = None

    def to_context_string(self) -> str:
        """
        Format resource content for context injection.

        Returns:
            Formatted string for LLM context
        """
        header = f"[Resource: {self.name}]"
        if self.mime_type:
            header += f" ({self.mime_type})"
        if self.server_name:
            header += f" from {self.server_name}"

        return f"{header}\n{self.content}"


def find_resource_references(text: str) -> List[ResourceReference]:
    """
    Find all MCP resource references in text.

    Args:
        text: Text to search

    Returns:
        List of ResourceReference objects
    """
    references = []
    for match in MCP_RESOURCE_PATTERN.finditer(text):
        ref = ResourceReference(
            server_name=match.group(1),
            resource_uri=match.group(2),
            original_text=match.group(0),
        )
        references.append(ref)
    return references


def load_resource(
    manager: MCPManager,
    server_name: str,
    resource_uri: str,
) -> Optional[ResourceContent]:
    """
    Load a resource from an MCP server.

    Args:
        manager: MCP manager
        server_name: Server name
        resource_uri: Resource URI

    Returns:
        ResourceContent or None if failed
    """
    client = manager.get_client(server_name)
    if not client:
        return None

    try:
        result = client.read_resource(resource_uri)

        # Parse result
        contents = result.get("contents", [])
        if not contents:
            return None

        # Get first content item
        content_item = contents[0]

        # Extract text content
        text_content = ""
        if "text" in content_item:
            text_content = content_item["text"]
        elif "blob" in content_item:
            # Binary content - indicate it's binary
            text_content = f"[Binary content: {len(content_item['blob'])} bytes]"

        return ResourceContent(
            uri=content_item.get("uri", resource_uri),
            name=content_item.get("name", resource_uri),
            content=text_content,
            mime_type=content_item.get("mimeType"),
            server_name=server_name,
        )

    except Exception:
        return None


def load_resource_reference(
    manager: MCPManager,
    reference: ResourceReference,
) -> Optional[ResourceContent]:
    """
    Load content for a resource reference.

    Args:
        manager: MCP manager
        reference: Resource reference

    Returns:
        ResourceContent or None if failed
    """
    return load_resource(
        manager,
        reference.server_name,
        reference.resource_uri,
    )


def expand_resource_references(
    text: str,
    manager: MCPManager,
    inline: bool = False,
) -> Tuple[str, List[ResourceContent]]:
    """
    Expand all resource references in text.

    Args:
        text: Text with resource references
        manager: MCP manager
        inline: If True, replace references with content inline.
                If False, return content separately.

    Returns:
        Tuple of (processed text, list of loaded resources)
    """
    references = find_resource_references(text)
    loaded_resources: List[ResourceContent] = []

    if not references:
        return text, loaded_resources

    result_text = text

    for ref in references:
        content = load_resource_reference(manager, ref)
        if content:
            loaded_resources.append(content)

            if inline:
                # Replace reference with content
                result_text = result_text.replace(
                    ref.original_text,
                    content.to_context_string(),
                )
        else:
            if inline:
                # Replace with error message
                result_text = result_text.replace(
                    ref.original_text,
                    f"[Failed to load resource: {ref.original_text}]",
                )

    return result_text, loaded_resources


def format_resources_for_context(resources: List[ResourceContent]) -> str:
    """
    Format multiple resources for context injection.

    Args:
        resources: List of loaded resources

    Returns:
        Formatted string for LLM context
    """
    if not resources:
        return ""

    parts = ["<mcp_resources>"]
    for resource in resources:
        parts.append(f"\n<resource uri=\"{resource.uri}\" server=\"{resource.server_name}\">")
        parts.append(resource.content)
        parts.append("</resource>")
    parts.append("\n</mcp_resources>")

    return "\n".join(parts)


class ResourceResolver:
    """
    Resolves and caches MCP resource references.

    Provides a higher-level interface for resource loading with caching.
    """

    def __init__(self, manager: MCPManager) -> None:
        """
        Initialize resource resolver.

        Args:
            manager: MCP manager
        """
        self._manager = manager
        self._cache: Dict[str, ResourceContent] = {}

    def resolve(
        self,
        server_name: str,
        resource_uri: str,
        use_cache: bool = True,
    ) -> Optional[ResourceContent]:
        """
        Resolve a resource reference.

        Args:
            server_name: Server name
            resource_uri: Resource URI
            use_cache: Whether to use cached content

        Returns:
            ResourceContent or None
        """
        cache_key = f"{server_name}:{resource_uri}"

        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]

        content = load_resource(self._manager, server_name, resource_uri)
        if content:
            self._cache[cache_key] = content

        return content

    def resolve_reference(
        self,
        reference: ResourceReference,
        use_cache: bool = True,
    ) -> Optional[ResourceContent]:
        """
        Resolve a parsed resource reference.

        Args:
            reference: Resource reference
            use_cache: Whether to use cached content

        Returns:
            ResourceContent or None
        """
        return self.resolve(
            reference.server_name,
            reference.resource_uri,
            use_cache,
        )

    def resolve_text(
        self,
        text: str,
        use_cache: bool = True,
    ) -> Tuple[str, List[ResourceContent]]:
        """
        Resolve all resource references in text.

        Args:
            text: Text with resource references
            use_cache: Whether to use cached content

        Returns:
            Tuple of (text with references removed, loaded resources)
        """
        references = find_resource_references(text)
        loaded: List[ResourceContent] = []

        # Remove references from text
        result_text = text
        for ref in references:
            result_text = result_text.replace(ref.original_text, "").strip()

            content = self.resolve_reference(ref, use_cache)
            if content:
                loaded.append(content)

        return result_text, loaded

    def clear_cache(self) -> None:
        """Clear the resource cache."""
        self._cache.clear()

    def invalidate(self, server_name: str, resource_uri: str) -> None:
        """
        Invalidate a cached resource.

        Args:
            server_name: Server name
            resource_uri: Resource URI
        """
        cache_key = f"{server_name}:{resource_uri}"
        if cache_key in self._cache:
            del self._cache[cache_key]

    def list_available_resources(self, server_name: str) -> List[Dict[str, Any]]:
        """
        List available resources from a server.

        Args:
            server_name: Server name

        Returns:
            List of resource definitions
        """
        client = self._manager.get_client(server_name)
        if not client:
            return []

        try:
            return client.list_resources()
        except Exception:
            return []
