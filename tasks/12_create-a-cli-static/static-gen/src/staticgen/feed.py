"""RSS/Atom feed generator."""

from datetime import datetime
from pathlib import Path
from typing import List

from feedgenerator import Rss201rev2Feed, Atom1Feed

from staticgen.config import ConfigManager
from staticgen.content import ContentDiscovery, ContentItem


class FeedGenerator:
    """Generate RSS and Atom feeds."""

    def __init__(
        self,
        config_manager: ConfigManager,
        content_discovery: ContentDiscovery,
    ):
        """Initialize feed generator.

        Args:
            config_manager: Configuration manager
            content_discovery: Content discovery instance
        """
        self.config_manager = config_manager
        self.content_discovery = content_discovery
        self.site_config = config_manager.load()
        self.base_dir = config_manager.base_dir
        self.base_url = self.site_config.url

    def generate_rss(self) -> None:
        """Generate RSS 2.0 feed."""
        feed = self._build_feed(Rss201rev2Feed)
        content = feed.writeString("utf-8")

        output_path = self.base_dir / self.site_config.output_dir / "feed.xml"
        output_path.write_text(content, encoding="utf-8")

    def generate_atom(self) -> None:
        """Generate Atom 1.0 feed."""
        feed = self._build_feed(Atom1Feed)
        content = feed.writeString("utf-8")

        output_path = self.base_dir / self.site_config.output_dir / "atom.xml"
        output_path.write_text(content, encoding="utf-8")

    def _build_feed(self, feed_class) -> Any:
        """Build feed object.

        Args:
            feed_class: Feed generator class

        Returns:
            Feed object
        """
        # Get recent posts
        feed_items = self.site_config.feed_items
        posts = self.content_discovery.posts.items[:feed_items]

        # Create feed
        feed = feed_class(
            title=self.site_config.title,
            link=self.base_url,
            description=self.site_config.description,
            language=self.site_config.language,
            feed_url=f"{self.base_url}/feed.xml",
        )

        # Add posts to feed
        for post in posts:
            feed.add_item(
                title=post.metadata.title,
                link=f"{self.base_url}{post.url}",
                description=post.metadata.description or post.excerpt,
                content=post.html_content,
                author_name=post.metadata.author or self.site_config.author,
                pubdate=self._parse_date(post.metadata.date),
                updateddate=self._parse_date(post.metadata.updated) if post.metadata.updated else None,
                categories=post.metadata.tags,
                unique_id=f"{self.base_url}{post.url}",
            )

        return feed

    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string to datetime.

        Args:
            date_str: Date string

        Returns:
            datetime object
        """
        if not date_str:
            return datetime.now()

        try:
            return datetime.fromisoformat(date_str)
        except (ValueError, TypeError):
            return datetime.now()

    def generate_tag_feed(self, tag: str) -> None:
        """Generate RSS feed for specific tag.

        Args:
            tag: Tag name
        """
        from staticgen.utils import slugify

        tags = self.content_discovery.get_all_tags()
        posts = tags.get(tag, [])

        if not posts:
            return

        feed = Rss201rev2Feed(
            title=f"{self.site_config.title} - Tag: {tag}",
            link=self.base_url,
            description=f"Posts tagged with {tag}",
            language=self.site_config.language,
            feed_url=f"{self.base_url}/tag/{slugify(tag)}/feed.xml",
        )

        for post in posts[:self.site_config.feed_items]:
            feed.add_item(
                title=post.metadata.title,
                link=f"{self.base_url}{post.url}",
                description=post.metadata.description or post.excerpt,
                content=post.html_content,
                author_name=post.metadata.author or self.site_config.author,
                pubdate=self._parse_date(post.metadata.date),
                categories=post.metadata.tags,
                unique_id=f"{self.base_url}{post.url}",
            )

        content = feed.writeString("utf-8")
        output_path = (
            self.base_dir
            / self.site_config.output_dir
            / "tag"
            / slugify(tag)
            / "feed.xml"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")

    def generate_category_feed(self, category: str) -> None:
        """Generate RSS feed for specific category.

        Args:
            category: Category name
        """
        from staticgen.utils import slugify

        categories = self.content_discovery.get_all_categories()
        posts = categories.get(category, [])

        if not posts:
            return

        feed = Rss201rev2Feed(
            title=f"{self.site_config.title} - Category: {category}",
            link=self.base_url,
            description=f"Posts in {category}",
            language=self.site_config.language,
            feed_url=f"{self.base_url}/category/{slugify(category)}/feed.xml",
        )

        for post in posts[:self.site_config.feed_items]:
            feed.add_item(
                title=post.metadata.title,
                link=f"{self.base_url}{post.url}",
                description=post.metadata.description or post.excerpt,
                content=post.html_content,
                author_name=post.metadata.author or self.site_config.author,
                pubdate=self._parse_date(post.metadata.date),
                categories=post.metadata.tags,
                unique_id=f"{self.base_url}{post.url}",
            )

        content = feed.writeString("utf-8")
        output_path = (
            self.base_dir
            / self.site_config.output_dir
            / "category"
            / slugify(category)
            / "feed.xml"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
