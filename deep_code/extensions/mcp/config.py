"""
MCP Configuration - Config File Parsing and Management

Python 3.8.10 compatible
Implements MCP server configuration parsing with environment variable expansion.
"""

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class MCPServerConfig:
    """MCP server configuration."""

    name: str
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    transport_type: str = "stdio"  # stdio, http, sse
    url: Optional[str] = None
    headers: Optional[Dict[str, str]] = None

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> "MCPServerConfig":
        """
        Create from dictionary.

        Args:
            name: Server name
            data: Server configuration data

        Returns:
            MCPServerConfig instance
        """
        # Determine transport type
        transport_type = data.get("type", "stdio")
        if "command" in data and transport_type == "stdio":
            transport_type = "stdio"
        elif "url" in data:
            if transport_type not in ("http", "sse"):
                transport_type = "http"

        return cls(
            name=name,
            command=data.get("command"),
            args=data.get("args"),
            env=data.get("env"),
            transport_type=transport_type,
            url=data.get("url"),
            headers=data.get("headers"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result: Dict[str, Any] = {}

        if self.transport_type == "stdio":
            if self.command:
                result["command"] = self.command
            if self.args:
                result["args"] = self.args
        else:
            result["type"] = self.transport_type
            if self.url:
                result["url"] = self.url
            if self.headers:
                result["headers"] = self.headers

        if self.env:
            result["env"] = self.env

        return result


# Environment variable pattern: ${VAR} or ${VAR:-default}
ENV_VAR_PATTERN = re.compile(r"\$\{([^}:]+)(?::-([^}]*))?\}")


def expand_env_vars(value: str) -> str:
    """
    Expand environment variables in a string.

    Supports:
    - ${VAR} - replaced with environment variable value
    - ${VAR:-default} - replaced with value or default if not set

    Args:
        value: String with potential environment variables

    Returns:
        String with environment variables expanded
    """
    def replace_var(match: re.Match) -> str:
        var_name = match.group(1)
        default_value = match.group(2)

        env_value = os.environ.get(var_name)
        if env_value is not None:
            return env_value
        elif default_value is not None:
            return default_value
        else:
            # Return empty string if not found and no default
            return ""

    return ENV_VAR_PATTERN.sub(replace_var, value)


def expand_config_env_vars(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively expand environment variables in config.

    Args:
        config: Configuration dictionary

    Returns:
        Configuration with environment variables expanded
    """
    result: Dict[str, Any] = {}

    for key, value in config.items():
        if isinstance(value, str):
            result[key] = expand_env_vars(value)
        elif isinstance(value, dict):
            result[key] = expand_config_env_vars(value)
        elif isinstance(value, list):
            result[key] = [
                expand_env_vars(item) if isinstance(item, str) else item
                for item in value
            ]
        else:
            result[key] = value

    return result


@dataclass
class MCPConfig:
    """
    MCP configuration container.

    Holds all MCP server configurations from a config file.
    """

    servers: Dict[str, MCPServerConfig] = field(default_factory=dict)
    source_path: Optional[Path] = None

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
        source_path: Optional[Path] = None,
        expand_env: bool = True,
    ) -> "MCPConfig":
        """
        Create from dictionary.

        Args:
            data: Configuration data
            source_path: Path to source config file
            expand_env: Whether to expand environment variables

        Returns:
            MCPConfig instance
        """
        servers: Dict[str, MCPServerConfig] = {}

        mcp_servers = data.get("mcpServers", {})
        for name, server_data in mcp_servers.items():
            if expand_env:
                # Expand environment variables
                expanded_data = expand_config_env_vars(server_data)
            else:
                expanded_data = server_data
            servers[name] = MCPServerConfig.from_dict(name, expanded_data)

        return cls(servers=servers, source_path=source_path)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "mcpServers": {
                name: server.to_dict()
                for name, server in self.servers.items()
            }
        }

    def get_server(self, name: str) -> Optional[MCPServerConfig]:
        """Get server configuration by name."""
        return self.servers.get(name)

    def list_servers(self) -> List[str]:
        """List all server names."""
        return list(self.servers.keys())

    def add_server(self, config: MCPServerConfig) -> None:
        """Add or update a server configuration."""
        self.servers[config.name] = config

    def remove_server(self, name: str) -> bool:
        """
        Remove a server configuration.

        Returns:
            True if removed, False if not found
        """
        if name in self.servers:
            del self.servers[name]
            return True
        return False

    def merge(self, other: "MCPConfig") -> "MCPConfig":
        """
        Merge with another configuration.

        Other configuration takes precedence for duplicate servers.

        Args:
            other: Other MCPConfig to merge

        Returns:
            New merged MCPConfig
        """
        merged_servers = dict(self.servers)
        merged_servers.update(other.servers)
        return MCPConfig(servers=merged_servers)

    def __len__(self) -> int:
        """Return number of configured servers."""
        return len(self.servers)

    def __contains__(self, name: str) -> bool:
        """Check if server is configured."""
        return name in self.servers

    def __iter__(self):
        """Iterate over server names."""
        return iter(self.servers)


def load_config_file(path: Path) -> MCPConfig:
    """
    Load MCP configuration from a JSON file.

    Args:
        path: Path to config file

    Returns:
        MCPConfig instance

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return MCPConfig.from_dict(data, source_path=path)


def save_config_file(config: MCPConfig, path: Path) -> None:
    """
    Save MCP configuration to a JSON file.

    Args:
        config: Configuration to save
        path: Path to save to
    """
    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)


def get_default_config_paths(project_root: Optional[Path] = None) -> Dict[str, Path]:
    """
    Get default configuration file paths.

    Args:
        project_root: Project root directory (defaults to cwd)

    Returns:
        Dictionary with config paths:
        - user: User-level config (~/.deepcode/mcp.json)
        - project: Project-level config (.deepcode/mcp.json)
        - local: Local config (.deepcode/mcp.local.json)
    """
    if project_root is None:
        project_root = Path.cwd()

    user_home = Path.home()

    return {
        "user": user_home / ".deepcode" / "mcp.json",
        "project": project_root / ".deepcode" / "mcp.json",
        "local": project_root / ".deepcode" / "mcp.local.json",
    }


# MCP-011: Configuration Scope Management

class ConfigScope:
    """Configuration scope constants."""

    USER = "user"
    PROJECT = "project"
    LOCAL = "local"

    # Priority order (lowest to highest)
    PRIORITY_ORDER = [USER, PROJECT, LOCAL]


def load_scoped_config(
    project_root: Optional[Path] = None,
    scopes: Optional[List[str]] = None,
) -> MCPConfig:
    """
    Load and merge MCP configuration from multiple scopes.

    Configurations are merged in priority order:
    1. User-level (~/.deepcode/mcp.json) - lowest priority
    2. Project-level (.deepcode/mcp.json)
    3. Local-level (.deepcode/mcp.local.json) - highest priority

    Args:
        project_root: Project root directory (defaults to cwd)
        scopes: List of scopes to load (defaults to all)

    Returns:
        Merged MCPConfig
    """
    if scopes is None:
        scopes = ConfigScope.PRIORITY_ORDER

    paths = get_default_config_paths(project_root)
    merged_config = MCPConfig()

    for scope in ConfigScope.PRIORITY_ORDER:
        if scope not in scopes:
            continue

        config_path = paths.get(scope)
        if config_path and config_path.exists():
            try:
                scope_config = load_config_file(config_path)
                merged_config = merged_config.merge(scope_config)
            except (json.JSONDecodeError, IOError):
                # Skip invalid config files
                pass

    return merged_config


def save_scoped_config(
    config: MCPConfig,
    scope: str,
    project_root: Optional[Path] = None,
) -> Path:
    """
    Save MCP configuration to a specific scope.

    Args:
        config: Configuration to save
        scope: Scope to save to (user, project, local)
        project_root: Project root directory (defaults to cwd)

    Returns:
        Path where config was saved

    Raises:
        ValueError: If scope is invalid
    """
    if scope not in ConfigScope.PRIORITY_ORDER:
        raise ValueError(f"Invalid scope: {scope}. Must be one of {ConfigScope.PRIORITY_ORDER}")

    paths = get_default_config_paths(project_root)
    config_path = paths[scope]

    save_config_file(config, config_path)
    return config_path


def get_server_scope(
    server_name: str,
    project_root: Optional[Path] = None,
) -> Optional[str]:
    """
    Determine which scope a server is defined in.

    Checks scopes in reverse priority order to find the highest
    priority scope where the server is defined.

    Args:
        server_name: Server name to look for
        project_root: Project root directory

    Returns:
        Scope name or None if not found
    """
    paths = get_default_config_paths(project_root)

    # Check in reverse priority order (highest first)
    for scope in reversed(ConfigScope.PRIORITY_ORDER):
        config_path = paths.get(scope)
        if config_path and config_path.exists():
            try:
                config = load_config_file(config_path)
                if server_name in config:
                    return scope
            except (json.JSONDecodeError, IOError):
                pass

    return None


def add_server_to_scope(
    server_config: MCPServerConfig,
    scope: str,
    project_root: Optional[Path] = None,
) -> None:
    """
    Add a server configuration to a specific scope.

    Args:
        server_config: Server configuration to add
        scope: Scope to add to
        project_root: Project root directory
    """
    paths = get_default_config_paths(project_root)
    config_path = paths[scope]

    # Load existing config or create new
    if config_path.exists():
        try:
            config = load_config_file(config_path)
        except (json.JSONDecodeError, IOError):
            config = MCPConfig()
    else:
        config = MCPConfig()

    config.add_server(server_config)
    save_config_file(config, config_path)


def remove_server_from_scope(
    server_name: str,
    scope: str,
    project_root: Optional[Path] = None,
) -> bool:
    """
    Remove a server configuration from a specific scope.

    Args:
        server_name: Server name to remove
        scope: Scope to remove from
        project_root: Project root directory

    Returns:
        True if removed, False if not found
    """
    paths = get_default_config_paths(project_root)
    config_path = paths[scope]

    if not config_path.exists():
        return False

    try:
        config = load_config_file(config_path)
        if config.remove_server(server_name):
            save_config_file(config, config_path)
            return True
    except (json.JSONDecodeError, IOError):
        pass

    return False


def list_servers_by_scope(
    project_root: Optional[Path] = None,
) -> Dict[str, List[str]]:
    """
    List all servers grouped by scope.

    Args:
        project_root: Project root directory

    Returns:
        Dictionary mapping scope to list of server names
    """
    paths = get_default_config_paths(project_root)
    result: Dict[str, List[str]] = {}

    for scope in ConfigScope.PRIORITY_ORDER:
        config_path = paths.get(scope)
        if config_path and config_path.exists():
            try:
                config = load_config_file(config_path)
                result[scope] = config.list_servers()
            except (json.JSONDecodeError, IOError):
                result[scope] = []
        else:
            result[scope] = []

    return result

