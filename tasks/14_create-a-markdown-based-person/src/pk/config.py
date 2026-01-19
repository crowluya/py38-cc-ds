"""Configuration management for PK"""

import os
import toml
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class Config:
    """Configuration settings for PK"""

    notes_directory: Path = field(default_factory=lambda: Path.home() / "notes")
    default_editor: str = field(default_factory=lambda: os.environ.get("EDITOR", "vim"))
    tag_syntax: str = "#tag"  # Could be "#tag" or "tag: value"
    auto_index: bool = True
    index_file: str = ".pk_index.json"

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "Config":
        """Load configuration from file"""
        if config_path is None:
            config_path = cls.default_config_path()

        if not config_path.exists():
            # Create default config
            config = cls()
            config.save(config_path)
            return config

        with open(config_path, "r") as f:
            data = toml.load(f)

        config = cls(
            notes_directory=Path(data.get("notes_directory", str(Path.home() / "notes"))),
            default_editor=data.get("default_editor", os.environ.get("EDITOR", "vim")),
            tag_syntax=data.get("tag_syntax", "#tag"),
            auto_index=data.get("auto_index", True),
            index_file=data.get("index_file", ".pk_index.json"),
        )

        return config

    @staticmethod
    def default_config_path() -> Path:
        """Get default configuration file path"""
        config_dir = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "pk"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "config.toml"

    def save(self, config_path: Optional[Path] = None) -> None:
        """Save configuration to file"""
        if config_path is None:
            config_path = self.default_config_path()

        config_dir = config_path.parent
        config_dir.mkdir(parents=True, exist_ok=True)

        data = {
            "notes_directory": str(self.notes_directory),
            "default_editor": self.default_editor,
            "tag_syntax": self.tag_syntax,
            "auto_index": self.auto_index,
            "index_file": self.index_file,
        }

        with open(config_path, "w") as f:
            toml.dump(data, f)

    def ensure_notes_directory(self) -> Path:
        """Ensure notes directory exists and return path"""
        self.notes_directory.mkdir(parents=True, exist_ok=True)
        return self.notes_directory
