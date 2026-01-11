"""
Skills Extension for DeepCode

Python 3.8.10 compatible
Implements skill discovery, loading, and execution.
"""

from deep_code.extensions.skills.loader import (
    SkillLoader,
    SkillLocation,
    find_skill_directories,
    get_default_skill_paths,
)
from deep_code.extensions.skills.parser import (
    SkillDefinition,
    parse_skill_definition,
    load_skill_from_path,
    load_skill_from_directory,
)
from deep_code.extensions.skills.registry import (
    SkillRegistry,
    SkillEntry,
)
from deep_code.extensions.skills.matcher import (
    SkillMatcher,
    MatchResult,
    create_matcher,
)
from deep_code.extensions.skills.executor import (
    SkillExecutor,
    SkillContext,
    build_skill_context,
)

__all__ = [
    # Loader
    "SkillLoader",
    "SkillLocation",
    "find_skill_directories",
    "get_default_skill_paths",
    # Parser
    "SkillDefinition",
    "parse_skill_definition",
    "load_skill_from_path",
    "load_skill_from_directory",
    # Registry
    "SkillRegistry",
    "SkillEntry",
    # Matcher
    "SkillMatcher",
    "MatchResult",
    "create_matcher",
    # Executor
    "SkillExecutor",
    "SkillContext",
    "build_skill_context",
]
