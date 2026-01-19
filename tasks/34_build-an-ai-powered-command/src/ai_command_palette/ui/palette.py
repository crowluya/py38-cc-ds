"""Textual-based command palette UI."""

from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import (
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Static,
)

from ai_command_palette.core.registry import Command
from ai_command_palette.core.scorer import ScoredCommand
from ai_command_palette.storage.config import Config


class CommandPaletteApp(App):
    """Main command palette application."""

    CSS = """
    Screen {
        background: $primary;
    }

    #search-container {
        height: 3;
        padding: 1;
    }

    #results-container {
        height: 1fr;
    }

    #preview-container {
        height: 10;
        dock: bottom;
        padding: 1;
        background: $panel;
    }

    ListView {
        scrollbar-size: 1 0;
    }

    ListItem {
        padding: 0 1;
    }

    ListItem.--highlight {
        background: $secondary;
    }

    .command-name {
        text-style: bold;
    }

    .command-description {
        color: $text-muted;
        text-style: italic;
    }

    .score {
        color: $success;
        text-align: right;
    }
    """

    def __init__(self, config: Optional[Config] = None):
        """Initialize command palette app."""
        super().__init__()
        self.config = config or Config()
        self.current_query = ""
        self.scored_commands: list[ScoredCommand] = []
        self.selected_command: Optional[Command] = None

    def compose(self) -> ComposeResult:
        """Compose the UI."""
        yield Header()

        with Container(id="search-container"):
            yield Input(
                placeholder="Search commands, files, actions...",
                id="search-input",
            )

        with Container(id="results-container"):
            yield ListView(id="results-list")

        with Container(id="preview-container"):
            yield Static(id="preview-content")

        yield Footer()

    def on_mount(self) -> None:
        """Handle app mount."""
        # Focus on search input
        search_input = self.query_one("#search-input", Input)
        search_input.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        self.current_query = event.value
        self.update_results()

    def update_results(self):
        """Update results list based on current query."""
        results_list = self.query_one("#results-list", ListView)

        # Clear current results
        results_list.clear()

        # Get filtered and scored commands
        # This would call the recommendation engine
        # For now, we'll show placeholder results

        if not self.current_query:
            # Show recent/frequent commands when no query
            pass
        else:
            # Show filtered results
            pass

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle list item selection."""
        # Update preview
        self.update_preview()

    def update_preview(self):
        """Update preview panel."""
        preview_content = self.query_one("#preview-content", Static)

        if self.selected_command:
            preview_text = f"""
[b]{self.selected_command.name}[/b]

{self.selected_command.description or 'No description'}

Category: {self.selected_command.category or 'None'}
Type: {self.selected_command.command_type.value}

Command Template:
{self.selected_command.command_template}
"""
            preview_content.update(preview_text)
        else:
            preview_content.update("Select a command to see details")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission (Enter key)."""
        # Execute selected command
        if self.selected_command:
            self.execute_command(self.selected_command)

    def execute_command(self, command: Command):
        """Execute a command."""
        import subprocess

        # Format command (handle placeholders)
        cmd_str = command.command_template

        # Execute command
        try:
            result = subprocess.run(
                cmd_str,
                shell=True,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                self.exit(result=result.stdout)
            else:
                self.exit(result=result.stderr)
        except Exception as e:
            self.exit(result=str(e))


class MiniCommandPaletteApp(App):
    """Mini version of command palette for quick access."""

    CSS = """
    Screen {
        layout: vertical;
        padding: 1;
    }

    #search {
        height: 1;
    }

    #results {
        height: 10fr;
    }

    ListItem {
        padding: 0 1;
    }
    """

    def __init__(self, config: Optional[Config] = None):
        """Initialize mini palette."""
        super().__init__()
        self.config = config or Config()
        self.current_query = ""
        self.scored_commands: list[ScoredCommand] = []

    def compose(self) -> ComposeResult:
        """Compose mini UI."""
        yield Input(placeholder="Type a command...", id="search")
        yield ListView(id="results")

    def on_mount(self) -> None:
        """Handle mount."""
        self.query_one("#search", Input).focus()
