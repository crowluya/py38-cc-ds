"""
Command Executor - Shell command execution

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)

Executes shell commands with:
- Windows 7: PowerShell (powershell.exe -Command)
- Unix: bash (/bin/bash -c)
- UTF-8 encoding handling
- Working directory support
- Environment variable support
- Timeout support
"""

import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class CommandResult:
    """Result of command execution."""

    command: str
    return_code: int
    stdout: str
    stderr: str
    timed_out: bool = False

    @property
    def success(self) -> bool:
        """Check if command executed successfully."""
        return self.return_code == 0 and not self.timed_out

    def combined_output(self) -> str:
        """
        Get combined stdout and stderr.

        Returns:
            Combined output string
        """
        parts = []
        if self.stdout:
            parts.append(self.stdout)
        if self.stderr:
            parts.append(self.stderr)
        return "\n".join(parts)

    def __str__(self) -> str:
        """String representation."""
        status = "success" if self.success else "failed"
        return f"CommandResult({self.command}, return_code={self.return_code}, {status})"


class CommandExecutor:
    """
    Execute shell commands with proper platform handling.

    Platform support:
    - Windows 7: PowerShell (powershell.exe -Command)
    - Windows 10+: PowerShell Core (pwsh) or Windows PowerShell
    - Unix/Linux/macOS: bash (or sh as fallback)
    """

    def __init__(self, default_timeout: int = 30) -> None:
        """
        Initialize command executor.

        Args:
            default_timeout: Default timeout in seconds
        """
        self._default_timeout = default_timeout

    def execute(
        self,
        *args: str,
        working_dir: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        capture: bool = True,
    ) -> CommandResult:
        """
        Execute a command.

        Args:
            *args: Command arguments (first arg is the command)
            working_dir: Working directory for command execution
            env: Environment variables (overrides default env)
            timeout: Timeout in seconds (None for no timeout)
            capture: Whether to capture output (False to output directly)

        Returns:
            CommandResult with execution details
        """
        if not args:
            raise ValueError("No command specified")

        command = args[0]
        cmd_args = args[1:] if len(args) > 1 else []

        # Build the shell command
        shell_cmd, shell_args = self._build_shell_command(command, cmd_args)

        # Prepare environment
        process_env = os.environ.copy()
        if env:
            process_env.update(env)

        # Prepare working directory
        cwd = working_dir or os.getcwd()

        # Execute command
        try:
            proc = subprocess.Popen(
                shell_args,
                stdout=subprocess.PIPE if capture else None,
                stderr=subprocess.PIPE if capture else None,
                cwd=cwd,
                env=process_env,
                universal_newlines=False,  # Use bytes for encoding control
            )

            # Wait for completion with timeout
            timeout_val = timeout if timeout is not None else self._default_timeout

            try:
                stdout_bytes, stderr_bytes = proc.communicate(timeout=timeout_val)
                timed_out = False
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout_bytes, stderr_bytes = proc.communicate()
                timed_out = True

            # Decode output with UTF-8, fallback to latin-1
            stdout = self._decode_output(stdout_bytes)
            stderr = self._decode_output(stderr_bytes)

            return CommandResult(
                command=command,
                return_code=proc.returncode,
                stdout=stdout,
                stderr=stderr,
                timed_out=timed_out,
            )

        except FileNotFoundError:
            # Shell executable not found
            return CommandResult(
                command=command,
                return_code=127,
                stdout="",
                stderr=f"Shell not found: {shell_cmd}",
                timed_out=False,
            )
        except OSError as e:
            return CommandResult(
                command=command,
                return_code=1,
                stdout="",
                stderr=str(e),
                timed_out=False,
            )

    def _build_shell_command(self, command: str, args: List[str]) -> Tuple[str, List[str]]:
        """
        Build shell command with proper platform handling.

        Args:
            command: Base command or full command string (if no args)
            args: Command arguments

        Returns:
            Tuple of (shell_executable, full_command_args)
        """
        shell_cmd, shell_prefix = self._get_shell_command()

        # If no additional args, treat command as the full command string
        # This allows `execute("echo hello")` to work as expected
        if not args:
            full_command = command
        else:
            # Build command with properly quoted arguments
            quoted_args = [shlex.quote(arg) for arg in args]
            full_command = f"{shlex.quote(command)} {' '.join(quoted_args)}"

        return shell_cmd, shell_prefix + [full_command]

    def _get_shell_command(self) -> Tuple[str, List[str]]:
        """
        Get the appropriate shell command for the platform.

        Returns:
            Tuple of (shell_executable, shell_prefix_args)
        """
        if sys.platform == "win32":
            # Windows: try PowerShell Core first, then Windows PowerShell
            # Check for pwsh (PowerShell Core)
            try:
                subprocess.run(
                    ["pwsh", "-Version"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return "pwsh", ["pwsh", "-NoProfile", "-Command"]
            except (OSError, FileNotFoundError):
                pass

            # Fall back to Windows PowerShell
            return "powershell", ["powershell", "-NoProfile", "-Command"]
        else:
            # Unix/Linux/macOS: prefer bash, fall back to sh
            try:
                subprocess.run(
                    ["bash", "--version"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return "bash", ["bash", "-c"]
            except (OSError, FileNotFoundError):
                pass

            # Fall back to sh
            return "sh", ["sh", "-c"]

    def _decode_output(self, output: bytes) -> str:
        """
        Decode command output with proper encoding handling.

        Args:
            output: Bytes output from command

        Returns:
            Decoded string
        """
        if not output:
            return ""

        # Try UTF-8 first
        try:
            return output.decode("utf-8")
        except UnicodeDecodeError:
            pass

        # Try latin-1 as fallback
        try:
            return output.decode("latin-1")
        except UnicodeDecodeError:
            # Last resort: replace errors
            return output.decode("utf-8", errors="replace")


# Convenience function
def execute_command(
    *args: str,
    working_dir: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    timeout: Optional[int] = None,
) -> CommandResult:
    """
    Execute a command with default executor.

    Args:
        *args: Command arguments
        working_dir: Working directory
        env: Environment variables
        timeout: Timeout in seconds

    Returns:
        CommandResult with execution details
    """
    executor = CommandExecutor()
    return executor.execute(*args, working_dir=working_dir, env=env, timeout=timeout)
