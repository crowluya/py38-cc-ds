"""
Skills Registry

Python 3.8.10 compatible
Implements SKILL-003: Skills index building.

Provides fast skill lookup by name and description keywords.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from deep_code.extensions.skills.loader import SkillLoader, SkillLocation
from deep_code.extensions.skills.parser import (
    SkillDefinition,
    load_skill_from_directory,
)


def extract_keywords(text: str) -> Set[str]:
    """
    Extract keywords from text for indexing.

    Args:
        text: Text to extract keywords from

    Returns:
        Set of lowercase keywords
    """
    # Remove punctuation and split into words
    words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9_-]*\b", text.lower())

    # Filter out common stop words
    stop_words = {
        "a", "an", "the", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "could", "should", "may", "might", "must", "shall",
        "can", "need", "dare", "ought", "used", "to", "of", "in",
        "for", "on", "with", "at", "by", "from", "as", "into",
        "through", "during", "before", "after", "above", "below",
        "between", "under", "again", "further", "then", "once",
        "here", "there", "when", "where", "why", "how", "all",
        "each", "few", "more", "most", "other", "some", "such",
        "no", "nor", "not", "only", "own", "same", "so", "than",
        "too", "very", "just", "and", "but", "if", "or", "because",
        "until", "while", "this", "that", "these", "those", "it",
        "its", "use", "using", "used", "when", "you", "your",
    }

    return {w for w in words if w not in stop_words and len(w) > 2}


@dataclass
class SkillEntry:
    """Entry in the skill registry."""

    definition: SkillDefinition
    location: SkillLocation
    keywords: Set[str] = field(default_factory=set)

    def __post_init__(self):
        """Build keyword index after initialization."""
        if not self.keywords:
            self.keywords = self._build_keywords()

    def _build_keywords(self) -> Set[str]:
        """Build keyword set from definition."""
        keywords = set()

        # Add name as keyword
        keywords.add(self.definition.name.lower())

        # Extract keywords from description
        if self.definition.description:
            keywords.update(extract_keywords(self.definition.description))

        # Add allowed tools as keywords
        for tool in self.definition.allowed_tools:
            keywords.add(tool.lower())

        return keywords

    def matches_query(self, query: str) -> float:
        """
        Calculate match score for a query.

        Args:
            query: Search query

        Returns:
            Match score (0.0 to 1.0)
        """
        query_keywords = extract_keywords(query)
        if not query_keywords:
            return 0.0

        # Calculate overlap
        matches = query_keywords & self.keywords
        if not matches:
            return 0.0

        # Score based on percentage of query keywords matched
        return len(matches) / len(query_keywords)


class SkillRegistry:
    """
    Registry for discovered skills.

    Provides fast lookup by name and keyword search.
    """

    def __init__(
        self,
        project_root: Optional[Path] = None,
        include_user_skills: bool = True,
    ) -> None:
        """
        Initialize skill registry.

        Args:
            project_root: Project root directory
            include_user_skills: Whether to include user-level skills
        """
        self._loader = SkillLoader(
            project_root=project_root,
            include_user_skills=include_user_skills,
        )
        self._entries: Dict[str, SkillEntry] = {}
        self._keyword_index: Dict[str, Set[str]] = {}  # keyword -> skill names
        self._loaded = False

        # Change callbacks
        self._on_change_callbacks: List[Callable[[], None]] = []

    def load(self) -> int:
        """
        Load and index all skills.

        Returns:
            Number of skills loaded
        """
        self._entries.clear()
        self._keyword_index.clear()

        # Scan for skill directories
        self._loader.scan()

        # Load each skill
        for location in self._loader.get_all():
            definition = load_skill_from_directory(
                location.path,
                scope=location.scope,
            )
            if definition:
                entry = SkillEntry(
                    definition=definition,
                    location=location,
                )
                self._entries[definition.name] = entry

                # Build keyword index
                for keyword in entry.keywords:
                    if keyword not in self._keyword_index:
                        self._keyword_index[keyword] = set()
                    self._keyword_index[keyword].add(definition.name)

        self._loaded = True

        # Notify callbacks
        for callback in self._on_change_callbacks:
            try:
                callback()
            except Exception:
                pass

        return len(self._entries)

    def get(self, name: str) -> Optional[SkillDefinition]:
        """
        Get a skill by name.

        Args:
            name: Skill name

        Returns:
            SkillDefinition or None
        """
        if not self._loaded:
            self.load()

        entry = self._entries.get(name)
        return entry.definition if entry else None

    def get_entry(self, name: str) -> Optional[SkillEntry]:
        """
        Get a skill entry by name.

        Args:
            name: Skill name

        Returns:
            SkillEntry or None
        """
        if not self._loaded:
            self.load()
        return self._entries.get(name)

    def search(self, query: str, limit: int = 5) -> List[SkillDefinition]:
        """
        Search for skills matching a query.

        Args:
            query: Search query
            limit: Maximum results to return

        Returns:
            List of matching SkillDefinition objects
        """
        if not self._loaded:
            self.load()

        # Score all skills
        scored: List[tuple] = []
        for entry in self._entries.values():
            score = entry.matches_query(query)
            if score > 0:
                scored.append((score, entry.definition))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        # Return top results
        return [s[1] for s in scored[:limit]]

    def find_by_keyword(self, keyword: str) -> List[SkillDefinition]:
        """
        Find skills by keyword.

        Args:
            keyword: Keyword to search for

        Returns:
            List of matching SkillDefinition objects
        """
        if not self._loaded:
            self.load()

        keyword_lower = keyword.lower()
        skill_names = self._keyword_index.get(keyword_lower, set())

        return [
            self._entries[name].definition
            for name in skill_names
            if name in self._entries
        ]

    def list_all(self) -> List[SkillDefinition]:
        """
        List all registered skills.

        Returns:
            List of all SkillDefinition objects
        """
        if not self._loaded:
            self.load()
        return [e.definition for e in self._entries.values()]

    def list_names(self) -> List[str]:
        """
        List all skill names.

        Returns:
            List of skill names
        """
        if not self._loaded:
            self.load()
        return list(self._entries.keys())

    def list_by_scope(self, scope: str) -> List[SkillDefinition]:
        """
        List skills by scope.

        Args:
            scope: Scope to filter by

        Returns:
            List of SkillDefinition objects
        """
        if not self._loaded:
            self.load()
        return [
            e.definition
            for e in self._entries.values()
            if e.definition.scope == scope
        ]

    def refresh(self) -> int:
        """
        Refresh the registry by reloading all skills.

        Returns:
            Number of skills loaded
        """
        return self.load()

    def on_change(self, callback: Callable[[], None]) -> None:
        """
        Register a callback for registry changes.

        Args:
            callback: Callback function
        """
        self._on_change_callbacks.append(callback)

    def format_available_skills(self) -> str:
        """
        Format available skills as XML for LLM context.

        Returns:
            XML string describing available skills
        """
        if not self._loaded:
            self.load()

        if not self._entries:
            return "<available_skills>\n  (No skills available)\n</available_skills>"

        lines = ["<available_skills>"]
        for entry in self._entries.values():
            skill = entry.definition
            lines.append("  <skill>")
            lines.append(f"    <name>{skill.name}</name>")
            lines.append(f"    <description>{skill.description}</description>")
            lines.append(f"    <location>{skill.scope}</location>")
            lines.append("  </skill>")
        lines.append("</available_skills>")

        return "\n".join(lines)

    @property
    def is_loaded(self) -> bool:
        """Check if registry has been loaded."""
        return self._loaded

    def __len__(self) -> int:
        """Return number of registered skills."""
        if not self._loaded:
            self.load()
        return len(self._entries)

    def __contains__(self, name: str) -> bool:
        """Check if a skill is registered."""
        if not self._loaded:
            self.load()
        return name in self._entries

    def __iter__(self):
        """Iterate over skill names."""
        if not self._loaded:
            self.load()
        return iter(self._entries.keys())
