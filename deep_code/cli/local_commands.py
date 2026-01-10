"""
Local command handling for DeepCode

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)
"""

import shlex
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console
from rich.text import Text

from deep_code.cli.filegen import detect_file_type, generate_validated, safe_write_text
from deep_code.cli.utils import resolve_under_root, format_dir_listing

if TYPE_CHECKING:
    from deep_code.core.agent import Agent


def handle_local_command(agent: "Agent", user_input: str, project_root: str) -> None:
    """
    Handle local filesystem commands.

    Supported commands:
    - /help, /? - Show help
    - /mkdir PATH - Create directory
    - /read-file PATH - Read file contents
    - /read-dir PATH [--recursive/--no-recursive] [--max N] - List directory
    - /write-file PATH -- CONTENT - Write file
    - /gen-file PATH [--type T] [--overwrite] [--max-attempts N] -- INSTRUCTION - Generate file

    Args:
        agent: Agent instance for file generation
        user_input: User input string (e.g., "/mkdir foo")
        project_root: Project root directory path
    """
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
            _handle_mkdir(console, args, project_root)
            return

        if cmd == "read-file":
            _handle_read_file(console, args, project_root)
            return

        if cmd == "read-dir":
            _handle_read_dir(console, args, project_root)
            return

        if cmd == "write-file":
            _handle_write_file(console, args, project_root)
            return

        if cmd == "gen-file":
            _handle_gen_file(console, args, project_root, agent)
            return

        console.print(Text(f"Unknown local command: /{cmd} (try /help)", style="yellow"))
    except Exception as e:
        console.print(Text(f"Error: {e}", style="red"))


def _handle_mkdir(console: Console, args: list, project_root: str) -> None:
    """Handle /mkdir command."""
    if not args:
        raise ValueError("mkdir requires PATH")
    target = resolve_under_root(project_root, args[0])
    Path(target).mkdir(parents=True, exist_ok=True)
    console.print(Text(f"OK: created {args[0]}", style="green"))


def _handle_read_file(console: Console, args: list, project_root: str) -> None:
    """Handle /read-file command."""
    if not args:
        raise ValueError("read-file requires PATH")
    target = resolve_under_root(project_root, args[0])
    p = Path(target)
    if not p.exists() or not p.is_file():
        raise ValueError(f"file not found: {args[0]}")
    content = p.read_text(encoding="utf-8")
    console.print(Text(content))


def _handle_read_dir(console: Console, args: list, project_root: str) -> None:
    """Handle /read-dir command."""
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
    target = resolve_under_root(project_root, path_arg)
    listing = format_dir_listing(target, recursive=recursive, max_entries=max_entries)
    console.print(Text(listing))


def _handle_write_file(console: Console, args: list, project_root: str) -> None:
    """Handle /write-file command."""
    if not args:
        raise ValueError("write-file requires PATH")
    if "--" not in args:
        raise ValueError("write-file requires -- CONTENT")
    sep = args.index("--")
    path_arg = args[0]
    content = " ".join(args[sep + 1:])
    target = resolve_under_root(project_root, path_arg)
    safe_write_text(target, content + "\n", overwrite=True)
    console.print(Text(f"OK: wrote {path_arg}", style="green"))


def _handle_gen_file(console: Console, args: list, project_root: str, agent: "Agent") -> None:
    """Handle /gen-file command."""
    if not args:
        raise ValueError("gen-file requires PATH")
    if "--" not in args:
        raise ValueError("gen-file requires -- INSTRUCTION")
    sep = args.index("--")
    pre = args[:sep]
    instruction = " ".join(args[sep + 1:]).strip()
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

    target = resolve_under_root(project_root, path_arg)
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
