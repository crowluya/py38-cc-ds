"""Content discovery and management."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from collections import defaultdict

import pathspec

from staticgen.config import ConfigManager, PageMetadata
from staticgen.processor import MarkdownProcessor


@dataclass
class ContentItem:
    """A single content item (page or post)."""

    filepath: Path
    metadata: PageMetadata
    html_content: str = ""
    url: str = ""
    output_path: Path = field(default_factory=Path)

    # Computed properties
    excerpt: str = ""
    word_count: int = 0
    reading_time: int = 0
    toc: str = ""

    # Relationships
    related_posts: List["ContentItem"] = field(default_factory=list)


@dataclass
class Collection:
    """A collection of content items."""

    name: str
    items: List[ContentItem] = field(default_factory=list)

    def sorted_by_date(self, reverse: bool = True) -> List[ContentItem]:
        """Get items sorted by date.

        Args:
            reverse: Sort descending if True

        Returns:
            Sorted list of items
        """
        def get_date(item: ContentItem) -> datetime:
            if item.metadata.date:
                try:
                    return datetime.fromisoformat(item.metadata.date)
                except (ValueError, TypeError):
                    pass
            # Use file modification time as fallback
            return datetime.fromtimestamp(item.filepath.stat().st_mtime)

        return sorted(self.items, key=get_date, reverse=reverse)

    def filter_by_tag(self, tag: str) -> List[ContentItem]:
        """Filter items by tag.

        Args:
            tag: Tag to filter by

        Returns:
            Filtered items
        """
        return [item for item in self.items if tag in item.metadata.tags]

    def filter_by_category(self, category: str) -> List[ContentItem]:
        """Filter items by category.

        Args:
            category: Category to filter by

        Returns:
            Filtered items
        """
        return [item for item in self.items if category in item.metadata.categories]

    def get_tags(self) -> Dict[str, List[ContentItem]]:
        """Get all tags and their items.

        Returns:
            Dictionary of tag -> items
        """
        tags = defaultdict(list)
        for item in self.items:
            for tag in item.metadata.tags:
                tags[tag].append(item)
        return dict(tags)

    def get_categories(self) -> Dict[str, List[ContentItem]]:
        """Get all categories and their items.

        Returns:
            Dictionary of category -> items
        """
        categories = defaultdict(list)
        for item in self.items:
            for category in item.metadata.categories:
                categories[category].append(item)
        return dict(categories)


class ContentDiscovery:
    """Discover and organize content files."""

    def __init__(self, config_manager: ConfigManager, processor: MarkdownProcessor):
        """Initialize content discovery.

        Args:
            config_manager: Configuration manager
            processor: Markdown processor
        """
        self.config_manager = config_manager
        self.processor = processor
        self.site_config = config_manager.load()
        self.base_dir = self.config_manager.base_dir

        # Content collections
        self.posts: Collection = Collection("posts")
        self.pages: Collection = Collection("pages")
        self.all_items: List[ContentItem] = []

    def discover(self) -> None:
        """Discover all content files."""
        content_dir = self.base_dir / self.site_config.content_dir

        if not content_dir.exists():
            return

        # Build ignore spec
        ignore_spec = self._build_ignore_spec()

        # Find all Markdown files
        for filepath in self._find_markdown_files(content_dir, ignore_spec):
            self._process_file(filepath)

        # Organize into collections
        self._organize_collections()

    def _build_ignore_spec(self) -> Optional[pathspec.PathSpec]:
        """Build pathspec from ignore patterns.

        Returns:
            PathSpec instance or None
        """
        if not self.site_config.ignore_files:
            return None

        return pathspec.PathSpec.from_lines(
            "gitwildmatch", self.site_config.ignore_files
        )

    def _find_markdown_files(
        self, root_dir: Path, ignore_spec: Optional[pathspec.PathSpec]
    ) -> List[Path]:
        """Find all Markdown files in directory.

        Args:
            root_dir: Root directory to search
            ignore_spec: PathSpec for ignore patterns

        Returns:
            List of Markdown file paths
        """
        markdown_files = []

        for filepath in root_dir.rglob("*.md"):
            # Check ignore patterns
            if ignore_spec:
                relative_path = filepath.relative_to(self.base_dir)
                if ignore_spec.match_file(str(relative_path)):
                    continue

            markdown_files.append(filepath)

        return markdown_files

    def _process_file(self, filepath: Path) -> None:
        """Process a single content file.

        Args:
            filepath: Path to file
        """
        # Parse file
        html_content, metadata = self.processor.process_file(filepath)

        # Skip drafts unless configured
        if metadata.draft and not self.site_config.include_drafts:
            return

        # Create content item
        item = ContentItem(
            filepath=filepath,
            metadata=metadata,
            html_content=html_content,
        )

        # Generate computed properties
        item.excerpt = self.processor.get_excerpt(html_content)
        item.word_count = self.processor.get_word_count(html_content)
        item.reading_time = self.processor.get_reading_time(html_content)
        item.toc = metadata.custom.get("toc", "")

        # Generate URL and output path
        item.url = self._generate_url(filepath, metadata)
        item.output_path = self._generate_output_path(item.url)

        self.all_items.append(item)

    def _generate_url(self, filepath: Path, metadata: PageMetadata) -> str:
        """Generate URL for content item.

        Args:
            filepath: Source file path
            metadata: Page metadata

        Returns:
            URL path
        """
        # Determine if post or page
        relative_path = filepath.relative_to(self.base_dir / self.site_config.content_dir)

        # Check if it's a post (in posts/ subdirectory)
        if "posts" in relative_path.parts:
            # Extract date prefix if present (YYYY-MM-DD-slug.md)
            stem = filepath.stem
            if stem.count("-") >= 2:
                # Remove date prefix
                parts = stem.split("-", 3)
                if len(parts) == 4:
                    slug = parts[3]
                else:
                    slug = stem
            else:
                slug = metadata.slug or stem

            # Use permalink format
            permalink = self.site_config.permalink_format
            url = permalink.replace("{{ slug }}", slug)
            url = url.replace("{{ year }}", metadata.date[:4] if metadata.date else "")
            url = url.replace("{{ month }}", metadata.date[5:7] if metadata.date and len(metadata.date) > 7 else "")
            url = url.replace("{{ day }}", metadata.date[8:10] if metadata.date and len(metadata.date) > 9 else "")
        else:
            # Page - use path structure
            slug = metadata.slug or filepath.stem
            url = f"/{slug}/" if slug != "index" else "/"

        # Ensure leading slash and no trailing slash for root
        url = "/" + url.lstrip("/")
        if url != "/":
            url = url.rstrip("/") + "/"

        return url

    def _generate_output_path(self, url: str) -> Path:
        """Generate output file path from URL.

        Args:
            url: Content URL

        Returns:
            Output file path
        """
        output_dir = self.base_dir / self.site_config.output_dir

        # Remove leading slash and convert URL to path
        if url == "/":
            return output_dir / "index.html"

        path = url.lstrip("/")
        if path.endswith("/"):
            path += "index.html"
        else:
            path += ".html"

        return output_dir / path

    def _organize_collections(self) -> None:
        """Organize content items into collections."""
        for item in self.all_items:
            # Check if it's a post
            if "posts" in item.filepath.parts or item.metadata.date:
                self.posts.items.append(item)
            else:
                self.pages.items.append(item)

        # Sort posts by date
        self.posts.items = self.posts.sorted_by_date()

    def get_recent_posts(self, limit: int = 10) -> List[ContentItem]:
        """Get recent posts.

        Args:
            limit: Maximum number of posts

        Returns:
            List of recent posts
        """
        return self.posts.items[:limit]

    def get_all_tags(self) -> Dict[str, List[ContentItem]]:
        """Get all tags across all posts.

        Returns:
            Dictionary of tag -> posts
        """
        return self.posts.get_tags()

    def get_all_categories(self) -> Dict[str, List[ContentItem]]:
        """Get all categories across all posts.

        Returns:
            Dictionary of category -> posts
        """
        return self.posts.get_categories()

    def get_archive_dates(self) -> Dict[str, List[ContentItem]]:
        """Get posts grouped by date (year/month).

        Returns:
            Dictionary of date string -> posts
        """
        archive = defaultdict(list)

        for item in self.posts.items:
            if item.metadata.date:
                try:
                    date_obj = datetime.fromisoformat(item.metadata.date)
                    key = date_obj.strftime("%Y/%m")
                    archive[key].append(item)
                except (ValueError, TypeError):
                    pass

        return dict(sorted(archive.items(), reverse=True))
