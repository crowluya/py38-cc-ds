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
- Permission checking (T071)
- Background execution (CMD-015)
- Streaming output (CMD-016)
"""

import os
import shlex
import subprocess
import sys
import threading
import queue
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

# Optional type hints for permission system
try:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from deep_code.security.permissions import (
            PermissionManager,
            PermissionDomain,
            ApprovalCallback,
        )
except ImportError:
    pass


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


@dataclass
class BackgroundCommand:
    """A command running in the background (CMD-015)."""

    command: str
    process: subprocess.Popen
    thread: threading.Thread
    result_queue: queue.Queue
    started_at: float = field(default_factory=lambda: __import__("time").time())
    completed: bool = False
    result: Optional[CommandResult] = None

    def is_running(self) -> bool:
        """Check if command is still running."""
        return self.process.poll() is None

    def get_result(self, timeout: Optional[float] = None) -> Optional[CommandResult]:
        """Get result if available."""
        if self.result is not None:
            return self.result
        try:
            self.result = self.result_queue.get(block=True, timeout=timeout)
            self.completed = True
            return self.result
        except queue.Empty:
            return None


class CommandExecutor:
    """
    Execute shell commands with proper platform handling.

    Platform support:
    - Windows 7: PowerShell (powershell.exe -Command)
    - Windows 10+: PowerShell Core (pwsh) or Windows PowerShell
    - Unix/Linux/macOS: bash (or sh as fallback)

    T071: Optional permission checking for command execution.
    """

    def __init__(
        self,
        default_timeout: int = 30,
        permission_manager: Optional[Any] = None,
        approval_callback: Optional[Callable] = None,
    ) -> None:
        """
        Initialize command executor.

        Args:
            default_timeout: Default timeout in seconds
            permission_manager: Optional PermissionManager for checking command permissions
            approval_callback: Optional callback for ASK permissions
        """
        self._default_timeout = default_timeout
        self._permission_manager = permission_manager
        self._approval_callback = approval_callback

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

        # T071: Check permissions if permission manager is set
        if self._permission_manager is not None:
            if not self._check_command_permission(command, cmd_args):
                # Permission denied
                return CommandResult(
                    command=command,
                    return_code=1,
                    stdout="",
                    stderr="Permission denied: Command execution not permitted",
                    timed_out=False,
                )

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

    def _check_command_permission(
        self,
        command: str,
        cmd_args: List[str],
    ) -> bool:
        """
        Check if command execution is permitted.

        Args:
            command: Command to check
            cmd_args: Command arguments

        Returns:
            True if permitted, False otherwise
        """
        # Lazy import to avoid circular dependency
        from deep_code.security.permissions import (
            PermissionApprover,
            PermissionDomain,
        )

        # Build full command string for permission check
        if cmd_args:
            full_command = f"{command} {' '.join(cmd_args)}"
        else:
            full_command = command

        # Create approver with callback if provided
        approver = PermissionApprover(
            self._permission_manager,
            approval_callback=self._approval_callback,
        )

        # Check permission
        permission = approver.request_permission(
            domain=PermissionDomain.COMMAND,
            target=full_command,
        )

        return permission.granted

    def _build_shell_command(self, command: str, args: List[str]) -> Tuple[str, List[str]]:
        """
        Build shell command with proper platform handling.

        Args:
            command: Base command or full command string (if no args)
            args: Command arguments

        Returns:
            Tuple of (shell_executable, full_command_args)
        """
        # NOTE:
        # On Windows, we execute commands via cmd.exe instead of PowerShell.
        # Reasons:
        # - cmd.exe expands %ENV_VAR% (tests rely on this)
        # - Passing args like: python.exe -c "print('x')" works reliably
        # - PowerShell has different quoting and env expansion semantics
        if sys.platform == "win32":
            shell_cmd = "cmd"
            shell_prefix = ["cmd", "/d", "/s", "/c"]

            if not args:
                full_command = command
            else:
                full_command = subprocess.list2cmdline([command, *args])

            return shell_cmd, shell_prefix + [full_command]

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

    # CMD-015: Background execution
    def execute_background(
        self,
        command: str,
        working_dir: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        on_complete: Optional[Callable[[CommandResult], None]] = None,
    ) -> BackgroundCommand:
        """
        Execute a command in the background.

        Args:
            command: Command to execute
            working_dir: Working directory
            env: Environment variables
            on_complete: Callback when command completes

        Returns:
            BackgroundCommand object to track execution
        """
        shell_cmd, shell_args = self._build_shell_command(command, [])

        process_env = os.environ.copy()
        if env:
            process_env.update(env)

        cwd = working_dir or os.getcwd()

        result_queue: queue.Queue = queue.Queue()

        proc = subprocess.Popen(
            shell_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            env=process_env,
            universal_newlines=False,
        )

        def _wait_for_completion() -> None:
            stdout_bytes, stderr_bytes = proc.communicate()
            stdout = self._decode_output(stdout_bytes)
            stderr = self._decode_output(stderr_bytes)

            result = CommandResult(
                command=command,
                return_code=proc.returncode,
                stdout=stdout,
                stderr=stderr,
                timed_out=False,
            )
            result_queue.put(result)

            if on_complete:
                on_complete(result)

        thread = threading.Thread(target=_wait_for_completion, daemon=True)
        thread.start()

        return BackgroundCommand(
            command=command,
            process=proc,
            thread=thread,
            result_queue=result_queue,
        )

    # CMD-016: Streaming output
    def execute_streaming(
        self,
        command: str,
        working_dir: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> Generator[Tuple[str, str], None, CommandResult]:
        """
        Execute a command with streaming output.

        Yields (stream_type, line) tuples where stream_type is 'stdout' or 'stderr'.
        Returns CommandResult when complete.

        Args:
            command: Command to execute
            working_dir: Working directory
            env: Environment variables
            timeout: Timeout in seconds

        Yields:
            Tuple of (stream_type, line)

        Returns:
            CommandResult with execution details
        """
        import select
        import time

        shell_cmd, shell_args = self._build_shell_command(command, [])

        process_env = os.environ.copy()
        if env:
            process_env.update(env)

        cwd = working_dir or os.getcwd()
        timeout_val = timeout if timeout is not None else self._default_timeout

        proc = subprocess.Popen(
            shell_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            env=process_env,
            universal_newlines=False,
        )

        stdout_lines: List[str] = []
        stderr_lines: List[str] = []
        start_time = time.time()
        timed_out = False

        # Set non-blocking mode on Unix
        if sys.platform != "win32":
            import fcntl
            for fd in [proc.stdout, proc.stderr]:
                if fd:
                    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
                    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

        try:
            while proc.poll() is None:
                # Check timeout
                if time.time() - start_time > timeout_val:
                    proc.kill()
                    timed_out = True
                    break

                if sys.platform != "win32":
                    # Unix: use select for non-blocking read
                    readable, _, _ = select.select(
                        [proc.stdout, proc.stderr], [], [], 0.1
                    )

                    for stream in readable:
                        line_bytes = stream.readline()
                        if line_bytes:
                            line = self._decode_output(line_bytes).rstrip("\n\r")
                            if stream == proc.stdout:
                                stdout_lines.append(line)
                                yield ("stdout", line)
                            else:
                                stderr_lines.append(line)
                                yield ("stderr", line)
                else:
                    # Windows: simple polling (less efficient)
                    time.sleep(0.1)

            # Read remaining output
            if proc.stdout:
                remaining_stdout = proc.stdout.read()
                if remaining_stdout:
                    for line in self._decode_output(remaining_stdout).splitlines():
                        stdout_lines.append(line)
                        yield ("stdout", line)

            if proc.stderr:
                remaining_stderr = proc.stderr.read()
                if remaining_stderr:
                    for line in self._decode_output(remaining_stderr).splitlines():
                        stderr_lines.append(line)
                        yield ("stderr", line)

        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()

        return CommandResult(
            command=command,
            return_code=proc.returncode if proc.returncode is not None else -1,
            stdout="\n".join(stdout_lines),
            stderr="\n".join(stderr_lines),
            timed_out=timed_out,
        )


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
