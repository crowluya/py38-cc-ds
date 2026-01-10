"""
MCP Configuration for DeepCode

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)

Handles MCP server configuration loading and management.
"""

import json
import os
from typing import Any, Dict, List, Optional


class MCPConfig:
    """
    MCP Configuration manager.

    Handles loading and accessing MCP server configurations
    from JSON files or dictionaries.
    """

    def __init__(self, servers: Optional[Dict[str, Dict[str, Any]]] = None):
        """
        Initialize MCP configuration.

        Args:
            servers: Dictionary of server configurations
        """
        self._servers = servers or {}

    @property
    def servers(self) -> Dict[str, Dict[str, Any]]:
        """Get all server configurations."""
        return self._servers

    def get_server(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific server.

        Args:
            name: Server name

        Returns:
            Server configuration or None if not found
        """
        return self._servers.get(name)

    def add_server(self, name: str, config: Dict[str, Any]) -> None:
        """
        Add a server configuration.

        Args:
            name: Server name
            config: Server configuration
        """
        self._servers[name] = config

    def remove_server(self, name: str) -> bool:
        """
        Remove a server configuration.

        Args:
            name: Server name

        Returns:
            True if removed, False if not found
        """
        if name in self._servers:
            del self._servers[name]
            return True
        return False

    def list_servers(self) -> List[str]:
        """
        List all configured server names.

        Returns:
            List of server names
        """
        return list(self._servers.keys())

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "MCPConfig":
        """
        Create configuration from dictionary.

        Args:
            config_dict: Configuration dictionary with "mcpServers" key

        Returns:
            MCPConfig instance
        """
        servers = config_dict.get("mcpServers", {})
        return cls(servers=servers)

    @classmethod
    def from_file(cls, file_path: str) -> "MCPConfig":
        """
        Load configuration from JSON file.

        Args:
            file_path: Path to JSON configuration file

        Returns:
            MCPConfig instance

        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If file is not valid JSON
        """
        with open(file_path, "r", encoding="utf-8") as f:
            config_dict = json.load(f)
        return cls.from_dict(config_dict)

    @classmethod
    def from_claude_settings(cls, settings_path: Optional[str] = None) -> "MCPConfig":
        """
        Load configuration from Claude settings file.

        Looks for MCP configuration in:
        1. Provided path
        2. .deepcode/settings.json in current directory
        3. ~/.deepcode/settings.json

        Args:
            settings_path: Optional explicit path to settings file

        Returns:
            MCPConfig instance (empty if no config found)
        """
        paths_to_try = []

        if settings_path:
            paths_to_try.append(settings_path)

        # Project local settings
        paths_to_try.append(os.path.join(".claude", "settings.json"))
        paths_to_try.append(os.path.join(".claude", "settings.local.json"))

        # User global settings
        home = os.path.expanduser("~")
        paths_to_try.append(os.path.join(home, ".claude", "settings.json"))

        for path in paths_to_try:
            if os.path.exists(path):
                try:
                    return cls.from_file(path)
                except (json.JSONDecodeError, IOError):
                    continue

        return cls()

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.

        Returns:
            Configuration dictionary
        """
        return {"mcpServers": self._servers}

    def save_to_file(self, file_path: str) -> None:
        """
        Save configuration to JSON file.

        Args:
            file_path: Path to save configuration
        """
        # Ensure directory exists
        dir_path = os.path.dirname(file_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    def merge(self, other: "MCPConfig") -> "MCPConfig":
        """
        Merge with another configuration.

        Other configuration takes precedence for duplicate servers.

        Args:
            other: Other MCPConfig to merge

        Returns:
            New merged MCPConfig
        """
        merged_servers = dict(self._servers)
        merged_servers.update(other._servers)
        return MCPConfig(servers=merged_servers)

    def __len__(self) -> int:
        """Return number of configured servers."""
        return len(self._servers)

    def __contains__(self, name: str) -> bool:
        """Check if server is configured."""
        return name in self._servers

    def __iter__(self):
        """Iterate over server names."""
        return iter(self._servers)
