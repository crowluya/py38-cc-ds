# AI Command Palette

An intelligent command palette tool that learns from your usage patterns to suggest relevant commands, files, and actions. Integrates seamlessly with your existing CLI workflows to provide intelligent command completion and workflow automation.

## Features

- 🔍 **Fuzzy Search Interface**: Fast, intuitive search for commands, files, and actions
- 🧠 **Usage Pattern Learning**: Learns from your behavior to provide smarter suggestions
- 📊 **Context-Aware Recommendations**: Suggestions based on time, directory, git branch, and recent activity
- ⚡ **Workflow Automation**: Create macros and command chains for common tasks
- 🎨 **Beautiful TUI**: Modern terminal UI built with Textual
- 🔒 **Privacy-First**: All data stored locally, no cloud dependencies

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/ai-command-palette.git
cd ai-command-palette

# Install with pip
pip install -e .

# Optional: Install ML dependencies for enhanced recommendations
pip install -e ".[ml,dev]"
```

## Quick Start

```bash
# Launch the command palette
aicp

# Or trigger with keybinding (configured in shell integration)
# Press Ctrl+Space to open the palette
```

## Usage

### Basic Usage

1. **Open the palette**: Run `aicp` or use your configured keybinding
2. **Type to search**: Fuzzy search matches commands, files, and actions
3. **Navigate**: Use arrow keys or vim-style navigation (j/k)
4. **Execute**: Press Enter to run the selected command

### Command Types

- **System Commands**: Any command in your PATH
- **Note Commands**: Quick access to note-taking operations
- **File Operations**: Open, edit, search files
- **Workflows**: Custom macros for multi-step tasks
- **Recent Items**: Previously executed commands

### Configuration

Configuration is stored in `~/.config/ai-command-palette/config.yaml`:

```yaml
# Keybindings
keybindings:
  toggle: "ctrl+space"
  navigate_up: "up"
  navigate_down: "down"
  execute: "enter"

# Learning settings
learning:
  enabled: true
  retention_days: 30
  min_frequency: 2

# Scoring weights
scoring:
  frequency: 0.4
  recency: 0.3
  fuzzy_match: 0.3
```

## Architecture

```
ai_command_palette/
├── cli.py              # Main CLI entry point
├── ui/
│   ├── palette.py      # Textual-based TUI
│   └── widgets.py      # Custom UI components
├── core/
│   ├── tracker.py      # Usage tracking engine
│   ├── registry.py     # Command registry and discovery
│   └── scorer.py       # Recommendation scoring
├── ml/
│   ├── recommend.py    # ML-based recommendations
│   └── context.py      # Context awareness
├── storage/
│   ├── database.py     # SQLAlchemy models
│   └── config.py       # Configuration management
└── integrations/
    ├── notes.py        # Note-taking CLI integration
    └── shell.py        # Shell integration hooks
```

## Development

### Running Tests

```bash
pytest tests/
```

### Code Formatting

```bash
black src/
ruff check src/
```

### Type Checking

```bash
mypy src/
```

## Contributing

Contributions welcome! Please read CONTRIBUTING.md for guidelines.

## License

MIT License - see LICENSE file for details.

## Roadmap

- [ ] Enhanced ML recommendations with embeddings
- [ ] Cloud sync support
- [ ] Plugin system for extensibility
- [ ] Visual analytics dashboard
- [ ] Team collaboration features
