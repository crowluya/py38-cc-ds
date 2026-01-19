"""Search functionality for PK"""

import re
from typing import List, Optional
from difflib import SequenceMatcher

from .models import Note, SearchResult


class SearchEngine:
    """Full-text search across notes"""

    def __init__(self, notes: List[Note]):
        self.notes = notes

    def search(self, query: str, limit: int = 20) -> List[SearchResult]:
        """Perform full-text search across all notes"""
        if not query.strip():
            return []

        results = []
        query_lower = query.lower()

        for note in self.notes:
            score, matched_fields, snippet = self._search_note(note, query_lower)
            if score > 0:
                result = SearchResult(
                    note=note, score=score, matched_fields=matched_fields, snippet=snippet
                )
                results.append(result)

        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)

        return results[:limit]

    def _search_note(self, note: Note, query: str) -> tuple[float, List[str], Optional[str]]:
        """Search a single note and return (score, matched_fields, snippet)"""
        score = 0.0
        matched_fields = []
        snippet = None

        # Search in title (highest weight)
        if query in note.title.lower():
            score += 10.0
            matched_fields.append("title")

        # Search in tags (high weight)
        for tag in note.tags:
            if query in tag.lower():
                score += 5.0
                matched_fields.append("tags")
                break

        # Search in content
        content_lower = note.content.lower()
        if query in content_lower:
            # Calculate relevance based on number of occurrences
            occurrences = content_lower.count(query)
            score += min(occurrences * 1.0, 5.0)  # Max 5 points from content
            matched_fields.append("content")

            # Extract snippet with highlight
            snippet = self._extract_snippet(note.content, query)

        # Fuzzy matching for title
        if score == 0:
            similarity = SequenceMatcher(None, query, note.title.lower()).ratio()
            if similarity > 0.7:
                score += similarity * 3.0
                matched_fields.append("title (fuzzy)")

        return score, matched_fields, snippet

    def _extract_snippet(self, content: str, query: str, context_chars: int = 100) -> str:
        """Extract a snippet of content around the search query"""
        # Find first occurrence
        content_lower = content.lower()
        idx = content_lower.find(query)

        if idx == -1:
            # Return first line if no match (shouldn't happen)
            lines = content.split("\n")
            return lines[0][:100] + "..." if len(lines[0]) > 100 else lines[0]

        # Extract context around match
        start = max(0, idx - context_chars)
        end = min(len(content), idx + len(query) + context_chars)

        snippet = content[start:end]

        # Add ellipsis if truncated
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."

        return snippet

    def search_by_tag(self, tag: str) -> List[Note]:
        """Search notes by tag"""
        normalized_tag = Note.normalize_tag(tag)
        return [note for note in self.notes if normalized_tag in [Note.normalize_tag(t) for t in note.tags]]

    def search_by_link_target(self, target_title: str) -> List[Note]:
        """Find notes that link to a specific note"""
        return [note for note in self.notes if target_title in note.links]

    def advanced_search(
        self,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        has_links: bool = False,
        orphan: bool = False,
    ) -> List[Note]:
        """Advanced search with multiple filters"""
        results = self.notes.copy()

        # Filter by query
        if query:
            search_results = self.search(query)
            result_notes = {r.note.title for r in search_results}
            results = [n for n in results if n.title in result_notes]

        # Filter by tags (AND logic)
        if tags:
            normalized_tags = [Note.normalize_tag(t) for t in tags]
            for tag in normalized_tags:
                results = [n for n in results if tag in [Note.normalize_tag(t) for t in n.tags]]

        # Filter by has links
        if has_links:
            results = [n for n in results if n.links]

        # Filter by orphan (no backlinks)
        if orphan:
            results = [n for n in results if not n.backlinks]

        return results
