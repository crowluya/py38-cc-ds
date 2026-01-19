"""Workflow automation and macros."""

import json
import subprocess
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel

from ai_command_palette.core.registry import Command, CommandType


class WorkflowStep(BaseModel):
    """A single step in a workflow."""

    command: str
    args: Optional[dict[str, Any]] = None
    continue_on_error: bool = False


class Workflow(BaseModel):
    """A workflow macro consisting of multiple steps."""

    name: str
    description: Optional[str] = None
    steps: list[WorkflowStep]
    category: Optional[str] = None
    tags: list[str] = []

    def execute(self, **kwargs) -> tuple[bool, str]:
        """Execute the workflow."""
        outputs = []

        for step in self.steps:
            try:
                # Format command with kwargs
                cmd = step.command.format(**kwargs)

                # Add step-specific args
                if step.args:
                    cmd = cmd.format(**step.args)

                # Execute command
                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                )

                if result.returncode != 0 and not step.continue_on_error:
                    return False, f"Step failed: {cmd}\n{result.stderr}"

                outputs.append(result.stdout)

            except Exception as e:
                if not step.continue_on_error:
                    return False, f"Step error: {e}"

        return True, "\n".join(outputs)


class WorkflowManager:
    """Manage workflow automation."""

    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize workflow manager."""
        if config_dir is None:
            from ai_command_palette.storage.config import Config

            config = Config()
            config_dir = config.config_dir

        self.workflows_dir = config_dir / "workflows"
        self.workflows_dir.mkdir(parents=True, exist_ok=True)

        self._workflows: dict[str, Workflow] = {}
        self._load_workflows()

    def _load_workflows(self):
        """Load workflows from directory."""
        for workflow_file in self.workflows_dir.glob("*.json"):
            try:
                with open(workflow_file, "r") as f:
                    data = json.load(f)
                    workflow = Workflow(**data)
                    self._workflows[workflow.name] = workflow
            except Exception as e:
                print(f"Warning: Failed to load workflow {workflow_file}: {e}")

    def save_workflow(self, workflow: Workflow):
        """Save a workflow to disk."""
        workflow_file = self.workflows_dir / f"{workflow.name}.json"

        with open(workflow_file, "w") as f:
            json.dump(workflow.model_dump(), f, indent=2)

        self._workflows[workflow.name] = workflow

    def get_workflow(self, name: str) -> Optional[Workflow]:
        """Get a workflow by name."""
        return self._workflows.get(name)

    def get_all_workflows(self) -> list[Workflow]:
        """Get all workflows."""
        return list(self._workflows.values())

    def execute_workflow(self, name: str, **kwargs) -> tuple[bool, str]:
        """Execute a workflow."""
        workflow = self.get_workflow(name)
        if not workflow:
            return False, f"Workflow not found: {name}"

        return workflow.execute(**kwargs)

    def create_commands_from_workflows(self) -> list[Command]:
        """Create Command objects from workflows."""
        commands = []

        for workflow in self._workflows.values():
            cmd = Command(
                name=f"workflow:{workflow.name}",
                command_type=CommandType.WORKFLOW,
                description=workflow.description or f"Execute workflow: {workflow.name}",
                command_template=f"aicp workflow execute {workflow.name}",
                category=workflow.category or "Workflows",
                tags=workflow.tags + ["workflow"],
                icon="⚡",
            )
            commands.append(cmd)

        return commands

    def create_default_workflows(self):
        """Create default workflow templates."""

        # Git workflow: Commit and push
        git_commit_push = Workflow(
            name="git:commit-push",
            description="Stage all changes, commit, and push to remote",
            steps=[
                WorkflowStep(
                    command="git add -A",
                    continue_on_error=False,
                ),
                WorkflowStep(
                    command="git commit -m '{message}'",
                    continue_on_error=False,
                ),
                WorkflowStep(
                    command="git push",
                    continue_on_error=False,
                ),
            ],
            category="Git",
            tags=["git", "commit", "push"],
        )

        # Development workflow: Format, lint, test
        dev_workflow = Workflow(
            name="dev:full-check",
            description="Format code, run linter, and execute tests",
            steps=[
                WorkflowStep(
                    command="black .",
                    continue_on_error=True,
                ),
                WorkflowStep(
                    command="ruff check .",
                    continue_on_error=True,
                ),
                WorkflowStep(
                    command="pytest tests/ -v",
                    continue_on_error=False,
                ),
            ],
            category="Development",
            tags=["dev", "test", "lint"],
        )

        # Project setup workflow
        setup_workflow = Workflow(
            name="project:setup",
            description="Initialize a new project with common tools",
            steps=[
                WorkflowStep(
                    command="git init",
                    continue_on_error=True,
                ),
                WorkflowStep(
                    command="python -m venv .venv",
                    continue_on_error=True,
                ),
                WorkflowStep(
                    command="touch README.md .gitignore",
                    continue_on_error=True,
                ),
            ],
            category="Project",
            tags=["setup", "init"],
        )

        # Note workflow: Daily standup
        standup_workflow = Workflow(
            name="note:standup",
            description="Create daily standup note with template",
            steps=[
                WorkflowStep(
                    command="note create 'standup-{date}' --content '## Yesterday\\n\\n## Today\\n\\n## Blockers'",
                    continue_on_error=False,
                ),
            ],
            category="Notes",
            tags=["note", "standup", "daily"],
        )

        # Save all workflows
        for workflow in [git_commit_push, dev_workflow, setup_workflow, standup_workflow]:
            self.save_workflow(workflow)
