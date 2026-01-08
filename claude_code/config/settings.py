"""
Settings data structure with default values

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LLMSettings:
    """LLM client settings."""

    provider: str = "openai"  # openai or requests
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    model: str = "gpt-3.5-turbo"
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: int = 30
    verify_ssl: bool = True
    ca_cert: Optional[str] = None


@dataclass
class PermissionSettings:
    """Security and permission settings."""

    default_mode: str = "ask"  # allow, deny, ask
    file_read: List[str] = field(default_factory=list)
    file_write: List[str] = field(default_factory=list)
    command_execute: List[str] = field(default_factory=list)
    network_access: List[str] = field(default_factory=list)


@dataclass
class HookSettings:
    """Hook configuration."""

    session_start: List[str] = field(default_factory=list)
    pre_tool_use: List[str] = field(default_factory=list)
    post_tool_use: List[str] = field(default_factory=list)


@dataclass
class Settings:
    """
    Main settings data class.

    Contains all configuration options with Python 3.8.10 compatible defaults.
    """

    llm: LLMSettings = field(default_factory=LLMSettings)
    permissions: PermissionSettings = field(default_factory=PermissionSettings)
    hooks: HookSettings = field(default_factory=HookSettings)

    # UI settings
    use_color: bool = True
    show_thinking: bool = False

    # Development settings
    debug: bool = False
    log_level: str = "INFO"

    # Paths
    project_root: Optional[str] = None
    checkpoint_dir: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary."""
        return {
            "llm": {
                "provider": self.llm.provider,
                "api_key": self.llm.api_key,
                "api_base": self.llm.api_base,
                "model": self.llm.model,
                "temperature": self.llm.temperature,
                "max_tokens": self.llm.max_tokens,
                "timeout": self.llm.timeout,
                "verify_ssl": self.llm.verify_ssl,
                "ca_cert": self.llm.ca_cert,
            },
            "permissions": {
                "default_mode": self.permissions.default_mode,
                "file_read": self.permissions.file_read,
                "file_write": self.permissions.file_write,
                "command_execute": self.permissions.command_execute,
                "network_access": self.permissions.network_access,
            },
            "hooks": {
                "session_start": self.hooks.session_start,
                "pre_tool_use": self.hooks.pre_tool_use,
                "post_tool_use": self.hooks.post_tool_use,
            },
            "use_color": self.use_color,
            "show_thinking": self.show_thinking,
            "debug": self.debug,
            "log_level": self.log_level,
            "project_root": self.project_root,
            "checkpoint_dir": self.checkpoint_dir,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Settings":
        """
        Create settings from dictionary.

        Args:
            data: Dictionary containing settings values

        Returns:
            Settings instance
        """
        llm_data = data.get("llm", {})
        llm = LLMSettings(
            provider=llm_data.get("provider", "openai"),
            api_key=llm_data.get("api_key"),
            api_base=llm_data.get("api_base"),
            model=llm_data.get("model", "gpt-3.5-turbo"),
            temperature=llm_data.get("temperature", 0.7),
            max_tokens=llm_data.get("max_tokens", 2048),
            timeout=llm_data.get("timeout", 30),
            verify_ssl=llm_data.get("verify_ssl", True),
            ca_cert=llm_data.get("ca_cert"),
        )

        perm_data = data.get("permissions", {})
        permissions = PermissionSettings(
            default_mode=perm_data.get("default_mode", "ask"),
            file_read=perm_data.get("file_read", []),
            file_write=perm_data.get("file_write", []),
            command_execute=perm_data.get("command_execute", []),
            network_access=perm_data.get("network_access", []),
        )

        hook_data = data.get("hooks", {})
        hooks = HookSettings(
            session_start=hook_data.get("session_start", []),
            pre_tool_use=hook_data.get("pre_tool_use", []),
            post_tool_use=hook_data.get("post_tool_use", []),
        )

        return cls(
            llm=llm,
            permissions=permissions,
            hooks=hooks,
            use_color=data.get("use_color", True),
            show_thinking=data.get("show_thinking", False),
            debug=data.get("debug", False),
            log_level=data.get("log_level", "INFO"),
            project_root=data.get("project_root"),
            checkpoint_dir=data.get("checkpoint_dir"),
        )


def get_default_settings() -> Settings:
    """Get default settings instance."""
    return Settings()
