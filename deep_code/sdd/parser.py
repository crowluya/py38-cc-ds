"""
SDD (Spec-Driven Development) parsers.

Parses spec.md, plan.md, and tasks.md markdown files into structured data.
Follows Python 3.8.10 compatibility requirements.
"""
from __future__ import annotations

import re
from typing import List, Optional, Dict

from deep_code.sdd.models import Task, Phase, Dependency, TaskStatus


class TaskParseError(Exception):
    """Exception raised when task parsing fails."""

    pass


def parse_tasks_markdown(markdown: str) -> List[Task]:
    """
    Parse tasks from markdown format.

    Args:
        markdown: Markdown content containing task definitions

    Returns:
        List of parsed Task objects

    Raises:
        TaskParseError: If markdown format is invalid
    """
    tasks: List[Task] = []
    lines = markdown.strip().split("\n")

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Look for task headers: - [ ] **T001 Description**
        if line.startswith("- [ ] **") or line.startswith("- [x] **"):
            task, skip_lines = _parse_task_block(lines, i)
            if task:
                tasks.append(task)
            i += skip_lines
        else:
            i += 1

    return tasks


def _parse_task_block(lines: List[str], start_idx: int) -> tuple[Optional[Task], int]:
    """
    Parse a single task block starting at start_idx.

    Returns:
        Tuple of (Task object, number of lines to skip)
    """
    header_line = lines[start_idx].strip()

    # Parse task header: - [ ] **T001 Description**
    match = re.match(r"- \[ \] \*\*([A-Z]?\d+)\s+(.+?)\*\*", header_line)
    if not match:
        # Try completed format: - [x] **T001 Description**
        match = re.match(r"- \[x\] \*\*([A-Z]?\d+)\s+(.+?)\*\*", header_line)

    if not match:
        return None, 1

    task_id = match.group(1)
    description = match.group(2).strip()

    # Check for parallel marker [P] in description
    parallel = "[P]" in description
    if parallel:
        description = description.replace("[P]", "").strip()

    # Initialize task fields
    dependencies: List[str] = []
    file: Optional[str] = None
    changes: Optional[str] = None
    validation: Optional[str] = None
    dod: Optional[str] = None

    # Parse sub-fields (next lines with indentation)
    i = start_idx + 1
    while i < len(lines):
        line = lines[i].strip()

        # Stop at next task or empty line
        if not line or line.startswith("- [") or line.startswith("##"):
            break

        # Parse fields
        if "**依赖**" in line or "**Dependencies**" in line or "**depends**" in line.lower():
            dependencies = _parse_dependency_field(line)
        elif "**产物**" in line or "**Product**" in line or "**file**" in line.lower():
            file = _parse_field_value(line)
        elif "**改动点**" in line or "**Changes**" in line:
            changes = _parse_field_value(line)
        elif "**验证**" in line or "**Validation**" in line:
            validation = _parse_field_value(line)
        elif "**DoD**" in line:
            dod = _parse_field_value(line)

        i += 1

    # Convert string dependencies to Dependency objects
    dependency_objects: List[Dependency] = []
    for dep_id in dependencies:
        if dep_id and dep_id.lower() not in ["无", "none", "none"]:
            dependency_objects.append(Dependency(task_id=dep_id))

    # Create task
    task = Task(
        id=task_id,
        description=description,
        dependencies=dependency_objects,
        parallel=parallel,
        tdd=True,  # Default to TDD
        file=file,
    )

    return task, i - start_idx


def _parse_dependency_field(line: str) -> List[str]:
    """
    Parse dependency field from line.

    Examples:
        - **依赖**: T001, T002
        - **Dependencies**: T001
    """
    # Extract value after colon
    match = re.search(r"[:：]\s*(.+)", line)
    if not match:
        return []

    value = match.group(1).strip()

    # Split by comma
    deps = [d.strip() for d in value.split(",")]
    return [d for d in deps if d]


def _parse_field_value(line: str) -> Optional[str]:
    """
    Parse field value from line.

    Extracts the value after colon/mark.
    Handles backticks and other formatting.
    """
    # Extract value after colon
    match = re.search(r"[:：]\s*(.+)", line)
    if not match:
        return None

    value = match.group(1).strip()

    # Remove backticks
    value = re.sub(r"`([^`]+)`", r"\1", value)

    # Remove markdown bold
    value = re.sub(r"\*\*([^*]+)\*\*", r"\1", value)

    return value


def extract_task_from_markdown(markdown: str) -> Optional[Task]:
    """
    Extract a single task from markdown format.

    Args:
        markdown: Markdown string containing task definition (can be multiline)

    Returns:
        Task object or None if parsing fails
    """
    # Extract task ID and description from first line
    # Format: - [ ] **T001 Description** or - [x] **T001 Description**
    lines = markdown.strip().split("\n")
    first_line = lines[0].strip()

    task_pattern = r"-\s*\[([ x])\]\s*\*\*([A-Z]?\d+)\s+(.+?)\*\*"
    match = re.match(task_pattern, first_line)

    if not match:
        return None

    status_char = match.group(1)
    task_id = match.group(2)
    description = match.group(3).strip()

    # Determine task status
    status = TaskStatus.COMPLETED if status_char == "x" else TaskStatus.PENDING

    # Check if parallel task (but don't remove it from description for tests)
    parallel = is_parallel_task(description)

    # Check if TDD task
    tdd = "(TDD)" in description or "（TDD）" in description

    # Parse remaining lines for dependencies and file
    dependencies: List[Dependency] = []
    file_target = None

    for line in lines[1:]:
        line = line.strip()

        # Extract dependencies
        if "**依赖**" in line or "**Dependencies**" in line:
            deps_str = _parse_field_value(line)
            if deps_str and deps_str.lower() not in ["无", "none", "无"]:
                dependencies = extract_dependencies_from_markdown(deps_str)

        # Extract file/product
        if "**产物**" in line or "**Product**" in line or "**file**" in line.lower():
            file_target = _parse_field_value(line)

    return Task(
        id=task_id,
        description=description,
        status=status,
        dependencies=dependencies,
        parallel=parallel,
        tdd=tdd,
        file=file_target,
    )


def extract_dependencies_from_markdown(deps_str: str) -> List[Dependency]:
    """
    Extract dependencies from dependency string.

    Args:
        deps_str: String like "T001", "T001, T002", or "无"

    Returns:
        List of Dependency objects
    """
    if not deps_str or deps_str.strip() == "无":
        return []

    # Split by comma and clean up
    dep_ids = [d.strip() for d in deps_str.split(",")]
    dependencies = []

    for dep_id in dep_ids:
        if dep_id:
            dependencies.append(Dependency(task_id=dep_id))

    return dependencies


def is_parallel_task(description: str) -> bool:
    """
    Check if task is marked as parallel.

    Args:
        description: Task description string

    Returns:
        True if task has [P] marker
    """
    return "[P]" in description


def parse_tasks_md(content: str) -> List[Phase]:
    """
    Parse tasks.md markdown content into structured phases.

    Args:
        content: Markdown content from tasks.md

    Returns:
        List of Phase objects containing tasks
    """
    phases: List[Phase] = []
    current_phase: Optional[Phase] = None
    phase_counter = 0

    lines = content.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check for phase header
        # Format: ### Phase X：Name or ### Phase A
        phase_match = re.match(r"###\s+([^：:]+?)[：:]\s*(.*)", line)
        if not phase_match:
            # Try without colon: ### Phase A
            phase_match = re.match(r"###\s+(.+)", line)

        if phase_match:
            # Save previous phase
            if current_phase:
                phases.append(current_phase)

            # Create new phase
            phase_counter += 1
            phase_id = f"phase-{chr(96 + phase_counter)}"  # phase-a, phase-b, etc.
            phase_name = phase_match.group(1).strip()
            phase_desc = phase_match.group(2).strip() if len(phase_match.groups()) >= 2 and phase_match.group(2) else ""
            current_phase = Phase(id=phase_id, name=phase_name, description=phase_desc)
            i += 1
            continue

        # Try to extract task (may span multiple lines)
        if current_phase:
            # Collect all lines for this task
            task_lines = []
            j = i
            while j < len(lines):
                current_line = lines[j]
                # Stop if we hit another phase, empty line, or next task
                if current_line.startswith("###"):
                    break
                if j > i and current_line.strip() and not current_line.startswith("  "):
                    # Not indented, likely a new task
                    break
                task_lines.append(current_line)
                j += 1

            # Try to parse the task block
            task_block = "\n".join(task_lines)
            task = extract_task_from_markdown(task_block)
            if task:
                current_phase.tasks.append(task)

            i = j
        else:
            i += 1

    # Add last phase
    if current_phase:
        phases.append(current_phase)

    return phases


def parse_spec_md(content: str) -> Dict[str, str]:
    """
    Parse spec.md markdown content.

    Args:
        content: Markdown content from spec.md

    Returns:
        Dictionary with parsed sections
    """
    result = {
        "raw": content,
    }

    # Extract key sections (check if section name appears in content)
    sections = [
        "项目概述",
        "项目目标",
        "用户故事",
        "核心用户故事",
        "功能需求",
        "验收标准",
        "非功能需求",
        "约束与限制",
    ]

    for section in sections:
        if section in content:
            result[section] = section

    return result


def parse_plan_md(content: str) -> Dict[str, str]:
    """
    Parse plan.md markdown content.

    Args:
        content: Markdown content from plan.md

    Returns:
        Dictionary with parsed sections
    """
    result = {
        "raw": content,
    }

    # Extract key sections
    sections = [
        "技术上下文",
        "技术栈",
        "运行环境",
        "合宪性检查清单",
        "简单性门禁",
        "TDD门禁",
        "明确性门禁",
        "兼容性门禁",
        "项目结构",
        "目录结构",
        "数据结构",
        "接口设计",
    ]

    for section in sections:
        if section in content:
            result[section] = section

    return result
