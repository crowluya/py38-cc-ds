"""Tests for Markdown parser"""

import pytest
from pathlib import Path
from datetime import datetime
from pk.parser import MarkdownParser
from pk.models import Note


def test_parse_basic_note():
    """Test parsing a basic note"""
    content = """---
title: Test Note
tags: [python, testing]
created: 2024-01-01T00:00:00
modified: 2024-01-01T00:00:00
---

# Test Note

This is a test note with some content.
"""
    note = MarkdownParser.parse_content(content, Path("test.md"))

    assert note.title == "Test Note"
    assert note.tags == ["python", "testing"]
    assert "This is a test note" in note.content


def test_parse_inline_tags():
    """Test extraction of inline tags"""
    content = """# Test Note

This note has #inline and #tags in the content.
"""
    note = MarkdownParser.parse_content(content, Path("test.md"))

    assert "inline" in note.tags
    assert "tags" in note.tags


def test_extract_wiki_links():
    """Test extraction of wiki-style links"""
    content = """# Test Note

This links to [[Another Note]] and [[Third Note|alias]].
"""
    links = MarkdownParser.extract_links(content)

    assert "Another Note" in links
    assert "Third Note" in links
    assert len(links) == 2


def test_create_note_markdown():
    """Test creating markdown with frontmatter"""
    md = MarkdownParser.create_note_markdown(
        "Test Title", "Some content", ["tag1", "tag2"]
    )

    assert "title: Test Title" in md
    assert "Some content" in md
    assert "tag1" in md
    assert "tag2" in md


def test_note_slug():
    """Test note slug generation"""
    note = Note(title="My Test Note!", content="", file_path=Path("test.md"))

    assert note.slug == "my-test-note"


def test_tag_normalization():
    """Test tag normalization"""
    assert Note.normalize_tag("Test Tag") == "test-tag"
    assert Note.normalize_tag("  spaces  ") == "spaces"
