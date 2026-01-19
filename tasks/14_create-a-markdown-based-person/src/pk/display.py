"""Display and formatting utilities for PK"""

from rich.console import Console
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from typing import List, Optional
from datetime import datetime

from .models import Note, SearchResult


class DisplayFormatter:
    """Format and display output using rich library"""

    def __init__(self):
        self.console = Console()

    def print_note(self, note: Note, show_metadata: bool = True) -> None:
        """Print a note with formatting"""
        # Title
        title_text = Text(note.title, style="bold cyan")
        self.console.print(title_text)
        self.console.print()

        # Metadata
        if show_metadata:
            metadata = []
            metadata.append(f"Created: {note.created.strftime('%Y-%m-%d %H:%M')}")
            metadata.append(f"Modified: {note.modified.strftime('%Y-%m-%d %H:%M')}")
            if note.tags:
                metadata.append(f"Tags: {', '.join(f'#{tag}' for tag in note.tags)}")
            if note.links:
                metadata.append(f"Links: {len(note.links)}")
            if note.backlinks:
                metadata.append(f"Backlinks: {len(note.backlinks)}")

            self.console.print(Text(" | ".join(metadata), style="dim"))
            self.console.print()

        # Content
        if note.content:
            md = Markdown(note.content)
            self.console.print(md)

    def print_note_list(self, notes: List[Note], show_tags: bool = False) -> None:
        """Print a list of notes"""
        if not notes:
            self.console.print("[dim]No notes found.[/dim]")
            return

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Title", style="cyan")
        table.add_column("Modified", style="dim")
        if show_tags:
            table.add_column("Tags", style="green")
        table.add_column("Links", style="blue")

        for note in notes:
            modified = note.modified.strftime("%Y-%m-%d")
            tags = ", ".join(f"#{tag}" for tag in note.tags[:3]) if note.tags else ""
            if show_tags and len(note.tags) > 3:
                tags += f" +{len(note.tags) - 3}"

            links = f"{len(note.links)}→ {len(note.backlinks)}←"

            if show_tags:
                table.add_row(note.title, modified, tags, links)
            else:
                table.add_row(note.title, modified, links)

        self.console.print(table)

    def print_search_results(self, results: List[SearchResult]) -> None:
        """Print search results"""
        if not results:
            self.console.print("[dim]No results found.[/dim]")
            return

        self.console.print(f"\n[bold]Found {len(results)} result(s)[/bold]\n")

        for i, result in enumerate(results, 1):
            # Score badge
            score_color = "green" if result.score > 8 else "yellow" if result.score > 4 else "dim"
            self.console.print(f"[{score_color}][{result.score:.1f}][/{score_color}] ", end="")

            # Title
            self.console.print(f"[bold cyan]{result.note.title}[/bold cyan]")

            # Metadata
            if result.matched_fields:
                fields = ", ".join(result.matched_fields)
                self.console.print(f"  [dim]Matched: {fields}[/dim]")

            # Snippet
            if result.snippet:
                self.console.print(f"  [dim]{result.snippet[:150]}[/dim]")

            # Tags
            if result.note.tags:
                tags_str = " ".join(f"#{tag}" for tag in result.note.tags[:5])
                self.console.print(f"  [green]{tags_str}[/green]")

            self.console.print()

    def print_tags(self, tags: dict, show_counts: bool = True) -> None:
        """Print all tags"""
        if not tags:
            self.console.print("[dim]No tags found.[/dim]")
            return

        table = Table(show_header=True, header_style="bold green")
        table.add_column("Tag", style="green")
        if show_counts:
            table.add_column("Count", style="dim")

        for tag, count in sorted(tags.items(), key=lambda x: x[1], reverse=True):
            if show_counts:
                table.add_row(f"#{tag}", str(count))
            else:
                table.add_row(f"#{tag}")

        self.console.print(table)

    def print_backlinks(self, note: Note, backlinks: List[Note]) -> None:
        """Print backlinks for a note"""
        self.console.print(f"\n[bold cyan]{note.title}[/bold cyan]\n")
        self.console.print(f"[dim]{len(backlinks)} notes link to this note[/dim]\n")

        if not backlinks:
            self.console.print("[dim]No backlinks found.[/dim]")
            return

        for i, bl in enumerate(backlinks, 1):
            self.console.print(f"{i}. [cyan]{bl.title}[/cyan]")
            if bl.tags:
                tags_str = " ".join(f"#{tag}" for tag in bl.tags[:3])
                self.console.print(f"   [green]{tags_str}[/green]")
            self.console.print()

    def print_link_report(
        self, broken_links: dict, orphans: List[Note]
    ) -> None:
        """Print link validation report"""
        has_issues = False

        if broken_links:
            has_issues = True
            self.console.print("\n[bold red]Broken Links[/bold red]\n")
            for source, targets in broken_links.items():
                targets_str = ", ".join(targets)
                self.console.print(f"[cyan]{source}[/cyan] → [red]{targets_str}[/red]")

        if orphans:
            has_issues = True
            self.console.print("\n[bold yellow]Orphan Notes[/bold yellow]")
            self.console.print("[dim](No other notes link to these)[/dim]\n")
            for orphan in orphans:
                self.console.print(f"• [cyan]{orphan.title}[/cyan]")

        if not has_issues:
            self.console.print("\n[green]✓ All links are valid and no orphan notes found![/green]")

    def print_error(self, message: str) -> None:
        """Print an error message"""
        self.console.print(f"[bold red]Error:[/bold red] {message}")

    def print_success(self, message: str) -> None:
        """Print a success message"""
        self.console.print(f"[bold green]✓[/bold green] {message}")

    def print_info(self, message: str) -> None:
        """Print an info message"""
        self.console.print(f"[dim]ℹ[/dim] {message}")

    def print_warning(self, message: str) -> None:
        """Print a warning message"""
        self.console.print(f"[bold yellow]Warning:[/bold yellow] {message}")
