# AI Command Palette - Usage Examples

## Basic Usage

### Launching the Palette

```bash
# Launch full command palette
aicp launch

# Launch mini palette (compact mode)
aicp launch --mini

# Quick alias
aicp
```

### Executing Commands with Tracking

```bash
# Execute and track a command
aicp execute git status
aicp execute pytest --type test

# Commands are automatically logged with:
# - Timestamp
# - Working directory
# - Git branch (if applicable)
# - Execution time
# - Exit status
```

### Searching Commands

```bash
# Search for commands
aicp search git
aicp search note --limit 10
aicp search deploy --type workflow
```

## Configuration

### Viewing Configuration

```bash
# Show current configuration
aicp config
```

### Editing Configuration

```bash
# Config file location
~/.config/ai-command-palette/config.json

# Example configuration
{
  "keybindings": {
    "toggle": "ctrl+space",
    "navigate_up": "up",
    "navigate_down": "down",
    "execute": "enter"
  },
  "learning": {
    "enabled": true,
    "retention_days": 90,
    "min_frequency": 2
  },
  "scoring": {
    "frequency": 0.4,
    "recency": 0.3,
    "fuzzy_match": 0.3
  },
  "ui": {
    "max_results": 20,
    "show_preview": true,
    "fuzzy_match_threshold": 60
  }
}
```

## Statistics and Insights

### Viewing Usage Statistics

```bash
# Show usage statistics (default: last 30 days)
aicp stats

# Show statistics for different time periods
aicp stats --days 7
aicp stats --days 90 --limit 50

# Output example:
# Usage Statistics (last 30 days)
# ==================================================
# Total Commands: 1,234
# Total Files: 567
#
# Command Types:
#   system: 890
#   note: 234
#   workflow: 110
#
# Top 20 Commands:
#   git status: 45
#   note create: 38
#   git commit: 32
#   pytest: 28
```

## Shell Integration

### Installing Shell Integration

```bash
# Auto-detect and install shell integration
aicp shell --install

# Install for specific shell
aicp shell --type bash --install
aicp shell --type zsh --install
aicp shell --type fish --install

# Generate script without installing (for custom setup)
aicp shell --type zsh >> ~/.zshrc
```

### Using Shell Integration

After installation, you can:

1. Press `Ctrl+Space` to open the command palette
2. Start typing to search commands
3. Use arrow keys to navigate
4. Press Enter to execute

## Workflows

### Built-in Workflows

```bash
# Execute a workflow
aicp execute workflow:git:commit-push --args '{"message": "My commit message"}'

# Available workflows:
# - git:commit-push: Stage, commit, and push changes
# - dev:full-check: Format, lint, and test code
# - project:setup: Initialize a new project
# - note:standup: Create daily standup note
```

### Creating Custom Workflows

Create a workflow file at `~/.config/ai-command-palette/workflows/my-workflow.json`:

```json
{
  "name": "deploy:staging",
  "description": "Deploy to staging environment",
  "category": "Deployment",
  "tags": ["deploy", "staging"],
  "steps": [
    {
      "command": "pytest tests/ -v",
      "continue_on_error": false
    },
    {
      "command": "git pull origin main",
      "continue_on_error": false
    },
    {
      "command": "docker build -t myapp:latest .",
      "continue_on_error": false
    },
    {
      "command": "docker push myapp:latest",
      "continue_on_error": false
    },
    {
      "command": "kubectl set image deployment/myapp myapp=myapp:latest",
      "continue_on_error": false
    }
  ]
}
```

Then use it:

```bash
aicp workflow execute deploy:staging
```

## Note-Taking Integration

### Note Commands

The palette includes built-in note-taking commands:

```bash
note:create     - Create a new note
note:search     - Search notes
note:edit       - Edit a note
note:list       - List all notes
note:delete     - Delete a note
note:recent     - Show recent notes
```

### Custom Note Integration

If you have a custom note-taking CLI, configure it:

```bash
# In config.json
{
  "integration": {
    "notes_cli_path": "/path/to/your/note/cli"
  }
}
```

## Advanced Usage

### Programmatic Usage

```python
from ai_command_palette import CommandRegistry, UsageTracker, Database

# Initialize components
db = Database()
tracker = UsageTracker(db)
registry = CommandRegistry()

# Track a command
tracker.track_command(
    command="git commit",
    command_type="system",
    working_dir="/home/user/project",
    exit_code=0,
    duration_ms=250
)

# Search commands
results = registry.search("git")
for cmd in results:
    print(f"{cmd.name}: {cmd.description}")

# Get usage statistics
freq = tracker.get_frequent_commands(days=30, limit=10)
for cmd, count in freq:
    print(f"{cmd}: {count} times")
```

### Keyboard Shortcuts

Default keyboard shortcuts in the palette:

- `Ctrl+Space`: Open command palette (in shell)
- `Up/Down`: Navigate results
- `Page Up/Down`: Navigate pages
- `Enter`: Execute selected command
- `Escape`: Cancel/close palette
- `Tab`: Show preview

### Tips and Tricks

1. **Fuzzy Search**: Type any part of a command name
   - "gs" matches "git status"
   - "nc" matches "note create"

2. **Category Filtering**: Type category name
   - "git" shows all git commands
   - "note" shows all note commands

3. **Context Awareness**: The palette learns your habits
   - Frequent commands appear higher
   - Git commands boosted in git repositories
   - Time-based patterns are learned

4. **Workflow Automation**: Chain commands together
   - Create workflows for repetitive tasks
   - Include error handling
   - Pass arguments dynamically

## Troubleshooting

### Database Issues

```bash
# Reinitialize database
rm ~/.local/share/ai-command-palette/usage.db
aicp init
```

### Configuration Problems

```bash
# Reset to defaults
rm ~/.config/ai-command-palette/config.json
aicp init
```

### Shell Integration Not Working

```bash
# Manually source the integration
source ~/.bashrc.aicp  # or ~/.zshrc.aicp

# Check shell detection
echo $SHELL
```

## Performance Tips

1. **Limit Results**: Reduce `max_results` in config for faster display
2. **Retention**: Lower `retention_days` to keep database smaller
3. **Index Files**: Limit file indexing depth in large projects
4. **Caching**: The system caches frequently accessed data automatically

## Privacy

All data is stored locally:
- No cloud syncing
- No telemetry
- No external dependencies
- Full control over your data

To disable tracking:

```json
{
  "learning": {
    "enabled": false
  }
}
```
