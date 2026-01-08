"""
SDD (Spec-Driven Development) Module

Python 3.8.10 compatible

This module implements the SDD workflow: spec → plan → tasks → implementation

Submodules:
- models: Data structures for Task, Phase, Dependency
- parser: Parse tasks.md markdown into Task objects
- analyzer: Analyze dependencies, topological sort, cycle detection
- generator: Generate tasks.md from plan.md using LLM
"""

from claude_code.sdd.analyzer import CircularDependencyError, DependencyAnalyzer
from claude_code.sdd.generator import TaskGenerator
from claude_code.sdd.models import Dependency, Phase, Task, TaskStatus
from claude_code.sdd.parser import TaskParseError, parse_tasks_markdown

__all__ = [
    # Models
    "Task",
    "Phase",
    "Dependency",
    "TaskStatus",
    # Parser
    "parse_tasks_markdown",
    "TaskParseError",
    # Analyzer
    "DependencyAnalyzer",
    "CircularDependencyError",
    # Generator
    "TaskGenerator",
]
