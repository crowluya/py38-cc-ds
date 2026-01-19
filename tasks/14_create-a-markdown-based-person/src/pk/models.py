"""Data models for the PK knowledge management system"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Set
import re


@dataclass
class Note:
    """Represents a single note in the knowledge base"""

    title: str
    content: str
    file_path: Path
    created: datetime = field(default_factory=datetime.now)
    modified: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    frontmatter: Dict = field(default_factory=dict)
    links: List[str] = field(default_factory=list)  # Outgoing links
    backlinks: List[str] = field(default_factory=list)  # Incoming links

    def __post_init__(self):
        """Normalize tags after initialization"""
        self.tags = [self.normalize_tag(tag) for tag in self.tags]

    @staticmethod
    def normalize_tag(tag: str) -> str:
        """Normalize tag format"""
        return tag.strip().lower().replace(" ", "-")

    @property
    def slug(self) -> str:
        """Generate slug from title for filename"""
        # Convert to lowercase, replace spaces with hyphens, remove special chars
        slug = re.sub(r'[^\w\s-]', '', self.title.lower())
        slug = re.sub(r'[-\s]+', '-', slug)
        return slug.strip('-')

    @property
    def filename(self) -> str:
        """Get the filename for this note"""
        return f"{self.slug}.md"


@dataclass
class Link:
    """Represents a link between notes"""

    source: str  # Source note title
    target: str  # Target note title
    alias: Optional[str] = None  # Optional display text
    line_number: Optional[int] = None


@dataclass
class SearchResult:
    """Represents a search result"""

    note: Note
    score: float
    matched_fields: List[str] = field(default_factory=list)
    snippet: Optional[str] = None


@dataclass
class Index:
    """Search and link index for the knowledge base"""

    notes_by_title: Dict[str, Note] = field(default_factory=dict)
    notes_by_tag: Dict[str, Set[str]] = field(default_factory=dict)
    links: List[Link] = field(default_factory=list)
    backlinks: Dict[str, Set[str]] = field(default_factory=dict)

    def add_note(self, note: Note):
        """Add a note to the index"""
        self.notes_by_title[note.title] = note

        # Index tags
        for tag in note.tags:
            if tag not in self.notes_by_tag:
                self.notes_by_tag[tag] = set()
            self.notes_by_tag[tag].add(note.title)

        # Initialize backlinks set
        if note.title not in self.backlinks:
            self.backlinks[note.title] = set()

    def remove_note(self, note: Note):
        """Remove a note from the index"""
        if note.title in self.notes_by_title:
            del self.notes_by_title[note.title]

        # Remove from tag index
        for tag in note.tags:
            if tag in self.notes_by_tag and note.title in self.notes_by_tag[tag]:
                self.notes_by_tag[tag].remove(note.title)

        # Remove from backlinks
        if note.title in self.backlinks:
            del self.backlinks[note.title]
