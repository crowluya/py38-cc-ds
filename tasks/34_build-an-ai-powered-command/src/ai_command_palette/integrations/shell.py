"""Shell integration hooks."""

import os
from pathlib import Path
from typing import Optional

from ai_command_palette.storage.config import Config


class ShellIntegration:
    """Generate shell integration scripts."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize shell integration."""
        self.config = config or Config()

    def generate_bash_integration(self) -> str:
        """Generate bash integration script."""
        keybinding = self.config.keybindings.toggle

        return f"""
# AI Command Palette Integration

# Add to ~/.bashrc or ~/.bashrc.local

# Function to launch command palette
aicp() {{
    # Save current directory
    AICP_PWD="$PWD"

    # Launch command palette
    command aicp

    # Return to original directory
    cd "$AICP_PWD"
}}

# Keybinding to open command palette
bind -x '"{keybinding}": aicp'

# Add command to history tracking
_PROMPT_COMMAND_HOOK() {{
    # Track command in background
    echo "$BASH_COMMAND" | aicp track --pipe &
}}

# Optional: Track all commands
# PROMPT_COMMAND="${{PROMPT_COMMAND}};_PROMPT_COMMAND_HOOK"
"""

    def generate_zsh_integration(self) -> str:
        """Generate zsh integration script."""
        keybinding = self.config.keybindings.toggle

        return f"""
# AI Command Palette Integration

# Add to ~/.zshrc

# Function to launch command palette
aicp() {{
    # Save current directory
    local AICP_PWD="$PWD"

    # Launch command palette
    command aicp

    # Return to original directory
    cd "$AICP_PWD"
}}

# Keybinding (zsh uses different syntax)
# Ctrl+Space
aicp-widget() {{
    aicp
    zle reset-prompt
}}
zle -N aicp-widget
bindkey '^@' aicp-widget  # Ctrl+Space sends ^@

# Or use the configured keybinding
# bindkey '{keybinding}' aicp-widget

# Add alias
alias cp='aicp'
"""

    def generate_fish_integration(self) -> str:
        """Generate fish shell integration script."""
        return """
# AI Command Palette Integration

# Add to ~/.config/fish/config.fish

# Function to launch command palette
function aicp
    # Save current directory
    set -l AICP_PWD $PWD

    # Launch command palette
    command aicp

    # Return to original directory
    cd $AICP_PWD
end

# Keybinding (Ctrl+Space)
function aicp_widget --description 'Launch AI Command Palette'
    aicp
    commandline -f repaint
end

bind \\c@ aicp_widget  # Ctrl+Space

# Add alias
alias cp aicp
"""

    def install_bash_integration(self) -> bool:
        """Install bash integration to user's bashrc."""
        bashrc = Path.home() / ".bashrc"
        integration_file = Path.home() / ".bashrc.aicp"

        try:
            # Write integration script
            with open(integration_file, "w") as f:
                f.write(self.generate_bash_integration())

            # Add source to bashrc if not already there
            with open(bashrc, "a+") as f:
                f.seek(0)
                content = f.read()

                if "[ -f ~/.bashrc.aicp ]" not in content:
                    f.write("\n# AI Command Palette\n")
                    f.write("[ -f ~/.bashrc.aicp ] && source ~/.bashrc.aicp\n")

            return True
        except Exception:
            return False

    def install_zsh_integration(self) -> bool:
        """Install zsh integration to user's zshrc."""
        zshrc = Path.home() / ".zshrc"
        integration_file = Path.home() / ".zshrc.aicp"

        try:
            # Write integration script
            with open(integration_file, "w") as f:
                f.write(self.generate_zsh_integration())

            # Add source to zshrc if not already there
            with open(zshrc, "a+") as f:
                f.seek(0)
                content = f.read()

                if "[ -f ~/.zshrc.aicp ]" not in content:
                    f.write("\n# AI Command Palette\n")
                    f.write("[ -f ~/.zshrc.aicp ] && source ~/.zshrc.aicp\n")

            return True
        except Exception:
            return False

    def get_current_shell(self) -> str:
        """Get current shell."""
        return os.environ.get("SHELL", "/bin/bash")

    def detect_shell_type(self) -> str:
        """Detect shell type from SHELL environment variable."""
        shell_path = self.get_current_shell()

        if "zsh" in shell_path:
            return "zsh"
        elif "fish" in shell_path:
            return "fish"
        elif "bash" in shell_path:
            return "bash"
        else:
            return "bash"  # Default to bash
