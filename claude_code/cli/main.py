"""
CLI entry point for Claude Code Python MVP

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)
"""

from typing import List

import click


# Version constant
VERSION = "0.1.0"


@click.group()
@click.version_option(version=VERSION, prog_name="claude-code")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """
    Claude Code Python MVP - AI-native development workflow engine.

    Target: Python 3.8.10 + Windows 7 + Internal Network (DeepSeek R1 70B)
    """
    # Context object for sharing state between commands
    ctx.ensure_object(dict)


@cli.command()
@click.argument("prompt", required=False, default="")
@click.option(
    "-p",
    "--print",
    "print_mode",
    is_flag=True,
    help="Print mode (non-interactive, headless)",
)
@click.option(
    "-m",
    "--model",
    default=None,
    help="LLM model to use",
)
@click.pass_context
def chat(ctx: click.Context, prompt: str, print_mode: bool, model: str) -> None:
    """
    Start interactive chat session.

    PROMPT: Optional initial prompt to send
    """
    if print_mode:
        click.echo("Headless print mode (not yet implemented)")
    else:
        click.echo("Interactive chat mode (not yet implemented)")

    if prompt:
        click.echo(f"Prompt: {prompt}")
    if model:
        click.echo(f"Model: {model}")


@cli.command()
@click.argument("prompt", required=False)
@click.option(
    "-o",
    "--output-format",
    type=click.Choice(["text", "json", "stream-json"]),
    default="text",
    help="Output format",
)
@click.pass_context
def print_cmd(ctx: click.Context, prompt: str, output_format: str) -> None:
    """
    Execute in headless mode (single prompt, output and exit).

    PROMPT: The prompt to execute
    """
    if not prompt:
        click.echo("Error: prompt required for print command", err=True)
        raise click.Abort()

    click.echo(f"Headless execution: {prompt}")
    click.echo(f"Output format: {output_format}")


# Alias for 'print' command (since 'print' is a Python keyword)
cli.add_command(print_cmd, name="print")


def main(args: List[str] = None) -> int:
    """
    Main CLI entry point.

    Args:
        args: Command line arguments (defaults to sys.argv[1:])

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    if args is None:
        import sys

        args = sys.argv[1:]

    # Click handles its own exit codes
    try:
        cli(args, standalone_mode=False)
        return 0
    except click.ClickException as e:
        e.show()
        return e.exit_code
    except click.Abort:
        return 130  # Standard exit code for SIGINT


if __name__ == "__main__":
    import sys

    sys.exit(main())
