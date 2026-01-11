"""
SKILL.md Parser

Python 3.8.10 compatible
Implements SKILL-002: SKILL.md file parsing.

Parses SKILL.md files with YAML frontmatter and markdown body.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


# Frontmatter pattern: content between --- markers
FRONTMATTER_PATTERN = re.compile(
    r"^---\s*\n(.*?)\n---\s*\n",
    re.DOTALL
)


@dataclass
class SkillDefinition:
    """Parsed skill definition from SKILL.md."""

    name: str
    description: str = ""
    allowed_tools: List[str] = field(default_factory=list)
    model: Optional[str] = None
    color: Optional[str] = None
    body: str = ""

    # Additional metadata
    source_path: Optional[Path] = None
    scope: str = "project"

    @property
    def has_tool_restrictions(self) -> bool:
        """Check if skill has tool restrictions."""
        return len(self.allowed_tools) > 0

    def is_tool_allowed(self, tool_name: str) -> bool:
        """
        Check if a tool is allowed for this skill.

        Args:
            tool_name: Tool name to check

        Returns:
            True if allowed (or no restrictions)
        """
        if not self.allowed_tools:
            return True  # No restrictions
        return tool_name in self.allowed_tools

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "allowed_tools": self.allowed_tools,
            "model": self.model,
            "color": self.color,
            "body": self.body,
            "scope": self.scope,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillDefinition":
        """Create from dictionary."""
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            allowed_tools=data.get("allowed_tools", []),
            model=data.get("model"),
            color=data.get("color"),
            body=data.get("body", ""),
            scope=data.get("scope", "project"),
        )


def parse_yaml_frontmatter(content: str) -> Dict[str, Any]:
    """
    Parse YAML frontmatter from content.

    Simple YAML parser that handles common cases without
    requiring the pyyaml dependency.

    Args:
        content: Frontmatter content (without --- markers)

    Returns:
        Dictionary of parsed values
    """
    result: Dict[str, Any] = {}
    current_key: Optional[str] = None
    current_list: Optional[List[str]] = None

    for line in content.split("\n"):
        # Skip empty lines
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Check for key: value
        if ":" in line and not line.startswith(" ") and not line.startswith("\t"):
            # Save previous list if any
            if current_key and current_list is not None:
                result[current_key] = current_list
                current_list = None

            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()

            if value:
                # Handle inline list: key: item1, item2, item3
                if "," in value:
                    result[key] = [v.strip() for v in value.split(",")]
                # Handle quoted strings
                elif value.startswith('"') and value.endswith('"'):
                    result[key] = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    result[key] = value[1:-1]
                # Handle boolean
                elif value.lower() in ("true", "yes"):
                    result[key] = True
                elif value.lower() in ("false", "no"):
                    result[key] = False
                # Handle numbers
                elif value.isdigit():
                    result[key] = int(value)
                else:
                    try:
                        result[key] = float(value)
                    except ValueError:
                        result[key] = value
            else:
                # Value might be a list on following lines
                current_key = key
                current_list = []

        # Check for list item
        elif stripped.startswith("-") and current_list is not None:
            item = stripped[1:].strip()
            # Remove quotes if present
            if item.startswith('"') and item.endswith('"'):
                item = item[1:-1]
            elif item.startswith("'") and item.endswith("'"):
                item = item[1:-1]
            current_list.append(item)

    # Save final list if any
    if current_key and current_list is not None:
        result[current_key] = current_list

    return result


def parse_skill_file(content: str) -> tuple:
    """
    Parse a SKILL.md file content.

    Args:
        content: File content

    Returns:
        Tuple of (frontmatter_dict, body_text)
    """
    frontmatter: Dict[str, Any] = {}
    body = content

    # Try to extract frontmatter
    match = FRONTMATTER_PATTERN.match(content)
    if match:
        frontmatter_text = match.group(1)
        frontmatter = parse_yaml_frontmatter(frontmatter_text)
        body = content[match.end():].strip()

    return frontmatter, body


def parse_skill_definition(
    content: str,
    source_path: Optional[Path] = None,
    scope: str = "project",
) -> SkillDefinition:
    """
    Parse SKILL.md content into SkillDefinition.

    Args:
        content: SKILL.md file content
        source_path: Path to the SKILL.md file
        scope: Skill scope ("user" or "project")

    Returns:
        SkillDefinition object
    """
    frontmatter, body = parse_skill_file(content)

    # Extract name (required)
    name = frontmatter.get("name", "")
    if not name and source_path:
        # Use directory name as fallback
        name = source_path.parent.name

    # Extract description
    description = frontmatter.get("description", "")

    # Extract allowed-tools (can be list or comma-separated string)
    allowed_tools_raw = frontmatter.get("allowed-tools", [])
    if isinstance(allowed_tools_raw, str):
        allowed_tools = [t.strip() for t in allowed_tools_raw.split(",")]
    elif isinstance(allowed_tools_raw, list):
        allowed_tools = allowed_tools_raw
    else:
        allowed_tools = []

    # Extract model
    model = frontmatter.get("model")

    # Extract color
    color = frontmatter.get("color")

    return SkillDefinition(
        name=name,
        description=description,
        allowed_tools=allowed_tools,
        model=model,
        color=color,
        body=body,
        source_path=source_path,
        scope=scope,
    )


def load_skill_from_path(path: Path, scope: str = "project") -> Optional[SkillDefinition]:
    """
    Load a skill definition from a SKILL.md file path.

    Args:
        path: Path to SKILL.md file
        scope: Skill scope

    Returns:
        SkillDefinition or None if file doesn't exist
    """
    if not path.exists():
        return None

    try:
        content = path.read_text(encoding="utf-8")
        return parse_skill_definition(content, source_path=path, scope=scope)
    except Exception:
        return None


def load_skill_from_directory(
    directory: Path,
    scope: str = "project",
) -> Optional[SkillDefinition]:
    """
    Load a skill definition from a skill directory.

    Args:
        directory: Skill directory path
        scope: Skill scope

    Returns:
        SkillDefinition or None if SKILL.md doesn't exist
    """
    skill_file = directory / "SKILL.md"
    return load_skill_from_path(skill_file, scope)
