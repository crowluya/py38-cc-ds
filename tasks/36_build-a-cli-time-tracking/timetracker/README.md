# TimeTracker CLI - Smart Time Tracking with Automatic Activity Detection

A powerful CLI time-tracking tool that automatically detects your activity through file watching, suggests projects/tasks based on what you're working on, generates automated reports, and integrates with git commits for accurate project time attribution.

## Features

- 🚀 **Simple CLI Interface** - Start/stop/pause time tracking with intuitive commands
- 🔍 **Automatic Activity Detection** - File watcher monitors filesystem changes to detect what you're working on
- 💡 **Smart Suggestions** - Get project/task suggestions based on recent file activity
- 📊 **Automated Reports** - Generate daily, weekly, or custom time reports in multiple formats
- 🔗 **Git Integration** - Automatically match commits to time entries for accurate attribution
- ⚙️ **Configurable** - Set up project mappings, directory patterns, and preferences
- 🎨 **Beautiful Output** - Clean, colorful console output with tables and formatting

## Installation

```bash
# Install dependencies
npm install

# Build the project
npm run build

# Install globally for easy access
npm link
```

## Quick Start

```bash
# Create your first project
track project create MyProject --description "My awesome project"

# Start tracking time
track start

# Check what you're working on
track status

# Stop tracking when done
track stop

# Generate a report
track report --days 7
```

## Commands

### Time Tracking

#### `track start [options]`
Start tracking time for a project.

```bash
track start
track start -p MyProject
track start -p MyProject -t "Feature X" -n "Working on user authentication"
```

**Options:**
- `-p, --project <name>` - Project name (prompts if not specified)
- `-t, --task <name>` - Task name
- `-n, --notes <notes>` - Notes for this time entry

#### `track stop`
Stop tracking time and save the entry.

```bash
track stop
```

#### `track pause`
Pause the current time entry.

```bash
track pause
```

#### `track resume`
Resume a paused time entry.

```bash
track resume
```

#### `track status`
Show the current time entry status.

```bash
track status
```

**Output:**
```
Current Time Entry:
  Status: ACTIVE
  Project: MyProject
  Task: Feature X
  Notes: Working on user authentication
  Started: 2024-01-15 10:30:00
  Elapsed: 1h 23m
  Git Commits: 3
```

#### `track list [options]`
List recent time entries.

```bash
track list
track list --limit 20
```

**Options:**
- `-l, --limit <number>` - Number of entries to show (default: 10)

### Project Management

#### `track project create <name> [options]`
Create a new project.

```bash
track project create WebDev --description "Web Development Projects"
track project create WebDev -d "Web Dev" -p "~/projects/web/*"
```

**Options:**
- `-d, --description <text>` - Project description
- `-p, --patterns <patterns>` - Directory patterns (comma-separated)

#### `track project list`
List all projects.

```bash
track project list
```

**Output:**
```
┌─────────────────┬──────────────────────┬─────────────────────────┬───────┐
│ Name            │ Description          │ Patterns                │ Repos │
├─────────────────┼──────────────────────┼─────────────────────────┼───────┤
│ WebDev          │ Web Development      │ ~/projects/web/*        │ 2     │
│ Documentation   │ Docs                 │ ~/docs/**/*.md          │ 0     │
└─────────────────┴──────────────────────┴─────────────────────────┴───────┘
```

#### `track project delete <name>`
Delete a project.

```bash
track project delete OldProject
```

#### `track project update <name>`
Update a project.

```bash
track project update MyProject
```

### Reports

#### `track report [options]`
Generate time reports.

```bash
# Weekly report (default)
track report

# Daily report
track report --days 1

# Filter by project
track report --project WebDev --days 30

# Include git commits
track report --commits

# Export to JSON
track report --format json --days 7 > report.json

# Export to CSV
track report --format csv --days 30 > report.csv

# Export to Markdown
track report --format markdown --days 7 > report.md
```

**Options:**
- `-p, --project <name>` - Filter by project
- `-t, --task <name>` - Filter by task
- `-d, --days <number>` - Number of days to include (default: 7)
- `-f, --format <format>` - Output format: table, json, csv, markdown (default: table)
- `--commits` - Include git commits in report

### File Watching

#### `track watch [options]`
Start the file watcher daemon to automatically detect activity.

```bash
# Watch default directories
track watch

# Watch specific directories
track watch --directories ~/projects,~/work
```

**Options:**
- `-d, --directories <dirs>` - Directories to watch (comma-separated)

### Smart Suggestions

#### `track suggest`
Get project/task suggestions based on recent file activity.

```bash
track suggest
```

**Output:**
```
💡 Suggestions based on your recent activity:

1. WebDev
   Confidence: 85%
   Reason: Working on 15 files in this project

2. Documentation
   Task: API Docs
   Confidence: 72%
   Reason: Working on 3 files in this project
```

### Git Integration

#### `track git-sync`
Sync git commits with time entries.

```bash
track git-sync
```

This command:
1. Scans git repositories for commits
2. Matches commits to time entries based on timestamps
3. Links commits to projects/tasks

## Configuration

### Configuration File

TimeTracker stores configuration in `~/.timetracker/config.json`:

```json
{
  "version": "1.0.0",
  "data_directory": "~/.timetracker",
  "database_path": "~/.timetracker/timetracker.db",
  "watch_directories": [
    "~/projects",
    "~/work",
    "~/code"
  ],
  "ignore_patterns": [
    "**/node_modules/**",
    "**/.git/**",
    "**/dist/**"
  ],
  "auto_suggest_enabled": true,
  "file_watcher_enabled": true,
  "git_integration_enabled": true,
  "debounce_interval": 1000,
  "suggestions_confidence_threshold": 0.5
}
```

### Project Mappings

Create `~/.timetracker/project-mappings.json` to map file patterns to projects:

```json
{
  "mappings": [
    {
      "pattern": "~/projects/*/package.json",
      "project_name": "Web Development",
      "priority": 10
    },
    {
      "pattern": "~/work/**/*",
      "project_name": "Work",
      "priority": 100
    },
    {
      "pattern": "**/*.ts",
      "project_name": "TypeScript Development",
      "priority": 8
    }
  ]
}
```

**Pattern Matching:**
- Use glob patterns for flexible matching
- Higher priority values take precedence
- Supports `**` for recursive matching, `*` for single-level wildcards

## Workflows

### Daily Workflow

```bash
# Start your day
track suggest          # See suggestions based on yesterday
track start            # Start tracking (will prompt for project)

# Work on your tasks...
track status           # Check progress any time

# Take a break
track pause            # Pause tracking
# ...break...
track resume           # Resume after break

# End of day
track stop             # Stop tracking
track report --days 1  # See today's summary
```

### Weekly Review

```bash
# Generate weekly report
track report --days 7 --format markdown > weekly-report.md

# Include git commits
track report --days 7 --commits

# Filter by specific project
track report --project MyProject --days 7
```

### Git Integration Workflow

```bash
# Start tracking a feature
track start -p MyProject -t "Feature X"

# Make commits while working
git add .
git commit -m "Implement feature X"

# Stop tracking - commits are automatically linked
track stop

# See which commits were made during this session
track report --commits --days 1
```

## Advanced Features

### File Watching

The file watcher monitors directories you specify and logs activity:

```bash
# Start the watcher in background
track watch &

# Or use a process manager like PM2
pm2 start "track watch" --name timetracker
```

**What Gets Watched:**
- File additions
- File changes
- File deletions

**What Gets Ignored:**
- `node_modules`, `.git`, `dist`, `build` directories
- Log files, temp files
- Configurable via `ignore_patterns`

### Smart Suggestions

The suggestion engine analyzes:

1. **Recent file activity** (last hour)
2. **Current working directory**
3. **Project mappings**
4. **Previous time entries**

It provides confidence scores and reasoning for each suggestion.

### Git Hooks

Automatically sync commits when they happen:

```bash
# Install git hooks (optional)
track git-hook install

# Now commits are automatically tracked
git commit -m "My changes"  # Auto-synced with TimeTracker
```

## Troubleshooting

### Database Issues

```bash
# Reset database (warning: deletes all data)
rm ~/.timetracker/timetracker.db
track project list  # Will recreate database
```

### File Watcher Not Working

```bash
# Check permissions
ls -la ~/.timetracker

# Ensure directories exist
mkdir -p ~/projects ~/work

# Check if directory is being watched
track watch --directories ~/projects
```

### Git Integration Not Finding Commits

```bash
# Manually trigger sync
track git-sync

# Verify git repository
cd ~/my-project
git log  # Ensure commits exist
```

### Suggestions Not Accurate

```bash
# Add more specific mappings
# Edit ~/.timetracker/project-mappings.json

# Increase confidence threshold
# Edit ~/.timetracker/config.json
# Set "suggestions_confidence_threshold": 0.7
```

## Examples

### Example 1: Web Developer

```bash
# Setup
track project create Website --description "Company Website"
track project create Blog --description "Personal Blog"

# Daily work
cd ~/projects/website
track start -p Website
# Work...
track stop

# End of week
track report --project Website --days 7 --format csv > website-time.csv
```

### Example 2: Multiple Projects

```bash
# Morning: Project A
track start -p ProjectA -t "Backend API"
track stop

# Afternoon: Project B
track start -p ProjectB -t "Frontend UI"
track stop

# See breakdown
track report --days 1 --group-by project
```

### Example 3: With Git Commits

```bash
track start -p FeatureX
# Make some changes
git add . && git commit -m "Add login feature"
# More work
git add . && git commit -m "Fix auth bug"
track stop

# See commits in report
track report --days 1 --commits
```

## Data Storage

All data is stored locally in `~/.timetracker/`:

- `timetracker.db` - SQLite database with time entries, projects, activities
- `config.json` - Configuration settings
- `project-mappings.json` - File pattern to project mappings

## Development

```bash
# Run in development mode
npm run dev

# Run tests
npm test

# Build for production
npm run build

# Lint code
npm run lint
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT

## Support

For issues, questions, or suggestions, please open an issue on GitHub.

---

**Happy Time Tracking!** 🚀
