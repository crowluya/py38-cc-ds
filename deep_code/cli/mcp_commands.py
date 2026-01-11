"""
MCP CLI Commands for DeepCode

Python 3.8.10 compatible
Implements MCP-016, MCP-017, MCP-018: CLI commands for MCP server management.
"""

import json
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from deep_code.extensions.mcp.config import (
    MCPConfig,
    MCPServerConfig,
    ConfigScope,
    load_config_file,
    save_config_file,
    get_default_config_paths,
    load_scoped_config,
    add_server_to_scope,
    remove_server_from_scope,
    list_servers_by_scope,
)


console = Console()


@click.group(name="mcp")
def mcp_group():
    """
    Manage MCP (Model Context Protocol) servers.

    MCP servers provide tools, resources, and prompts that extend
    DeepCode's capabilities.
    """
    pass


# MCP-016: deepcode mcp add command

@mcp_group.command(name="add")
@click.argument("name")
@click.option(
    "-t", "--transport",
    type=click.Choice(["stdio", "http", "sse"], case_sensitive=False),
    default="stdio",
    help="Transport type (default: stdio)",
)
@click.option(
    "-c", "--command",
    help="Command to run (for stdio transport)",
)
@click.option(
    "-u", "--url",
    help="Server URL (for http/sse transport)",
)
@click.option(
    "-e", "--env",
    multiple=True,
    help="Environment variable (KEY=VALUE format, can be repeated)",
)
@click.option(
    "-H", "--header",
    multiple=True,
    help="HTTP header (KEY=VALUE format, can be repeated)",
)
@click.option(
    "-s", "--scope",
    type=click.Choice(["user", "project", "local"], case_sensitive=False),
    default="project",
    help="Config scope (default: project)",
)
@click.argument("args", nargs=-1)
def add_command(
    name: str,
    transport: str,
    command: Optional[str],
    url: Optional[str],
    env: tuple,
    header: tuple,
    scope: str,
    args: tuple,
):
    """
    Add an MCP server configuration.

    NAME is the server name (e.g., 'filesystem', 'github').

    For stdio transport, provide command and optional args:

        deepcode mcp add fs --command npx -- -y @modelcontextprotocol/server-filesystem /path

    For http/sse transport, provide URL:

        deepcode mcp add github --transport http --url https://api.github.com/mcp
    """
    transport = transport.lower()

    # Validate transport-specific options
    if transport == "stdio":
        if not command:
            console.print("[red]Error:[/red] --command is required for stdio transport")
            raise SystemExit(1)
    else:
        if not url:
            console.print(f"[red]Error:[/red] --url is required for {transport} transport")
            raise SystemExit(1)

    # Parse environment variables
    env_dict = {}
    for e in env:
        if "=" in e:
            key, value = e.split("=", 1)
            env_dict[key] = value
        else:
            console.print(f"[yellow]Warning:[/yellow] Invalid env format: {e} (expected KEY=VALUE)")

    # Parse headers
    headers_dict = {}
    for h in header:
        if "=" in h:
            key, value = h.split("=", 1)
            headers_dict[key] = value
        else:
            console.print(f"[yellow]Warning:[/yellow] Invalid header format: {h} (expected KEY=VALUE)")

    # Create server config
    server_config = MCPServerConfig(
        name=name,
        command=command,
        args=list(args) if args else None,
        env=env_dict if env_dict else None,
        transport_type=transport,
        url=url,
        headers=headers_dict if headers_dict else None,
    )

    # Add to config
    try:
        add_server_to_scope(server_config, scope)
        console.print(f"[green]Added MCP server '{name}' to {scope} config[/green]")

        # Show config location
        paths = get_default_config_paths()
        console.print(f"Config file: {paths[scope]}")

    except Exception as e:
        console.print(f"[red]Error adding server:[/red] {e}")
        raise SystemExit(1)


# MCP-017: deepcode mcp list/get/remove commands

@mcp_group.command(name="list")
@click.option(
    "-s", "--scope",
    type=click.Choice(["user", "project", "local", "all"], case_sensitive=False),
    default="all",
    help="Config scope to list (default: all)",
)
@click.option(
    "--json", "json_output",
    is_flag=True,
    help="Output as JSON",
)
def list_command(scope: str, json_output: bool):
    """
    List configured MCP servers.
    """
    if scope == "all":
        servers_by_scope = list_servers_by_scope()
    else:
        servers_by_scope = {scope: list_servers_by_scope().get(scope, [])}

    if json_output:
        output = {}
        for s, servers in servers_by_scope.items():
            output[s] = servers
        console.print(json.dumps(output, indent=2))
        return

    # Create table
    table = Table(title="MCP Servers")
    table.add_column("Name", style="cyan")
    table.add_column("Scope", style="green")
    table.add_column("Transport", style="yellow")

    # Load full config for details
    config = load_scoped_config()

    for scope_name, server_names in servers_by_scope.items():
        for name in server_names:
            server = config.get_server(name)
            transport = server.transport_type if server else "unknown"
            table.add_row(name, scope_name, transport)

    if table.row_count == 0:
        console.print("[dim]No MCP servers configured[/dim]")
    else:
        console.print(table)


@mcp_group.command(name="get")
@click.argument("name")
@click.option(
    "--json", "json_output",
    is_flag=True,
    help="Output as JSON",
)
def get_command(name: str, json_output: bool):
    """
    Get details of an MCP server.

    NAME is the server name.
    """
    config = load_scoped_config()
    server = config.get_server(name)

    if not server:
        console.print(f"[red]Error:[/red] Server '{name}' not found")
        raise SystemExit(1)

    if json_output:
        console.print(json.dumps(server.to_dict(), indent=2))
        return

    # Display details
    console.print(f"\n[bold cyan]{name}[/bold cyan]")
    console.print(f"  Transport: {server.transport_type}")

    if server.command:
        console.print(f"  Command: {server.command}")
    if server.args:
        console.print(f"  Args: {' '.join(server.args)}")
    if server.url:
        console.print(f"  URL: {server.url}")
    if server.env:
        console.print("  Environment:")
        for key, value in server.env.items():
            # Mask sensitive values
            if any(s in key.lower() for s in ["key", "token", "secret", "password"]):
                display_value = value[:4] + "****" if len(value) > 4 else "****"
            else:
                display_value = value
            console.print(f"    {key}={display_value}")
    if server.headers:
        console.print("  Headers:")
        for key, value in server.headers.items():
            # Mask authorization headers
            if "auth" in key.lower():
                display_value = value[:10] + "****" if len(value) > 10 else "****"
            else:
                display_value = value
            console.print(f"    {key}: {display_value}")

    console.print()


@mcp_group.command(name="remove")
@click.argument("name")
@click.option(
    "-s", "--scope",
    type=click.Choice(["user", "project", "local"], case_sensitive=False),
    help="Config scope to remove from (auto-detected if not specified)",
)
@click.option(
    "-y", "--yes",
    is_flag=True,
    help="Skip confirmation",
)
def remove_command(name: str, scope: Optional[str], yes: bool):
    """
    Remove an MCP server configuration.

    NAME is the server name.
    """
    # Find scope if not specified
    if not scope:
        servers_by_scope = list_servers_by_scope()
        found_scopes = [s for s, servers in servers_by_scope.items() if name in servers]

        if not found_scopes:
            console.print(f"[red]Error:[/red] Server '{name}' not found in any scope")
            raise SystemExit(1)

        if len(found_scopes) > 1:
            console.print(f"[yellow]Server '{name}' found in multiple scopes: {', '.join(found_scopes)}[/yellow]")
            console.print("Please specify --scope to remove from a specific scope")
            raise SystemExit(1)

        scope = found_scopes[0]

    # Confirm removal
    if not yes:
        if not click.confirm(f"Remove server '{name}' from {scope} config?"):
            console.print("Cancelled")
            return

    # Remove
    if remove_server_from_scope(name, scope):
        console.print(f"[green]Removed server '{name}' from {scope} config[/green]")
    else:
        console.print(f"[red]Error:[/red] Failed to remove server '{name}'")
        raise SystemExit(1)


# MCP-018: Interactive /mcp command support

def handle_mcp_slash_command(args: str, manager=None) -> str:
    """
    Handle /mcp interactive command.

    Args:
        args: Command arguments
        manager: Optional MCPManager instance

    Returns:
        Response string
    """
    parts = args.strip().split()
    subcommand = parts[0] if parts else "status"

    if subcommand == "status":
        return _mcp_status(manager)
    elif subcommand == "list":
        return _mcp_list()
    elif subcommand == "connect" and len(parts) > 1:
        return _mcp_connect(parts[1], manager)
    elif subcommand == "disconnect" and len(parts) > 1:
        return _mcp_disconnect(parts[1], manager)
    elif subcommand == "tools":
        server = parts[1] if len(parts) > 1 else None
        return _mcp_tools(server, manager)
    elif subcommand == "help":
        return _mcp_help()
    else:
        return _mcp_help()


def _mcp_status(manager) -> str:
    """Show MCP server status."""
    lines = ["MCP Server Status:", ""]

    if manager is None:
        # Load config and show configured servers
        config = load_scoped_config()
        if len(config) == 0:
            lines.append("No MCP servers configured.")
            lines.append("Use 'deepcode mcp add' to add servers.")
        else:
            for name in config.list_servers():
                server = config.get_server(name)
                lines.append(f"  {name}: configured ({server.transport_type})")
    else:
        # Show live status
        all_status = manager.get_all_status()
        if not all_status:
            lines.append("No MCP servers configured.")
        else:
            for name, status in all_status.items():
                status_str = status.value
                if status.value == "connected":
                    status_str = f"[green]{status_str}[/green]"
                elif status.value == "error":
                    status_str = f"[red]{status_str}[/red]"
                lines.append(f"  {name}: {status_str}")

    return "\n".join(lines)


def _mcp_list() -> str:
    """List configured servers."""
    config = load_scoped_config()
    if len(config) == 0:
        return "No MCP servers configured."

    lines = ["Configured MCP Servers:", ""]
    for name in config.list_servers():
        server = config.get_server(name)
        lines.append(f"  {name} ({server.transport_type})")

    return "\n".join(lines)


def _mcp_connect(name: str, manager) -> str:
    """Connect to a server."""
    if manager is None:
        return "MCP manager not available. Start a chat session first."

    if manager.connect(name):
        return f"Connected to {name}"
    else:
        info = manager.get_server_info(name)
        error = info.get("error_message", "Unknown error") if info else "Server not found"
        return f"Failed to connect to {name}: {error}"


def _mcp_disconnect(name: str, manager) -> str:
    """Disconnect from a server."""
    if manager is None:
        return "MCP manager not available."

    if manager.disconnect(name):
        return f"Disconnected from {name}"
    else:
        return f"Failed to disconnect from {name}"


def _mcp_tools(server: Optional[str], manager) -> str:
    """List available tools."""
    if manager is None:
        return "MCP manager not available. Start a chat session first."

    if server:
        tools = manager.get_client(server)
        if not tools:
            return f"Server '{server}' not connected."
        try:
            tool_list = tools.list_tools()
            if not tool_list:
                return f"No tools available from {server}"
            lines = [f"Tools from {server}:", ""]
            for tool in tool_list:
                lines.append(f"  {tool.get('name', 'unknown')}: {tool.get('description', '')[:60]}")
            return "\n".join(lines)
        except Exception as e:
            return f"Error listing tools: {e}"
    else:
        all_tools = manager.get_all_tools()
        if not all_tools:
            return "No tools available. Connect to MCP servers first."
        lines = ["Available MCP Tools:", ""]
        for tool in all_tools:
            server_name = tool.get("_server", "unknown")
            lines.append(f"  [{server_name}] {tool.get('name', 'unknown')}")
        return "\n".join(lines)


def _mcp_help() -> str:
    """Show help for /mcp command."""
    return """MCP Commands:

  /mcp status      - Show server connection status
  /mcp list        - List configured servers
  /mcp connect <n> - Connect to server
  /mcp disconnect <n> - Disconnect from server
  /mcp tools [server] - List available tools
  /mcp help        - Show this help

CLI Commands:

  deepcode mcp add <name> [options] - Add server
  deepcode mcp list                 - List servers
  deepcode mcp get <name>           - Show server details
  deepcode mcp remove <name>        - Remove server
"""
