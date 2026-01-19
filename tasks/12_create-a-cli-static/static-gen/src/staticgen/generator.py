"""Main site generator - orchestrates the build process."""

import shutil
from pathlib import Path
from typing import List

from staticgen.config import ConfigManager
from staticgen.processor import MarkdownProcessor
from staticgen.content import ContentDiscovery, ContentItem
from staticgen.renderer import TemplateRenderer, TemplateError
from staticgen.sitemap import SitemapGenerator
from staticgen.feed import FeedGenerator
from staticgen.assets import AssetCopier


class SiteGenerator:
    """Generate static site from content."""

    def __init__(
        self,
        config_manager: ConfigManager,
        verbose: bool = False,
    ):
        """Initialize site generator.

        Args:
            config_manager: Configuration manager
            verbose: Enable verbose output
        """
        self.config_manager = config_manager
        self.verbose = verbose
        self.site_config = config_manager.load()
        self.base_dir = config_manager.base_dir

        # Initialize components
        self.processor = MarkdownProcessor(config_manager)
        self.content_discovery = ContentDiscovery(config_manager, self.processor)
        self.renderer = TemplateRenderer(config_manager)

        # Statistics
        self.stats = {
            "posts": 0,
            "pages": 0,
            "assets": 0,
            "tags": 0,
            "categories": 0,
        }

    def build(self) -> None:
        """Build the complete site."""
        if self.verbose:
            print("Starting site build...")

        # Step 1: Discover content
        if self.verbose:
            print("Discovering content...")
        self.content_discovery.discover()

        # Step 2: Create output directory
        output_dir = self.base_dir / self.site_config.output_dir
        self._create_output_dir(output_dir)

        # Step 3: Copy static assets
        if self.verbose:
            print("Copying assets...")
        self._copy_assets()

        # Step 4: Generate pages and posts
        if self.verbose:
            print("Rendering content...")
        self._render_content()

        # Step 5: Generate index pages
        if self.verbose:
            print("Generating index pages...")
        self._render_indexes()

        # Step 6: Generate tag and category pages
        if self.verbose:
            print("Generating tag and category pages...")
        self._render_taxonomies()

        # Step 7: Generate sitemap
        if self.site_config.generate_sitemap:
            if self.verbose:
                print("Generating sitemap...")
            self._generate_sitemap()

        # Step 8: Generate RSS feeds
        if self.site_config.generate_feeds:
            if self.verbose:
                print("Generating feeds...")
            self._generate_feeds()

        # Print statistics
        self._print_stats()

    def _create_output_dir(self, output_dir: Path) -> None:
        """Create output directory.

        Args:
            output_dir: Output directory path
        """
        if output_dir.exists():
            # Clean output directory
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    def _copy_assets(self) -> None:
        """Copy static assets to output."""
        asset_copier = AssetCopier(self.config_manager)
        copied = asset_copier.copy_assets()
        self.stats["assets"] = copied

    def _render_content(self) -> None:
        """Render individual pages and posts."""
        for item in self.content_discovery.all_items:
            try:
                html = self.renderer.render_page(item)
                self._write_file(item.output_path, html)

                if item in self.content_discovery.posts.items:
                    self.stats["posts"] += 1
                else:
                    self.stats["pages"] += 1

                if self.verbose:
                    print(f"  Rendered: {item.url}")

            except TemplateError as e:
                print(f"Error rendering {item.filepath}: {e}")

    def _render_indexes(self) -> None:
        """Render index pages with pagination."""
        posts = self.content_discovery.posts.items
        posts_per_page = self.site_config.posts_per_page

        # Calculate total pages
        total_pages = (len(posts) + posts_per_page - 1) // posts_per_page

        # Generate paginated index pages
        for page_num in range(1, total_pages + 1):
            start_idx = (page_num - 1) * posts_per_page
            end_idx = start_idx + posts_per_page
            page_posts = posts[start_idx:end_idx]

            try:
                html = self.renderer.render_index(
                    posts=page_posts,
                    page=page_num,
                    total_pages=total_pages,
                )

                # Determine output path
                if page_num == 1:
                    output_path = self.base_dir / self.site_config.output_dir / "index.html"
                else:
                    output_path = (
                        self.base_dir
                        / self.site_config.output_dir
                        / "page"
                        / str(page_num)
                        / "index.html"
                    )

                self._write_file(output_path, html)

                if self.verbose:
                    print(f"  Rendered index: page {page_num}/{total_pages}")

            except TemplateError as e:
                print(f"Error rendering index page {page_num}: {e}")

    def _render_taxonomies(self) -> None:
        """Render tag and category pages."""
        # Render tag pages
        tags = self.content_discovery.get_all_tags()
        self.stats["tags"] = len(tags)

        for tag, tag_posts in tags.items():
            try:
                html = self.renderer.render_tag(tag, tag_posts)
                output_path = (
                    self.base_dir
                    / self.site_config.output_dir
                    / "tag"
                    / self._slugify(tag)
                    / "index.html"
                )
                self._write_file(output_path, html)

                if self.verbose:
                    print(f"  Rendered tag: {tag}")

            except TemplateError as e:
                print(f"Error rendering tag page {tag}: {e}")

        # Render category pages
        categories = self.content_discovery.get_all_categories()
        self.stats["categories"] = len(categories)

        for category, cat_posts in categories.items():
            try:
                html = self.renderer.render_category(category, cat_posts)
                output_path = (
                    self.base_dir
                    / self.site_config.output_dir
                    / "category"
                    / self._slugify(category)
                    / "index.html"
                )
                self._write_file(output_path, html)

                if self.verbose:
                    print(f"  Rendered category: {category}")

            except TemplateError as e:
                print(f"Error rendering category page {category}: {e}")

    def _generate_sitemap(self) -> None:
        """Generate XML sitemap."""
        sitemap_gen = SitemapGenerator(self.config_manager, self.content_discovery)
        sitemap_gen.generate()

    def _generate_feeds(self) -> None:
        """Generate RSS/Atom feeds."""
        feed_gen = FeedGenerator(self.config_manager, self.content_discovery)

        if self.site_config.feed_format in ["rss", "both"]:
            feed_gen.generate_rss()

        if self.site_config.feed_format in ["atom", "both"]:
            feed_gen.generate_atom()

    def _write_file(self, path: Path, content: str) -> None:
        """Write content to file.

        Args:
            path: Output file path
            content: Content to write
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def _slugify(self, text: str) -> str:
        """Convert text to URL slug.

        Args:
            text: Text to slugify

        Returns:
            Slugified text
        """
        from staticgen.utils import slugify
        return slugify(text)

    def _print_stats(self) -> None:
        """Print build statistics."""
        print("\n✓ Build complete!")
        print(f"\nStatistics:")
        print(f"  Posts: {self.stats['posts']}")
        print(f"  Pages: {self.stats['pages']}")
        print(f"  Tags: {self.stats['tags']}")
        print(f"  Categories: {self.stats['categories']}")
        print(f"  Assets: {self.stats['assets']}")
