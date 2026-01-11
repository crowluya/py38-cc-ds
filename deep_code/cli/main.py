"""
CLI entry point for DeepCode

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)
"""

import os
import shlex
import shutil
import sys
import time
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import List, Optional, Callable

import click
import colorama

# Rich imports - consolidated at top level
from rich.console import Console
from rich.columns import Columns
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from deep_code.cli.filegen import detect_file_type
from deep_code.cli.filegen import generate_validated
from deep_code.cli.filegen import safe_write_text
from deep_code.cli.approval import get_approval
from deep_code.cli.utils import (
    get_terminal_width as _get_terminal_width,
    coerce_log_level as _coerce_log_level,
    init_file_logging as _init_file_logging,
    find_project_root as _find_project_root,
    resolve_under_root as _resolve_under_root,
    format_dir_listing as _format_dir_listing,
    truncate_lines as _truncate_lines,
    extract_first_json_object as _extract_first_json_object,
)
from deep_code.cli.models import ToolBlock as _ToolBlock
from deep_code.cli.local_commands import handle_local_command as _handle_local_command
from deep_code.config.loader import load_settings
from deep_code.core.agent import Agent, AgentConfig
from deep_code.llm.factory import create_llm_client
from deep_code.cli.mcp_commands import mcp_group

# Initialize colorama for Windows 7 ANSI support
colorama.init()


# Version constant
VERSION = "0.1.0"


_LOGGER = logging.getLogger("pycc")


def _check_permission(
    domain,
    target: str,
    ask_message: str,
    mode: str,
    auto_approve: bool,
    permission_manager,
    approval_callback: Optional[Callable[[str], bool]] = None,
) -> bool:
    """
    Check permission for an action.

    Args:
        domain: PermissionDomain enum value
        target: Target path or command
        ask_message: Message to show when asking user
        mode: Current mode (default/plan/bypass)
        auto_approve: Whether to auto-approve all actions
        permission_manager: PermissionManager instance or None
        approval_callback: Optional callback for approval (used in UI context)

    Returns:
        True if permission granted, False otherwise
    """
    from deep_code.security.permissions import PermissionStatus

    approval = get_approval()
    mode_norm = (mode or "default").strip().lower()

    # Bypass mode or auto-approve: always allow
    if mode_norm == "bypass" or auto_approve:
        try:
            _LOGGER.info(
                "perm_check mode=%s domain=%s target=%s decision=ALLOW reason=%s",
                mode_norm,
                getattr(domain, "value", str(domain)),
                target,
                "bypass" if mode_norm == "bypass" else "auto_approve",
            )
        except Exception:
            pass
        return True

    # No permission manager: ask user
    if permission_manager is None:
        try:
            _LOGGER.info(
                "perm_check mode=%s domain=%s target=%s decision=ASK reason=no_permission_manager",
                mode_norm,
                getattr(domain, "value", str(domain)),
                target,
            )
        except Exception:
            pass
        try:
            if approval_callback is not None:
                ok = bool(approval_callback(ask_message))
            else:
                ok = bool(approval.confirm(ask_message, default=False))
            _LOGGER.info(
                "perm_check mode=%s domain=%s target=%s decision=%s reason=user_response",
                mode_norm,
                getattr(domain, "value", str(domain)),
                target,
                "ALLOW" if ok else "DENY",
            )
            return ok
        except Exception:
            return False

    # Check with permission manager
    try:
        res = permission_manager.check_permission(domain, target)
    except Exception:
        return approval.confirm(ask_message, default=False)

    try:
        rule = getattr(res, "matching_rule", None)
        _LOGGER.info(
            "perm_check mode=%s domain=%s target=%s status=%s action=%s rule=%s",
            mode_norm,
            getattr(domain, "value", str(domain)),
            target,
            getattr(getattr(res, "status", None), "value", str(getattr(res, "status", None))),
            getattr(getattr(res, "action", None), "value", str(getattr(res, "action", None))),
            getattr(rule, "pattern", None),
        )
    except Exception:
        pass

    if res.status == PermissionStatus.GRANTED:
        return True
    if res.status == PermissionStatus.DENIED:
        return False

    # PENDING status: ask user
    try:
        _LOGGER.info(
            "perm_check mode=%s domain=%s target=%s decision=ASK prompt=%s",
            mode_norm,
            getattr(domain, "value", str(domain)),
            target,
            ask_message,
        )
    except Exception:
        pass

    try:
        if approval_callback is not None:
            ok = bool(approval_callback(ask_message))
        else:
            ok = bool(approval.confirm(ask_message, default=False))
    except Exception:
        ok = False

    try:
        _LOGGER.info(
            "perm_check mode=%s domain=%s target=%s decision=%s reason=ask_user",
            mode_norm,
            getattr(domain, "value", str(domain)),
            target,
            "ALLOW" if ok else "DENY",
        )
    except Exception:
        pass
    return ok


@click.group()
@click.version_option(version=VERSION, prog_name="claude-code")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """
    DeepCode - AI-native development workflow engine.

    Target: Python 3.8.10 + Windows 7 + Internal Network (DeepSeek R1 70B)
    """
    # Context object for sharing state between commands
    ctx.ensure_object(dict)


# Register MCP command group (MCP-016, MCP-017, MCP-018)
cli.add_command(mcp_group)


@cli.command(name="print")
@click.argument("prompt", required=False, default="")
@click.option(
    "-m",
    "--model",
    default=None,
    help="LLM model to use",
)
@click.option(
    "-o",
    "--output-format",
    "output_format",
    type=click.Choice(["text", "json", "stream-json"], case_sensitive=False),
    default="text",
    show_default=True,
)
@click.pass_context
def print_command(
    ctx: click.Context,
    prompt: str,
    model: Optional[str],
    output_format: str,
) -> None:
    json_output = str(output_format).lower() == "json"
    json_stream_output = str(output_format).lower() == "stream-json"
    _handle_headless_mode(
        ctx,
        prompt,
        model,
        json_output=json_output,
        json_stream_output=json_stream_output,
    )


# CMD-008 to CMD-010: Init command
@cli.command(name="init")
@click.option(
    "-y",
    "--yes",
    is_flag=True,
    help="Skip interactive prompts, use defaults",
)
@click.pass_context
def init_command(ctx: click.Context, yes: bool) -> None:
    """
    Initialize a new DeepCode project.

    Creates .deepcode/ directory and generates CLAUDE.md template.
    """
    project_root = Path.cwd()
    deepcode_dir = project_root / ".deepcode"
    claude_md = project_root / "CLAUDE.md"

    # Check if already initialized
    if deepcode_dir.exists():
        click.echo(f"Project already initialized: {deepcode_dir}")
        if not yes and not click.confirm("Reinitialize?"):
            return

    # Detect project type
    project_type = _detect_project_type(project_root)
    project_name = project_root.name

    if not yes:
        # Interactive mode
        project_name = click.prompt("Project name", default=project_name)
        project_type = click.prompt(
            "Project type",
            default=project_type,
            type=click.Choice(["python", "node", "go", "rust", "java", "other"]),
        )

    # Create .deepcode directory
    deepcode_dir.mkdir(parents=True, exist_ok=True)
    (deepcode_dir / "sessions").mkdir(exist_ok=True)

    # Create default settings.json
    settings_path = deepcode_dir / "settings.json"
    if not settings_path.exists():
        default_settings = {
            "llm": {
                "provider": "openai",
                "model": "deepseek-r1-70b",
                "base_url": "http://localhost:8000/v1",
            },
            "permissions": {
                "default_mode": "ask",
            },
        }
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(default_settings, f, indent=2, ensure_ascii=False)
        click.echo(f"Created: {settings_path}")

    # Generate CLAUDE.md
    if not claude_md.exists() or (yes or click.confirm("Generate CLAUDE.md?")):
        content = _generate_claude_md(project_name, project_type, project_root)
        with open(claude_md, "w", encoding="utf-8") as f:
            f.write(content)
        click.echo(f"Created: {claude_md}")

    click.echo(f"\nProject initialized: {project_root}")
    click.echo("Run 'deepcode chat' to start.")


def _detect_project_type(project_root: Path) -> str:
    """Detect project type from files."""
    if (project_root / "pyproject.toml").exists() or (project_root / "setup.py").exists():
        return "python"
    if (project_root / "package.json").exists():
        return "node"
    if (project_root / "go.mod").exists():
        return "go"
    if (project_root / "Cargo.toml").exists():
        return "rust"
    if (project_root / "pom.xml").exists() or (project_root / "build.gradle").exists():
        return "java"
    return "other"


def _generate_claude_md(project_name: str, project_type: str, project_root: Path) -> str:
    """Generate CLAUDE.md content based on project type."""
    templates = {
        "python": '''# {name}

## Project Overview

This is a Python project.

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest

# Run linting
flake8 .
```

## Project Structure

```
{name}/
├── src/           # Source code
├── tests/         # Test files
└── requirements.txt
```

## Key Files

- `requirements.txt` - Python dependencies
- `setup.py` or `pyproject.toml` - Package configuration
''',
        "node": '''# {name}

## Project Overview

This is a Node.js project.

## Development Commands

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Run tests
npm test

# Build for production
npm run build
```

## Project Structure

```
{name}/
├── src/           # Source code
├── tests/         # Test files
└── package.json
```
''',
        "go": '''# {name}

## Project Overview

This is a Go project.

## Development Commands

```bash
# Build
go build ./...

# Run tests
go test ./...

# Run linting
golangci-lint run
```

## Project Structure

```
{name}/
├── cmd/           # Main applications
├── internal/      # Private code
├── pkg/           # Public libraries
└── go.mod
```
''',
        "other": '''# {name}

## Project Overview

Describe your project here.

## Development Commands

Add your development commands here.

## Project Structure

Describe your project structure here.
''',
    }

    template = templates.get(project_type, templates["other"])
    return template.format(name=project_name)


@cli.command(name="write-file")
@click.argument("path")
@click.argument("instruction")
@click.option(
    "--type",
    "file_type",
    default=None,
    help="File type hint for generation (e.g. requirements)",
)
@click.option(
    "--overwrite",
    is_flag=True,
    help="Overwrite if target exists",
)
@click.option(
    "-m",
    "--model",
    default=None,
    help="LLM model to use",
)
@click.pass_context
def write_file_command(
    ctx: click.Context,
    path: str,
    instruction: str,
    file_type: Optional[str],
    overwrite: bool,
    model: Optional[str],
) -> None:
    project_root = ctx.obj.get("project_root") if ctx.obj else None
    if project_root is None:
        project_root = _find_project_root() or os.getcwd()

    settings = load_settings(project_root=project_root)
    _init_file_logging(
        project_root or os.getcwd(),
        getattr(settings, "log_level", None) or os.getenv("LOG_LEVEL"),
    )

    if model:
        settings.llm.model = model

    llm_client = create_llm_client(settings)
    agent_config = AgentConfig(
        llm_client=llm_client,
        max_tokens=settings.llm.max_tokens,
        temperature=settings.llm.temperature,
        stream=False,
        project_root=project_root,
    )
    agent = Agent(agent_config)

    target_path = str(Path(path))
    ft = detect_file_type(target_path, file_type)

    def _gen(p: str) -> str:
        return agent.process(p).content

    content, result = generate_validated(
        generate_fn=_gen,
        file_type=ft,
        target_path=target_path,
        instruction=instruction,
        max_attempts=3,
    )
    if not result.ok:
        raise click.Abort()

    safe_write_text(target_path, content, overwrite=overwrite)
    click.echo(path)


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
    "-c",
    "--continue",
    "continue_session",
    is_flag=True,
    help="Continue the most recent conversation",
)
@click.option(
    "-r",
    "--resume",
    "resume_session",
    default=None,
    help="Resume a specific session by ID (or latest if no ID given)",
    is_flag=False,
    flag_value="__latest__",
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
@click.option(
    "--auto",
    "auto_mode",
    is_flag=True,
    help="Auto agent mode: interpret natural language and execute filesystem/command actions",
)
@click.option(
    "--auto-approve",
    "auto_approve",
    is_flag=True,
    help="Auto-approve all actions in --auto mode (no confirmations)",
)
@click.option(
    "--auto-max-steps",
    "auto_max_steps",
    type=int,
    default=20,
    show_default=True,
    help="Max action-execution iterations per user input in --auto mode",
)
@click.pass_context
def chat(
    ctx: click.Context,
    prompt: str,
    print_mode: bool,
    model: Optional[str],
    continue_session: bool,
    resume_session: Optional[str],
    json_output: bool,
    json_stream_output: bool,
    auto_mode: bool,
    auto_approve: bool,
    auto_max_steps: int,
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

    If -c/--continue is specified, continues the most recent conversation.
    If -r/--resume is specified, resumes a specific session by ID.
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

    if auto_max_steps < 1:
        click.echo("Error: --auto-max-steps must be >= 1", err=True)
        raise click.Abort()

    # Handle session resume/continue
    session_to_resume = None
    if continue_session or resume_session:
        from deep_code.cli.session import SessionStore, get_latest_session, load_session

        project_root = str(Path.cwd())

        if continue_session or resume_session == "__latest__":
            session_to_resume = get_latest_session(project_root)
            if not session_to_resume:
                click.echo("No previous session found to continue.", err=True)
                # Continue without session, don't abort
        elif resume_session:
            session_to_resume = load_session(resume_session, project_root)
            if not session_to_resume:
                click.echo(f"Session '{resume_session}' not found.", err=True)
                raise click.Abort()

        if session_to_resume:
            click.echo(f"Resuming session: {session_to_resume.id} ({len(session_to_resume.messages)} messages)")

    if print_mode:
        _handle_headless_mode(
            ctx,
            prompt,
            model,
            json_output=json_output,
            json_stream_output=json_stream_output,
            session=session_to_resume,
        )
        return

    _handle_interactive_mode(
        ctx,
        prompt,
        model,
        auto_mode=auto_mode,
        auto_approve=auto_approve,
        auto_max_steps=auto_max_steps,
        session=session_to_resume,
    )
    return


def _handle_headless_mode(
    ctx: click.Context,
    prompt: str,
    model: Optional[str],
    json_output: bool = False,
    json_stream_output: bool = False,
    session: Optional["Session"] = None,
) -> None:
    """
    Handle headless mode execution.

    Args:
        ctx: Click context
        prompt: Prompt from command line argument (may be empty)
        model: Optional model override
        json_output: Output as JSON
        json_stream_output: Output as streaming JSON
        session: Optional session to resume

    Raises:
        SystemExit: On error
    """
    # Determine input source: prompt argument or stdin
    user_input = prompt
    input_source = "prompt"

    if not user_input or not user_input.strip():
        # Try to read from stdin
        if not sys.stdin.isatty():
            # Read from stdin pipe
            try:
                user_input = sys.stdin.read()
                input_source = "stdin"
            except Exception as e:
                _LOGGER.exception("headless stdin read failed")
                click.echo(f"Error reading from stdin: {e}", err=True)
                sys.exit(1)
        else:
            # No input source available
            _LOGGER.error("headless no input source")
            click.echo(
                "Error: No prompt provided. "
                "Provide PROMPT argument or pipe via stdin.",
                err=True,
            )
            sys.exit(1)

    if not user_input.strip():
        _LOGGER.error("headless empty prompt")
        click.echo("Error: Empty prompt", err=True)
        sys.exit(1)

    # Load configuration
    try:
        # Use project_root from context, or auto-detect
        project_root = ctx.obj.get("project_root") if ctx.obj else None
        if project_root is None:
            project_root = _find_project_root()
        settings = load_settings(project_root=project_root)

        _init_file_logging(
            project_root or os.getcwd(),
            getattr(settings, "log_level", None) or os.getenv("LOG_LEVEL"),
        )

        _LOGGER.info(
            "headless start project_root=%s model=%s json=%s json_stream=%s auto_mode=%s auto_approve=%s auto_max_steps=%s input_source=%s prompt_len=%s",
            str(project_root),
            str(model or settings.llm.model),
            bool(json_output),
            bool(json_stream_output),
            bool(ctx.obj.get("auto_mode") if ctx.obj else False),
            bool(ctx.obj.get("auto_approve") if ctx.obj else False),
            int(ctx.obj.get("auto_max_steps") if ctx.obj else 0),
            input_source,
            len(user_input or ""),
        )

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
        from deep_code.interaction.parser import Parser
        from deep_code.core.context import ContextManager

        parser = Parser()
        parsed = parser.parse(user_input)

        try:
            _LOGGER.info(
                "headless parsed_refs files=%s dirs=%s cmds=%s",
                len(getattr(parsed, "file_refs", []) or []),
                len(getattr(parsed, "directory_refs", []) or []),
                len(getattr(parsed, "command_refs", []) or []),
            )
        except Exception:
            pass

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
            from deep_code.core.executor import CommandExecutor
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

        try:
            _LOGGER.info(
                "headless enhanced_input_len=%s context_parts=%s",
                len(enhanced_input or ""),
                len(context_parts),
            )
        except Exception:
            pass

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
            t0 = time.time()
            turn = agent.process(enhanced_input)
            dt_ms = int((time.time() - t0) * 1000)
            try:
                _LOGGER.info(
                    "headless agent_done duration_ms=%s content_len=%s",
                    dt_ms,
                    len(getattr(turn, "content", "") or ""),
                )
                _LOGGER.debug(
                    "headless agent_content_prefix=%s",
                    (getattr(turn, "content", "") or "")[:1200],
                )
            except Exception:
                pass
            click.echo(turn.content)
    except Exception as e:
        _LOGGER.exception("headless processing failed")
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
    from deep_code.cli.output import format_json_output, format_tool_calls_for_json

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
    from deep_code.cli.output import format_json_stream_chunk, format_tool_calls_for_json

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
    auto_mode: bool = False,
    auto_approve: bool = False,
    auto_max_steps: int = 20,
    session: Optional["Session"] = None,
) -> None:
    """
    Handle interactive chat mode.

    Args:
        ctx: Click context
        initial_prompt: Optional initial prompt to send
        model: Optional model override
        auto_mode: Enable auto agent mode
        auto_approve: Auto-approve all actions
        auto_max_steps: Max iterations in auto mode
        session: Optional session to resume

    Raises:
        SystemExit: On error
    """
    # Load configuration
    try:
        project_root = ctx.obj.get("project_root") if ctx.obj else None
        if project_root is None:
            project_root = _find_project_root()
        settings = load_settings(project_root=project_root)

        _init_file_logging(
            project_root or os.getcwd(),
            getattr(settings, "log_level", None) or os.getenv("LOG_LEVEL"),
        )

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

    current_mode = "default"

    # Build permission manager from settings
    try:
        from deep_code.security.permissions import PermissionManager, PermissionRule, PermissionAction, PermissionDomain

        perm_manager = PermissionManager()
        default_mode = (settings.permissions.default_mode or "ask").strip().lower()
        default_action = {
            "allow": PermissionAction.ALLOW,
            "deny": PermissionAction.DENY,
            "ask": PermissionAction.ASK,
        }.get(default_mode, PermissionAction.ASK)

        # Default rules: apply to all targets
        perm_manager.add_rule(
            PermissionRule(
                domain=PermissionDomain.FILE_READ,
                action=default_action,
                pattern="*",
                description="default file read policy",
            )
        )
        perm_manager.add_rule(
            PermissionRule(
                domain=PermissionDomain.FILE_WRITE,
                action=default_action,
                pattern="*",
                description="default file write policy",
            )
        )
        perm_manager.add_rule(
            PermissionRule(
                domain=PermissionDomain.COMMAND,
                action=default_action,
                pattern="*",
                description="default command policy",
            )
        )

        # Specific allow lists from settings
        for pat in settings.permissions.file_read:
            perm_manager.add_rule(
                PermissionRule(
                    domain=PermissionDomain.FILE_READ,
                    action=PermissionAction.ALLOW,
                    pattern=str(pat),
                    description=f"allow read {pat}",
                )
            )
        for pat in settings.permissions.file_write:
            perm_manager.add_rule(
                PermissionRule(
                    domain=PermissionDomain.FILE_WRITE,
                    action=PermissionAction.ALLOW,
                    pattern=str(pat),
                    description=f"allow write {pat}",
                )
            )
        for pat in settings.permissions.command_execute:
            perm_manager.add_rule(
                PermissionRule(
                    domain=PermissionDomain.COMMAND,
                    action=PermissionAction.ALLOW,
                    pattern=str(pat),
                    description=f"allow command {pat}",
                )
            )
    except Exception:
        perm_manager = None

    # Start prompt_toolkit UI (supports mode switching and 100% terminal-like layout)
    _run_prompt_toolkit_chat(
        agent=agent,
        settings=settings,
        project_root=project_root,
        permission_manager=perm_manager,
        start_mode=current_mode,
        auto_mode=auto_mode,
        auto_approve=auto_approve,
        auto_max_steps=auto_max_steps,
        initial_prompt=initial_prompt.strip() if initial_prompt else "",
        session=session,
    )


def _print_welcome(settings) -> None:
    """
    Print welcome message for interactive mode.

    Args:
        settings: Loaded settings
    """
    console = Console()

    left = Text()
    left.append(f"Claude Code v{VERSION}\n", style="bold")
    left.append("\n")
    left.append("Welcome back!\n", style="bold")
    left.append("\n")
    left.append(f"Model: {settings.llm.model}\n", style="dim")
    if settings.project_root:
        left.append(f"{settings.project_root}\n", style="dim")

    right = Text()
    right.append("Tips for getting started\n", style="bold")
    right.append("- Use /mode default|plan|bypass to switch modes\n")
    right.append("- Type ? for shortcuts\n")
    right.append("\n")
    right.append("Recent activity\n", style="bold")
    right.append("No recent activity\n", style="dim")

    panel = Panel(
        Columns([left, right], equal=True, expand=True),
        border_style="dark_orange",
        padding=(1, 2),
    )
    console.print(panel)
    console.print(Text("Type 'exit' to quit.", style="dim"))
    console.print()


def _format_action_to_blocks(results: List[dict]) -> List[_ToolBlock]:
    blocks: List[_ToolBlock] = []
    for r in results:
        t = str(r.get("type", ""))
        ok = bool(r.get("ok", False))
        if t == "done":
            continue

        if t == "run":
            title = f"Bash({r.get('command','')})"
            out = (r.get("stdout") or "")
            err = (r.get("stderr") or "")
            body = out
            if err:
                body = (out + "\n" + err).strip("\n")
            blocks.append(_ToolBlock(title=title, body=body, ok=ok))
            continue

        if t == "read_file":
            title = f"Read({r.get('path','')})"
            body = r.get("content") if isinstance(r.get("content"), str) else (r.get("error") or "")
            blocks.append(_ToolBlock(title=title, body=body or "", ok=ok))
            continue

        if t == "read_dir":
            title = f"Read({r.get('path','')})"
            body = r.get("listing") or r.get("error", "") or ""
            blocks.append(_ToolBlock(title=title, body=body, ok=ok))
            continue

        if t in ("write_file", "gen_file", "mkdir"):
            title = f"Write({r.get('path','')})"
            body = r.get("error", "") or ""
            blocks.append(_ToolBlock(title=title, body=body, ok=ok))
            continue

        blocks.append(_ToolBlock(title=f"Tool({t})", body=r.get("error", "") or "", ok=ok))
    return blocks


def _run_prompt_toolkit_chat(
    agent: Agent,
    settings,
    project_root: str,
    permission_manager: Optional[object],
    start_mode: str,
    auto_mode: bool,
    auto_approve: bool,
    auto_max_steps: int,
    initial_prompt: str,
    session: Optional["Session"] = None,
) -> None:
    """Prompt-toolkit based chat UI with fold/unfold tool blocks."""
    try:
        from prompt_toolkit.application import Application
        from prompt_toolkit.application.current import get_app
        from prompt_toolkit.buffer import Buffer
        from prompt_toolkit.history import InMemoryHistory
        from prompt_toolkit.document import Document
        from prompt_toolkit.completion import Completer, Completion
        from prompt_toolkit.key_binding import KeyBindings
        from prompt_toolkit.layout import Layout
        from prompt_toolkit.layout.containers import Float, FloatContainer, HSplit, VSplit, Window
        from prompt_toolkit.layout.controls import BufferControl
        from prompt_toolkit.layout.controls import FormattedTextControl
        from prompt_toolkit.layout.menus import CompletionsMenu
        from prompt_toolkit.formatted_text import ANSI
        from prompt_toolkit.styles import Style
    except Exception:
        # Fallback to old behavior if prompt_toolkit missing
        click.echo("prompt_toolkit not available; falling back to basic input.")
        return

    import concurrent.futures
    from deep_code.cli.session import Session, create_session, save_session
    from deep_code.cli.command_history import CommandHistory, parse_history_reference, is_history_reference

    # Create or use existing session
    if session is None:
        session = create_session(project_root, start_mode)
    current_session = session

    # CMD-017: Initialize command history
    cmd_history = CommandHistory(project_root=project_root)

    # CMD-019: Output truncation settings
    OUTPUT_TRUNCATE_LIMIT = 10000  # characters

    mode = {"value": (start_mode or "default").strip().lower()}
    thinking = {"value": ""}

    blocks: List[_ToolBlock] = []

    # Background execution control
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    running = {"future": None, "cancelled": False}

    def _header_text() -> ANSI:
        # Orange bordered header box, two columns.
        orange = "\x1b[38;5;208m"
        gray = "\x1b[90m"
        white = "\x1b[37m"
        reset = "\x1b[0m"

        cols = _get_terminal_width(app=app, default=100, min_width=60)

        inner_w = cols - 2
        mid = inner_w // 2
        left_w = mid
        right_w = inner_w - left_w

        def pad_plain(s: str, w: int) -> str:
            if len(s) >= w:
                return s[:w]
            return s + " " * (w - len(s))

        # Keep text plain for padding correctness; apply color after padding.
        left_lines = [
            (f"Claude Code v{VERSION}", white),
            ("", reset),
            ("Welcome back!", white),
            ("", reset),
            (f"Model: {settings.llm.model}", gray),
            (str(project_root), gray),
        ]

        right_lines = [
            ("Tips for getting started", white),
            ("Run /mode default|plan|bypass", gray),
            ("Ctrl+O to expand", gray),
            ("", reset),
            ("Recent activity", white),
            ("No recent activity", gray),
        ]

        n = max(len(left_lines), len(right_lines))
        left_lines += [("", reset)] * (n - len(left_lines))
        right_lines += [("", reset)] * (n - len(right_lines))

        top = f"{orange}┌{'─' * (cols - 2)}┐{reset}"
        bottom = f"{orange}└{'─' * (cols - 2)}┘{reset}"

        rows = [top]
        for i in range(n):
            lt, lc = left_lines[i]
            rt, rc = right_lines[i]
            l = pad_plain(lt, left_w)
            r = pad_plain(rt, right_w)
            rows.append(f"{orange}│{reset}{lc}{l}{reset}{rc}{r}{reset}{orange}│{reset}")
        rows.append(bottom)
        return ANSI("\n".join(rows) + "\n")

    def _output_text() -> ANSI:
        s = "".join([b.render() for b in blocks])
        return ANSI(s)

    def _refresh_output() -> None:
        # UI-004: Auto scroll to bottom only if auto_scroll is enabled
        try:
            text = "".join([b.render() for b in blocks])
            total_lines = max(1, text.count("\n"))
            size = app.output.get_size()
            # header(10)+status(1)+seps/prompt/footer(1+1+3+1+1)=18 approx for multiline input
            visible = max(5, size.rows - 18)

            if scroll_state["auto_scroll"]:
                # Auto scroll to bottom
                output_win.vertical_scroll = max(0, total_lines - visible)
            else:
                # Keep manual scroll position
                output_win.vertical_scroll = scroll_state["manual_offset"]
        except Exception:
            pass

    def _footer_text() -> ANSI:
        gray = "\x1b[90m"
        reset = "\x1b[0m"
        # UI-010: Updated keyboard shortcuts (Enter to submit)
        return ANSI(f"{gray}PgUp/PgDn: scroll | Enter: send | Ctrl+L: clear | Esc: cancel{reset}")

    def _status_text() -> ANSI:
        if thinking["value"]:
            return ANSI(thinking["value"])
        return ANSI("")

    header_ctl = FormattedTextControl(text=_header_text)
    output_ctl = FormattedTextControl(text=_output_text)
    footer_ctl = FormattedTextControl(text=_footer_text)
    status_ctl = FormattedTextControl(text=_status_text)

    header_win = Window(content=header_ctl, height=10, dont_extend_height=True)
    # UI-001: Configure output_win for scrolling
    # Track scroll state: auto_scroll=True means follow new content
    scroll_state = {"auto_scroll": True, "manual_offset": 0}
    output_win = Window(
        content=output_ctl,
        wrap_lines=False,
        always_hide_cursor=True,
        allow_scroll_beyond_bottom=True,
    )
    status_win = Window(content=status_ctl, height=1, dont_extend_height=True)
    footer_win = Window(content=footer_ctl, height=1, dont_extend_height=True)

    prompt_ctl = FormattedTextControl(text=lambda: ANSI(f"\x1b[37m>\x1b[0m \x1b[90m[{mode['value']}]\x1b[0m "))

    # IMPORTANT: Use a real Buffer/BufferControl so the terminal cursor is real.
    # This fixes Windows IME candidate window jumping to top-left.
    input_state = {"last_text": ""}

    def _accept(buf: Buffer) -> None:
        text = buf.text
        # Ensure up/down history works even with a custom accept_handler.
        try:
            if text.strip():
                buf.append_to_history()
        except Exception:
            try:
                # Fallback for older/newer prompt_toolkit variants.
                if text.strip() and hasattr(buf, "history") and hasattr(buf.history, "append_string"):
                    buf.history.append_string(text)
            except Exception:
                pass
        buf.document = Document(text="", cursor_position=0)
        input_state["last_text"] = text
        # UI-004: Re-enable auto scroll when user submits input
        scroll_state["auto_scroll"] = True
        try:
            _handle_user_line(text)
        except EOFError:
            app.exit(result=None)
        except Exception as e:
            _append_text(f"\x1b[31mError: {e}\x1b[0m\n")
        app.invalidate()

    # UI-005 & UI-006: Single-line input with auto-wrap for long content
    # CMD-006: Integrate file completion
    # Enter submits, long content wraps visually
    from prompt_toolkit.layout.dimension import Dimension
    from deep_code.cli.completion import create_completer

    file_completer = create_completer(project_root=project_root)
    input_buf = Buffer(multiline=False, accept_handler=_accept, history=InMemoryHistory(), completer=file_completer)
    input_ctl = BufferControl(buffer=input_buf, focusable=True)
    # Single line input, but wrap_lines=True allows visual wrapping for long input
    input_win = Window(
        content=input_ctl,
        height=Dimension(min=1, max=5, preferred=1),
        dont_extend_height=False,
        wrap_lines=True,
    )

    def _input_sep_text() -> ANSI:
        orange = "\x1b[38;5;208m"
        reset = "\x1b[0m"
        cols = _get_terminal_width(app=get_app(), default=100, min_width=20)
        return ANSI(f"{orange}{'─' * cols}{reset}")

    input_sep_ctl = FormattedTextControl(text=_input_sep_text)
    input_sep_win_top = Window(content=input_sep_ctl, height=1, dont_extend_height=True)
    input_sep_win_bottom = Window(content=input_sep_ctl, height=1, dont_extend_height=True)

    body = HSplit(
        [
            header_win,
            output_win,
            status_win,
            input_sep_win_top,
            # UI-006: Prompt on top, multiline input below
            HSplit([
                Window(prompt_ctl, height=1, dont_extend_height=True),
                input_win,
            ]),
            input_sep_win_bottom,
            footer_win,
        ]
    )

    container = FloatContainer(
        content=body,
        floats=[
            Float(
                content=CompletionsMenu(max_height=8, scroll_offset=1),
                xcursor=True,
                ycursor=True,
            )
        ],
    )

    kb = KeyBindings()

    def _set_thinking(on: bool) -> None:
        orange = "\x1b[38;5;208m"
        gray = "\x1b[90m"
        reset = "\x1b[0m"
        if on:
            thinking["value"] = f"{orange}* Puzzling...{reset} {gray}(esc to interrupt · thinking){reset}"
        else:
            thinking["value"] = ""

    def _handle_user_line(line: str) -> None:
        line = (line or "").strip("\r\n")
        if not line.strip():
            return
        _LOGGER.info("user_input mode=%s text=%s", mode.get("value"), (line[:500] if len(line) > 500 else line))
        if line.strip().lower() in ("exit", "quit", "q"):
            # Save session before exit
            save_session(current_session, project_root)
            raise EOFError()

        # Record user message in session
        current_session.add_user_message(line)

        # show user prompt as a block
        blocks.append(_ToolBlock(title=f"> {line}", body="", ok=True, expanded=True))
        _refresh_output()

        if line.startswith("/"):
            try:
                parts = shlex.split(line, posix=False)
            except Exception:
                parts = [line]

            # shortcut
            if parts and parts[0].lower() == "/plan":
                mode["value"] = "plan"
                _LOGGER.info("mode_switch to=plan via /plan")
                blocks.append(_ToolBlock(title="Mode: plan", body="", ok=True, expanded=True))
                _refresh_output()
                return

            if parts and parts[0].lower() in ("/mode", "/m"):
                if len(parts) >= 2 and str(parts[1]).strip().lower() in ("default", "plan", "bypass"):
                    mode["value"] = str(parts[1]).strip().lower()
                    _LOGGER.info("mode_switch to=%s via /mode", mode["value"])
                    blocks.append(_ToolBlock(title=f"Mode: {mode['value']}", body="", ok=True, expanded=True))
                    _refresh_output()
                else:
                    blocks.append(_ToolBlock(title="Usage: /mode default|plan|bypass", body="", ok=True, expanded=True))
                    _refresh_output()
                return

            if parts and parts[0].lower() in ("/help", "/?"):
                blocks.append(
                    _ToolBlock(
                        title="Help",
                        body="/mode default|plan|bypass\n/plan (shortcut for plan mode)\nCtrl+O: expand/collapse last tool block\nEsc: cancel current execution",
                        ok=True,
                        expanded=True,
                    )
                )
                _refresh_output()
                return

            # Other local commands fallback to existing handler (prints to stdout).
            try:
                from io import StringIO
                import contextlib

                buf = StringIO()
                with contextlib.redirect_stdout(buf):
                    _handle_local_command(agent=agent, user_input=line, project_root=project_root)
                out = buf.getvalue()
                blocks.append(_ToolBlock(title=f"Local({line})", body=out, ok=True))
                _refresh_output()
            except Exception as e:
                blocks.append(_ToolBlock(title=f"Local({line})", body=str(e), ok=False))
                _refresh_output()
            return

        # CMD-018: Handle history references (!! !-N !prefix)
        if is_history_reference(line):
            resolved_cmd = parse_history_reference(line, cmd_history)
            if resolved_cmd:
                blocks.append(_ToolBlock(
                    title=f"History: {line} -> {resolved_cmd}",
                    body="",
                    ok=True,
                    expanded=True,
                ))
                _refresh_output()
                # Execute the resolved command
                line = f"! {resolved_cmd}"
            else:
                blocks.append(_ToolBlock(
                    title=f"History: {line}",
                    body="No matching command found in history",
                    ok=False,
                    expanded=True,
                ))
                _refresh_output()
                return

        # CMD-015/016/017/019: Handle direct shell commands with ! prefix
        if line.strip().startswith("!") and " " in line:
            from deep_code.core.executor import CommandExecutor
            cmd_text = line.strip()[1:].strip()

            # Check for background execution (ends with &)
            run_background = cmd_text.endswith(" &") or cmd_text.endswith("&")
            if run_background:
                cmd_text = cmd_text.rstrip("&").strip()

            cmd_executor = CommandExecutor()

            if run_background:
                # CMD-015: Background execution
                def _on_bg_complete(result):
                    # Record in history
                    cmd_history.add(cmd_text, result.return_code, project_root)
                    # Notify user
                    output = result.combined_output()
                    if len(output) > OUTPUT_TRUNCATE_LIMIT:
                        output = output[:OUTPUT_TRUNCATE_LIMIT] + f"\n... [truncated, {len(output)} chars total]"
                    status = "OK" if result.success else f"FAILED (exit {result.return_code})"

                    def _update():
                        blocks.append(_ToolBlock(
                            title=f"Background: {cmd_text} [{status}]",
                            body=output,
                            ok=result.success,
                        ))
                        _refresh_output()

                    try:
                        app.call_from_executor(_update)
                    except Exception:
                        pass

                bg_cmd = cmd_executor.execute_background(
                    cmd_text,
                    working_dir=project_root,
                    on_complete=_on_bg_complete,
                )
                blocks.append(_ToolBlock(
                    title=f"Background: {cmd_text} (running...)",
                    body="Command started in background",
                    ok=True,
                    expanded=True,
                ))
                _refresh_output()
                return
            else:
                # CMD-016: Streaming execution for interactive feedback
                # For simplicity, use regular execution with output truncation
                try:
                    result = cmd_executor.execute(cmd_text, working_dir=project_root, timeout=120)
                    output = result.combined_output()

                    # CMD-017: Record in history
                    cmd_history.add(cmd_text, result.return_code, project_root)

                    # CMD-019: Truncate long output
                    truncated = False
                    if len(output) > OUTPUT_TRUNCATE_LIMIT:
                        truncated = True
                        output = output[:OUTPUT_TRUNCATE_LIMIT] + f"\n... [truncated, {len(output)} chars total]"

                    status = "OK" if result.success else f"exit {result.return_code}"
                    blocks.append(_ToolBlock(
                        title=f"$ {cmd_text} [{status}]",
                        body=output,
                        ok=result.success,
                    ))
                    _refresh_output()
                except Exception as e:
                    blocks.append(_ToolBlock(
                        title=f"$ {cmd_text} [ERROR]",
                        body=str(e),
                        ok=False,
                    ))
                    _refresh_output()
                return

        use_auto = auto_mode or mode["value"] in ("plan", "bypass")

        # If a run is in progress, don't start another.
        fut = running.get("future")
        if fut is not None and not fut.done():
            blocks.append(_ToolBlock(title="Busy", body="(press Esc to cancel)", ok=False))
            _refresh_output()
            return

        _set_thinking(True)
        running["cancelled"] = False
        app.invalidate()

        def _work() -> List[dict]:
            if use_auto:
                _LOGGER.info("auto_start mode=%s max_steps=%s", mode.get("value"), int(auto_max_steps))

                def _approval_cb(message: str) -> bool:
                    import threading

                    approval = get_approval()
                    flag = {"value": False}
                    evt = threading.Event()

                    def _run() -> None:
                        try:
                            flag["value"] = bool(approval.confirm(message, default=False))
                        finally:
                            evt.set()

                    def _request() -> None:
                        try:
                            app.run_in_terminal(_run)
                        except Exception:
                            _run()

                    try:
                        app.call_from_executor(_request)
                    except Exception:
                        _request()
                    evt.wait()
                    return bool(flag["value"])

                return _process_input_auto_collect(
                    agent=agent,
                    user_input=line,
                    project_root=project_root,
                    auto_approve=(auto_approve or mode["value"] == "bypass"),
                    permission_manager=permission_manager,
                    mode=mode["value"],
                    max_steps=auto_max_steps,
                    approval_callback=_approval_cb,
                )
            turn = agent.process(line)
            return [{"type": "assistant", "ok": True, "content": getattr(turn, "content", "") or ""}]

        running["future"] = executor.submit(_work)

        def _on_done(_fut) -> None:
            try:
                results = _fut.result()
            except Exception as e:
                results = [{"type": "assistant", "ok": False, "content": str(e)}]

            if running.get("cancelled"):
                # Ignore late results after cancel.
                try:
                    app.call_from_executor(lambda: None)
                except Exception:
                    pass
                return

            def _apply() -> None:
                _set_thinking(False)
                assistant_content = ""
                if use_auto:
                    blocks.extend(_format_action_to_blocks(results))
                    blocks.append(_ToolBlock(title="DONE", body="", ok=True, expanded=True))
                    # Collect all content for session
                    for r in results:
                        if isinstance(r, dict) and r.get("content"):
                            assistant_content += str(r.get("content", "")) + "\n"
                else:
                    content = ""
                    if results and isinstance(results[0], dict):
                        content = str(results[0].get("content", "") or "")
                    blocks.append(_ToolBlock(title="Assistant", body=content, ok=True))
                    assistant_content = content

                # Record assistant message and save session
                if assistant_content.strip():
                    current_session.add_assistant_message(assistant_content.strip())
                save_session(current_session, project_root)

                _refresh_output()
                try:
                    app.layout.focus(input_win)
                except Exception:
                    pass
                app.invalidate()

            try:
                app.call_from_executor(_apply)
            except Exception:
                _apply()

        running["future"].add_done_callback(_on_done)
        return

    # UI-002: Page Up/Down for scrolling output
    @kb.add("pageup")
    def _(event) -> None:
        try:
            text = "".join([b.render() for b in blocks])
            total_lines = max(1, text.count("\n"))
            size = event.app.output.get_size()
            visible = max(5, size.rows - 18)
            scroll_amount = max(1, visible - 2)

            # Disable auto scroll when user manually scrolls
            scroll_state["auto_scroll"] = False
            new_scroll = max(0, output_win.vertical_scroll - scroll_amount)
            output_win.vertical_scroll = new_scroll
            scroll_state["manual_offset"] = new_scroll
            event.app.invalidate()
        except Exception:
            pass

    @kb.add("pagedown")
    def _(event) -> None:
        try:
            text = "".join([b.render() for b in blocks])
            total_lines = max(1, text.count("\n"))
            size = event.app.output.get_size()
            visible = max(5, size.rows - 18)
            scroll_amount = max(1, visible - 2)
            max_scroll = max(0, total_lines - visible)

            # Disable auto scroll when user manually scrolls
            scroll_state["auto_scroll"] = False
            new_scroll = min(max_scroll, output_win.vertical_scroll + scroll_amount)
            output_win.vertical_scroll = new_scroll
            scroll_state["manual_offset"] = new_scroll

            # Re-enable auto scroll if at bottom
            if new_scroll >= max_scroll:
                scroll_state["auto_scroll"] = True

            event.app.invalidate()
        except Exception:
            pass

    # UI-003: Ctrl+Home/End for jumping to top/bottom
    @kb.add("c-home")
    def _(event) -> None:
        try:
            scroll_state["auto_scroll"] = False
            output_win.vertical_scroll = 0
            scroll_state["manual_offset"] = 0
            event.app.invalidate()
        except Exception:
            pass

    @kb.add("c-end")
    def _(event) -> None:
        try:
            text = "".join([b.render() for b in blocks])
            total_lines = max(1, text.count("\n"))
            size = event.app.output.get_size()
            visible = max(5, size.rows - 18)
            max_scroll = max(0, total_lines - visible)

            scroll_state["auto_scroll"] = True
            output_win.vertical_scroll = max_scroll
            scroll_state["manual_offset"] = max_scroll
            event.app.invalidate()
        except Exception:
            pass

    # UI-008: Ctrl+L to clear screen
    @kb.add("c-l")
    def _(event) -> None:
        blocks.clear()
        scroll_state["auto_scroll"] = True
        scroll_state["manual_offset"] = 0
        output_win.vertical_scroll = 0
        event.app.invalidate()

    @kb.add("c-o")
    def _(event) -> None:
        # Toggle last foldable block
        found = None
        for b in reversed(blocks):
            if b.body and len(b.body.splitlines()) > b.max_lines:
                b.expanded = not b.expanded
                found = b
                break
        try:
            _LOGGER.debug(
                "ui_fold_toggle found=%s title=%s expanded=%s",
                bool(found),
                getattr(found, "title", None),
                getattr(found, "expanded", None),
            )
        except Exception:
            pass
        event.app.invalidate()

    @kb.add("c-c")
    @kb.add("escape")
    def _(event) -> None:
        # Escape cancels current run if any, otherwise exit.
        if thinking["value"]:
            try:
                _LOGGER.debug("ui_cancel esc pressed while thinking")
            except Exception:
                pass
            running["cancelled"] = True
            thinking["value"] = ""
            blocks.append(_ToolBlock(title="Cancelled", body="", ok=False))
            _refresh_output()
            event.app.invalidate()
            return
        event.app.exit(result=None)

    @kb.add("tab")
    def _(event) -> None:
        # Trigger completion.
        try:
            b = input_buf
            _LOGGER.debug("ui_completion tab text_prefix=%s", (b.text[:200] if isinstance(b.text, str) else ""))
            b.start_completion(select_first=False)
        except Exception:
            pass

    @kb.add("up")
    def _(event) -> None:
        # Single-line buffer uses up/down for cursor movement by default;
        # bind them to history navigation.
        try:
            before = input_buf.text
            input_buf.history_backward(count=1)
            after = input_buf.text
            _LOGGER.debug(
                "ui_history up before_len=%s after_len=%s",
                len(before or ""),
                len(after or ""),
            )
        except Exception:
            pass

    @kb.add("down")
    def _(event) -> None:
        try:
            before = input_buf.text
            input_buf.history_forward(count=1)
            after = input_buf.text
            _LOGGER.debug(
                "ui_history down before_len=%s after_len=%s",
                len(before or ""),
                len(after or ""),
            )
        except Exception:
            pass

    # Tab completion for slash commands.
    slash_words = [
        "/mode",
        "/m",
        "/plan",
        "/help",
        "/?",
        "/mkdir",
        "/read-file",
        "/read-dir",
        "/write-file",
        "/gen-file",
    ]

    class _SlashCompleter(Completer):
        def get_completions(self, document, complete_event):
            text = document.text_before_cursor
            if not text.startswith("/"):
                return

            # /m -> /mode convenience.
            if text == "/m":
                yield Completion("/mode", start_position=-len(text))
                return

            # /mode argument completion.
            if text.startswith("/mode"):
                # Normalize: allow "/mode" and "/mode "
                if text.strip() == "/mode":
                    yield Completion("/mode ", start_position=-len(text))
                    return
                if text.startswith("/mode "):
                    prefix = text[len("/mode ") :]
                    for opt in ("default", "plan", "bypass"):
                        if opt.startswith(prefix):
                            yield Completion(opt, start_position=-len(prefix))
                    return

            for w in slash_words:
                if w.startswith(text):
                    yield Completion(w, start_position=-len(text))

    input_buf.completer = _SlashCompleter()
    try:
        # In prompt_toolkit 3.x this is a callable/filter, not a bool.
        input_buf.complete_while_typing = lambda: False
    except Exception:
        pass

    style = Style.from_dict(
        {
            # Keep terminal palette; screenshot-like colors are produced by ANSI sequences.
        }
    )

    # UI-009: Enable mouse support for scrolling
    app = Application(layout=Layout(container), key_bindings=kb, full_screen=True, style=style, mouse_support=True)

    # Always keep focus on the input buffer so IME tracks cursor.
    try:
        app.layout.focus(input_win)
    except Exception:
        pass

    if initial_prompt:
        try:
            _handle_user_line(initial_prompt)
        except Exception:
            pass

    app.run()


def _process_input_auto_collect(
    agent: Agent,
    user_input: str,
    project_root: str,
    auto_approve: bool,
    permission_manager: Optional[object],
    mode: str = "default",
    max_steps: int = 20,
    approval_callback: Optional[Callable[[str], bool]] = None,
) -> List[dict]:
    """Run auto loop but return the last step results for UI rendering."""
    import json

    from deep_code.cli.filegen import detect_file_type, generate_validated, safe_write_text
    from deep_code.core.executor import CommandExecutor
    from deep_code.security.permissions import PermissionDomain

    executor = CommandExecutor()

    mode_norm = (mode or "default").strip().lower()
    try:
        _LOGGER.info("auto_collect_start mode=%s max_steps=%s", mode_norm, int(max_steps))
    except Exception:
        pass
    allowed_write_paths = {
        "plan": {".pycc/plan.md", ".pycc/tasks.md", ".pycc/plan.txt", ".pycc/tasks.txt"},
    }
    allowed_action_types = {
        "plan": {"read_file", "read_dir", "write_file", "gen_file", "done"},
        "default": {"mkdir", "read_file", "read_dir", "write_file", "gen_file", "run", "done"},
        "bypass": {"mkdir", "read_file", "read_dir", "write_file", "gen_file", "run", "done"},
    }

    def _check(domain: PermissionDomain, target: str, ask_message: str) -> bool:
        return _check_permission(
            domain=domain,
            target=target,
            ask_message=ask_message,
            mode=mode_norm,
            auto_approve=auto_approve,
            permission_manager=permission_manager,
            approval_callback=approval_callback,
        )

    def _execute_action(action: dict) -> dict:
        at = str(action.get("type", "")).strip().lower()
        try:
            _LOGGER.info(
                "auto_action_start mode=%s type=%s action=%s",
                mode_norm,
                at,
                str(action)[:800],
            )
        except Exception:
            pass
        allowed = allowed_action_types.get(mode_norm, allowed_action_types["default"])
        if at not in allowed:
            r0 = {"type": at, "ok": False, "error": f"action not allowed in mode {mode_norm}"}
            try:
                _LOGGER.warning(
                    "auto_action_end mode=%s type=%s ok=%s error=%s",
                    mode_norm,
                    at,
                    False,
                    r0.get("error"),
                )
            except Exception:
                pass
            return r0

        if at == "done":
            r1 = {"type": "done", "ok": True}
            try:
                _LOGGER.info("auto_action_end mode=%s type=done ok=True", mode_norm)
            except Exception:
                pass
            return r1

        if at == "mkdir":
            path_arg = str(action.get("path", "")).strip()
            if not path_arg:
                return {"type": "mkdir", "ok": False, "error": "mkdir requires path"}
            if not _check(PermissionDomain.FILE_WRITE, path_arg, f"Write directory: {path_arg}"):
                return {"type": "mkdir", "path": path_arg, "ok": False, "error": "permission denied"}
            target = _resolve_under_root(project_root, path_arg)
            Path(target).mkdir(parents=True, exist_ok=True)
            r2 = {"type": "mkdir", "path": path_arg, "ok": True}
            try:
                _LOGGER.info("auto_action_end mode=%s type=mkdir ok=True path=%s", mode_norm, path_arg)
            except Exception:
                pass
            return r2

        if at == "read_file":
            path_arg = str(action.get("path", "")).strip()
            if not path_arg:
                return {"type": "read_file", "ok": False, "error": "read_file requires path"}
            if not _check(PermissionDomain.FILE_READ, path_arg, f"Read file: {path_arg}"):
                return {"type": "read_file", "path": path_arg, "ok": False, "error": "permission denied"}
            target = _resolve_under_root(project_root, path_arg)
            p = Path(target)
            if not p.exists() or not p.is_file():
                return {"type": "read_file", "path": path_arg, "ok": False, "error": "file not found"}
            content = p.read_text(encoding="utf-8")
            r3 = {"type": "read_file", "path": path_arg, "ok": True, "content": content}
            try:
                _LOGGER.info(
                    "auto_action_end mode=%s type=read_file ok=True path=%s content_len=%s",
                    mode_norm,
                    path_arg,
                    len(content),
                )
            except Exception:
                pass
            return r3

        if at == "read_dir":
            path_arg = str(action.get("path", "")).strip()
            if not path_arg:
                return {"type": "read_dir", "ok": False, "error": "read_dir requires path"}
            recursive = bool(action.get("recursive", True))
            max_entries = int(action.get("max_entries", 200))
            if max_entries < 1:
                max_entries = 1
            if not _check(PermissionDomain.FILE_READ, path_arg, f"Read directory: {path_arg}"):
                return {"type": "read_dir", "path": path_arg, "ok": False, "error": "permission denied"}
            target = _resolve_under_root(project_root, path_arg)
            listing = _format_dir_listing(target, recursive=recursive, max_entries=max_entries)
            r4 = {"type": "read_dir", "path": path_arg, "ok": True, "listing": listing}
            try:
                _LOGGER.info(
                    "auto_action_end mode=%s type=read_dir ok=True path=%s listing_len=%s",
                    mode_norm,
                    path_arg,
                    len(listing or ""),
                )
            except Exception:
                pass
            return r4

        if at == "write_file":
            path_arg = str(action.get("path", "")).strip()
            content = action.get("content", "")
            overwrite = bool(action.get("overwrite", True))
            if not path_arg or not isinstance(content, str):
                return {"type": "write_file", "ok": False, "error": "write_file requires path/content"}
            if mode_norm == "plan":
                norm = path_arg.replace("\\", "/")
                if norm not in allowed_write_paths["plan"]:
                    return {"type": "write_file", "path": path_arg, "ok": False, "error": "plan mode: write restricted"}
            if not _check(PermissionDomain.FILE_WRITE, path_arg, f"Write file: {path_arg}"):
                return {"type": "write_file", "path": path_arg, "ok": False, "error": "permission denied"}
            target = _resolve_under_root(project_root, path_arg)
            safe_write_text(target, content, overwrite=overwrite)
            r5 = {"type": "write_file", "path": path_arg, "ok": True}
            try:
                _LOGGER.info(
                    "auto_action_end mode=%s type=write_file ok=True path=%s content_len=%s overwrite=%s",
                    mode_norm,
                    path_arg,
                    len(content or ""),
                    bool(overwrite),
                )
            except Exception:
                pass
            return r5

        if at == "gen_file":
            path_arg = str(action.get("path", "")).strip()
            instruction = str(action.get("instruction", "")).strip()
            file_type = action.get("file_type")
            overwrite = bool(action.get("overwrite", False))
            max_attempts = int(action.get("max_attempts", 3))
            if not path_arg or not instruction:
                return {"type": "gen_file", "ok": False, "error": "gen_file requires path/instruction"}
            if max_attempts < 1:
                max_attempts = 1
            if mode_norm == "plan":
                norm = path_arg.replace("\\", "/")
                if norm not in allowed_write_paths["plan"]:
                    return {"type": "gen_file", "path": path_arg, "ok": False, "error": "plan mode: write restricted"}
            if not _check(PermissionDomain.FILE_WRITE, path_arg, f"Generate file: {path_arg}"):
                return {"type": "gen_file", "path": path_arg, "ok": False, "error": "permission denied"}
            target = _resolve_under_root(project_root, path_arg)
            ft = detect_file_type(target, file_type)

            def _gen(prompt: str) -> str:
                return agent.process(prompt).content

            content2, result = generate_validated(
                generate_fn=_gen,
                file_type=ft,
                target_path=target,
                instruction=instruction,
                max_attempts=max_attempts,
            )
            if not result.ok:
                return {"type": "gen_file", "path": path_arg, "ok": False, "error": result.error}
            safe_write_text(target, content2, overwrite=overwrite)
            r6 = {"type": "gen_file", "path": path_arg, "ok": True}
            try:
                _LOGGER.info(
                    "auto_action_end mode=%s type=gen_file ok=True path=%s content_len=%s overwrite=%s",
                    mode_norm,
                    path_arg,
                    len(content2 or ""),
                    bool(overwrite),
                )
            except Exception:
                pass
            return r6

        if at == "run":
            command = str(action.get("command", "")).strip()
            if not command:
                return {"type": "run", "ok": False, "error": "run requires command"}
            if not _check(PermissionDomain.COMMAND, command, f"Run command: {command}"):
                return {"type": "run", "command": command, "ok": False, "error": "permission denied"}
            working_dir = str(action.get("working_dir", "")).strip() or project_root
            working_dir_resolved = _resolve_under_root(project_root, working_dir) if working_dir != project_root else project_root
            cmd_parts = shlex.split(command, posix=False)
            if not cmd_parts:
                return {"type": "run", "command": command, "ok": False, "error": "run command parsed empty"}

            # Windows-friendly: shlex(posix=False) may preserve surrounding quotes.
            # Strip wrapping quotes so `python -c "print(123)"` works.
            norm_parts = []
            for p in cmd_parts:
                if len(p) >= 2 and ((p[0] == '"' and p[-1] == '"') or (p[0] == "'" and p[-1] == "'")):
                    norm_parts.append(p[1:-1])
                else:
                    norm_parts.append(p)

            res = executor.execute(*norm_parts, working_dir=working_dir_resolved)
            r7 = {
                "type": "run",
                "command": command,
                "ok": bool(res.success),
                "return_code": res.return_code,
                "stdout": res.stdout,
                "stderr": res.stderr,
                "timed_out": res.timed_out,
            }
            try:
                _LOGGER.info(
                    "auto_action_end mode=%s type=run ok=%s rc=%s stdout_len=%s stderr_len=%s timed_out=%s cmd=%s",
                    mode_norm,
                    bool(r7.get("ok")),
                    r7.get("return_code"),
                    len((r7.get("stdout") or "")),
                    len((r7.get("stderr") or "")),
                    bool(r7.get("timed_out")),
                    (command[:500] if isinstance(command, str) else ""),
                )
            except Exception:
                pass
            return r7

        return {"type": at, "ok": False, "error": f"unknown action type: {at}"}

    tool_context = ""
    last_results: List[dict] = []
    system_rules = (
        "You are operating in AUTO MODE.\n"
        "You MUST respond with a single JSON object of the form {\"actions\": [...]} and nothing else.\n"
        "Each action is an object with a 'type'. Allowed types: mkdir, read_file, read_dir, write_file, gen_file, run, done.\n"
        "When finished, return one action: {\"type\": \"done\"}.\n"
    )
    if mode_norm == "plan":
        system_rules += "PLAN MODE: Focus on writing plan files only.\n"

    for step in range(max_steps):
        prompt = user_input
        if tool_context:
            prompt = tool_context + "\n\n" + prompt
        prompt = system_rules + "\n" + prompt
        turn = agent.process(prompt)
        try:
            _LOGGER.debug(
                "auto_collect_model_output step=%s content_prefix=%s",
                step,
                (getattr(turn, "content", "") or "")[:1200],
            )
        except Exception:
            pass
        raw = _extract_first_json_object(turn.content)
        data = json.loads(raw) if raw else {}
        actions = data.get("actions") if isinstance(data, dict) else None
        if not isinstance(actions, list):
            try:
                _LOGGER.warning(
                    "auto_collect_invalid_actions step=%s output_prefix=%s",
                    step,
                    (getattr(turn, "content", "") or "")[:1200],
                )
            except Exception:
                pass
            return [{"type": "tool", "ok": False, "error": "invalid actions"}]
        results: List[dict] = []
        done = False
        for act in actions:
            if not isinstance(act, dict):
                results.append({"type": "tool", "ok": False, "error": "invalid action"})
                continue
            r = _execute_action(act)
            results.append(r)
            if r.get("type") == "done":
                done = True
        last_results = results
        try:
            _LOGGER.info(
                "auto_collect_step_results step=%s done=%s results=%s",
                step,
                bool(done),
                ",".join([f"{x.get('type')}:{'ok' if x.get('ok') else 'fail'}" for x in results]),
            )
        except Exception:
            pass
        tool_context = "--- Tool Results ---\n" + json.dumps({"results": results}, ensure_ascii=False) + "\n--- End Tool Results ---"
        if done:
            break

    return last_results


def _render_tool_block(console, title: str, body: str = "", ok: bool = True) -> None:
    dot_style = "green" if ok else "red"
    title_style = "white" if ok else "red"

    t = Text()
    t.append("● ", style=dot_style)
    t.append(title, style=title_style)
    console.print(t)
    if body:
        console.print(Text(_truncate_lines(body).rstrip("\n"), style="bright_black"))


def _render_action_results(console, results: List[dict]) -> None:
    for r in results:
        t = str(r.get("type", ""))
        ok = bool(r.get("ok", False))

        if t == "run":
            title = f"Bash({r.get('command','')})"
            out = (r.get("stdout") or "")
            err = (r.get("stderr") or "")
            body = out
            if err:
                body = (out + "\n" + err).strip("\n")
            if not body:
                body = ""
            _render_tool_block(console, title, body=body, ok=ok)
            continue

        if t == "read_file":
            title = f"Read({r.get('path','')})"
            content = r.get("content")
            if isinstance(content, str):
                body = content
            else:
                body = r.get("error", "") or ""
            _render_tool_block(console, title, body=body, ok=ok)
            continue

        if t == "read_dir":
            title = f"Read({r.get('path','')})"
            body = r.get("listing") or r.get("error", "") or ""
            _render_tool_block(console, title, body=body, ok=ok)
            continue

        if t in ("write_file", "gen_file", "mkdir"):
            label = {"write_file": "Write", "gen_file": "Write", "mkdir": "Write"}.get(t, "Write")
            title = f"{label}({r.get('path','')})"
            body = r.get("error", "") or ""
            _render_tool_block(console, title, body=body, ok=ok)
            continue

        if t == "done":
            continue

        title = f"Tool({t})"
        body = r.get("error", "") or ""
        _render_tool_block(console, title, body=body, ok=ok)


def _read_input(mode: str = "default") -> str:
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
        from prompt_toolkit.styles import Style

        style = Style.from_dict(
            {
                "prompt": "bold",
                "mode": "ansibrightblack",
            }
        )

        prompt_text = FormattedText(
            [
                ("class:prompt", "> "),
                ("class:mode", f"[{mode}] "),
            ]
        )

        user_input = prompt(
            prompt_text,
            style=style,
        )
        return user_input
    except Exception:
        # Fallback to built-in input
        try:
            return input(f"> [{mode}] ")
        except EOFError:
            raise


def _process_input(agent: Agent, user_input: str) -> None:
    """
    Process user input in interactive mode.

    Args:
        agent: Agent instance
        user_input: User's input string
    """
    from deep_code.interaction.parser import Parser
    from deep_code.core.context import ContextManager

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
        from deep_code.core.executor import CommandExecutor
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
    with console.status("[dark_orange]Puzzling...[/] [bright_black](thinking)[/]"):
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


def _parse_auto_actions(model_output: str) -> List[dict]:
    import json

    raw = _extract_first_json_object(model_output)
    if not raw:
        raise ValueError("no json found in model output")
    data = json.loads(raw)
    if not isinstance(data, dict) or "actions" not in data:
        raise ValueError("auto mode requires JSON object with 'actions'")
    actions = data.get("actions")
    if not isinstance(actions, list):
        raise ValueError("'actions' must be a list")
    cleaned = []
    for a in actions:
        if not isinstance(a, dict) or "type" not in a:
            raise ValueError("each action must be an object with 'type'")
        cleaned.append(a)
    return cleaned


def _format_action_results(results: List[dict]) -> str:
    import json

    return json.dumps({"results": results}, ensure_ascii=False)


def _process_input_auto(
    agent: Agent,
    user_input: str,
    project_root: str,
    auto_approve: bool,
    permission_manager: Optional[object],
    mode: str = "default",
    max_steps: int = 20,
) -> None:
    from deep_code.core.executor import CommandExecutor
    from deep_code.cli.filegen import detect_file_type, generate_validated, safe_write_text
    from deep_code.security.permissions import PermissionDomain

    console = Console()
    approval = get_approval()
    executor = CommandExecutor()

    mode_norm = (mode or "default").strip().lower()

    allowed_write_paths = {
        "plan": {".pycc/plan.md", ".pycc/tasks.md", ".pycc/plan.txt", ".pycc/tasks.txt"},
    }

    allowed_action_types = {
        "plan": {"read_file", "read_dir", "write_file", "gen_file", "done"},
        "default": {"mkdir", "read_file", "read_dir", "write_file", "gen_file", "run", "done"},
        "bypass": {"mkdir", "read_file", "read_dir", "write_file", "gen_file", "run", "done"},
    }

    def _check(domain: PermissionDomain, target: str, ask_message: str) -> bool:
        return _check_permission(
            domain=domain,
            target=target,
            ask_message=ask_message,
            mode=mode_norm,
            auto_approve=auto_approve,
            permission_manager=permission_manager,
        )

    system_rules = (
        "You are operating in AUTO MODE.\n"
        "You MUST respond with a single JSON object of the form {\"actions\": [...]} and nothing else.\n"
        "Each action is an object with a 'type'. Allowed types: mkdir, read_file, read_dir, write_file, gen_file, run, done.\n"
        "All file paths must be relative to the project root unless explicitly told otherwise.\n"
        "For gen_file you must include: path, instruction. Optional: file_type, overwrite, max_attempts.\n"
        "For write_file you must include: path, content, overwrite.\n"
        "For run you must include: command, working_dir(optional, default project root).\n"
        "When finished, return one action: {\"type\": \"done\"}.\n"
    )

    if mode_norm == "plan":
        system_rules += (
            "PLAN MODE: Focus on writing a plan only.\n"
            "- Do NOT run commands.\n"
            "- Only write plan files under .pycc/: plan.md and tasks.md.\n"
        )

    def _execute_action(action: dict) -> dict:
        at = str(action.get("type", "")).strip().lower()

        allowed = allowed_action_types.get(mode_norm, allowed_action_types["default"])
        if at not in allowed:
            return {"type": at, "ok": False, "error": f"action not allowed in mode {mode_norm}"}

        if at == "done":
            return {"type": "done", "ok": True}

        if at == "mkdir":
            path_arg = str(action.get("path", "")).strip()
            if not path_arg:
                raise ValueError("mkdir requires path")
            if not _check(PermissionDomain.FILE_WRITE, path_arg, f"mkdir: {path_arg}"):
                return {"type": "mkdir", "path": path_arg, "ok": False, "error": "permission denied"}
            target = _resolve_under_root(project_root, path_arg)
            Path(target).mkdir(parents=True, exist_ok=True)
            return {"type": "mkdir", "path": path_arg, "ok": True}

        if at == "read_file":
            path_arg = str(action.get("path", "")).strip()
            if not path_arg:
                raise ValueError("read_file requires path")
            if not _check(PermissionDomain.FILE_READ, path_arg, f"read-file: {path_arg}"):
                return {"type": "read_file", "path": path_arg, "ok": False, "error": "permission denied"}
            target = _resolve_under_root(project_root, path_arg)
            p = Path(target)
            if not p.exists() or not p.is_file():
                return {"type": "read_file", "path": path_arg, "ok": False, "error": "file not found"}
            return {"type": "read_file", "path": path_arg, "ok": True, "content": p.read_text(encoding="utf-8")}

        if at == "read_dir":
            path_arg = str(action.get("path", "")).strip()
            if not path_arg:
                raise ValueError("read_dir requires path")
            recursive = bool(action.get("recursive", True))
            max_entries = int(action.get("max_entries", 200))
            if max_entries < 1:
                max_entries = 1
            if not _check(PermissionDomain.FILE_READ, path_arg, f"read-dir: {path_arg}"):
                return {"type": "read_dir", "path": path_arg, "ok": False, "error": "permission denied"}
            target = _resolve_under_root(project_root, path_arg)
            listing = _format_dir_listing(target, recursive=recursive, max_entries=max_entries)
            return {"type": "read_dir", "path": path_arg, "ok": True, "listing": listing}

        if at == "write_file":
            path_arg = str(action.get("path", "")).strip()
            content = action.get("content", "")
            overwrite = bool(action.get("overwrite", True))
            if not path_arg:
                raise ValueError("write_file requires path")
            if not isinstance(content, str):
                raise ValueError("write_file content must be string")
            if mode_norm == "plan":
                norm = path_arg.replace("\\", "/")
                if norm not in allowed_write_paths["plan"]:
                    return {"type": "write_file", "path": path_arg, "ok": False, "error": "plan mode: write restricted"}
            if not _check(PermissionDomain.FILE_WRITE, path_arg, f"write-file: {path_arg}"):
                return {"type": "write_file", "path": path_arg, "ok": False, "error": "permission denied"}
            target = _resolve_under_root(project_root, path_arg)
            safe_write_text(target, content, overwrite=overwrite)
            return {"type": "write_file", "path": path_arg, "ok": True}

        if at == "gen_file":
            path_arg = str(action.get("path", "")).strip()
            instruction = str(action.get("instruction", "")).strip()
            if not path_arg:
                raise ValueError("gen_file requires path")
            if not instruction:
                raise ValueError("gen_file requires instruction")
            file_type = action.get("file_type")
            overwrite = bool(action.get("overwrite", False))
            max_attempts = int(action.get("max_attempts", 3))
            if max_attempts < 1:
                max_attempts = 1
            if mode_norm == "plan":
                norm = path_arg.replace("\\", "/")
                if norm not in allowed_write_paths["plan"]:
                    return {"type": "gen_file", "path": path_arg, "ok": False, "error": "plan mode: write restricted"}
            if not _check(PermissionDomain.FILE_WRITE, path_arg, f"gen-file: {path_arg}"):
                return {"type": "gen_file", "path": path_arg, "ok": False, "error": "permission denied"}
            target = _resolve_under_root(project_root, path_arg)
            ft = detect_file_type(target, file_type)

            def _gen(prompt: str) -> str:
                return agent.process(prompt).content

            content2, result = generate_validated(
                generate_fn=_gen,
                file_type=ft,
                target_path=target,
                instruction=instruction,
                max_attempts=max_attempts,
            )
            if not result.ok:
                return {"type": "gen_file", "path": path_arg, "ok": False, "error": result.error}
            safe_write_text(target, content2, overwrite=overwrite)
            return {"type": "gen_file", "path": path_arg, "ok": True}

        if at == "run":
            command = str(action.get("command", "")).strip()
            if not command:
                raise ValueError("run requires command")
            working_dir = str(action.get("working_dir", "")).strip() or project_root
            working_dir_resolved = _resolve_under_root(project_root, working_dir) if working_dir != project_root else project_root
            if not _check(PermissionDomain.COMMAND, command, f"Run command: {command}"):
                return {"type": "run", "command": command, "ok": False, "error": "permission denied"}

            cmd_parts = shlex.split(command, posix=False)
            if not cmd_parts:
                raise ValueError("run command parsed empty")
            res = executor.execute(*cmd_parts, working_dir=working_dir_resolved)
            return {
                "type": "run",
                "command": command,
                "ok": bool(res.success),
                "return_code": res.return_code,
                "stdout": res.stdout,
                "stderr": res.stderr,
                "timed_out": res.timed_out,
            }

        raise ValueError(f"unknown action type: {at}")

    tool_context = ""

    for step in range(max_steps):
        prompt = user_input
        if tool_context:
            prompt = tool_context + "\n\n" + prompt
        prompt = system_rules + "\n" + prompt

        with console.status("[dark_orange]Puzzling...[/] [bright_black](thinking)[/]", spinner="dots"):
            turn = agent.process(prompt)
        try:
            _LOGGER.debug("auto_model_output step=%s content_prefix=%s", step, (turn.content[:1200] if getattr(turn, "content", None) else ""))
        except Exception:
            pass

        try:
            actions = _parse_auto_actions(turn.content)
        except Exception as e:
            _LOGGER.exception("auto_parse_failed step=%s", step)
            console.print(Text(f"Error: auto output parse failed: {e}", style="red"))
            console.print(Text(turn.content, style="dim"))
            return

        results = []
        done = False
        for act in actions:
            try:
                r = _execute_action(act)
            except Exception as e:
                r = {"type": str(act.get("type", "")), "ok": False, "error": str(e)}
            results.append(r)
            if r.get("type") == "done":
                done = True

        _render_action_results(console, results)

        tool_context = "--- Tool Results ---\n" + _format_action_results(results) + "\n--- End Tool Results ---"

        if done:
            console.print(Text("DONE", style="green"))
            return

        time.sleep(0.05)


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
