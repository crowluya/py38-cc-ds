#!/usr/bin/env python3
"""
NoteSearch - A portable note search utility

Indexes markdown files into an in-memory SQLite database with full-text search.
Supports tagging, filtering by date ranges, and exports results to JSON/HTML reports.

Usage:
    notesearch.py index <directory>
    notesearch.py search <query>
    notesearch.py export <query> --format json --output results.json
"""

import argparse
import sys
from pathlib import Path
from typing import Optional, Iterator, List, Dict, Any
import os
import sqlite3
import re

__version__ = "1.0.0"

# Global database connection (shared between index and search commands)
_db_connection = None


def discover_markdown_files(
    directory: str,
    pattern: str = "*.md",
    recursive: bool = True
) -> Iterator[Path]:
    """
    Discover markdown files in a directory.

    Args:
        directory: Root directory to search
        pattern: Glob pattern for file matching (default: *.md)
        recursive: Whether to search subdirectories (default: True)

    Yields:
        Path objects for each discovered markdown file
    """
    root_path = Path(directory).resolve()

    if not root_path.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")

    if not root_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory}")

    # Use glob to find files
    if recursive:
        glob_pattern = f"**/{pattern}"
    else:
        glob_pattern = pattern

    try:
        for file_path in root_path.glob(glob_pattern):
            # Skip directories and symlinks to directories
            if not file_path.is_file():
                continue

            # Skip if not a regular file (handles special files, sockets, etc.)
            if not file_path.is_file():
                continue

            # Check file is readable
            if not os.access(file_path, os.R_OK):
                print(f"Warning: Skipping unreadable file: {file_path}", file=sys.stderr)
                continue

            yield file_path

    except PermissionError as e:
        print(f"Warning: Permission denied accessing {directory}: {e}", file=sys.stderr)
        raise
    except Exception as e:
        print(f"Error scanning directory {directory}: {e}", file=sys.stderr)
        raise


def init_db() -> sqlite3.Connection:
    """
    Initialize an in-memory SQLite database with FTS5 full-text search.

    Creates tables for:
    - notes: Main note storage
    - tags: Tag indexing
    - note_tags: Many-to-many relationship between notes and tags
    - notes_fts: Full-text search virtual table

    Returns:
        SQLite connection object
    """
    conn = sqlite3.connect(":memory:")

    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON")

    # Create main notes table
    conn.execute("""
        CREATE TABLE notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT UNIQUE NOT NULL,
            title TEXT,
            content TEXT NOT NULL,
            created_date TEXT,
            modified_date TEXT,
            file_created_date TEXT,
            file_modified_date TEXT,
            indexed_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # Create tags table
    conn.execute("""
        CREATE TABLE tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            name_normalized TEXT UNIQUE NOT NULL
        )
    """)

    # Create many-to-many relationship table
    conn.execute("""
        CREATE TABLE note_tags (
            note_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            PRIMARY KEY (note_id, tag_id),
            FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
        )
    """)

    # Create FTS5 virtual table for full-text search
    conn.execute("""
        CREATE VIRTUAL TABLE notes_fts USING fts5(
            title,
            content,
            file_path,
            content=notes,
            content_rowid=id
        )
    """)

    # Create triggers to keep FTS index in sync
    conn.execute("""
        CREATE TRIGGER notes_ai AFTER INSERT ON notes BEGIN
            INSERT INTO notes_fts(rowid, title, content, file_path)
            VALUES (new.id, new.title, new.content, new.file_path);
        END
    """)

    conn.execute("""
        CREATE TRIGGER notes_ad AFTER DELETE ON notes BEGIN
            DELETE FROM notes_fts WHERE rowid = old.id;
        END
    """)

    conn.execute("""
        CREATE TRIGGER notes_au AFTER UPDATE ON notes BEGIN
            DELETE FROM notes_fts WHERE rowid = old.id;
            INSERT INTO notes_fts(rowid, title, content, file_path)
            VALUES (new.id, new.title, new.content, new.file_path);
        END
    """)

    # Create indexes for faster lookups
    conn.execute("CREATE INDEX idx_notes_file_path ON notes(file_path)")
    conn.execute("CREATE INDEX idx_notes_created_date ON notes(created_date)")
    conn.execute("CREATE INDEX idx_tags_normalized ON tags(name_normalized)")
    conn.execute("CREATE INDEX idx_note_tags_note_id ON note_tags(note_id)")
    conn.execute("CREATE INDEX idx_note_tags_tag_id ON note_tags(tag_id)")

    return conn


def parse_markdown_metadata(file_path: Path) -> Dict[str, Any]:
    """
    Extract metadata and content from a markdown file.

    Extracts:
    - YAML frontmatter (title, date, tags)
    - First heading as title if no title in frontmatter
    - Inline hashtags from content
    - File creation and modification dates

    Args:
        file_path: Path to the markdown file

    Returns:
        Dictionary with metadata:
        - title: Note title
        - content: Full content
        - tags: List of tags (from frontmatter or hashtags)
        - created_date: ISO date string or None
        - file_created_date: File creation time
        - file_modified_date: File modification time
    """
    metadata = {
        "title": None,
        "content": "",
        "tags": [],
        "created_date": None,
        "file_created_date": None,
        "file_modified_date": None,
    }

    # Get file stats
    try:
        stat = file_path.stat()
        metadata["file_created_date"] = stat.st_ctime
        metadata["file_modified_date"] = stat.st_mtime
    except Exception:
        pass

    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            content = file_path.read_text(encoding="latin-1")
        except Exception as e:
            print(f"Warning: Could not read {file_path}: {e}", file=sys.stderr)
            return metadata
    except Exception as e:
        print(f"Warning: Could not read {file_path}: {e}", file=sys.stderr)
        return metadata

    metadata["content"] = content
    lines = content.split("\n")

    # Check for YAML frontmatter
    if lines and lines[0].strip() == "---":
        frontmatter_lines = []
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == "---":
                # End of frontmatter
                frontmatter = "\n".join(frontmatter_lines)
                parse_yaml_frontmatter(frontmatter, metadata)
                break
            frontmatter_lines.append(line)

    # Extract first heading if no title found
    if not metadata["title"]:
        for line in lines:
            line = line.strip()
            if line.startswith("#"):
                # Remove # and whitespace
                title = re.sub(r"^#+\s+", "", line)
                metadata["title"] = title
                break

    # Extract inline hashtags
    if content:
        hashtags = re.findall(r"#(\w[\w-]*)", content)
        # Filter out common markdown uses
        for tag in hashtags:
            if tag.lower() not in metadata["tags"]:
                metadata["tags"].append(tag.lower())

    # Extract title from filename if still no title
    if not metadata["title"]:
        metadata["title"] = file_path.stem.replace("-", " ").replace("_", " ").title()

    return metadata


def parse_yaml_frontmatter(yaml_text: str, metadata: Dict[str, Any]) -> None:
    """
    Parse YAML frontmatter and update metadata dict.

    Handles:
    - title: "My Title"
    - date: 2024-01-15
    - tags: [tag1, tag2, tag3]
    - tags: tag1, tag2

    Args:
        yaml_text: YAML content (without --- markers)
        metadata: Dictionary to update with extracted values
    """
    lines = yaml_text.strip().split("\n")

    for line in lines:
        # Skip empty lines and comments
        if not line.strip() or line.strip().startswith("#"):
            continue

        # Parse key: value pairs
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip().lower()
            value = value.strip()

            if key == "title" and value:
                metadata["title"] = value
            elif key == "date" and value:
                parsed_date = parse_date(value)
                if parsed_date:
                    metadata["created_date"] = parsed_date
            elif key == "tags":
                # Parse tags as list or comma-separated
                if value.startswith("["):
                    # List format: [tag1, tag2]
                    tags = re.findall(r'[\w-]+', value)
                    metadata["tags"].extend([t.lower() for t in tags if t])
                elif value:
                    # Comma-separated: tag1, tag2
                    tags = [t.strip().lower() for t in value.split(",")]
                    metadata["tags"].extend([t for t in tags if t])


def parse_date(date_str: str) -> Optional[str]:
    """
    Parse various date formats and return ISO 8601 string.

    Handles:
    - ISO 8601: 2024-01-15, 2024-01-15T10:30:00
    - Common formats: 15/01/2024, 01/15/2024, Jan 15, 2024

    Args:
        date_str: Date string to parse

    Returns:
        ISO 8601 date string (YYYY-MM-DD) or None
    """
    date_str = date_str.strip()

    # Try ISO 8601 format
    iso_pattern = r"^(\d{4})-(\d{1,2})-(\d{1,2})"
    match = re.match(iso_pattern, date_str)
    if match:
        year, month, day = match.groups()
        try:
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        except ValueError:
            pass

    # Try common formats with datetime
    from datetime import datetime

    # List of formats to try
    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%Y/%m/%d",
        "%d %b %Y",
        "%b %d, %Y",
        "%d %B %Y",
        "%B %d, %Y",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.split()[0], fmt)
            return dt.strftime("%Y-%m-%d")
        except (ValueError, IndexError):
            continue

    return None


def extract_clean_content(markdown_content: str) -> str:
    """
    Extract clean text content from markdown for full-text search indexing.

    Removes:
    - Code blocks (preserves code separately)
    - Markdown syntax characters (#, *, -, etc.)
    - URLs
    - Excessive whitespace

    Preserves:
    - Text content
    - Word separation
    - Basic structure

    Args:
        markdown_content: Raw markdown content

    Returns:
        Cleaned text suitable for FTS indexing
    """
    lines = markdown_content.split("\n")
    clean_lines = []
    in_code_block = False
    code_fence = None

    for line in lines:
        # Track code blocks
        if line.strip().startswith("```"):
            if not in_code_block:
                in_code_block = True
                code_fence = line.strip()
            else:
                in_code_block = False
                code_fence = None
            continue

        if in_code_block:
            # Skip code block content (or index separately if needed)
            continue

        # Remove markdown syntax
        line = re.sub(r"^#+\s+", "", line)  # Headings
        line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)  # Bold
        line = re.sub(r"\*(.+?)\*", r"\1", line)  # Italic
        line = re.sub(r"__(.+?)__", r"\1", line)  # Bold
        line = re.sub(r"_(.+?)_", r"\1", line)  # Italic
        line = re.sub(r"`(.+?)`", r"\1", line)  # Inline code
        line = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", line)  # Links
        line = re.sub(r"!\[.*?\]\(.+?\)", "", line)  # Images
        line = re.sub(r"^\s*[-*+]\s+", "", line)  # List items
        line = re.sub(r"^\s*\d+\.\s+", "", line)  # Numbered lists
        line = re.sub(r"^\s*>\s+", "", line)  # Blockquotes
        line = re.sub(r"\|", " ", line)  # Table separators

        # Remove URLs
        line = re.sub(r"https?://\S+", "", line)

        # Clean up whitespace
        line = line.strip()
        if line:
            clean_lines.append(line)

    return "\n".join(clean_lines)


def cmd_index(args):
    """Index markdown files from a directory"""
    import time

    print(f"Indexing markdown files in: {args.directory}")
    start_time = time.time()

    try:
        # Initialize database
        conn = init_db()
        cursor = conn.cursor()

        # Discover files
        file_list = list(discover_markdown_files(
            args.directory,
            pattern=args.pattern,
            recursive=args.recursive
        ))

        total_files = len(file_list)
        print(f"Found {total_files} markdown file(s)")

        if total_files == 0:
            print("No files to index")
            return

        # Index files with progress tracking
        indexed_count = 0
        error_count = 0

        for i, file_path in enumerate(file_list, 1):
            try:
                # Extract metadata
                metadata = parse_markdown_metadata(file_path)

                # Clean content for FTS
                clean_content = extract_clean_content(metadata["content"])

                # Prepare file dates
                file_created = None
                file_modified = None
                if metadata["file_created_date"]:
                    from datetime import datetime
                    file_created = datetime.fromtimestamp(
                        metadata["file_created_date"]
                    ).isoformat()
                if metadata["file_modified_date"]:
                    from datetime import datetime
                    file_modified = datetime.fromtimestamp(
                        metadata["file_modified_date"]
                    ).isoformat()

                # Insert note
                cursor.execute("""
                    INSERT INTO notes (
                        file_path, title, content,
                        created_date, modified_date,
                        file_created_date, file_modified_date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(file_path),
                    metadata["title"],
                    clean_content,
                    metadata["created_date"],
                    None,  # modified_date
                    file_created,
                    file_modified
                ))

                note_id = cursor.lastrowid

                # Insert tags
                for tag in metadata["tags"]:
                    # Normalize tag (lowercase, alphanumeric)
                    tag_normalized = re.sub(r"[^\w]", "", tag.lower())

                    if not tag_normalized:
                        continue

                    # Insert tag if not exists
                    cursor.execute("""
                        INSERT OR IGNORE INTO tags (name, name_normalized)
                        VALUES (?, ?)
                    """, (tag, tag_normalized))

                    # Get tag ID
                    cursor.execute("""
                        SELECT id FROM tags WHERE name_normalized = ?
                    """, (tag_normalized,))
                    tag_row = cursor.fetchone()
                    if tag_row:
                        tag_id = tag_row[0]

                        # Link note to tag
                        cursor.execute("""
                            INSERT OR IGNORE INTO note_tags (note_id, tag_id)
                            VALUES (?, ?)
                        """, (note_id, tag_id))

                indexed_count += 1

                # Progress indicator
                if i % 10 == 0 or i == total_files:
                    print(f"  Progress: {i}/{total_files} files indexed")

            except Exception as e:
                error_count += 1
                print(f"Warning: Error indexing {file_path}: {e}", file=sys.stderr)

        # Commit and show statistics
        conn.commit()

        # Get statistics
        cursor.execute("SELECT COUNT(*) FROM notes")
        note_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tags")
        tag_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM note_tags")
        relation_count = cursor.fetchone()[0]

        elapsed = time.time() - start_time

        print(f"\nIndexing complete!")
        print(f"  Notes indexed: {note_count}")
        print(f"  Unique tags: {tag_count}")
        print(f"  Tag associations: {relation_count}")
        print(f"  Errors: {error_count}")
        print(f"  Time: {elapsed:.2f} seconds")

        # Store database connection globally for search commands
        global _db_connection
        _db_connection = conn

    except Exception as e:
        print(f"Error during indexing: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


def search_fts(
    conn: sqlite3.Connection,
    query: str,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Perform full-text search using FTS5.

    Args:
        conn: Database connection
        query: Search query (supports boolean operators, phrases)
        limit: Maximum number of results

    Returns:
        List of result dictionaries with note info and snippet
    """
    cursor = conn.cursor()

    # Build FTS5 query with ranking
    # FTS5 supports AND, OR, NOT operators natively
    try:
        cursor.execute("""
            SELECT
                n.id,
                n.file_path,
                n.title,
                n.content,
                n.created_date,
                n.file_modified_date,
                snippet(notes_fts, 2, '>>>', '<<<', ..., 64) as snippet,
                bm25(notes_fts) as rank
            FROM notes n
            JOIN notes_fts fts ON n.id = fts.rowid
            WHERE notes_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (query, limit))

        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "file_path": row[1],
                "title": row[2],
                "content": row[3],
                "created_date": row[4],
                "modified_date": row[5],
                "snippet": row[6],
                "rank": row[7],
            })

        return results

    except sqlite3.OperationalError as e:
        if "malformed MATCH" in str(e) or "syntax error" in str(e):
            print(f"Invalid query syntax: {query}", file=sys.stderr)
            print("Tip: Use quotes for phrases: \"exact phrase\"", file=sys.stderr)
            return []
        raise


def filter_by_tags(
    conn: sqlite3.Connection,
    note_ids: List[int],
    tags: List[str]
) -> List[int]:
    """
    Filter notes by tags (AND logic - all tags must be present).

    Args:
        conn: Database connection
        note_ids: List of note IDs to filter
        tags: List of tag names to filter by

    Returns:
        Filtered list of note IDs
    """
    if not tags:
        return note_ids

    cursor = conn.cursor()

    # Normalize tags for matching
    normalized_tags = [re.sub(r"[^\w]", "", tag.lower()) for tag in tags]

    # Build query for each tag
    for tag_normalized in normalized_tags:
        cursor.execute("""
            SELECT DISTINCT note_id
            FROM note_tags nt
            JOIN tags t ON nt.tag_id = t.id
            WHERE t.name_normalized = ?
        """, (tag_normalized,))

        matching_ids = [row[0] for row in cursor.fetchall()]
        note_ids = [nid for nid in note_ids if nid in matching_ids]

    return note_ids


def filter_by_date_range(
    conn: sqlite3.Connection,
    note_ids: List[int],
    after: Optional[str] = None,
    before: Optional[str] = None
) -> List[int]:
    """
    Filter notes by date range.

    Args:
        conn: Database connection
        note_ids: List of note IDs to filter
        after: ISO date string (YYYY-MM-DD) - exclude notes before this
        before: ISO date string (YYYY-MM-DD) - exclude notes after this

    Returns:
        Filtered list of note IDs
    """
    if not after and not before:
        return note_ids

    cursor = conn.cursor()

    # Build the filter query
    conditions = []
    params = []

    if after:
        conditions.append("COALESCE(created_date, file_created_date) >= ?")
        params.append(after)

    if before:
        conditions.append("COALESCE(created_date, file_created_date) <= ?")
        params.append(before)

    if conditions:
        where_clause = " AND ".join(conditions)

        # Get all note IDs that match date criteria
        cursor.execute(f"""
            SELECT id FROM notes
            WHERE id IN ({','.join(map(str, note_ids))})
            AND {where_clause}
        """, params)

        return [row[0] for row in cursor.fetchall()]

    return note_ids


def search(
    conn: sqlite3.Connection,
    query: str,
    tags: Optional[List[str]] = None,
    after: Optional[str] = None,
    before: Optional[str] = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Unified search function combining full-text, tag, and date filtering.

    Args:
        conn: Database connection
        query: Full-text search query
        tags: Optional list of tags to filter by
        after: Optional date filter (after this date)
        before: Optional date filter (before this date)
        limit: Maximum results

    Returns:
        List of search results
    """
    # Start with full-text search
    results = search_fts(conn, query, limit * 2)  # Get more, then filter

    if not results:
        return []

    # Extract note IDs
    note_ids = [r["id"] for r in results]

    # Apply tag filter
    if tags:
        note_ids = filter_by_tags(conn, note_ids, tags)

    # Apply date filter
    if after or before:
        note_ids = filter_by_date_range(conn, note_ids, after, before)

    # Filter results by matching IDs
    filtered_results = [r for r in results if r["id"] in note_ids]

    # Add tags to each result
    cursor = conn.cursor()
    for result in filtered_results:
        cursor.execute("""
            SELECT t.name
            FROM tags t
            JOIN note_tags nt ON t.id = nt.tag_id
            WHERE nt.note_id = ?
        """, (result["id"],))

        result["tags"] = [row[0] for row in cursor.fetchall()]

    # Limit results
    return filtered_results[:limit]


def cmd_search(args):
    """Search indexed notes"""
    global _db_connection

    if _db_connection is None:
        print("Error: No index found. Please run 'notesearch index' first.", file=sys.stderr)
        sys.exit(1)

    try:
        results = search(
            _db_connection,
            args.query,
            tags=args.tags,
            after=args.after,
            before=args.before,
            limit=args.limit
        )

        if not results:
            print(f"No results found for: {args.query}")
            return

        print(f"Found {len(results)} result(s) for: {args.query}\n")

        for i, result in enumerate(results, 1):
            # Title
            title = result["title"] or "Untitled"
            print(f"[{i}] {title}")

            # Tags
            if result.get("tags"):
                tags_str = " ".join(f"#{t}" for t in result["tags"])
                print(f"    Tags: {tags_str}")

            # File path
            print(f"    File: {result['file_path']}")

            # Date
            if result.get("created_date"):
                print(f"    Date: {result['created_date']}")

            # Snippet with highlights
            if result.get("snippet"):
                snippet = result["snippet"].replace(">>>", "\x1b[1;31m").replace("<<<", "\x1b[0m")
                print(f"    {snippet}")

            print()

    except Exception as e:
        print(f"Error during search: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


def cmd_export(args):
    """Export search results to JSON or HTML"""
    print(f"Exporting results for query: {args.query}")
    print(f"Format: {args.format}, Output: {args.output}")
    # TODO: Implement export
    print("Export not yet implemented")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        prog="notesearch",
        description="Portable note search utility for markdown files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s index ~/Documents/notes
  %(prog)s search "python tutorial"
  %(prog)s search "project" --tag work --after 2024-01-01
  %(prog)s export "meeting" --format html --output report.html
        """
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )

    subparsers = parser.add_subparsers(
        dest="command",
        title="Available commands",
        metavar="COMMAND"
    )

    # Index command
    parser_index = subparsers.add_parser(
        "index",
        help="Index markdown files from a directory",
        description="Scan a directory and build a full-text search index of all markdown files"
    )
    parser_index.add_argument(
        "directory",
        type=str,
        help="Directory containing markdown files to index"
    )
    parser_index.add_argument(
        "--recursive",
        action="store_true",
        default=True,
        help="Recursively scan subdirectories (default: True)"
    )
    parser_index.add_argument(
        "--pattern",
        type=str,
        default="*.md",
        help="File glob pattern to match (default: *.md)"
    )
    parser_index.set_defaults(func=cmd_index)

    # Search command
    parser_search = subparsers.add_parser(
        "search",
        help="Search indexed notes",
        description="Search the note index using full-text query"
    )
    parser_search.add_argument(
        "query",
        type=str,
        help="Search query (supports boolean operators, phrases)"
    )
    parser_search.add_argument(
        "--tag",
        action="append",
        dest="tags",
        help="Filter by tag (can be used multiple times)"
    )
    parser_search.add_argument(
        "--after",
        type=str,
        help="Only show notes after this date (YYYY-MM-DD)"
    )
    parser_search.add_argument(
        "--before",
        type=str,
        help="Only show notes before this date (YYYY-MM-DD)"
    )
    parser_search.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of results (default: 20)"
    )
    parser_search.add_argument(
        "--context",
        type=int,
        default=3,
        help="Number of context lines around matches (default: 3)"
    )
    parser_search.set_defaults(func=cmd_search)

    # Export command
    parser_export = subparsers.add_parser(
        "export",
        help="Export search results to file",
        description="Export search results to JSON or HTML format"
    )
    parser_export.add_argument(
        "query",
        type=str,
        help="Search query"
    )
    parser_export.add_argument(
        "--format",
        type=str,
        choices=["json", "html"],
        default="json",
        help="Export format (default: json)"
    )
    parser_export.add_argument(
        "-o", "--output",
        type=str,
        required=True,
        help="Output file path"
    )
    parser_export.add_argument(
        "--tag",
        action="append",
        dest="tags",
        help="Filter by tag"
    )
    parser_export.add_argument(
        "--after",
        type=str,
        help="Filter by date range (after)"
    )
    parser_export.add_argument(
        "--before",
        type=str,
        help="Filter by date range (before)"
    )
    parser_export.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum results to export (default: 100)"
    )
    parser_export.set_defaults(func=cmd_export)

    # Parse arguments
    args = parser.parse_args()

    # Show help if no command specified
    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute command
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
