"""Utility functions."""

import re
import unicodedata
from datetime import datetime


def slugify(text: str) -> str:
    """Convert text to URL slug.

    Args:
        text: Text to convert

    Returns:
        Slugified text
    """
    # Normalize unicode
    text = unicodedata.normalize("NFKD", text)

    # Convert to lowercase
    text = text.lower()

    # Remove non-word characters
    text = re.sub(r"[^\w\s-]", "", text)

    # Convert spaces/hyphens to single hyphen
    text = re.sub(r"[-\s]+", "-", text)

    # Strip leading/trailing hyphens
    text = text.strip("-")

    return text


def get_current_date() -> str:
    """Get current date in ISO format.

    Returns:
        Current date string
    """
    return datetime.now().isoformat()


def truncate_words(text: str, num_words: int, suffix: str = "...") -> str:
    """Truncate text to number of words.

    Args:
        text: Text to truncate
        num_words: Maximum number of words
        suffix: Suffix to add if truncated

    Returns:
        Truncated text
    """
    words = text.split()
    if len(words) <= num_words:
        return text
    return " ".join(words[:num_words]) + suffix


def format_date(
    date_str: str,
    input_format: str = "%Y-%m-%d",
    output_format: str = "%B %d, %Y",
) -> str:
    """Format date string.

    Args:
        date_str: Date string
        input_format: Format of input date
        output_format: Format for output

    Returns:
        Formatted date string
    """
    try:
        date_obj = datetime.strptime(date_str, input_format)
        return date_obj.strftime(output_format)
    except ValueError:
        return date_str


def clean_html(html: str) -> str:
    """Clean HTML by removing extra whitespace.

    Args:
        html: HTML content

    Returns:
        Cleaned HTML
    """
    # Remove multiple spaces
    html = re.sub(r"\s+", " ", html)
    # Remove spaces between tags
    html = re.sub(r">\s+<", "><", html)
    return html.strip()


def get_relative_url(current_url: str, target_url: str) -> str:
    """Get relative URL from current to target.

    Args:
        current_url: Current page URL
        target_url: Target page URL

    Returns:
        Relative URL path
    """
    # Simple implementation - just return absolute URL
    # A full implementation would compute relative paths
    return target_url
