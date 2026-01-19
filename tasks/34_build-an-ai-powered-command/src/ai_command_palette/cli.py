"""Main CLI entry point for AI Command Palette."""

import sys
from pathlib import Path
from typing import Optional

import click

from ai_command_palette.core.registry import CommandRegistry
from ai_command_palette.core.tracker import UsageTracker
from ai_command_palette.integrations.notes import NotesIntegration
from ai_command_palette.integrations.shell import ShellIntegration
from ai_command_palette.storage.config import Config
from ai_command_palette.storage.database import Database
from ai_command_palette.ui.palette import CommandPaletteApp


@click.group()
@click.version_option(version="0.1.0")
@click.pass_context
def cli(ctx):
    """AI Command Palette - Intelligent command completion and workflow automation."""
    # Initialize configuration
    config = Config()
    config.ensure_directories()

    # Initialize database
    db = Database(config)

    # Store in context for subcommands
    ctx.ensure_object(dict)
    ctx.obj["config"] = config
    ctx.obj["db"] = db


@cli.command()
@click.option("--mini", is_flag=True, help="Launch in mini mode")
@click.pass_context
def launch(ctx, mini):
    """Launch the command palette UI."""
    config = ctx.obj["config"]

    if mini:
        # Launch mini palette
        from ai_command_palette.ui.palette import MiniCommandPaletteApp

        app = MiniCommandPaletteApp(config)
    else:
        # Launch full palette
        app = CommandPaletteApp(config)

    app.run()


@cli.command()
@click.argument("command")
@click.argument("args", nargs=-1)
@click.option("--type", "command_type", default="system", help="Command type")
@click.option("--dir", "working_dir", help="Working directory")
@click.pass_context
def execute(ctx, command, args, command_type, working_dir):
    """Execute a command and track it."""
    db = ctx.obj["db"]
    tracker = UsageTracker(db)

    # Get working directory
    if not working_dir:
        working_dir = str(Path.cwd())

    # Build full command string
    full_command = command
    if args:
        full_command = f"{command} {' '.join(args)}"

    # Track execution
    import subprocess
    import time

    start_time = time.time()

    try:
        result = subprocess.run(full_command, shell=True)
        exit_code = result.returncode
    except Exception as e:
        exit_code = 1
        click.echo(f"Error executing command: {e}", err=True)

    duration_ms = int((time.time() - start_time) * 1000)

    # Track the command
    tracker.track_command(
        command=command,
        command_type=command_type,
        args=" ".join(args) if args else None,
        working_dir=working_dir,
        exit_code=exit_code,
        duration_ms=duration_ms,
    )

    sys.exit(exit_code)


@cli.command()
@click.argument("query")
@click.option("--limit", default=20, help="Maximum results")
@click.option("--type", "command_type", help="Filter by command type")
@click.pass_context
def search(ctx, query, limit, command_type):
    """Search for commands."""
    registry = CommandRegistry()
    registry.initialize()

    # Search commands
    results = registry.search(query)

    # Filter by type if specified
    if command_type:
        from ai_command_palette.core.registry import CommandType

        cmd_type = CommandType(command_type)
        results = [r for r in results if r.command_type == cmd_type]

    # Limit results
    results = results[:limit]

    # Display results
    for cmd in results:
        click.echo(f"{cmd.name} - {cmd.description or 'No description'}")


@cli.command()
@click.option("--days", default=30, help="Number of days to analyze")
@click.option("--limit", default=20, help="Maximum results")
@click.pass_context
def stats(ctx, days, limit):
    """Show usage statistics."""
    db = ctx.obj["db"]

    click.echo(f"Usage Statistics (last {days} days)")
    click.echo("=" * 50)

    # Get overall stats
    overall = db.get_usage_stats()
    click.echo(f"\nTotal Commands: {overall['total_commands']}")
    click.echo(f"Total Files: {overall['total_files']}")

    click.echo("\nCommand Types:")
    for cmd_type, count in overall.get("command_types", {}).items():
        click.echo(f"  {cmd_type}: {count}")

    # Get most frequent commands
    click.echo(f"\nTop {limit} Commands:")
    tracker = UsageTracker(db)
    frequent = tracker.get_frequent_commands(limit=limit, days=days)

    for cmd, count in frequent:
        click.echo(f"  {cmd}: {count}")


@cli.command()
@click.option("--type", "shell_type", help="Shell type (bash, zsh, fish)")
@click.option("--install", is_flag=True, help="Install integration")
@click.pass_context
def shell(ctx, shell_type, install):
    """Generate shell integration scripts."""
    integration = ShellIntegration(ctx.obj["config"])

    # Detect shell if not specified
    if not shell_type:
        shell_type = integration.detect_shell_type()

    # Generate script
    if shell_type == "bash":
        script = integration.generate_bash_integration()
    elif shell_type == "zsh":
        script = integration.generate_zsh_integration()
    elif shell_type == "fish":
        script = integration.generate_fish_integration()
    else:
        click.echo(f"Unknown shell type: {shell_type}", err=True)
        sys.exit(1)

    if install:
        # Install integration
        if shell_type == "bash":
            success = integration.install_bash_integration()
        elif shell_type == "zsh":
            success = integration.install_zsh_integration()
        else:
            click.echo(f"Auto-install not supported for {shell_type}", err=True)
            sys.exit(1)

        if success:
            click.echo(f"✓ Installed {shell_type} integration")
            click.echo(f"  Please restart your shell or run: source ~/.{shell_type}rc")
        else:
            click.echo(f"✗ Failed to install {shell_type} integration", err=True)
            sys.exit(1)
    else:
        # Print script to stdout
        click.echo(script)
        click.echo(
            f"\n# Add this to your ~/{shell_type}rc file, "
            f"or run: aicp shell --type {shell_type} --install"
        )


@cli.command()
@click.pass_context
def init(ctx):
    """Initialize AI Command Palette configuration."""
    config = ctx.obj["config"]
    db = ctx.obj["db"]

    # Ensure directories exist
    config.ensure_directories()

    # Save default configuration
    config.save()

    # Initialize database
    # (Already done by Database constructor)

    # Register default commands
    registry = CommandRegistry()
    registry.initialize()

    click.echo("✓ AI Command Palette initialized successfully")
    click.echo(f"  Config: {config.config_dir}")
    click.echo(f"  Data: {config.data_dir}")


@cli.command()
@click.pass_context
def config_cmd(ctx):
    """Show current configuration."""
    config = ctx.obj["config"]

    click.echo("AI Command Palette Configuration")
    click.echo("=" * 50)

    import json

    click.echo(json.dumps(config.model_dump(), indent=2))


def main():
    """Main entry point."""
    # Make cli available for direct execution
    cli(obj={})


if __name__ == "__main__":
    main()
