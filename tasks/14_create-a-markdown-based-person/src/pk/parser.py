"""Markdown parsing utilities for PK"""

import frontmatter
import re
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional
from .models import Note


class MarkdownParser:
    """Parse and manipulate Markdown notes"""

    # Wiki-style link pattern: [[Note Title]] or [[Note Title|Alias]]
    LINK_PATTERN = re.compile(r'\[\[([^\]]+)\]\]')

    # Tag patterns
    INLINE_TAG_PATTERN = re.compile(r'#(\w+(?:[-_]\w+)*)')

    @staticmethod
    def parse_file(file_path: Path) -> Note:
        """Parse a Markdown file into a Note object"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        return MarkdownParser.parse_content(content, file_path)

    @staticmethod
    def parse_content(content: str, file_path: Path) -> Note:
        """Parse Markdown content into a Note object"""
        # Parse frontmatter
        post = frontmatter.loads(content)

        # Extract title from frontmatter or first heading
        title = post.get('title', '')
        if not title:
            # Try to extract from first heading
            match = re.search(r'^#\s+(.+)$', post.content, re.MULTILINE)
            if match:
                title = match.group(1).strip()
            else:
                # Use filename as fallback
                title = file_path.stem.replace('-', ' ').replace('_', ' ').title()

        # Extract metadata
        created = post.get('created')
        if isinstance(created, str):
            try:
                created = datetime.fromisoformat(created)
            except ValueError:
                created = datetime.now()
        elif not isinstance(created, datetime):
            created = datetime.now()

        modified = post.get('modified')
        if isinstance(modified, str):
            try:
                modified = datetime.fromisoformat(modified)
            except ValueError:
                modified = datetime.now()
        elif not isinstance(modified, datetime):
            modified = datetime.now()

        # Extract tags
        tags = post.get('tags', [])
        if isinstance(tags, str):
            tags = [tag.strip() for tag in tags.split(',')]
        elif not isinstance(tags, list):
            tags = []

        # Also extract inline tags from content
        inline_tags = MarkdownParser.extract_inline_tags(post.content)
        all_tags = list(set(tags + inline_tags))

        # Extract links
        links = MarkdownParser.extract_links(post.content)

        # Create note
        note = Note(
            title=title,
            content=post.content,
            file_path=file_path,
            created=created,
            modified=modified,
            tags=all_tags,
            frontmatter=dict(post.metadata),
            links=links,
        )

        return note

    @staticmethod
    def extract_links(content: str) -> List[str]:
        """Extract wiki-style links from content"""
        links = []
        for match in MarkdownParser.LINK_PATTERN.finditer(content):
            link_text = match.group(1)
            # Handle alias syntax: [[Title|Alias]]
            if '|' in link_text:
                target_title = link_text.split('|')[0].strip()
            else:
                target_title = link_text.strip()
            links.append(target_title)
        return links

    @staticmethod
    def extract_inline_tags(content: str) -> List[str]:
        """Extract inline #tags from content"""
        tags = []
        for match in MarkdownParser.INLINE_TAG_PATTERN.finditer(content):
            tag = match.group(1)
            tags.append(tag)
        return tags

    @staticmethod
    def create_note_markdown(title: str, content: str = "", tags: List[str] = None) -> str:
        """Create a Markdown document with frontmatter"""
        if tags is None:
            tags = []

        frontmatter_data = {
            'title': title,
            'created': datetime.now().isoformat(),
            'modified': datetime.now().isoformat(),
            'tags': tags,
        }

        post = frontmatter.Post(content, **frontmatter_data)
        return frontmatter.dumps(post)

    @staticmethod
    def update_note_frontmatter(note: Note) -> str:
        """Update frontmatter for an existing note"""
        frontmatter_data = {
            'title': note.title,
            'created': note.created.isoformat() if isinstance(note.created, datetime) else note.created,
            'modified': datetime.now().isoformat(),
            'tags': note.tags,
        }

        # Add any additional frontmatter fields
        for key, value in note.frontmatter.items():
            if key not in ['title', 'created', 'modified', 'tags']:
                frontmatter_data[key] = value

        post = frontmatter.Post(note.content, **frontmatter_data)
        return frontmatter.dumps(post)
