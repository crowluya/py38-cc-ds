"""
CLI entry point for Claude Code Python MVP

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)
"""

import sys
from typing import List, Optional

import click

from claude_code.config.loader import load_settings
from claude_code.core.agent import Agent, AgentConfig
from claude_code.llm.factory import create_llm_client


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
def chat(ctx: click.Context, prompt: str, print_mode: bool, model: Optional[str]) -> None:
    """
    Start interactive chat session.

    PROMPT: Optional initial prompt to send

    If -p/--print is specified, runs in headless mode:
    - Reads from PROMPT argument if provided
    - Falls back to stdin if PROMPT is empty
    - Prints response and exits
    """
    if print_mode:
        _handle_headless_mode(ctx, prompt, model)
    else:
        click.echo("Interactive chat mode (not yet implemented)")

    if prompt and not print_mode:
        click.echo(f"Prompt: {prompt}")
    if model and not print_mode:
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


# ===== T090: Headless Mode Implementation =====


def _handle_headless_mode(
    ctx: click.Context,
    prompt: str,
    model: Optional[str],
) -> None:
    """
    Handle headless mode execution.

    Args:
        ctx: Click context
        prompt: Prompt from command line argument (may be empty)
        model: Optional model override

    Raises:
        click.Exit: On error or completion
    """
    # Determine input source: prompt argument or stdin
    user_input = prompt

    if not user_input or not user_input.strip():
        # Try to read from stdin
        if not sys.stdin.isatty():
            # Read from stdin pipe
            try:
                user_input = sys.stdin.read()
            except Exception as e:
                click.echo(f"Error reading from stdin: {e}", err=True)
                raise click.Exit(1)
        else:
            # No input source available
            click.echo(
                "Error: No prompt provided. "
                "Provide PROMPT argument or pipe via stdin.",
                err=True,
            )
            raise click.Exit(1)

    if not user_input.strip():
        click.echo("Error: Empty prompt", err=True)
        raise click.Exit(1)

    # Load configuration
    try:
        project_root = ctx.obj.get("project_root") if ctx.obj else None
        settings = load_settings(project_root=project_root)

        # Apply model override if provided
        if model:
            settings.llm.model = model

    except Exception as e:
        click.echo(f"Error loading configuration: {e}", err=True)
        raise click.Exit(1)

    # Create LLM client
    try:
        llm_client = create_llm_client(settings)
    except Exception as e:
        click.echo(f"Error creating LLM client: {e}", err=True)
        raise click.Exit(1)

    # Create agent
    try:
        agent_config = AgentConfig(
            llm_client=llm_client,
            max_tokens=settings.llm.max_tokens,
            temperature=settings.llm.temperature,
            stream=False,  # No streaming in headless mode
        )
        agent = Agent(agent_config)
    except Exception as e:
        click.echo(f"Error initializing agent: {e}", err=True)
        raise click.Exit(1)

    # Process prompt and print response
    try:
        turn = agent.process(user_input)
        click.echo(turn.content)
    except Exception as e:
        click.echo(f"Error processing prompt: {e}", err=True)
        raise click.Exit(1)


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
