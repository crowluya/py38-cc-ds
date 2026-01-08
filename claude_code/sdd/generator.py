"""
SDD Generator - Generate tasks.md from plan.md using LLM.

Python 3.8.10 compatible
T112: 从plan.md生成tasks.md的工作流

Features:
- Uses LLM to decompose plan into atomic tasks
- Ensures tasks have proper dependencies
- Marks parallel tasks with [P]
- Follows TDD principles
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from claude_code.llm.client import LLMClient
from claude_code.sdd.models import Task
from claude_code.sdd.parser import parse_tasks_markdown


class TaskGenerator:
    """
    Generate tasks.md from plan.md using LLM.

    This class implements T112: 从plan.md生成tasks.md的工作流
    """

    def __init__(
        self,
        plan_content: str,
        llm_client: Optional[LLMClient] = None,
    ):
        """
        Initialize task generator.

        Args:
            plan_content: Content of plan.md
            llm_client: LLM client for generation (optional, for testing)
        """
        self.plan_content = plan_content
        self.llm_client = llm_client

    def _generate_prompt(self) -> str:
        """
        Generate prompt for LLM to create tasks.md.

        Returns:
            Prompt string for LLM
        """
        return f"""You are a senior software architect specializing in Spec-Driven Development (SDD).

Your task is to generate a tasks.md file based on the provided plan.md.

# Input: plan.md

{self.plan_content}

# Output Requirements

Generate a tasks.md file with the following structure:

## 任务清单（带依赖/并行标记）

### Phase X: [Phase Name]

- [ ] **TXXX Task description** [P] (if parallel)
  - **依赖**: Task IDs or "无"
  - **产物**: Target files
  - **改动点**: Changed files
  - **验证**: Validation commands
  - **DoD**: Definition of Done

# Guidelines

1. Task IDs should be sequential (T001, T002, etc.)
2. Each task must be atomic (one file/function/feature)
3. Mark parallel tasks with [P]
4. All dependencies must be explicit
5. Follow TDD principles
6. Tasks should be verifiable
7. Group related tasks into phases

Please generate the complete tasks.md file now:"""

    def generate(self) -> List[Task]:
        """
        Generate tasks from plan.md using LLM.

        Returns:
            List of generated Task objects

        Raises:
            ValueError: If LLM client is not configured
            TaskParseError: If LLM output cannot be parsed
        """
        if not self.llm_client:
            raise ValueError("LLM client is required for generation")

        # Generate prompt
        prompt = self._generate_prompt()

        # Call LLM
        messages = [
            {"role": "system", "content": "You are a senior software architect."},
            {"role": "user", "content": prompt},
        ]

        response = self.llm_client.chat_completion(
            messages=messages,
            temperature=0.7,
        )

        # Extract content
        content = response.get("content", "")

        # Parse tasks from LLM output
        tasks = self._parse_llm_output(content)

        return tasks

    @staticmethod
    def _parse_llm_output(output: str) -> List[Task]:
        """
        Parse tasks from LLM-generated markdown.

        Args:
            output: LLM output containing tasks.md content

        Returns:
            List of parsed Task objects
        """
        # Extract the tasks section
        # Look for task markers: - [ ] **TXXX
        return parse_tasks_markdown(output)

    def validate_generated_tasks(self, tasks: List[Task]) -> Dict[str, Any]:
        """
        Validate generated tasks for quality.

        Checks:
        - All tasks have IDs
        - All tasks have descriptions
        - Dependencies reference valid tasks
        - No circular dependencies

        Args:
            tasks: List of generated tasks

        Returns:
            Dict with validation results
        """
        from claude_code.sdd.analyzer import DependencyAnalyzer

        issues: List[str] = []
        warnings: List[str] = []

        # Check basic structure
        for task in tasks:
            if not task.id:
                issues.append(f"Task missing ID: {task.description}")

            if not task.description:
                issues.append(f"Task {task.id} missing description")

        # Check dependencies
        analyzer = DependencyAnalyzer(tasks)
        missing_deps = analyzer.validate_dependencies()

        if missing_deps:
            issues.append(f"Missing dependencies: {', '.join(missing_deps)}")

        # Check for circular dependencies
        try:
            analyzer.topological_sort()
        except Exception as e:
            issues.append(f"Dependency error: {str(e)}")

        # Check TDD compliance
        non_tdd = [t.id for t in tasks if not t.tdd]
        if non_tdd:
            warnings.append(f"Non-TDD tasks: {', '.join(non_tdd)}")

        # Check parallel task distribution
        parallel_count = sum(1 for t in tasks if t.parallel)
        if parallel_count == 0:
            warnings.append("No parallel tasks identified")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "total_tasks": len(tasks),
            "parallel_tasks": parallel_count,
        }
