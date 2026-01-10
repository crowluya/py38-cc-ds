"""
CLI data models for DeepCode

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)
"""

from dataclasses import dataclass


@dataclass
class ToolBlock:
    """
    Represents a tool execution block for display.

    Attributes:
        title: Title of the tool block (e.g., "Read(file.py)")
        body: Content/output of the tool execution
        ok: Whether the tool execution succeeded
        expanded: Whether to show full content (default: collapsed)
        max_lines: Maximum lines to show when collapsed
    """
    title: str
    body: str
    ok: bool
    expanded: bool = False
    max_lines: int = 12

    def render(self) -> str:
        """
        Render the tool block as ANSI-colored text with tree-style formatting.

        Returns:
            Formatted string with ANSI color codes
        """
        # ANSI colors approximating the screenshot
        green = "\x1b[32m"
        red = "\x1b[31m"
        white = "\x1b[37m"
        gray = "\x1b[90m"
        reset = "\x1b[0m"

        dot = green if self.ok else red
        out = f"{dot}●{reset} {white}{self.title}{reset}\n"

        body = self.body or ""
        if not body:
            return out
        lines = body.splitlines()
        # Tree style body rendering.
        if (not self.expanded) and len(lines) > self.max_lines:
            shown_lines = lines[: self.max_lines]
            remain = len(lines) - self.max_lines
            for ln in shown_lines:
                out += f"{gray}│  {ln}{reset}\n"
            out += f"{gray}└  … +{remain} lines (Ctrl+O to expand){reset}\n"
            return out

        for i, ln in enumerate(lines):
            prefix = "│" if i < len(lines) - 1 else "└"
            out += f"{gray}{prefix}  {ln}{reset}\n"
        return out
