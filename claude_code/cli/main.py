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
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Output response as JSON (for programmatic integration)",
)
@click.option(
    "--json-stream",
    "json_stream_output",
    is_flag=True,
    help="Output response as streaming JSON (newline-delimited)",
)
@click.pass_context
def chat(
    ctx: click.Context,
    prompt: str,
    print_mode: bool,
    model: Optional[str],
    json_output: bool,
    json_stream_output: bool,
) -> None:
    """
    Start interactive chat session.

    PROMPT: Optional initial prompt to send

    If -p/--print is specified, runs in headless mode:
    - Reads from PROMPT argument if provided
    - Falls back to stdin if PROMPT is empty
    - Prints response and exits

    If --json is specified, outputs response as JSON (requires -p).
    If --json-stream is specified, outputs streaming JSON (requires -p).
    """
    # Validate JSON flag usage
    if (json_output or json_stream_output) and not print_mode:
        click.echo(
            "Error: --json and --json-stream require -p/--print mode",
            err=True,
        )
        raise click.Exit(1)

    if json_output and json_stream_output:
        click.echo(
            "Error: Cannot specify both --json and --json-stream",
            err=True,
        )
        raise click.Exit(1)

    if print_mode:
        _handle_headless_mode(
            ctx,
            prompt,
            model,
            json_output=json_output,
            json_stream_output=json_stream_output,
        )
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
@click.option(
    "-m",
    "--model",
    default=None,
    help="LLM model to use",
)
@click.pass_context
def print_cmd(
    ctx: click.Context,
    prompt: str,
    output_format: str,
    model: Optional[str],
) -> None:
    """
    Execute in headless mode (single prompt, output and exit).

    PROMPT: The prompt to execute

    Output formats:
    - text: Plain text output (default)
    - json: Single JSON object with response
    - stream-json: Streaming JSON (newline-delimited)
    """
    if not prompt:
        click.echo("Error: prompt required for print command", err=True)
        raise click.Abort()

    # Map output format to JSON flags
    json_output = output_format == "json"
    json_stream_output = output_format == "stream-json"

    # Delegate to headless mode handler
    _handle_headless_mode(
        ctx,
        prompt,
        model,
        json_output=json_output,
        json_stream_output=json_stream_output,
    )


# Alias for 'print' command (since 'print' is a Python keyword)
cli.add_command(print_cmd, name="print")


# ===== T090: Headless Mode Implementation =====


def _handle_headless_mode(
    ctx: click.Context,
    prompt: str,
    model: Optional[str],
    json_output: bool = False,
    json_stream_output: bool = False,
) -> None:
    """
    Handle headless mode execution.

    Args:
        ctx: Click context
        prompt: Prompt from command line argument (may be empty)
        model: Optional model override
        json_output: Output as JSON
        json_stream_output: Output as streaming JSON

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
            stream=json_stream_output,  # Enable streaming for --json-stream
        )
        agent = Agent(agent_config)
    except Exception as e:
        click.echo(f"Error initializing agent: {e}", err=True)
        raise click.Exit(1)

    # Process prompt and print response
    try:
        if json_stream_output:
            _handle_json_stream_output(agent, user_input)
        elif json_output:
            _handle_json_output(agent, user_input)
        else:
            # Regular text output
            turn = agent.process(user_input)
            click.echo(turn.content)
    except Exception as e:
        # Format error as JSON if in JSON mode
        if json_output or json_stream_output:
            error_json = _format_error_json(str(e))
            click.echo(error_json)
        else:
            click.echo(f"Error processing prompt: {e}", err=True)
        raise click.Exit(1)


# ===== T091: JSON Output Helpers =====


def _handle_json_output(agent: Agent, user_input: str) -> None:
    """
    Handle non-streaming JSON output.

    Args:
        agent: Agent instance
        user_input: User prompt
    """
    from claude_code.cli.output import format_json_output, format_tool_calls_for_json

    turn = agent.process(user_input)

    # Format tool calls for JSON
    tool_calls_json = format_tool_calls_for_json(turn.tool_calls)

    # Output as JSON
    json_output = format_json_output(
        content=turn.content,
        finish_reason=turn.finish_reason,
        tool_calls=tool_calls_json,
    )
    click.echo(json_output)


def _handle_json_stream_output(agent: Agent, user_input: str) -> None:
    """
    Handle streaming JSON output.

    Args:
        agent: Agent instance (configured for streaming)
        user_input: User prompt
    """
    from claude_code.cli.output import format_json_stream_chunk, format_tool_calls_for_json

    # Add user message
    agent._add_user_message(user_input)

    # Get streaming response
    messages = agent._format_messages_for_llm()

    chunks = agent._config.llm_client.chat_completion_stream(
        messages=messages,
        max_tokens=agent._config.max_tokens,
        temperature=agent._config.temperature,
    )

    # Stream each chunk as JSON
    for chunk in chunks:
        if hasattr(chunk, "content"):
            json_chunk = format_json_stream_chunk(content=chunk.content, done=False)
            click.echo(json_chunk)

    # Send final chunk with done=True
    final_chunk = format_json_stream_chunk(
        done=True,
        finish_reason="stop",
        tool_calls=None,
    )
    click.echo(final_chunk)


def _format_error_json(error_message: str) -> str:
    """
    Format error as JSON.

    Args:
        error_message: Error message

    Returns:
        JSON string with error field
    """
    import json

    error_dict = {
        "error": error_message,
        "content": "",
        "finish_reason": "error",
        "tool_calls": None,
        "timestamp": None,
    }
    return json.dumps(error_dict, ensure_ascii=False)


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
