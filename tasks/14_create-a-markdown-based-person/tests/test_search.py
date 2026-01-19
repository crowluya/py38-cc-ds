"""Tests for search functionality"""

import pytest
from pk.search import SearchEngine
from pk.models import Note
from pathlib import Path
from datetime import datetime


@pytest.fixture
def sample_notes():
    """Create sample notes for testing"""
    return [
        Note(
            title="Python Tutorial",
            content="Learn Python programming from scratch",
            file_path=Path("python.md"),
            tags=["python", "programming"],
        ),
        Note(
            title="JavaScript Guide",
            content="JavaScript for web development",
            file_path=Path("javascript.md"),
            tags=["javascript", "web"],
        ),
        Note(
            title="Web Development",
            content="Building websites with #python and #javascript",
            file_path=Path("web.md"),
            tags=["web", "development"],
            links=["Python Tutorial", "JavaScript Guide"],
        ),
    ]


def test_basic_search(sample_notes):
    """Test basic search functionality"""
    engine = SearchEngine(sample_notes)
    results = engine.search("python")

    assert len(results) > 0
    assert any(r.note.title == "Python Tutorial" for r in results)


def test_search_in_title(sample_notes):
    """Test search matches in title"""
    engine = SearchEngine(sample_notes)
    results = engine.search("python")

    # Title match should have higher score
    top_result = results[0]
    assert top_result.note.title == "Python Tutorial"
    assert top_result.score > 5


def test_search_by_tag(sample_notes):
    """Test filtering by tag"""
    engine = SearchEngine(sample_notes)
    results = engine.search_by_tag("python")

    assert len(results) == 1
    assert results[0].title == "Python Tutorial"


def test_search_by_link_target(sample_notes):
    """Test finding notes that link to a specific note"""
    engine = SearchEngine(sample_notes)
    results = engine.search_by_link_target("Python Tutorial")

    assert len(results) == 1
    assert results[0].title == "Web Development"


def test_advanced_search(sample_notes):
    """Test advanced search with filters"""
    engine = SearchEngine(sample_notes)

    # Search with tag filter
    results = engine.advanced_search(query="web", tags=["web"])
    assert len(results) == 1

    # Search for notes with links
    results = engine.advanced_search(has_links=True)
    assert len(results) == 1


def test_snippet_extraction(sample_notes):
    """Test snippet extraction around matches"""
    engine = SearchEngine(sample_notes)
    results = engine.search("programming")

    # Should have snippet
    assert results[0].snippet is not None
    assert "programming" in results[0].snippet.lower()
