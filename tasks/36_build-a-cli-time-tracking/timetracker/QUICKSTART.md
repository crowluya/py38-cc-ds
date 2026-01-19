# Quick Start Guide - TimeTracker CLI

## Installation

```bash
cd timetracker
npm install
npm run build
npm link
```

## 5-Minute Setup

### Step 1: Create Your First Project
```bash
track project create MyProject --description "My first project"
```

### Step 2: Start Tracking Time
```bash
track start -p MyProject -t "Initial setup" -n "Setting up the project"
```

### Step 3: Check Status
```bash
track status
```

### Step 4: Stop When Done
```bash
track stop
```

### Step 5: View Your Report
```bash
track report --days 1
```

## Common Workflows

### Daily Workflow
```bash
# Morning
track start -p MyProject

# Take a break
track pause

# After break
track resume

# End of day
track stop
track report --days 1
```

### Multiple Projects
```bash
# Project A in morning
track start -p ProjectA
track stop

# Project B in afternoon
track start -p ProjectB
track stop

# See breakdown
track report --days 1
```

### With Git Integration
```bash
# Start tracking
track start -p FeatureX

# Make commits while working
git add .
git commit -m "Add new feature"

# Stop - commits automatically linked
track stop

# See commits in report
track report --days 1 --commits
```

## Configuration

### Set Up Project Mappings
```bash
mkdir -p ~/.timetracker
cat > ~/.timetracker/project-mappings.json << 'EOF'
{
  "mappings": [
    {
      "pattern": "~/projects/web/*",
      "project_name": "Web Development",
      "priority": 10
    },
    {
      "pattern": "~/work/**/*",
      "project_name": "Work",
      "priority": 100
    }
  ]
}
EOF
```

### Start File Watcher
```bash
# In one terminal
track watch

# In another terminal
track start
# Now it will suggest projects based on files you edit!
```

## Export Reports

### JSON
```bash
track report --format json --days 7 > weekly.json
```

### CSV
```bash
track report --format csv --days 30 > monthly.csv
```

### Markdown
```bash
track report --format markdown --days 7 > report.md
```

## Tips

1. **Use Aliases**: Create shell aliases for common commands
   ```bash
   alias tts='track start'
   alias ttp='track stop'
   alias ttr='track report --days 7'
   ```

2. **Auto-suggest**: Use `track suggest` before starting to see recommendations

3. **Git Sync**: Run `track git-sync` periodically to match commits

4. **Check Status**: Use `track status` to see current session anytime

5. **Review Weekly**: `track report --days 7 --format markdown` for weekly reviews

## Troubleshooting

### Database issues
```bash
rm ~/.timetracker/timetracker.db
track project list  # Will recreate
```

### Permission issues
```bash
chmod +x ~/.timetracker
```

### Git not syncing
```bash
cd ~/my-project
git log  # Ensure repo has commits
track git-sync
```

## Next Steps

- Read full documentation: `README.md`
- Set up project mappings for your workflow
- Configure file watcher for automatic suggestions
- Integrate with your git workflow

Enjoy tracking your time! 🚀
