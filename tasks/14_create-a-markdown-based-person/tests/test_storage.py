"""Tests for storage and indexing"""

import pytest
import tempfile
import shutil
from pathlib import Path
from pk.storage import Storage
from pk.config import Config
from pk.parser import MarkdownParser


@pytest.fixture
def temp_storage():
    """Create a temporary storage for testing"""
    temp_dir = tempfile.mkdtemp()
    notes_dir = Path(temp_dir) / "notes"
    notes_dir.mkdir()

    config = Config()
    config.notes_directory = notes_dir

    storage = Storage(config)
    yield storage

    # Cleanup
    shutil.rmtree(temp_dir)


def test_create_note(temp_storage):
    """Test creating a new note"""
    note = temp_storage.create_note("Test Note", "Content here", ["tag1"])

    assert note.title == "Test Note"
    assert note.content == "Content here"
    assert "tag1" in note.tags
    assert note.file_path.exists()


def test_build_index(temp_storage):
    """Test building the index"""
    # Create multiple notes
    temp_storage.create_note("Note 1", "Content 1", ["python"])
    temp_storage.create_note("Note 2", "Content 2", ["javascript"])
    temp_storage.create_note("Note 3", "Content 3", ["python"])

    index = temp_storage.build_index()

    assert len(index.notes_by_title) == 3
    assert "python" in index.notes_by_tag
    assert len(index.notes_by_tag["python"]) == 2


def test_notes_by_tag(temp_storage):
    """Test filtering notes by tag"""
    temp_storage.create_note("Note 1", "Content 1", ["python"])
    temp_storage.create_note("Note 2", "Content 2", ["javascript"])
    temp_storage.build_index()

    python_notes = temp_storage.get_notes_by_tag("python")
    assert len(python_notes) == 1
    assert python_notes[0].title == "Note 1"


def test_backlink_tracking(temp_storage):
    """Test backlink tracking"""
    note1 = temp_storage.create_note("Note 1", "Links to [[Note 2]]")
    note2 = temp_storage.create_note("Note 2", "Links to [[Note 1]]")

    temp_storage.build_index()

    backlinks_to_1 = temp_storage.get_backlinks("Note 1")
    assert len(backlinks_to_1) == 1
    assert backlinks_to_1[0].title == "Note 2"


def test_find_broken_links(temp_storage):
    """Test finding broken links"""
    note = temp_storage.create_note("Note 1", "Links to [[Non-existent Note]]")
    temp_storage.build_index()

    broken = temp_storage.find_broken_links()
    assert "Note 1" in broken
    assert "Non-existent Note" in broken["Note 1"]


def test_find_orphan_notes(temp_storage):
    """Test finding orphan notes"""
    note1 = temp_storage.create_note("Note 1", "Content")
    note2 = temp_storage.create_note("Note 2", "Links to [[Note 1]]")

    temp_storage.build_index()

    orphans = temp_storage.find_orphan_notes()
    assert len(orphans) == 1
    assert orphans[0].title == "Note 1"
