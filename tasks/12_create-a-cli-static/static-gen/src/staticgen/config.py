"""Configuration handling for static site generator."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class SiteConfig:
    """Site-wide configuration."""

    title: str = "My Site"
    description: str = ""
    author: str = ""
    email: str = ""
    url: str = ""
    base_url: str = ""
    language: str = "en"
    timezone: str = "UTC"
    posts_per_page: int = 10
    theme: str = "default"
    markdown_extensions: List[str] = field(default_factory=lambda: [
        "markdown.extensions.extra",
        "markdown.extensions.codehilite",
        "markdown.extensions.toc",
        "markdown.extensions.meta",
        "markdown.extensions.admonition",
        "markdown.extensions.sane_lists",
    ])
    ignore_files: List[str] = field(default_factory=list)
    include_drafts: bool = False
    date_format: str = "%B %d, %Y"
    permalink_format: str = "/{{ slug }}/"
    generate_sitemap: bool = True
    generate_feeds: bool = True
    feed_format: str = "rss"  # rss, atom, or both
    feed_items: int = 20

    # SEO settings
    meta_description: str = ""
    open_graph: bool = True
    twitter_card: str = ""  # summary, summary_large_image, etc.
    canonical_url: bool = True

    # Paths
    content_dir: str = "content"
    output_dir: str = "output"
    static_dir: str = "static"
    templates_dir: str = "templates"
    themes_dir: str = "themes"


@dataclass
class PageMetadata:
    """Metadata for a single page/post."""

    title: str
    slug: str
    date: Optional[str] = None
    updated: Optional[str] = None
    author: str = ""
    tags: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    description: str = ""
    draft: bool = False
    template: str = ""
    layout: str = ""
    aliases: List[str] = field(default_factory=list)
    custom: Dict[str, Any] = field(default_factory=dict)


class ConfigManager:
    """Manages configuration loading and validation."""

    DEFAULT_CONFIG_FILES = [
        "staticgen.yml",
        "staticgen.yaml",
        "_config.yml",
        "_config.yaml",
        "config.yml",
        "config.yaml",
    ]

    def __init__(self, config_path: Optional[Path] = None, base_dir: Optional[Path] = None):
        """Initialize config manager.

        Args:
            config_path: Path to config file
            base_dir: Base directory for the site
        """
        self.base_dir = base_dir or Path.cwd()
        self.config_path = config_path or self._find_config_file()
        self.site_config: Optional[SiteConfig] = None
        self.page_configs: Dict[str, PageMetadata] = {}

    def _find_config_file(self) -> Optional[Path]:
        """Find config file in default locations.

        Returns:
            Path to config file if found, None otherwise
        """
        for filename in self.DEFAULT_CONFIG_FILES:
            path = self.base_dir / filename
            if path.exists():
                return path
        return None

    def load(self) -> SiteConfig:
        """Load site configuration from file.

        Returns:
            SiteConfig object with loaded settings
        """
        if self.site_config is not None:
            return self.site_config

        config_data = {}

        if self.config_path and self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config_data = yaml.safe_load(f) or {}
            except yaml.YAMLError as e:
                raise ConfigError(f"Error parsing config file {self.config_path}: {e}")
            except Exception as e:
                raise ConfigError(f"Error reading config file {self.config_path}: {e}")

        # Convert keys to match SiteConfig fields
        normalized_data = self._normalize_config(config_data)
        self.site_config = SiteConfig(**normalized_data)
        return self.site_config

    def _normalize_config(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize config keys to match SiteConfig fields.

        Args:
            data: Raw config dictionary

        Returns:
            Normalized dictionary
        """
        normalized = {}

        # Handle common variations
        key_mapping = {
            "site_title": "title",
            "site_description": "description",
            "site_url": "url",
            "baseurl": "base_url",
            "markdown": "markdown_extensions",
            "exclude": "ignore_files",
            "paginate": "posts_per_page",
        }

        for key, value in data.items():
            norm_key = key_mapping.get(key, key)
            normalized[norm_key] = value

        return normalized

    def load_page_metadata(self, content: str, source_path: Path) -> PageMetadata:
        """Load metadata from page frontmatter.

        Args:
            content: Raw content with frontmatter
            source_path: Path to content file

        Returns:
            PageMetadata object
        """
        metadata = self._parse_frontmatter(content)

        # Generate slug from filename if not provided
        if not metadata.get("slug"):
            metadata["slug"] = source_path.stem

        # Ensure title exists
        if not metadata.get("title"):
            metadata["title"] = metadata["slug"].replace("-", " ").replace("_", " ").title()

        # Separate custom fields
        standard_fields = {
            "title", "slug", "date", "updated", "author", "tags",
            "categories", "description", "draft", "template", "layout", "aliases"
        }
        custom_fields = {k: v for k, v in metadata.items() if k not in standard_fields}

        metadata["custom"] = custom_fields

        try:
            return PageMetadata(**metadata)
        except TypeError as e:
            raise ConfigError(f"Invalid metadata in {source_path}: {e}")

    def _parse_frontmatter(self, content: str) -> Dict[str, Any]:
        """Parse YAML frontmatter from content.

        Args:
            content: Content with frontmatter

        Returns:
            Parsed metadata dictionary
        """
        metadata = {}

        if not content.startswith("---"):
            return metadata

        # Find end of frontmatter
        parts = content.split("---", 2)
        if len(parts) < 3:
            return metadata

        try:
            metadata = yaml.safe_load(parts[1]) or {}
        except yaml.YAMLError:
            # Invalid YAML, return empty dict
            pass

        # Convert string values to lists where needed
        for field in ["tags", "categories", "aliases"]:
            if field in metadata and isinstance(metadata[field], str):
                metadata[field] = [t.strip() for t in metadata[field].split(",")]

        return metadata

    def validate(self) -> List[str]:
        """Validate configuration.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        if self.site_config is None:
            self.load()

        # Check required fields
        if not self.site_config.title:
            errors.append("Site title is required")

        # Check URL format
        if self.site_config.url and not self.site_config.url.startswith(("http://", "https://")):
            errors.append("Site URL must start with http:// or https://")

        # Check directories exist
        for dir_field in ["content_dir", "static_dir", "templates_dir"]:
            dir_path = getattr(self.site_config, dir_field)
            full_path = self.base_dir / dir_path
            if not full_path.exists():
                errors.append(f"{dir_field} directory does not exist: {dir_path}")

        return errors


class ConfigError(Exception):
    """Configuration-related errors."""

    pass
