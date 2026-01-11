"""
Skills Directory Scanner and Loader

Python 3.8.10 compatible
Implements SKILL-001: Skills directory scanning.

Scans .deepcode/skills/ directories to discover available skills.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set


# Skill definition file name
SKILL_FILE_NAME = "SKILL.md"

# Default skill directory names
SKILL_DIR_NAME = "skills"
CONFIG_DIR_NAME = ".deepcode"


@dataclass
class SkillLocation:
    """Location information for a discovered skill."""

    path: Path
    scope: str  # "user" or "project"
    name: str

    @property
    def skill_file(self) -> Path:
        """Get path to SKILL.md file."""
        return self.path / SKILL_FILE_NAME

    @property
    def exists(self) -> bool:
        """Check if skill file exists."""
        return self.skill_file.exists()

    def list_files(self) -> List[Path]:
        """
        List all files in the skill directory.

        Returns:
            List of file paths (excluding SKILL.md)
        """
        files = []
        if self.path.exists():
            for item in self.path.iterdir():
                if item.is_file() and item.name != SKILL_FILE_NAME:
                    files.append(item)
                elif item.is_dir():
                    # Include files from subdirectories
                    for subitem in item.rglob("*"):
                        if subitem.is_file():
                            files.append(subitem)
        return files

    def __str__(self) -> str:
        """String representation."""
        return f"SkillLocation({self.name}, scope={self.scope})"


def get_user_skill_path() -> Path:
    """
    Get user-level skills directory path.

    Returns:
        Path to ~/.deepcode/skills/
    """
    home = Path.home()
    return home / CONFIG_DIR_NAME / SKILL_DIR_NAME


def get_project_skill_path(project_root: Optional[Path] = None) -> Path:
    """
    Get project-level skills directory path.

    Args:
        project_root: Project root directory (defaults to cwd)

    Returns:
        Path to <project>/.deepcode/skills/
    """
    root = project_root or Path.cwd()
    return root / CONFIG_DIR_NAME / SKILL_DIR_NAME


def get_default_skill_paths(project_root: Optional[Path] = None) -> Dict[str, Path]:
    """
    Get default skill directory paths.

    Args:
        project_root: Project root directory

    Returns:
        Dictionary mapping scope to path
    """
    return {
        "user": get_user_skill_path(),
        "project": get_project_skill_path(project_root),
    }


def find_skill_directories(
    base_path: Path,
    scope: str = "project",
) -> List[SkillLocation]:
    """
    Find all skill directories under a base path.

    Recursively searches for directories containing SKILL.md files.

    Args:
        base_path: Base directory to search
        scope: Scope identifier ("user" or "project")

    Returns:
        List of SkillLocation objects
    """
    skills: List[SkillLocation] = []

    if not base_path.exists():
        return skills

    # Check if base_path itself is a skill directory
    skill_file = base_path / SKILL_FILE_NAME
    if skill_file.exists():
        skills.append(SkillLocation(
            path=base_path,
            scope=scope,
            name=base_path.name,
        ))
        return skills

    # Search subdirectories
    try:
        for item in base_path.iterdir():
            if item.is_dir():
                # Check if this directory contains SKILL.md
                item_skill_file = item / SKILL_FILE_NAME
                if item_skill_file.exists():
                    skills.append(SkillLocation(
                        path=item,
                        scope=scope,
                        name=item.name,
                    ))
                else:
                    # Recursively search subdirectories (one level deep)
                    for subitem in item.iterdir():
                        if subitem.is_dir():
                            subitem_skill_file = subitem / SKILL_FILE_NAME
                            if subitem_skill_file.exists():
                                # Use parent/name as skill name for nested skills
                                skill_name = f"{item.name}/{subitem.name}"
                                skills.append(SkillLocation(
                                    path=subitem,
                                    scope=scope,
                                    name=skill_name,
                                ))
    except PermissionError:
        pass  # Skip directories we can't access

    return skills


class SkillLoader:
    """
    Loads and manages skill discovery.

    Scans configured directories for skills and provides
    access to discovered skill locations.
    """

    def __init__(
        self,
        project_root: Optional[Path] = None,
        include_user_skills: bool = True,
    ) -> None:
        """
        Initialize skill loader.

        Args:
            project_root: Project root directory
            include_user_skills: Whether to include user-level skills
        """
        self._project_root = project_root or Path.cwd()
        self._include_user_skills = include_user_skills
        self._skills: Dict[str, SkillLocation] = {}
        self._loaded = False

    def scan(self) -> int:
        """
        Scan for skills in configured directories.

        Returns:
            Number of skills found
        """
        self._skills.clear()

        # Scan project skills
        project_path = get_project_skill_path(self._project_root)
        project_skills = find_skill_directories(project_path, scope="project")
        for skill in project_skills:
            self._skills[skill.name] = skill

        # Scan user skills (lower priority, don't override project skills)
        if self._include_user_skills:
            user_path = get_user_skill_path()
            user_skills = find_skill_directories(user_path, scope="user")
            for skill in user_skills:
                if skill.name not in self._skills:
                    self._skills[skill.name] = skill

        self._loaded = True
        return len(self._skills)

    def get(self, name: str) -> Optional[SkillLocation]:
        """
        Get a skill by name.

        Args:
            name: Skill name

        Returns:
            SkillLocation or None if not found
        """
        if not self._loaded:
            self.scan()
        return self._skills.get(name)

    def list_skills(self) -> List[str]:
        """
        List all discovered skill names.

        Returns:
            List of skill names
        """
        if not self._loaded:
            self.scan()
        return list(self._skills.keys())

    def list_by_scope(self, scope: str) -> List[SkillLocation]:
        """
        List skills by scope.

        Args:
            scope: Scope to filter by ("user" or "project")

        Returns:
            List of SkillLocation objects
        """
        if not self._loaded:
            self.scan()
        return [s for s in self._skills.values() if s.scope == scope]

    def get_all(self) -> List[SkillLocation]:
        """
        Get all discovered skills.

        Returns:
            List of all SkillLocation objects
        """
        if not self._loaded:
            self.scan()
        return list(self._skills.values())

    def refresh(self) -> int:
        """
        Refresh skill list by rescanning directories.

        Returns:
            Number of skills found
        """
        return self.scan()

    @property
    def project_root(self) -> Path:
        """Get project root path."""
        return self._project_root

    @property
    def is_loaded(self) -> bool:
        """Check if skills have been loaded."""
        return self._loaded

    def __len__(self) -> int:
        """Return number of discovered skills."""
        if not self._loaded:
            self.scan()
        return len(self._skills)

    def __contains__(self, name: str) -> bool:
        """Check if a skill exists."""
        if not self._loaded:
            self.scan()
        return name in self._skills

    def __iter__(self):
        """Iterate over skill names."""
        if not self._loaded:
            self.scan()
        return iter(self._skills.keys())
