"""
SDD (Spec-Driven Development) Module

Python 3.8.10 compatible

This module implements the SDD workflow: spec → plan → tasks → implementation

Submodules:
- models: Data structures for Task, Phase, Dependency
- parser: Parse spec.md, plan.md, tasks.md markdown into structured data
- analyzer: Analyze dependencies, topological sort, cycle detection
- generator: Generate plan.md from spec.md, tasks.md from plan.md using LLM
"""

from claude_code.sdd.analyzer import CircularDependencyError, DependencyAnalyzer
from claude_code.sdd.generator import PlanGenerator, TaskGenerator
from claude_code.sdd.models import Dependency, Phase, Task, TaskStatus
from claude_code.sdd.parser import (
    TaskParseError,
    extract_dependencies_from_markdown,
    extract_task_from_markdown,
    is_parallel_task,
    parse_plan_md,
    parse_spec_md,
    parse_tasks_markdown,
    parse_tasks_md,
)

__all__ = [
    # Models
    "Task",
    "Phase",
    "Dependency",
    "TaskStatus",
    # Parser
    "parse_tasks_markdown",
    "parse_tasks_md",
    "parse_spec_md",
    "parse_plan_md",
    "extract_task_from_markdown",
    "extract_dependencies_from_markdown",
    "is_parallel_task",
    "TaskParseError",
    # Analyzer
    "DependencyAnalyzer",
    "CircularDependencyError",
    # Generator
    "PlanGenerator",
    "TaskGenerator",
]
