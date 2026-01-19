"""Configuration management for AI Command Palette."""

import json
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field


class KeybindingsConfig(BaseModel):
    """Keybinding configuration."""

    toggle: str = "ctrl+space"
    navigate_up: str = "up"
    navigate_down: str = "down"
    navigate_page_up: str = "page_up"
    navigate_page_down: str = "page_down"
    execute: str = "enter"
    cancel: str = "escape"
    preview: str = "tab"


class LearningConfig(BaseModel):
    """Machine learning and tracking configuration."""

    enabled: bool = True
    retention_days: int = 90
    min_frequency: int = 2
    track_files: bool = True
    track_context: bool = True


class ScoringConfig(BaseModel):
    """Scoring weights for recommendations."""

    frequency: float = Field(default=0.4, ge=0.0, le=1.0)
    recency: float = Field(default=0.3, ge=0.0, le=1.0)
    fuzzy_match: float = Field(default=0.3, ge=0.0, le=1.0)
    context_boost: float = Field(default=0.2, ge=0.0, le=1.0)


class UIConfig(BaseModel):
    """UI appearance configuration."""

    theme: str = "default"
    max_results: int = 20
    show_preview: bool = True
    show_scores: bool = False
    fuzzy_match_threshold: int = 60


class IntegrationConfig(BaseModel):
    """Integration with external tools."""

    notes_cli_path: Optional[str] = None
    shell_integration: bool = True
    git_integration: bool = True
    index_hidden_files: bool = False


class Config(BaseModel):
    """Main configuration model."""

    keybindings: KeybindingsConfig = Field(default_factory=KeybindingsConfig)
    learning: LearningConfig = Field(default_factory=LearningConfig)
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    integration: IntegrationConfig = Field(default_factory=IntegrationConfig)

    # Config file paths
    config_dir: Path = Field(default_factory=lambda: Path.home() / ".config" / "ai-command-palette")
    data_dir: Path = Field(default_factory=lambda: Path.home() / ".local" / "share" / "ai-command-palette")

    def __init__(self, **data):
        """Initialize config with defaults and load from file if exists."""
        # Set up paths first
        if "config_dir" not in data:
            data["config_dir"] = Path.home() / ".config" / "ai-command-palette"
        if "data_dir" not in data:
            data["data_dir"] = Path.home() / ".local" / "share" / "ai-command-palette"

        super().__init__(**data)

        # Load from config file if exists
        config_file = self.config_dir / "config.json"
        if config_file.exists():
            self._load_from_file(config_file)

    def _load_from_file(self, config_file: Path):
        """Load configuration from JSON file."""
        try:
            with open(config_file, "r") as f:
                data = json.load(f)
                # Update config with loaded values
                for key, value in data.items():
                    if hasattr(self, key):
                        setattr(self, key, value)
        except Exception as e:
            print(f"Warning: Failed to load config file: {e}")

    def save(self):
        """Save configuration to file."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        config_file = self.config_dir / "config.json"

        with open(config_file, "w") as f:
            json.dump(self.model_dump(), f, indent=2)

    def ensure_directories(self):
        """Ensure all required directories exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "Config":
        """Load configuration from specific path."""
        if config_path and config_path.exists():
            config = cls()
            config._load_from_file(config_path)
            return config
        return cls()
