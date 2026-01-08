"""
Terminal output wrapper using Rich

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)
"""

from io import StringIO
from typing import Any, List, Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.panel import Panel


class Output:
    """
    Terminal output wrapper using Rich.

    Provides:
    - Markdown rendering
    - Code block syntax highlighting
    - Panel display
    - Table display
    """

    def __init__(self, console: Optional[Console] = None):
        """
        Initialize Output wrapper.

        Args:
            console: Rich Console instance (for testing/injection)
        """
        self._console = console or Console()

    @property
    def console(self) -> Console:
        """Get the underlying Console instance."""
        return self._console

    def print_markdown(self, text: str) -> None:
        """
        Print Markdown formatted text.

        Args:
            text: Markdown text to render
        """
        markdown = Markdown(text)
        self._console.print(markdown)

    def print_code(self, code: str, language: str = "python") -> None:
        """
        Print code block with syntax highlighting.

        Args:
            code: Code to display
            language: Programming language for syntax highlighting
        """
        syntax = Syntax(code, language, theme="monokai", line_numbers=True)
        self._console.print(syntax)

    def print_panel(self, content: str, title: str = "", border_style: str = "blue") -> None:
        """
        Print content in a panel.

        Args:
            content: Panel content
            title: Optional panel title
            border_style: Border color/style
        """
        panel = Panel(content, title=title, border_style=border_style)
        self._console.print(panel)

    def print_table(self, data: List[List[str]], headers: List[str]) -> None:
        """
        Print data as a table.

        Args:
            data: Table data (list of rows)
            headers: Column headers
        """
        from rich.table import Table

        table = Table(show_header=True, header_style="bold magenta")
        for header in headers:
            table.add_column(header)

        for row in data:
            table.add_row(*row)

        self._console.print(table)

    def print_text(self, text: str) -> None:
        """
        Print plain text.

        Args:
            text: Text to print
        """
        self._console.print(text)

    def print_error(self, message: str) -> None:
        """
        Print error message.

        Args:
            message: Error message
        """
        self._console.print(f"[bold red]Error:[/bold red] {message}")

    def print_warning(self, message: str) -> None:
        """
        Print warning message.

        Args:
            message: Warning message
        """
        self._console.print(f"[bold yellow]Warning:[/bold yellow] {message}")

    def print_success(self, message: str) -> None:
        """
        Print success message.

        Args:
            message: Success message
        """
        self._console.print(f"[bold green]✓[/bold green] {message}")


# Default singleton (can be replaced for testing)
_default_output: Optional[Output] = None


def get_output() -> Output:
    """Get the default Output instance."""
    global _default_output
    if _default_output is None:
        _default_output = Output()
    return _default_output


def set_output(output: Output) -> None:
    """Set the default Output instance (for testing)."""
    global _default_output
    _default_output = output
