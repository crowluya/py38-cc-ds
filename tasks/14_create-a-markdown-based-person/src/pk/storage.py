"""Storage and index management for PK"""

import json
from pathlib import Path
from typing import List, Optional, Set, Dict
from datetime import datetime
from difflib import get_close_matches

from .models import Note, Index, Link
from .config import Config
from .parser import MarkdownParser


class Storage:
    """Manage note storage and indexing"""

    def __init__(self, config: Config):
        self.config = config
        self.index = Index()
        self.notes_dir = config.ensure_notes_directory()

    def scan_notes(self) -> List[Note]:
        """Scan notes directory and load all notes"""
        notes = []
        for md_file in self.notes_dir.glob("*.md"):
            try:
                note = MarkdownParser.parse_file(md_file)
                notes.append(note)
            except Exception as e:
                print(f"Warning: Failed to parse {md_file}: {e}")
        return notes

    def build_index(self) -> Index:
        """Build the search and link index"""
        self.index = Index()
        notes = self.scan_notes()

        # Add all notes to index
        for note in notes:
            self.index.add_note(note)

        # Build link relationships
        for note in notes:
            for link_target in note.links:
                # Create outgoing link
                link = Link(source=note.title, target=link_target)
                self.index.links.append(link)

                # Add backlink
                if link_target not in self.index.backlinks:
                    self.index.backlinks[link_target] = set()
                self.index.backlinks[link_target].add(note.title)

        return self.index

    def resolve_link(self, link_text: str) -> Optional[Note]:
        """Resolve a wiki-style link to a note"""
        # Direct match
        if link_text in self.index.notes_by_title:
            return self.index.notes_by_title[link_text]

        # Case-insensitive match
        link_lower = link_text.lower()
        for title, note in self.index.notes_by_title.items():
            if title.lower() == link_lower:
                return note

        # Fuzzy match for typos
        titles = list(self.index.notes_by_title.keys())
        matches = get_close_matches(link_text, titles, n=1, cutoff=0.8)
        if matches:
            return self.index.notes_by_title[matches[0]]

        return None

    def get_notes_by_tag(self, tag: str) -> List[Note]:
        """Get all notes with a specific tag"""
        normalized_tag = Note.normalize_tag(tag)
        if normalized_tag not in self.index.notes_by_tag:
            return []

        note_titles = self.index.notes_by_tag[normalized_tag]
        return [self.index.notes_by_title[title] for title in note_titles]

    def get_all_tags(self) -> Set[str]:
        """Get all unique tags"""
        return set(self.index.notes_by_tag.keys())

    def get_backlinks(self, note_title: str) -> List[Note]:
        """Get all notes that link to the given note"""
        if note_title not in self.index.backlinks:
            return []

        backlink_titles = self.index.backlinks[note_title]
        return [self.index.notes_by_title[title] for title in backlink_titles]

    def create_note(
        self, title: str, content: str = "", tags: List[str] = None
    ) -> Note:
        """Create a new note"""
        if tags is None:
            tags = []

        # Create note object
        note = Note(
            title=title,
            content=content,
            file_path=self.notes_dir / "",  # Will be set below
            tags=tags,
        )

        # Set file path
        note.file_path = self.notes_dir / note.filename

        # Check if file already exists
        if note.file_path.exists():
            raise FileExistsError(f"Note already exists: {note.file_path}")

        # Create Markdown content
        markdown = MarkdownParser.create_note_markdown(title, content, tags)

        # Write to file
        with open(note.file_path, 'w', encoding='utf-8') as f:
            f.write(markdown)

        # Add to index
        self.index.add_note(note)

        return note

    def update_note(self, note: Note) -> None:
        """Update an existing note"""
        markdown = MarkdownParser.update_note_frontmatter(note)

        with open(note.file_path, 'w', encoding='utf-8') as f:
            f.write(markdown)

        # Update index
        self.index.add_note(note)

    def delete_note(self, note: Note) -> None:
        """Delete a note"""
        if note.file_path.exists():
            note.file_path.unlink()

        # Remove from index
        self.index.remove_note(note)

    def get_note_by_title(self, title: str) -> Optional[Note]:
        """Get a note by title"""
        return self.index.notes_by_title.get(title)

    def get_note_by_path(self, file_path: Path) -> Optional[Note]:
        """Get a note by file path"""
        for note in self.index.notes_by_title.values():
            if note.file_path == file_path:
                return note
        return None

    def find_broken_links(self) -> Dict[str, List[str]]:
        """Find all broken links (links to non-existent notes)"""
        broken = {}
        for link in self.index.links:
            if link.target not in self.index.notes_by_title:
                if link.source not in broken:
                    broken[link.source] = []
                broken[link.source].append(link.target)
        return broken

    def find_orphan_notes(self) -> List[Note]:
        """Find notes with no backlinks (not referenced by any other note)"""
        orphans = []
        for note in self.index.notes_by_title.values():
            if not self.index.backlinks.get(note.title):
                orphans.append(note)
        return orphans
