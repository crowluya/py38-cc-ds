"""XML sitemap generator."""

from datetime import datetime
from pathlib import Path
from typing import Optional

from staticgen.config import ConfigManager
from staticgen.content import ContentDiscovery, ContentItem


class SitemapGenerator:
    """Generate XML sitemaps for SEO."""

    def __init__(
        self,
        config_manager: ConfigManager,
        content_discovery: ContentDiscovery,
    ):
        """Initialize sitemap generator.

        Args:
            config_manager: Configuration manager
            content_discovery: Content discovery instance
        """
        self.config_manager = config_manager
        self.content_discovery = content_discovery
        self.site_config = config_manager.load()
        self.base_url = self.site_config.url

    def generate(self) -> None:
        """Generate sitemap.xml file."""
        output_dir = self.config_manager.base_dir / self.site_config.output_dir
        sitemap_path = output_dir / "sitemap.xml"

        # Generate sitemap content
        content = self._generate_sitemap_content()

        # Write to file
        sitemap_path.write_text(content, encoding="utf-8")

        if self.site_config.generate_sitemap:
            # Also create robots.txt
            self._generate_robots_txt()

    def _generate_sitemap_content(self) -> str:
        """Generate sitemap XML content.

        Returns:
            XML content
        """
        lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')

        # Add homepage
        lines.append(self._format_url_entry(
            self.base_url + "/",
            changefreq="daily",
            priority="1.0"
        ))

        # Add posts
        for item in self.content_discovery.posts.items:
            url = self.base_url + item.url
            lastmod = self._get_lastmod(item)
            lines.append(self._format_url_entry(
                url,
                lastmod=lastmod,
                changefreq="monthly",
                priority="0.8"
            ))

        # Add pages
        for item in self.content_discovery.pages.items:
            url = self.base_url + item.url
            lastmod = self._get_lastmod(item)
            lines.append(self._format_url_entry(
                url,
                lastmod=lastmod,
                changefreq="monthly",
                priority="0.6"
            ))

        # Add tag pages
        tags = self.content_discovery.get_all_tags()
        for tag in tags.keys():
            from staticgen.utils import slugify
            url = f"{self.base_url}/tag/{slugify(tag)}/"
            lines.append(self._format_url_entry(
                url,
                changefreq="weekly",
                priority="0.5"
            ))

        # Add category pages
        categories = self.content_discovery.get_all_categories()
        for category in categories.keys():
            from staticgen.utils import slugify
            url = f"{self.base_url}/category/{slugify(category)}/"
            lines.append(self._format_url_entry(
                url,
                changefreq="weekly",
                priority="0.5"
            ))

        lines.append("</urlset>")
        return "\n".join(lines)

    def _format_url_entry(
        self,
        loc: str,
        lastmod: Optional[str] = None,
        changefreq: str = "monthly",
        priority: str = "0.5",
    ) -> str:
        """Format a URL entry for sitemap.

        Args:
            loc: URL location
            lastmod: Last modification date
            changefreq: Change frequency
            priority: Priority (0.0-1.0)

        Returns:
            Formatted XML entry
        """
        entry = f"  <url>"
        entry += f"<loc>{loc}</loc>"

        if lastmod:
            entry += f"<lastmod>{lastmod}</lastmod>"

        entry += f"<changefreq>{changefreq}</changefreq>"
        entry += f"<priority>{priority}</priority>"
        entry += f"</url>"

        return entry

    def _get_lastmod(self, item: ContentItem) -> str:
        """Get last modification date for item.

        Args:
            item: Content item

        Returns:
            Last modification date in ISO format
        """
        # Use updated date if available, otherwise use date
        date_str = item.metadata.updated or item.metadata.date

        if date_str:
            # Format as YYYY-MM-DD
            try:
                dt = datetime.fromisoformat(date_str)
                return dt.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                pass

        # Fallback to file modification time
        try:
            mtime = item.filepath.stat().st_mtime
            dt = datetime.fromtimestamp(mtime)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return datetime.now().strftime("%Y-%m-%d")

    def _generate_robots_txt(self) -> None:
        """Generate robots.txt file."""
        output_dir = self.config_manager.base_dir / self.site_config.output_dir
        robots_path = output_dir / "robots.txt"

        content = "# robots.txt\n"
        content += f"User-agent: *\n"
        content += "Allow: /\n"
        content += f"\n"
        content += f"Sitemap: {self.base_url}/sitemap.xml\n"

        robots_path.write_text(content, encoding="utf-8")
