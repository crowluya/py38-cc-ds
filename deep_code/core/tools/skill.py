"""
Skill Tool for DeepCode

Python 3.8.10 compatible
Implements SKILL-005: Skill tool that can be called by the Agent.

Provides the Skill tool that allows the LLM to invoke skills.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from deep_code.core.tools.base import (
    Tool,
    ToolCategory,
    ToolParameter,
    ToolResult,
)
from deep_code.extensions.skills.registry import SkillRegistry
from deep_code.extensions.skills.executor import (
    SkillExecutor,
    build_skill_context,
)


class SkillTool(Tool):
    """
    Tool for invoking skills.

    Allows the LLM to activate a skill by name, receiving
    the skill's instructions and context.
    """

    def __init__(
        self,
        registry: SkillRegistry,
        executor: Optional[SkillExecutor] = None,
    ) -> None:
        """
        Initialize skill tool.

        Args:
            registry: Skill registry
            executor: Optional skill executor (created if not provided)
        """
        self._registry = registry
        self._executor = executor or SkillExecutor()

    @property
    def name(self) -> str:
        """Get tool name."""
        return "Skill"

    @property
    def description(self) -> str:
        """Get tool description with available skills."""
        base_desc = (
            "Execute a skill within the main conversation. "
            "Skills provide specialized capabilities and domain knowledge.\n\n"
            "When users ask you to perform tasks, check if any of the available "
            "skills below can help complete the task more effectively.\n\n"
            "When users ask you to run a \"slash command\" or reference \"/<something>\" "
            "(e.g., \"/commit\", \"/review-pr\"), they are referring to a skill. "
            "Use this tool to invoke the corresponding skill.\n\n"
        )

        # Add available skills
        skills_xml = self._registry.format_available_skills()

        return base_desc + skills_xml

    @property
    def category(self) -> ToolCategory:
        """Get tool category."""
        return ToolCategory.AGENT

    @property
    def parameters(self) -> List[ToolParameter]:
        """Get tool parameters."""
        return [
            ToolParameter(
                name="skill",
                type="string",
                description="The skill name to invoke (e.g., \"pdf\", \"commit\")",
                required=True,
            ),
            ToolParameter(
                name="args",
                type="string",
                description="Optional arguments for the skill",
                required=False,
            ),
        ]

    @property
    def requires_permission(self) -> bool:
        """Skills don't require permission by default."""
        return False

    @property
    def is_dangerous(self) -> bool:
        """Skills are not dangerous by default."""
        return False

    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """
        Execute the skill tool.

        Args:
            arguments: Tool arguments (skill, args)

        Returns:
            ToolResult with skill context
        """
        skill_name = arguments.get("skill", "")
        skill_args = arguments.get("args", "")

        if not skill_name:
            return ToolResult.error_result(
                self.name,
                "skill parameter is required",
            )

        # Remove leading slash if present
        skill_name = skill_name.lstrip("/")

        # Look up skill
        entry = self._registry.get_entry(skill_name)
        if not entry:
            available = ", ".join(self._registry.list_names())
            return ToolResult.error_result(
                self.name,
                f"Skill '{skill_name}' not found. Available skills: {available}",
            )

        # Prepare and activate context
        context = self._executor.prepare_context(
            entry.definition,
            entry.location,
        )
        context_str = self._executor.activate(context)

        # Build result
        output_parts = [
            f"Skill '{skill_name}' activated.",
            "",
            context_str,
        ]

        if skill_args:
            output_parts.append("")
            output_parts.append(f"Arguments: {skill_args}")

        return ToolResult.success_result(
            self.name,
            "\n".join(output_parts),
            metadata={
                "skill_name": skill_name,
                "base_path": str(context.base_path),
                "allowed_tools": context.skill.allowed_tools,
                "model": context.skill.model,
            },
        )

    def get_json_schema(self) -> Dict[str, Any]:
        """
        Get OpenAI-compatible function schema.

        Returns:
            JSON Schema for the tool
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "skill": {
                            "type": "string",
                            "description": "The skill name to invoke",
                        },
                        "args": {
                            "type": "string",
                            "description": "Optional arguments for the skill",
                        },
                    },
                    "required": ["skill"],
                },
            },
        }


def create_skill_tool(
    project_root: Optional[Path] = None,
    include_user_skills: bool = True,
) -> SkillTool:
    """
    Create a skill tool with a new registry.

    Args:
        project_root: Project root directory
        include_user_skills: Whether to include user-level skills

    Returns:
        Configured SkillTool
    """
    registry = SkillRegistry(
        project_root=project_root,
        include_user_skills=include_user_skills,
    )
    registry.load()
    return SkillTool(registry)
