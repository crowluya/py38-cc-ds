"""
CLI entry point for Claude Code Python MVP

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)
"""

import os
import shlex
import sys
from pathlib import Path
from typing import List, Optional

import click

from claude_code.cli.filegen import detect_file_type
from claude_code.cli.filegen import generate_validated
from claude_code.cli.filegen import safe_write_text
from claude_code.config.loader import load_settings
from claude_code.core.agent import Agent, AgentConfig
from claude_code.llm.factory import create_llm_client


# Version constant
VERSION = "0.1.0"


def _find_project_root() -> Optional[str]:
    """
    Find project root by looking for .env, .env.local, or .pycc directory.

    Searches upward from current directory until finding a project marker.

    Returns:
        Project root path as string, or None if not found
    """
    cwd = Path.cwd()

    # Search upward from current directory
    for path in [cwd] + list(cwd.parents):
        # Check for project markers
        if (path / ".env.local").exists():
            return str(path)
        if (path / ".env").exists():
            return str(path)
        if (path / ".pycc").exists():
            return str(path)
        if (path / "pyproject.toml").exists():
            return str(path)
        if (path / "setup.py").exists():
            return str(path)
        if (path / ".git").exists():
            return str(path)

    return None


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
        raise click.Abort()

    if json_output and json_stream_output:
        click.echo(
            "Error: Cannot specify both --json and --json-stream",
            err=True,
        )
        raise click.Abort()

    if print_mode:
        _handle_headless_mode(
            ctx,
            prompt,
            model,
            json_output=json_output,
            json_stream_output=json_stream_output,
        )
    else:
        _handle_interactive_mode(
            ctx,
            prompt,
            model,
        )


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


@cli.command(name="write-file")
@click.argument("path", required=True)
@click.argument("instruction", required=False, default="")
@click.option(
    "--type",
    "file_type",
    type=click.Choice(["python", "requirements", "json", "markdown", "yaml", "text"]),
    default=None,
    help="File type hint (defaults to auto-detect from filename)",
)
@click.option(
    "--overwrite/--no-overwrite",
    default=False,
    help="Overwrite existing file",
)
@click.option(
    "--max-attempts",
    type=int,
    default=3,
    show_default=True,
    help="Max regeneration attempts if validation fails",
)
@click.option(
    "-m",
    "--model",
    default=None,
    help="LLM model to use",
)
@click.pass_context
def write_file_cmd(
    ctx: click.Context,
    path: str,
    instruction: str,
    file_type: Optional[str],
    overwrite: bool,
    max_attempts: int,
    model: Optional[str],
) -> None:
    """
    Generate a single file with strict, machine-consumable output and write it to disk.

    This command is designed to avoid "prose" contamination for files like requirements.txt.
    """
    # Determine instruction source: argument or stdin
    user_instruction = instruction
    if (not user_instruction or not user_instruction.strip()) and not sys.stdin.isatty():
        try:
            user_instruction = sys.stdin.read()
        except Exception as e:
            click.echo(f"Error reading from stdin: {e}", err=True)
            raise click.Abort()

    if not user_instruction or not user_instruction.strip():
        click.echo("Error: instruction required (argument or stdin)", err=True)
        raise click.Abort()

    if max_attempts < 1:
        click.echo("Error: --max-attempts must be >= 1", err=True)
        raise click.Abort()

    # Load configuration
    try:
        project_root = ctx.obj.get("project_root") if ctx.obj else None
        if project_root is None:
            project_root = _find_project_root()
        settings = load_settings(project_root=project_root)

        if model:
            settings.llm.model = model
    except Exception as e:
        click.echo(f"Error loading configuration: {e}", err=True)
        raise click.Abort()

    # Create LLM client + agent
    try:
        llm_client = create_llm_client(settings)
        agent = Agent(
            AgentConfig(
                llm_client=llm_client,
                max_tokens=settings.llm.max_tokens,
                temperature=settings.llm.temperature,
                stream=False,
                project_root=project_root,
            )
        )
    except Exception as e:
        click.echo(f"Error initializing agent: {e}", err=True)
        raise click.Abort()

    # Generate validated content
    try:
        ft = detect_file_type(path, file_type)

        def _gen(prompt: str) -> str:
            return agent.process(prompt).content

        content, result = generate_validated(
            generate_fn=_gen,
            file_type=ft,
            target_path=path,
            instruction=user_instruction,
            max_attempts=max_attempts,
        )

        if not result.ok:
            click.echo(f"Error: could not generate valid content: {result.error}", err=True)
            raise click.Abort()

        safe_write_text(path, content, overwrite=overwrite)
        click.echo(path)
    except FileExistsError:
        click.echo(f"Error: file exists (use --overwrite): {path}", err=True)
        raise click.Abort()
    except click.Abort:
        raise
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


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
        SystemExit: On error
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
                sys.exit(1)
        else:
            # No input source available
            click.echo(
                "Error: No prompt provided. "
                "Provide PROMPT argument or pipe via stdin.",
                err=True,
            )
            sys.exit(1)

    if not user_input.strip():
        click.echo("Error: Empty prompt", err=True)
        sys.exit(1)

    # Load configuration
    try:
        # Use project_root from context, or auto-detect
        project_root = ctx.obj.get("project_root") if ctx.obj else None
        if project_root is None:
            project_root = _find_project_root()
        settings = load_settings(project_root=project_root)

        # Apply model override if provided
        if model:
            settings.llm.model = model

    except Exception as e:
        click.echo(f"Error loading configuration: {e}", err=True)
        sys.exit(1)

    # Create LLM client
    try:
        llm_client = create_llm_client(settings)
    except Exception as e:
        click.echo(f"Error creating LLM client: {e}", err=True)
        sys.exit(1)

    # Create agent
    try:
        agent_config = AgentConfig(
            llm_client=llm_client,
            max_tokens=settings.llm.max_tokens,
            temperature=settings.llm.temperature,
            stream=json_stream_output,  # Enable streaming for --json-stream
            project_root=project_root,  # T051: Enable auto-load of long-term memory
        )
        agent = Agent(agent_config)
    except Exception as e:
        click.echo(f"Error initializing agent: {e}", err=True)
        sys.exit(1)

    # Process prompt and print response
    try:
        # Parse input for @file, @dir/, !command references
        from claude_code.interaction.parser import Parser
        from claude_code.core.context import ContextManager

        parser = Parser()
        parsed = parser.parse(user_input)

        # Build enhanced prompt with context from references
        enhanced_input = user_input
        context_parts = []

        # Process file references
        if parsed.file_refs:
            ctx_mgr = ContextManager()
            for file_ref in parsed.file_refs:
                try:
                    file_context = ctx_mgr.load_file(
                        file_ref.path,
                        line_range=file_ref.line_range,
                    )
                    context_parts.append(file_context.format())
                except Exception as e:
                    click.echo(f"Warning: Could not load file {file_ref.path}: {e}", err=True)

        # Process directory references
        if parsed.directory_refs:
            ctx_mgr = ContextManager()
            for dir_ref in parsed.directory_refs:
                try:
                    dir_context = ctx_mgr.load_directory(dir_ref.path, recursive=dir_ref.recursive)
                    context_parts.append(dir_context.format())
                except Exception as e:
                    click.echo(f"Warning: Could not load directory {dir_ref.path}: {e}", err=True)

        # Process command references
        if parsed.command_refs:
            from claude_code.core.executor import CommandExecutor
            cmd_executor = CommandExecutor()
            for cmd_ref in parsed.command_refs:
                try:
                    cmd_result = cmd_executor.execute(cmd_ref.command)
                    output = cmd_result.combined_output()
                    context_parts.append(f"Command: {cmd_ref.command}\n{output}")
                except Exception as e:
                    click.echo(f"Warning: Command execution failed: {e}", err=True)

        # Prepend context to prompt if any references were found
        if context_parts:
            context_block = "--- Context ---\n" + "\n\n".join(context_parts) + "\n--- End Context ---\n\n"
            enhanced_input = context_block + parsed.prompt
        else:
            # No references found, use original input
            enhanced_input = user_input

        # Debug: show what's being sent to the agent (for testing)
        import os
        if os.environ.get("DEBUG_CLI"):
            click.echo(f"[DEBUG] Enhanced input:\n{enhanced_input[:500]}...", err=True)

        if json_stream_output:
            _handle_json_stream_output(agent, enhanced_input)
        elif json_output:
            _handle_json_output(agent, enhanced_input)
        else:
            # Regular text output
            turn = agent.process(enhanced_input)
            click.echo(turn.content)
    except Exception as e:
        # Format error as JSON if in JSON mode
        if json_output or json_stream_output:
            error_json = _format_error_json(str(e))
            click.echo(error_json)
        else:
            click.echo(f"Error processing prompt: {e}", err=True)
        sys.exit(1)


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
    agent.add_user_message(user_input)

    # Get streaming response
    messages = agent.get_formatted_messages()

    chunks = agent.llm_client.chat_completion_stream(
        messages=messages,
        max_tokens=agent.config.max_tokens,
        temperature=agent.config.temperature,
    )

    # Stream each chunk as JSON
    for chunk in chunks:
        # Handle both dict and object chunks
        if isinstance(chunk, dict):
            content = chunk.get("delta", "")
        elif hasattr(chunk, "content"):
            content = chunk.content
        else:
            continue

        if content:
            json_chunk = format_json_stream_chunk(content=content, done=False)
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


# ===== T012: Interactive Mode Implementation =====


def _handle_interactive_mode(
    ctx: click.Context,
    initial_prompt: str,
    model: Optional[str],
) -> None:
    """
    Handle interactive chat mode.

    Args:
        ctx: Click context
        initial_prompt: Optional initial prompt to send
        model: Optional model override

    Raises:
        SystemExit: On error
    """
    # Load configuration
    try:
        project_root = ctx.obj.get("project_root") if ctx.obj else None
        if project_root is None:
            project_root = _find_project_root()
        settings = load_settings(project_root=project_root)

        # Apply model override if provided
        if model:
            settings.llm.model = model

    except Exception as e:
        click.echo(f"Error loading configuration: {e}", err=True)
        sys.exit(1)

    # Create LLM client
    try:
        llm_client = create_llm_client(settings)
    except Exception as e:
        click.echo(f"Error creating LLM client: {e}", err=True)
        sys.exit(1)

    # Create agent
    try:
        agent_config = AgentConfig(
            llm_client=llm_client,
            max_tokens=settings.llm.max_tokens,
            temperature=settings.llm.temperature,
            stream=False,  # No streaming in interactive mode
            project_root=project_root,
        )
        agent = Agent(agent_config)
    except Exception as e:
        click.echo(f"Error initializing agent: {e}", err=True)
        sys.exit(1)

    # Show welcome message
    _print_welcome(settings)

    # Process initial prompt if provided
    if initial_prompt and initial_prompt.strip():
        _process_input(agent, initial_prompt.strip())

    # Main interactive loop
    try:
        while True:
            try:
                # Read user input
                user_input = _read_input()

                # Check for exit commands
                if not user_input or user_input.strip().lower() in ("exit", "quit", "q"):
                    click.echo("\nGoodbye!")
                    break

                # Skip empty input
                if not user_input.strip():
                    continue

                if user_input.strip().startswith("/"):
                    _handle_local_command(
                        agent=agent,
                        user_input=user_input.strip(),
                        project_root=project_root,
                    )
                    continue

                # Process input
                _process_input(agent, user_input.strip())

            except EOFError:
                click.echo("\nGoodbye!")
                break
            except KeyboardInterrupt:
                click.echo("\nUse 'exit' or 'quit' to exit, or Ctrl+D to end.")
                continue

    except Exception as e:
        click.echo(f"\nError: {e}", err=True)
        sys.exit(1)


def _print_welcome(settings) -> None:
    """
    Print welcome message for interactive mode.

    Args:
        settings: Loaded settings
    """
    from rich.console import Console
    from rich.text import Text

    console = Console()

    # Welcome banner
    welcome_text = Text()
    welcome_text.append("Claude Code Python MVP", style="bold cyan")
    welcome_text.append(f" v{VERSION}", style="dim cyan")
    console.print(welcome_text)

    # Show model info
    model_info = f"Model: {settings.llm.model}"
    console.print(Text(model_info, style="dim"))

    # Show help hint
    help_hint = "Type 'exit', 'quit', or 'q' to exit. Ctrl+D also works."
    console.print(Text(help_hint, style="dim"))
    console.print()


def _read_input() -> str:
    """
    Read user input from stdin.

    Returns:
        User input string

    Raises:
        EOFError: On EOF (Ctrl+D)
    """
    try:
        # Use prompt_toolkit for better input handling if available
        from prompt_toolkit import prompt
        from prompt_toolkit.formatted_text import FormattedText

        user_input = prompt(
            FormattedText([
                ("class:prompt", ">>> "),
            ]),
            style=cls.__dict__.get("style", None)
        )
        return user_input
    except Exception:
        # Fallback to built-in input
        try:
            return input(">>> ")
        except EOFError:
            raise


def _process_input(agent: Agent, user_input: str) -> None:
    """
    Process user input in interactive mode.

    Args:
        agent: Agent instance
        user_input: User's input string
    """
    from rich.console import Console
    from rich.markdown import Markdown
    from claude_code.interaction.parser import Parser
    from claude_code.core.context import ContextManager

    console = Console()

    # Parse input for @file, @dir/, !command references
    parser = Parser()
    parsed = parser.parse(user_input)

    # Build enhanced prompt with context from references
    enhanced_input = user_input
    context_parts = []

    # Process file references
    if parsed.file_refs:
        ctx_mgr = ContextManager()
        for file_ref in parsed.file_refs:
            try:
                file_context = ctx_mgr.load_file(
                    file_ref.path,
                    line_range=file_ref.line_range,
                )
                context_parts.append(file_context.format())
            except Exception as e:
                console.print(Text(f"[Warning] Could not load file {file_ref.path}: {e}", style="yellow"))

    # Process directory references
    if parsed.directory_refs:
        ctx_mgr = ContextManager()
        for dir_ref in parsed.directory_refs:
            try:
                dir_context = ctx_mgr.load_directory(dir_ref.path, recursive=dir_ref.recursive)
                context_parts.append(dir_context.format())
            except Exception as e:
                console.print(Text(f"[Warning] Could not load directory {dir_ref.path}: {e}", style="yellow"))

    # Process command references
    if parsed.command_refs:
        from claude_code.core.executor import CommandExecutor
        cmd_executor = CommandExecutor()
        for cmd_ref in parsed.command_refs:
            try:
                cmd_result = cmd_executor.execute(cmd_ref.command)
                output = cmd_result.combined_output()
                context_parts.append(f"Command: {cmd_ref.command}\n{output}")
            except Exception as e:
                console.print(Text(f"[Warning] Command execution failed: {e}", style="yellow"))

    # Prepend context to prompt if any references were found
    if context_parts:
        context_block = "--- Context ---\n" + "\n\n".join(context_parts) + "\n--- End Context ---\n\n"
        enhanced_input = context_block + parsed.prompt
    else:
        # No references found, use original input
        enhanced_input = user_input

    # Show thinking indicator
    with console.status("[bold yellow]Thinking...") as status:
        try:
            turn = agent.process(enhanced_input)
        except Exception as e:
            console.print(Text(f"Error: {e}", style="red"))
            return

    # Print response (use Markdown formatting)
    if turn.content:
        console.print(Markdown(turn.content))
    else:
        console.print(Text("(No response)", style="dim"))

    console.print()  # Blank line between turns


def _resolve_under_root(project_root: str, user_path: str) -> str:
    base = Path(project_root).resolve()
    p = Path(user_path)
    if not p.is_absolute():
        p = (base / p).resolve()
    else:
        p = p.resolve()
    try:
        p.relative_to(base)
    except Exception:
        raise ValueError(f"path escapes project_root: {user_path}")
    return str(p)


def _format_dir_listing(root: str, recursive: bool, max_entries: int) -> str:
    root_p = Path(root)
    if not root_p.exists():
        return f"Error: directory not found: {root}"
    if not root_p.is_dir():
        return f"Error: not a directory: {root}"

    items = []
    if recursive:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames.sort()
            filenames.sort()
            for dn in dirnames:
                items.append(str(Path(dirpath, dn)))
                if len(items) >= max_entries:
                    break
            if len(items) >= max_entries:
                break
            for fn in filenames:
                items.append(str(Path(dirpath, fn)))
                if len(items) >= max_entries:
                    break
            if len(items) >= max_entries:
                break
    else:
        for child in sorted(root_p.iterdir(), key=lambda x: x.name.lower()):
            items.append(str(child))
            if len(items) >= max_entries:
                break

    rel_items = []
    base = root_p
    for it in items:
        try:
            rel_items.append(str(Path(it).relative_to(base)))
        except Exception:
            rel_items.append(str(Path(it)))

    suffix = "\n... (truncated)" if len(items) >= max_entries else ""
    return "\n".join(rel_items) + suffix


def _handle_local_command(agent: Agent, user_input: str, project_root: str) -> None:
    from rich.console import Console
    from rich.text import Text
    from claude_code.cli.filegen import detect_file_type, generate_validated, safe_write_text

    console = Console()
    try:
        # Windows-friendly: preserve backslashes in paths (e.g. ..\README.md)
        parts = shlex.split(user_input, posix=False)
    except Exception as e:
        console.print(Text(f"Error parsing command: {e}", style="red"))
        return

    if not parts:
        return

    cmd = parts[0].lstrip("/").lower()
    args = parts[1:]

    if cmd in ("help", "?"):
        console.print(
            Text(
                "Local commands: /mkdir PATH | /read-file PATH | /read-dir PATH [--recursive/--no-recursive] [--max N] | /write-file PATH -- CONTENT | /gen-file PATH [--type T] [--overwrite] [--max-attempts N] -- INSTRUCTION",
                style="dim",
            )
        )
        return

    try:
        if cmd == "mkdir":
            if not args:
                raise ValueError("mkdir requires PATH")
            target = _resolve_under_root(project_root, args[0])
            Path(target).mkdir(parents=True, exist_ok=True)
            console.print(Text(f"OK: created {args[0]}", style="green"))
            return

        if cmd == "read-file":
            if not args:
                raise ValueError("read-file requires PATH")
            target = _resolve_under_root(project_root, args[0])
            p = Path(target)
            if not p.exists() or not p.is_file():
                raise ValueError(f"file not found: {args[0]}")
            content = p.read_text(encoding="utf-8")
            console.print(Text(content))
            return

        if cmd == "read-dir":
            if not args:
                raise ValueError("read-dir requires PATH")
            recursive = True
            max_entries = 200
            path_arg = None
            i = 0
            while i < len(args):
                a = args[i]
                if a == "--recursive":
                    recursive = True
                elif a == "--no-recursive":
                    recursive = False
                elif a == "--max":
                    i += 1
                    if i >= len(args):
                        raise ValueError("--max requires integer")
                    max_entries = int(args[i])
                else:
                    if path_arg is None:
                        path_arg = a
                    else:
                        raise ValueError(f"unexpected argument: {a}")
                i += 1
            if path_arg is None:
                raise ValueError("read-dir requires PATH")
            target = _resolve_under_root(project_root, path_arg)
            listing = _format_dir_listing(target, recursive=recursive, max_entries=max_entries)
            console.print(Text(listing))
            return

        if cmd == "write-file":
            if not args:
                raise ValueError("write-file requires PATH")
            if "--" not in args:
                raise ValueError("write-file requires -- CONTENT")
            sep = args.index("--")
            path_arg = args[0]
            content = " ".join(args[sep + 1 :])
            target = _resolve_under_root(project_root, path_arg)
            safe_write_text(target, content + "\n", overwrite=True)
            console.print(Text(f"OK: wrote {path_arg}", style="green"))
            return

        if cmd == "gen-file":
            if not args:
                raise ValueError("gen-file requires PATH")
            if "--" not in args:
                raise ValueError("gen-file requires -- INSTRUCTION")
            sep = args.index("--")
            pre = args[:sep]
            instruction = " ".join(args[sep + 1 :]).strip()
            if not instruction:
                raise ValueError("gen-file instruction is empty")

            path_arg = pre[0]
            file_type = None
            overwrite = False
            max_attempts = 3
            i = 1
            while i < len(pre):
                a = pre[i]
                if a == "--type":
                    i += 1
                    if i >= len(pre):
                        raise ValueError("--type requires value")
                    file_type = pre[i]
                elif a == "--overwrite":
                    overwrite = True
                elif a == "--max-attempts":
                    i += 1
                    if i >= len(pre):
                        raise ValueError("--max-attempts requires integer")
                    max_attempts = int(pre[i])
                else:
                    raise ValueError(f"unexpected argument: {a}")
                i += 1

            target = _resolve_under_root(project_root, path_arg)
            ft = detect_file_type(target, file_type)

            def _gen(prompt: str) -> str:
                return agent.process(prompt).content

            content, result = generate_validated(
                generate_fn=_gen,
                file_type=ft,
                target_path=target,
                instruction=instruction,
                max_attempts=max_attempts,
            )

            if not result.ok:
                raise ValueError(f"could not generate valid content: {result.error}")

            safe_write_text(target, content, overwrite=overwrite)
            console.print(Text(f"OK: generated {path_arg}", style="green"))
            return

        console.print(Text(f"Unknown local command: /{cmd} (try /help)", style="yellow"))
    except Exception as e:
        console.print(Text(f"Error: {e}", style="red"))


class _Styles:
    """Styles for prompt_toolkit."""
    style = """
    <style>
    prompt {
        font-weight: bold;
        text-color: cyan;
    }
    </style>
    """

cls = _Styles()


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
