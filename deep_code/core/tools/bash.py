"""
Bash tool for DeepCode

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)
"""

import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from deep_code.core.tools.base import (
    Tool,
    ToolCategory,
    ToolParameter,
    ToolResult,
)
from deep_code.core.executor import CommandExecutor


# Dangerous command patterns
DANGEROUS_PATTERNS = [
    # rm -rf variations
    r"rm\s+(-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*|-[a-zA-Z]*f[a-zA-Z]*r[a-zA-Z]*|--recursive\s+--force|--force\s+--recursive)\s+(/|~|/\*)",
    r"rm\s+(-rf|-fr)\s+\S*",  # Any rm -rf
    # Filesystem destruction
    r"mkfs\.",
    r"dd\s+.*of=/dev/",
    # Permission changes on root
    r"chmod\s+(-R\s+)?[0-7]{3,4}\s+/\s*$",
    r"chmod\s+-R\s+[0-7]{3,4}\s+/",
    r"chown\s+-R\s+.*\s+/\s*$",
    # Fork bombs
    r":\(\)\s*\{\s*:\|:\s*&\s*\}\s*;",
    # Windows dangerous commands
    r"format\s+[a-zA-Z]:",
    r"del\s+/[sS]\s+/[qQ]",
    r"rd\s+/[sS]\s+/[qQ]",
]

# Compiled patterns for efficiency
DANGEROUS_REGEX = [re.compile(p, re.IGNORECASE) for p in DANGEROUS_PATTERNS]


class BashTool(Tool):
    """
    Tool for executing shell commands.

    Supports:
    - Shell command execution (bash on Unix, cmd on Windows)
    - Timeout parameter
    - Working directory parameter
    - Dangerous command detection
    - Path security checks
    """

    # Maximum timeout in seconds (10 minutes)
    MAX_TIMEOUT = 600
    # Default timeout in seconds (2 minutes)
    DEFAULT_TIMEOUT = 120

    def __init__(self, project_root: Optional[str] = None):
        """
        Initialize Bash tool.

        Args:
            project_root: Optional project root for path security checks
        """
        self._project_root = project_root
        self._executor = CommandExecutor(default_timeout=self.DEFAULT_TIMEOUT)

    @property
    def name(self) -> str:
        return "Bash"

    @property
    def description(self) -> str:
        return (
            "Executes a shell command in a persistent shell session. "
            "Use for running system commands, scripts, and terminal operations. "
            "Supports timeout and working directory parameters."
        )

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.SHELL

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="command",
                type="string",
                description="The shell command to execute",
                required=True,
            ),
            ToolParameter(
                name="timeout",
                type="integer",
                description=f"Timeout in seconds (default: {self.DEFAULT_TIMEOUT}, max: {self.MAX_TIMEOUT})",
                required=False,
                default=self.DEFAULT_TIMEOUT,
            ),
            ToolParameter(
                name="working_dir",
                type="string",
                description="Working directory for command execution",
                required=False,
            ),
        ]

    @property
    def requires_permission(self) -> bool:
        return True

    @property
    def is_dangerous(self) -> bool:
        return True  # Shell commands are potentially dangerous

    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """
        Execute the shell command.

        Args:
            arguments: Tool arguments containing command, timeout, working_dir

        Returns:
            ToolResult with command output or error
        """
        self.validate_arguments(arguments)

        command = arguments["command"]
        timeout = arguments.get("timeout", self.DEFAULT_TIMEOUT)
        working_dir = arguments.get("working_dir")

        # Validate command is not empty
        if not command or not command.strip():
            return ToolResult.error_result(
                self.name,
                "Command cannot be empty",
            )

        # Validate timeout
        if timeout is not None:
            if timeout < 1:
                timeout = self.DEFAULT_TIMEOUT
            elif timeout > self.MAX_TIMEOUT:
                timeout = self.MAX_TIMEOUT

        # Check for dangerous commands
        danger_check = self._check_dangerous_command(command)
        if danger_check:
            return ToolResult.error_result(
                self.name,
                f"Dangerous command blocked: {danger_check}",
            )

        # Validate working directory
        if working_dir:
            wd_path = Path(working_dir)

            if not wd_path.exists():
                return ToolResult.error_result(
                    self.name,
                    f"Working directory not found: {working_dir}",
                )

            if not wd_path.is_dir():
                return ToolResult.error_result(
                    self.name,
                    f"Not a directory: {working_dir}",
                )

            # Security check: prevent path traversal
            if self._project_root:
                try:
                    resolved = wd_path.resolve()
                    root = Path(self._project_root).resolve()
                    resolved.relative_to(root)
                except ValueError:
                    return ToolResult.error_result(
                        self.name,
                        f"Working directory escapes project root: {working_dir}",
                    )

        try:
            # Execute command using CommandExecutor
            cmd_result = self._executor.execute(
                command,
                working_dir=working_dir,
                timeout=timeout,
            )

            # Build output
            output_parts = []
            if cmd_result.stdout:
                output_parts.append(cmd_result.stdout.rstrip())
            if cmd_result.stderr:
                if output_parts:
                    output_parts.append("")  # Empty line separator
                output_parts.append(cmd_result.stderr.rstrip())

            output = "\n".join(output_parts) if output_parts else "(no output)"

            # Build metadata
            metadata = {
                "command": command,
                "return_code": cmd_result.return_code,
                "timed_out": cmd_result.timed_out,
                "stdout": cmd_result.stdout,
                "stderr": cmd_result.stderr,
            }

            if working_dir:
                metadata["working_dir"] = working_dir

            # Determine success
            if cmd_result.timed_out:
                return ToolResult.error_result(
                    self.name,
                    f"Command timed out after {timeout} seconds\n{output}",
                    metadata=metadata,
                )

            if cmd_result.return_code != 0:
                return ToolResult.error_result(
                    self.name,
                    f"Command failed with exit code {cmd_result.return_code}\n{output}",
                    metadata=metadata,
                )

            return ToolResult.success_result(
                self.name,
                output,
                metadata=metadata,
            )

        except Exception as e:
            return ToolResult.error_result(
                self.name,
                f"Error executing command: {str(e)}",
            )

    def _check_dangerous_command(self, command: str) -> Optional[str]:
        """
        Check if command matches dangerous patterns.

        Args:
            command: Command to check

        Returns:
            Description of danger if dangerous, None otherwise
        """
        # Check against compiled patterns
        for pattern in DANGEROUS_REGEX:
            if pattern.search(command):
                return f"Command matches dangerous pattern"

        # Additional checks for specific dangerous commands
        cmd_lower = command.lower().strip()

        # Check for rm -rf with dangerous targets
        if "rm " in cmd_lower and ("-rf" in cmd_lower or "-fr" in cmd_lower):
            # Check for dangerous targets
            dangerous_targets = ["/", "/*", "~", "~/", "$HOME", "${HOME}"]
            for target in dangerous_targets:
                if target in command:
                    return f"rm -rf with dangerous target: {target}"

        # Check for format on Windows
        if sys.platform == "win32":
            if cmd_lower.startswith("format "):
                return "format command is dangerous"

        return None
