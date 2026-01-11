"""
Skills Executor

Python 3.8.10 compatible
Implements SKILL-006: Context injection for skills.

Handles skill execution context and file injection.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from deep_code.extensions.skills.parser import SkillDefinition
from deep_code.extensions.skills.loader import SkillLocation


@dataclass
class SkillContext:
    """Context for skill execution."""

    skill: SkillDefinition
    location: SkillLocation
    base_path: Path
    auxiliary_files: List[Path] = field(default_factory=list)

    def get_instructions(self) -> str:
        """
        Get skill instructions (SKILL.md body without frontmatter).

        Returns:
            Skill instructions text
        """
        return self.skill.body

    def get_file_list(self) -> List[str]:
        """
        Get list of auxiliary files relative to skill directory.

        Returns:
            List of relative file paths
        """
        return [
            str(f.relative_to(self.base_path))
            for f in self.auxiliary_files
        ]

    def read_auxiliary_file(self, relative_path: str) -> Optional[str]:
        """
        Read an auxiliary file from the skill directory.

        Args:
            relative_path: Path relative to skill directory

        Returns:
            File content or None if not found
        """
        file_path = self.base_path / relative_path
        if file_path.exists() and file_path.is_file():
            try:
                return file_path.read_text(encoding="utf-8")
            except Exception:
                return None
        return None

    def format_for_injection(self) -> str:
        """
        Format skill context for LLM injection.

        Returns:
            Formatted context string
        """
        lines = []

        # Skill header
        lines.append(f"<skill name=\"{self.skill.name}\">")

        # Base path
        lines.append(f"<base_path>{self.base_path}</base_path>")

        # Instructions
        if self.skill.body:
            lines.append("<instructions>")
            lines.append(self.skill.body)
            lines.append("</instructions>")

        # Auxiliary files list
        if self.auxiliary_files:
            lines.append("<auxiliary_files>")
            for f in self.auxiliary_files:
                rel_path = f.relative_to(self.base_path)
                lines.append(f"  - {rel_path}")
            lines.append("</auxiliary_files>")

        # Tool restrictions
        if self.skill.allowed_tools:
            lines.append("<allowed_tools>")
            for tool in self.skill.allowed_tools:
                lines.append(f"  - {tool}")
            lines.append("</allowed_tools>")

        lines.append("</skill>")

        return "\n".join(lines)


class SkillExecutor:
    """
    Executes skills with proper context injection.

    Handles:
    - Context preparation
    - Tool restriction enforcement
    - Model selection
    """

    def __init__(self) -> None:
        """Initialize skill executor."""
        self._active_skill: Optional[SkillContext] = None
        self._original_model: Optional[str] = None

    def prepare_context(
        self,
        skill: SkillDefinition,
        location: SkillLocation,
    ) -> SkillContext:
        """
        Prepare execution context for a skill.

        Args:
            skill: Skill definition
            location: Skill location

        Returns:
            SkillContext ready for execution
        """
        # Get auxiliary files
        auxiliary_files = location.list_files()

        context = SkillContext(
            skill=skill,
            location=location,
            base_path=location.path,
            auxiliary_files=auxiliary_files,
        )

        return context

    def activate(self, context: SkillContext) -> str:
        """
        Activate a skill context.

        Args:
            context: Skill context to activate

        Returns:
            Context string for LLM injection
        """
        self._active_skill = context
        return context.format_for_injection()

    def deactivate(self) -> None:
        """Deactivate the current skill."""
        self._active_skill = None
        self._original_model = None

    def is_tool_allowed(self, tool_name: str) -> bool:
        """
        Check if a tool is allowed in the current skill context.

        Args:
            tool_name: Tool name to check

        Returns:
            True if allowed (or no active skill)
        """
        if not self._active_skill:
            return True

        return self._active_skill.skill.is_tool_allowed(tool_name)

    def get_allowed_tools(self) -> Optional[List[str]]:
        """
        Get list of allowed tools for active skill.

        Returns:
            List of allowed tool names, or None if no restrictions
        """
        if not self._active_skill:
            return None

        if not self._active_skill.skill.allowed_tools:
            return None

        return self._active_skill.skill.allowed_tools

    def get_model_override(self) -> Optional[str]:
        """
        Get model override for active skill.

        Returns:
            Model name or None if no override
        """
        if not self._active_skill:
            return None
        return self._active_skill.skill.model

    @property
    def active_skill(self) -> Optional[SkillContext]:
        """Get active skill context."""
        return self._active_skill

    @property
    def is_active(self) -> bool:
        """Check if a skill is active."""
        return self._active_skill is not None


def build_skill_context(
    skill: SkillDefinition,
    location: SkillLocation,
) -> str:
    """
    Build context string for a skill.

    Convenience function for simple context injection.

    Args:
        skill: Skill definition
        location: Skill location

    Returns:
        Context string for LLM
    """
    executor = SkillExecutor()
    context = executor.prepare_context(skill, location)
    return context.format_for_injection()


def format_skill_result(
    skill_name: str,
    base_path: Path,
    instructions: str,
    files: List[str],
) -> Dict[str, Any]:
    """
    Format skill invocation result.

    Args:
        skill_name: Name of the skill
        base_path: Base path of the skill
        instructions: Skill instructions
        files: List of auxiliary files

    Returns:
        Result dictionary
    """
    return {
        "skill_name": skill_name,
        "base_path": str(base_path),
        "instructions": instructions,
        "auxiliary_files": files,
    }
