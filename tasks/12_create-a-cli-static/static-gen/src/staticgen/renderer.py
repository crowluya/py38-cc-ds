"""Template renderer using Jinja2."""

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from jinja2 import (
    Environment,
    FileSystemLoader,
    ChoiceLoader,
    select_autoescape,
    TemplateNotFound,
)

from staticgen.config import ConfigManager, PageMetadata
from staticgen.content import ContentItem


class TemplateRenderer:
    """Render templates using Jinja2."""

    def __init__(self, config_manager: ConfigManager):
        """Initialize template renderer.

        Args:
            config_manager: Configuration manager
        """
        self.config_manager = config_manager
        self.site_config = config_manager.load()
        self.base_dir = config_manager.base_dir

        # Setup Jinja2 environment
        self.env = self._setup_environment()

    def _setup_environment(self) -> Environment:
        """Setup Jinja2 environment with template loaders.

        Returns:
            Jinja2 Environment
        """
        # Template directories in order of precedence
        template_dirs = []

        # User's theme directory
        theme_name = self.site_config.theme
        if theme_name != "default":
            theme_dir = self.base_dir / "themes" / theme_name
            if theme_dir.exists():
                template_dirs.append(str(theme_dir / "templates"))

        # User's templates directory
        user_templates = self.base_dir / self.site_config.templates_dir
        if user_templates.exists():
            template_dirs.append(str(user_templates))

        # Built-in default templates
        default_templates = (
            Path(__file__).parent.parent.parent / "templates" / "default"
        )
        if default_templates.exists():
            template_dirs.append(str(default_templates))

        # Create loader
        if template_dirs:
            loader = ChoiceLoader([FileSystemLoader(d) for d in template_dirs])
        else:
            loader = FileSystemLoader(".")

        # Create environment
        env = Environment(
            loader=loader,
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Add custom filters
        self._register_filters(env)

        # Add custom globals
        self._register_globals(env)

        return env

    def _register_filters(self, env: Environment) -> None:
        """Register custom Jinja2 filters.

        Args:
            env: Jinja2 Environment
        """

        def date_filter(value: Any, format_str: Optional[str] = None) -> str:
            """Format date value."""
            if not value:
                return ""

            if format_str is None:
                format_str = self.site_config.date_format

            # Parse date if string
            if isinstance(value, str):
                try:
                    value = datetime.fromisoformat(value)
                except (ValueError, TypeError):
                    return value

            if isinstance(value, datetime):
                return value.strftime(format_str)

            return str(value)

        def slug_filter(value: str) -> str:
            """Convert string to URL slug."""
            from staticgen.utils import slugify
            return slugify(value)

        def excerpt_filter(html: str, length: int = 200) -> str:
            """Generate excerpt from HTML."""
            from staticgen.processor import MarkdownProcessor
            processor = MarkdownProcessor(self.config_manager)
            return processor.get_excerpt(html, length)

        def reading_time_filter(html: str) -> int:
            """Calculate reading time."""
            from staticgen.processor import MarkdownProcessor
            processor = MarkdownProcessor(self.config_manager)
            return processor.get_reading_time(html)

        def word_count_filter(html: str) -> int:
            """Count words in HTML."""
            from staticgen.processor import MarkdownProcessor
            processor = MarkdownProcessor(self.config_manager)
            return processor.get_word_count(html)

        # Register filters
        env.filters["date"] = date_filter
        env.filters["slug"] = slug_filter
        env.filters["excerpt"] = excerpt_filter
        env.filters["reading_time"] = reading_time_filter
        env.filters["word_count"] = word_count_filter

    def _register_globals(self, env: Environment) -> None:
        """Register global variables and functions.

        Args:
            env: Jinja2 Environment
        """
        env.globals["site"] = {
            "title": self.site_config.title,
            "description": self.site_config.description,
            "author": self.site_config.author,
            "email": self.site_config.email,
            "url": self.site_config.url,
            "base_url": self.site_config.base_url,
            "language": self.site_config.language,
            "timezone": self.site_config.timezone,
        }

        env.globals["now"] = datetime.now()

    def render(
        self,
        template_name: str,
        context: Dict[str, Any],
    ) -> str:
        """Render a template with context.

        Args:
            template_name: Name of template file
            context: Template context variables

        Returns:
            Rendered HTML
        """
        try:
            template = self.env.get_template(template_name)
            return template.render(**context)
        except TemplateNotFound:
            # Try to fallback to a default template
            try:
                template = self.env.get_template("default.html")
                return template.render(**context)
            except TemplateNotFound as e:
                raise TemplateError(f"Template not found: {template_name}") from e
        except Exception as e:
            raise TemplateError(f"Error rendering template {template_name}: {e}")

    def render_page(self, item: ContentItem, extra_context: Optional[Dict[str, Any]] = None) -> str:
        """Render a content item.

        Args:
            item: Content item to render
            extra_context: Additional context variables

        Returns:
            Rendered HTML
        """
        # Determine template
        template_name = item.metadata.template or "post.html"
        if item.metadata.layout:
            template_name = item.metadata.layout

        # Build context
        context = {
            "page": {
                "title": item.metadata.title,
                "slug": item.metadata.slug,
                "date": item.metadata.date,
                "updated": item.metadata.updated,
                "author": item.metadata.author,
                "tags": item.metadata.tags,
                "categories": item.metadata.categories,
                "description": item.metadata.description,
                "url": item.url,
                "excerpt": item.excerpt,
                "word_count": item.word_count,
                "reading_time": item.reading_time,
                "toc": item.toc,
            },
            "content": item.html_content,
            "metadata": item.metadata,
        }

        # Add custom metadata
        context.update(item.metadata.custom)

        # Add extra context
        if extra_context:
            context.update(extra_context)

        return self.render(template_name, context)

    def render_index(
        self,
        posts: list,
        page: int = 1,
        total_pages: int = 1,
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Render index page with posts.

        Args:
            posts: List of posts to display
            page: Current page number
            total_pages: Total number of pages
            extra_context: Additional context variables

        Returns:
            Rendered HTML
        """
        context = {
            "page": {
                "title": self.site_config.title,
                "description": self.site_config.description,
            },
            "posts": posts,
            "pagination": {
                "page": page,
                "total_pages": total_pages,
                "has_prev": page > 1,
                "has_next": page < total_pages,
                "prev_page": page - 1 if page > 1 else None,
                "next_page": page + 1 if page < total_pages else None,
            },
        }

        if extra_context:
            context.update(extra_context)

        return self.render("index.html", context)

    def render_tag(
        self,
        tag: str,
        posts: list,
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Render tag page.

        Args:
            tag: Tag name
            posts: Posts with this tag
            extra_context: Additional context variables

        Returns:
            Rendered HTML
        """
        context = {
            "page": {
                "title": f"Tag: {tag}",
                "description": f"Posts tagged with {tag}",
            },
            "tag": tag,
            "posts": posts,
        }

        if extra_context:
            context.update(extra_context)

        return self.render("tag.html", context)

    def render_category(
        self,
        category: str,
        posts: list,
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Render category page.

        Args:
            category: Category name
            posts: Posts in this category
            extra_context: Additional context variables

        Returns:
            Rendered HTML
        """
        context = {
            "page": {
                "title": f"Category: {category}",
                "description": f"Posts in {category}",
            },
            "category": category,
            "posts": posts,
        }

        if extra_context:
            context.update(extra_context)

        return self.render("category.html", context)


class TemplateError(Exception):
    """Template rendering errors."""

    pass
