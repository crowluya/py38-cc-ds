"""Command-line interface for PK"""

import click
import subprocess
import sys
from pathlib import Path
from typing import Optional

from .config import Config
from .storage import Storage
from .search import SearchEngine
from .display import DisplayFormatter


@click.group()
@click.version_option(version="0.1.0")
@click.pass_context
def main(ctx):
    """PK - Personal Knowledge Management System

    A Markdown-based note-taking system with tagging, bidirectional linking,
    and full-text search capabilities.
    """
    ctx.ensure_object(dict)
    ctx.obj['config'] = Config.load()
    ctx.obj['storage'] = Storage(ctx.obj['config'])
    ctx.obj['display'] = DisplayFormatter()

    # Build index on startup
    ctx.obj['storage'].build_index()


@main.command()
@click.argument('title')
@click.option('--tag', '-t', multiple=True, help='Tags to add to the note')
@click.option('--content', '-c', help='Initial content for the note')
@click.pass_context
def new(ctx, title: str, tag: tuple, content: Optional[str]):
    """Create a new note

    Example:
        pk new "My Note" --tag python --tag tutorial
    """
    storage = ctx.obj['storage']
    display = ctx.obj['display']

    # Validate title
    if not title.strip():
        display.print_error("Title cannot be empty")
        sys.exit(1)

    # Check if note already exists
    existing = storage.get_note_by_title(title)
    if existing:
        display.print_error(f"Note '{title}' already exists")
        sys.exit(1)

    # Create note
    tags = list(tag) if tag else []
    if content is None:
        content = ""

    try:
        note = storage.create_note(title, content, tags)
        display.print_success(f"Created note: {note.title}")
        display.print_info(f"File: {note.file_path}")
    except FileExistsError as e:
        display.print_error(str(e))
        sys.exit(1)


@main.command()
@click.argument('title')
@click.pass_context
def edit(ctx, title: str):
    """Edit a note in your default editor

    Example:
        pk edit "My Note"
    """
    storage = ctx.obj['storage']
    config = ctx.obj['config']
    display = ctx.obj['display']

    # Find note
    note = storage.get_note_by_title(title)
    if not note:
        display.print_error(f"Note '{title}' not found")
        sys.exit(1)

    # Open in editor
    editor = config.default_editor
    try:
        subprocess.call([editor, str(note.file_path)])
        display.print_success(f"Edited: {note.title}")

        # Rebuild index to capture changes
        storage.build_index()
    except Exception as e:
        display.print_error(f"Failed to open editor: {e}")
        sys.exit(1)


@main.command()
@click.argument('title')
@click.pass_context
def show(ctx, title: str):
    """Display a note

    Example:
        pk show "My Note"
    """
    storage = ctx.obj['storage']
    display = ctx.obj['display']

    note = storage.get_note_by_title(title)
    if not note:
        display.print_error(f"Note '{title}' not found")
        sys.exit(1)

    # Refresh backlinks from current index
    note.backlinks = [bl.title for bl in storage.get_backlinks(title)]

    display.print_note(note)


@main.command()
@click.option('--tag', '-t', multiple=True, help='Filter by tags')
@click.option('--limit', '-l', default=20, help='Limit number of results')
@click.pass_context
def list(ctx, tag: tuple, limit: int):
    """List all notes

    Example:
        pk list --tag python
    """
    storage = ctx.obj['storage']
    display = ctx.obj['display']

    notes = list(storage.index.notes_by_title.values())

    # Filter by tags if specified
    if tag:
        filtered = []
        for note in notes:
            if all(t.lower() in [nt.lower() for nt in note.tags] for t in tag):
                filtered.append(note)
        notes = filtered

    # Sort by modified date (newest first)
    notes.sort(key=lambda n: n.modified, reverse=True)

    # Apply limit
    notes = notes[:limit]

    display.print_note_list(notes, show_tags=bool(tag))


@main.command()
@click.argument('title')
@click.option('--force', '-f', is_flag=True, help='Skip confirmation')
@click.pass_context
def delete(ctx, title: str, force: bool):
    """Delete a note

    Example:
        pk delete "My Note"
    """
    storage = ctx.obj['storage']
    display = ctx.obj['display']

    note = storage.get_note_by_title(title)
    if not note:
        display.print_error(f"Note '{title}' not found")
        sys.exit(1)

    # Check for backlinks
    backlinks = storage.get_backlinks(title)
    if backlinks and not force:
        display.print_warning(f"{len(backlinks)} note(s) link to this note:")
        for bl in backlinks:
            display.print_info(f"  - {bl.title}")
        display.print_warning("Deleting this note will create broken links!")

    # Confirm deletion
    if not force:
        click.confirm(f"Are you sure you want to delete '{title}'?", abort=True)

    storage.delete_note(note)
    display.print_success(f"Deleted: {title}")


@main.command()
@click.argument('query')
@click.option('--limit', '-l', default=20, help='Limit number of results')
@click.pass_context
def search(ctx, query: str, limit: int):
    """Search notes by content, title, or tags

    Example:
        pk search "python tutorial"
    """
    storage = ctx.obj['storage']
    display = ctx.obj['display']

    search_engine = SearchEngine(list(storage.index.notes_by_title.values()))
    results = search_engine.search(query, limit=limit)

    display.print_search_results(results)


@main.command()
@click.pass_context
def tags(ctx):
    """List all tags

    Example:
        pk tags
    """
    storage = ctx.obj['storage']
    display = ctx.obj['display']

    tags_dict = {}
    for tag, note_titles in storage.index.notes_by_tag.items():
        tags_dict[tag] = len(note_titles)

    display.print_tags(tags_dict)


@main.command()
@click.argument('tag')
@click.pass_context
def tag(ctx, tag: str):
    """Show all notes with a specific tag

    Example:
        pk tag python
    """
    storage = ctx.obj['storage']
    display = ctx.obj['display']

    notes = storage.get_notes_by_tag(tag)
    if not notes:
        display.print_info(f"No notes found with tag '#{tag}'")
        return

    display.print_note_list(notes, show_tags=True)


@main.command()
@click.argument('title')
@click.pass_context
def backlinks(ctx, title: str):
    """Show notes that link to this note

    Example:
        pk backlinks "My Note"
    """
    storage = ctx.obj['storage']
    display = ctx.obj['display']

    note = storage.get_note_by_title(title)
    if not note:
        display.print_error(f"Note '{title}' not found")
        sys.exit(1)

    backlinks = storage.get_backlinks(title)
    display.print_backlinks(note, backlinks)


@main.command()
@click.pass_context
def check_links(ctx):
    """Check for broken links and orphan notes

    Example:
        pk check-links
    """
    storage = ctx.obj['storage']
    display = ctx.obj['display']

    broken_links = storage.find_broken_links()
    orphans = storage.find_orphan_notes()

    display.print_link_report(broken_links, orphans)


@main.command()
@click.pass_context
def init(ctx):
    """Initialize PK configuration

    Example:
        pk init
    """
    config = ctx.obj['config']
    display = ctx.obj['display']

    # Create config
    config.save()
    display.print_success(f"Configuration saved to {config.default_config_path()}")

    # Create notes directory
    notes_dir = config.ensure_notes_directory()
    display.print_success(f"Notes directory: {notes_dir}")


@main.command()
@click.pass_context
def info(ctx):
    """Show PK configuration and statistics

    Example:
        pk info
    """
    config = ctx.obj['config']
    storage = ctx.obj['storage']
    display = ctx.obj['display']

    # Rebuild index for accurate stats
    storage.build_index()

    # Stats
    num_notes = len(storage.index.notes_by_title)
    num_tags = len(storage.index.notes_by_tag)
    num_links = len(storage.index.links)

    display.console.print("\n[bold cyan]PK - Personal Knowledge Management[/bold cyan]\n")

    display.console.print(f"[dim]Configuration[/dim]")
    display.console.print(f"  Notes directory: {config.notes_directory}")
    display.console.print(f"  Default editor: {config.default_editor}")
    display.console.print()

    display.console.print(f"[dim]Statistics[/dim]")
    display.console.print(f"  Total notes: {num_notes}")
    display.console.print(f"  Total tags: {num_tags}")
    display.console.print(f"  Total links: {num_links}")
    display.console.print()


if __name__ == '__main__':
    main()
