"""
Task tool for Claude Code Python MVP

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)

Provides subagent execution for complex, multi-step tasks.
"""

import uuid
from typing import Any, Dict, List, Optional

from claude_code.core.tools.base import (
    Tool,
    ToolCategory,
    ToolParameter,
    ToolResult,
)


# Valid subagent types
VALID_SUBAGENT_TYPES = {
    "Explore",
    "Plan",
    "Bash",
    "general-purpose",
}


def get_agent_system_prompt(subagent_type: str) -> str:
    """
    Get the system prompt for a specific agent type.

    Args:
        subagent_type: Type of subagent

    Returns:
        System prompt string
    """
    prompts = {
        "Explore": (
            "You are an Explore agent specialized for exploring codebases. "
            "Your task is to quickly find files by patterns, search code for keywords, "
            "or answer questions about the codebase. Be thorough but efficient. "
            "Focus on finding relevant information and summarizing your findings."
        ),
        "Plan": (
            "You are a Plan agent for designing implementation plans. "
            "Your task is to plan the implementation strategy for a task. "
            "Return step-by-step plans, identify critical files, and consider "
            "architectural trade-offs. Be specific and actionable."
        ),
        "Bash": (
            "You are a Bash agent specialized for running bash commands. "
            "Use this for git operations, command execution, and other terminal tasks. "
            "Be careful with destructive commands and always verify before executing."
        ),
        "general-purpose": (
            "You are a general-purpose agent for researching complex questions, "
            "searching for code, and executing multi-step tasks. "
            "Be thorough and provide detailed results."
        ),
    }

    return prompts.get(subagent_type, prompts["general-purpose"])


class TaskTool(Tool):
    """
    Tool for launching subagents to handle complex tasks.

    Features:
    - Launch specialized agents (Explore, Plan, Bash, general-purpose)
    - Execute multi-step tasks autonomously
    - Return summarized results
    - Support max_turns limit
    """

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        tool_registry: Optional[Any] = None,
    ):
        """
        Initialize Task tool.

        Args:
            llm_client: LLM client for subagent execution
            tool_registry: Optional tool registry for subagent tools
        """
        self._llm_client = llm_client
        self._tool_registry = tool_registry

    @property
    def name(self) -> str:
        return "Task"

    @property
    def description(self) -> str:
        return (
            "Launch a new agent to handle complex, multi-step tasks autonomously. "
            "Available agent types: Explore (for codebase exploration), "
            "Plan (for implementation planning), Bash (for command execution), "
            "general-purpose (for research and multi-step tasks)."
        )

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.AGENT

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="prompt",
                type="string",
                description="The task for the agent to perform",
                required=True,
            ),
            ToolParameter(
                name="subagent_type",
                type="string",
                description="The type of specialized agent to use (Explore, Plan, Bash, general-purpose)",
                required=True,
                enum=list(VALID_SUBAGENT_TYPES),
            ),
            ToolParameter(
                name="description",
                type="string",
                description="A short (3-5 word) description of the task",
                required=True,
            ),
            ToolParameter(
                name="max_turns",
                type="integer",
                description="Maximum number of agentic turns before stopping (default: 10)",
                required=False,
                default=10,
            ),
        ]

    @property
    def requires_permission(self) -> bool:
        return False

    @property
    def is_dangerous(self) -> bool:
        return False

    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """
        Execute the Task tool.

        Args:
            arguments: Tool arguments

        Returns:
            ToolResult with subagent execution result
        """
        prompt = arguments.get("prompt")
        subagent_type = arguments.get("subagent_type")
        description = arguments.get("description", "")
        max_turns = arguments.get("max_turns", 10)

        # Validate required fields before calling validate_arguments
        if not prompt:
            return ToolResult.error_result(
                self.name,
                "Missing required field 'prompt'",
            )

        if not subagent_type:
            return ToolResult.error_result(
                self.name,
                "Missing required field 'subagent_type'",
            )

        # Validate subagent type
        if subagent_type not in VALID_SUBAGENT_TYPES:
            return ToolResult.error_result(
                self.name,
                f"Invalid subagent_type '{subagent_type}'. "
                f"Must be one of: {', '.join(sorted(VALID_SUBAGENT_TYPES))}",
            )

        # Check LLM client
        if not self._llm_client:
            return ToolResult.error_result(
                self.name,
                "No LLM client configured for subagent execution",
            )

        # Generate task ID
        task_id = str(uuid.uuid4())[:8]

        try:
            # Execute subagent
            result = self._execute_subagent(
                prompt=prompt,
                subagent_type=subagent_type,
                max_turns=max_turns,
            )

            return ToolResult.success_result(
                self.name,
                result,
                metadata={
                    "subagent_type": subagent_type,
                    "task_id": task_id,
                    "description": description,
                    "max_turns": max_turns,
                },
            )

        except Exception as e:
            return ToolResult.error_result(
                self.name,
                f"Subagent execution failed: {str(e)}",
                metadata={
                    "subagent_type": subagent_type,
                    "task_id": task_id,
                },
            )

    def _execute_subagent(
        self,
        prompt: str,
        subagent_type: str,
        max_turns: int,
    ) -> str:
        """
        Execute a subagent with the given prompt.

        Args:
            prompt: Task prompt
            subagent_type: Type of agent
            max_turns: Maximum turns

        Returns:
            Subagent result string
        """
        # Get system prompt for agent type
        system_prompt = get_agent_system_prompt(subagent_type)

        # Build messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        # Simple execution - single turn for now
        # In a full implementation, this would support multi-turn with tools
        response = self._llm_client.chat_completion(
            messages=messages,
            max_tokens=4096,
            temperature=0.7,
        )

        # Extract content
        if isinstance(response, dict):
            content = response.get("content", "")
        else:
            content = getattr(response, "content", "")

        return content or "Task completed (no output)"

    def get_json_schema(self) -> Dict[str, Any]:
        """
        Get JSON schema for the tool.

        Returns:
            JSON schema dictionary
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "The task for the agent to perform",
                        },
                        "subagent_type": {
                            "type": "string",
                            "enum": list(VALID_SUBAGENT_TYPES),
                            "description": "The type of specialized agent to use",
                        },
                        "description": {
                            "type": "string",
                            "description": "A short (3-5 word) description of the task",
                        },
                        "max_turns": {
                            "type": "integer",
                            "description": "Maximum number of agentic turns",
                            "default": 10,
                        },
                    },
                    "required": ["prompt", "subagent_type", "description"],
                },
            },
        }
