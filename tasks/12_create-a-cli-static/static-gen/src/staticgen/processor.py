"""Markdown processor for converting Markdown to HTML."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import markdown
from markdown.extensions import Extension

from staticgen.config import ConfigManager, PageMetadata, ConfigError


class MarkdownProcessor:
    """Process Markdown files with frontmatter."""

    def __init__(self, config_manager: ConfigManager):
        """Initialize Markdown processor.

        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.site_config = config_manager.load()
        self._setup_markdown()

    def _setup_markdown(self) -> None:
        """Configure Markdown processor with extensions."""
        self.md = markdown.Markdown(
            extensions=self.site_config.markdown_extensions,
            extension_configs={
                "codehilite": {
                    "css_class": "highlight",
                    "linenums": False,
                },
                "toc": {
                    "permalink": True,
                    "permalink_title": "Link to this section",
                    "anchorlink": True,
                },
            },
            output_format="html",
        )

    def process_file(self, filepath: Path) -> Tuple[str, PageMetadata]:
        """Process a Markdown file.

        Args:
            filepath: Path to Markdown file

        Returns:
            Tuple of (HTML content, PageMetadata)
        """
        try:
            content = filepath.read_text(encoding="utf-8")
            return self.process_content(content, filepath)
        except Exception as e:
            raise ConfigError(f"Error processing {filepath}: {e}")

    def process_content(
        self, content: str, source_path: Path
    ) -> Tuple[str, PageMetadata]:
        """Process Markdown content.

        Args:
            content: Raw Markdown content
            source_path: Path to source file (for metadata)

        Returns:
            Tuple of (HTML content, PageMetadata)
        """
        # Load metadata from frontmatter
        metadata = self.config_manager.load_page_metadata(content, source_path)

        # Strip frontmatter from content
        content_without_frontmatter = self._strip_frontmatter(content)

        # Reset Markdown processor state
        self.md.reset()

        # Convert to HTML
        html_content = self.md.convert(content_without_frontmatter)

        # Extract table of contents if available
        toc = getattr(self.md, "toc", "")
        metadata.custom["toc"] = toc

        return html_content, metadata

    def _strip_frontmatter(self, content: str) -> str:
        """Remove YAML frontmatter from content.

        Args:
            content: Content with frontmatter

        Returns:
            Content without frontmatter
        """
        if not content.startswith("---"):
            return content

        parts = content.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()
        return content

    def get_excerpt(self, html_content: str, max_length: int = 200) -> str:
        """Generate excerpt from HTML content.

        Args:
            html_content: HTML content
            max_length: Maximum length in characters

        Returns:
            Plain text excerpt
        """
        from html.parser import HTMLParser

        class TextExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.text = []

            def handle_data(self, data: str) -> None:
                self.text.append(data)

        parser = TextExtractor()
        parser.feed(html_content)
        text = " ".join(parser.text)

        # Truncate to max length
        if len(text) > max_length:
            text = text[: max_length - 3].rsplit(" ", 1)[0] + "..."

        return text

    def get_reading_time(self, html_content: str, words_per_minute: int = 200) -> int:
        """Estimate reading time in minutes.

        Args:
            html_content: HTML content
            words_per_minute: Average reading speed

        Returns:
            Reading time in minutes
        """
        from html.parser import HTMLParser

        class WordCounter(HTMLParser):
            def __init__(self):
                super().__init__()
                self.word_count = 0

            def handle_data(self, data: str) -> None:
                self.word_count += len(data.split())

        parser = WordCounter()
        parser.feed(html_content)

        minutes = parser.word_count / words_per_minute
        return max(1, int(round(minutes)))

    def get_word_count(self, html_content: str) -> int:
        """Count words in HTML content.

        Args:
            html_content: HTML content

        Returns:
            Word count
        """
        from html.parser import HTMLParser

        class WordCounter(HTMLParser):
            def __init__(self):
                super().__init__()
                self.word_count = 0

            def handle_data(self, data: str) -> None:
                self.word_count += len(data.split())

        parser = WordCounter()
        parser.feed(html_content)
        return parser.word_count


class CodeHighlightExtension(Extension):
    """Custom extension for code highlighting with Pygments."""

    def extendMarkdown(self, md: markdown.Markdown) -> None:
        """Extend Markdown with code highlighting.

        Args:
            md: Markdown instance
        """
        # This would integrate with Pygments for syntax highlighting
        # For now, we rely on the codehilite extension
        pass


def render_markdown(content: str, extensions: Optional[List[str]] = None) -> str:
    """Quick Markdown to HTML conversion.

    Args:
        content: Markdown content
        extensions: List of extension names

    Returns:
        HTML content
    """
    md = markdown.Markdown(extensions=extensions or [])
    return md.convert(content)
