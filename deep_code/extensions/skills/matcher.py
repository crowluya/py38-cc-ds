"""
Skills Task Matcher

Python 3.8.10 compatible
Implements SKILL-004: Task matching algorithm.

Matches user tasks to relevant skills based on description similarity.
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from deep_code.extensions.skills.parser import SkillDefinition
from deep_code.extensions.skills.registry import SkillRegistry, extract_keywords


@dataclass
class MatchResult:
    """Result of skill matching."""

    skill: SkillDefinition
    score: float
    matched_keywords: List[str]

    @property
    def is_strong_match(self) -> bool:
        """Check if this is a strong match (score > 0.5)."""
        return self.score > 0.5

    @property
    def is_weak_match(self) -> bool:
        """Check if this is a weak match (score <= 0.3)."""
        return self.score <= 0.3


def calculate_keyword_overlap(
    query_keywords: set,
    skill_keywords: set,
) -> Tuple[float, List[str]]:
    """
    Calculate keyword overlap score.

    Args:
        query_keywords: Keywords from query
        skill_keywords: Keywords from skill

    Returns:
        Tuple of (score, matched_keywords)
    """
    if not query_keywords or not skill_keywords:
        return 0.0, []

    matches = query_keywords & skill_keywords
    if not matches:
        return 0.0, []

    # Score based on percentage of query keywords matched
    # Also consider what percentage of skill keywords matched
    query_coverage = len(matches) / len(query_keywords)
    skill_coverage = len(matches) / len(skill_keywords)

    # Weighted average favoring query coverage
    score = (query_coverage * 0.7) + (skill_coverage * 0.3)

    return score, list(matches)


def extract_task_keywords(task: str) -> set:
    """
    Extract keywords from a task description.

    Applies task-specific preprocessing.

    Args:
        task: Task description

    Returns:
        Set of keywords
    """
    # Normalize task
    task_lower = task.lower()

    # Remove common task prefixes
    prefixes = [
        "please ", "can you ", "could you ", "i want to ",
        "i need to ", "help me ", "let's ", "let me ",
    ]
    for prefix in prefixes:
        if task_lower.startswith(prefix):
            task_lower = task_lower[len(prefix):]
            break

    return extract_keywords(task_lower)


class SkillMatcher:
    """
    Matches tasks to relevant skills.

    Uses keyword-based matching with scoring.
    """

    # Minimum score threshold for a match
    MIN_MATCH_SCORE = 0.2

    # Score boost for exact name match
    NAME_MATCH_BOOST = 0.5

    def __init__(self, registry: SkillRegistry) -> None:
        """
        Initialize skill matcher.

        Args:
            registry: Skill registry to search
        """
        self._registry = registry

    def match(
        self,
        task: str,
        limit: int = 3,
        min_score: Optional[float] = None,
    ) -> List[MatchResult]:
        """
        Find skills matching a task.

        Args:
            task: Task description
            limit: Maximum results to return
            min_score: Minimum score threshold (defaults to MIN_MATCH_SCORE)

        Returns:
            List of MatchResult objects, sorted by score descending
        """
        if min_score is None:
            min_score = self.MIN_MATCH_SCORE

        task_keywords = extract_task_keywords(task)
        if not task_keywords:
            return []

        results: List[MatchResult] = []

        for entry in self._registry._entries.values():
            skill = entry.definition

            # Calculate keyword overlap
            score, matched = calculate_keyword_overlap(
                task_keywords,
                entry.keywords,
            )

            # Boost score if skill name appears in task
            if skill.name.lower() in task.lower():
                score += self.NAME_MATCH_BOOST
                if skill.name.lower() not in matched:
                    matched.append(skill.name.lower())

            # Check for slash command reference (e.g., "/pdf")
            slash_pattern = rf"/{re.escape(skill.name)}\b"
            if re.search(slash_pattern, task, re.IGNORECASE):
                score += self.NAME_MATCH_BOOST * 2  # Strong boost for explicit reference
                if skill.name.lower() not in matched:
                    matched.append(skill.name.lower())

            if score >= min_score:
                results.append(MatchResult(
                    skill=skill,
                    score=min(score, 1.0),  # Cap at 1.0
                    matched_keywords=matched,
                ))

        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)

        return results[:limit]

    def find_best_match(self, task: str) -> Optional[MatchResult]:
        """
        Find the best matching skill for a task.

        Args:
            task: Task description

        Returns:
            Best MatchResult or None if no match
        """
        results = self.match(task, limit=1)
        return results[0] if results else None

    def find_by_name(self, name: str) -> Optional[SkillDefinition]:
        """
        Find a skill by exact name.

        Args:
            name: Skill name

        Returns:
            SkillDefinition or None
        """
        return self._registry.get(name)

    def find_by_slash_command(self, command: str) -> Optional[SkillDefinition]:
        """
        Find a skill by slash command.

        Args:
            command: Slash command (e.g., "/pdf" or "pdf")

        Returns:
            SkillDefinition or None
        """
        # Remove leading slash if present
        name = command.lstrip("/")
        return self._registry.get(name)

    def suggest_skills(
        self,
        task: str,
        threshold: float = 0.3,
    ) -> List[SkillDefinition]:
        """
        Suggest skills that might be relevant for a task.

        Lower threshold than match() for suggestions.

        Args:
            task: Task description
            threshold: Minimum score threshold

        Returns:
            List of suggested SkillDefinition objects
        """
        results = self.match(task, limit=5, min_score=threshold)
        return [r.skill for r in results]

    def is_skill_relevant(self, task: str, skill_name: str) -> bool:
        """
        Check if a specific skill is relevant for a task.

        Args:
            task: Task description
            skill_name: Skill name to check

        Returns:
            True if skill is relevant
        """
        results = self.match(task, limit=10)
        return any(r.skill.name == skill_name for r in results)


def create_matcher(
    project_root=None,
    include_user_skills: bool = True,
) -> SkillMatcher:
    """
    Create a skill matcher with a new registry.

    Args:
        project_root: Project root directory
        include_user_skills: Whether to include user-level skills

    Returns:
        Configured SkillMatcher
    """
    registry = SkillRegistry(
        project_root=project_root,
        include_user_skills=include_user_skills,
    )
    registry.load()
    return SkillMatcher(registry)
