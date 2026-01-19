# Task Workspace

Task #36: Build a CLI time-tracking tool with automatic acti

## Summary
- Priority: THOUGHT
- Project: None
- Created: 2026-01-19T13:52:56.503794

## Description
Build a CLI time-tracking tool with automatic activity detection using file watcher events to suggest projects/tasks based on what you're working on, generate automated reports, and integrate with git commits for accurate project time attribution.

## Plan & Analysis
# Executive Summary
This task involves building a comprehensive CLI time-tracking tool with smart features including automatic activity detection through file watching, project/task suggestions, automated reporting, and git commit integration. The tool needs to monitor filesystem activity to intelligently suggest what the user is working on, while maintaining accurate time attribution through git hooks.

# Task Analysis

## Core Requirements Breakdown:
1. **CLI Interface** - Command-line tool for starting/stopping time tracking
2. **Activity Detection** - File watcher that monitors filesystem changes
3. **Smart Suggestions** - Suggest projects/tasks based on active files/directories
4. **Automated Reports** - Generate time reports (daily, weekly, custom ranges)
5. **Git Integration** - Integrate with git commits for accurate attribution

## Technical Considerations:
- **Language Choice**: Python or Node.js/TypeScript (both excellent for CLI tools and file watching)
- **File Watching**: Need efficient filesystem monitoring (chokidar for Node.js, watchdog for Python)
- **State Management**: Local database or JSON file for tracking time entries
- **Git Integration**: Git hooks or commit message parsing
- **Configuration**: Project/task mapping rules (e.g., directory patterns → project names)

## Potential Architecture:
- **Core Time Tracker**: Start/stop/pause functionality
- **Activity Monitor**: Background file watcher daemon
- **Project Matcher**: Pattern matching engine (directory → project)
- **Report Generator**: Summarize time by project/task/date
- **Git Bridge**: Parse commits, match with time entries

# Structured TODO List
# Detailed Task Breakdown

## 1. Decide on tech stack and set up project structure
**Effort**: Low | **Dependencies**: None
- Evaluate Python vs Node.js/TypeScript for file watching, CLI libraries, and ecosystem
- Initialize project with proper structure (src, tests, config, docs)
- Set up package management and build tools
- Choose libraries: commander/ink (Node.js) or click/typer (Python), file watcher library

## 2. Design data model for time entries, projects, tasks, and configuration storage
**Effort**: Medium | **Dependencies**: Task 1
- Define schema for time entries (start_time, end_time, project, task, notes, git commits)
- Define project/task structure with metadata
- Define configuration schema (directory patterns, project mappings, git repo mappings)
- Choose storage: SQLite (Python) or JSON/YAML files
- Design activity log structure for file watcher events

## 3. Implement core CLI interface with start/stop/pause/status commands
**Effort**: Medium | **Dependencies**: Task 2
- Build CLI framework with argument parsing
- Implement `track start` command with project/task selection
- Implement `track stop` command with time duration calculation
- Implement `track pause/resume` functionality
- Implement `track status` to show current session
- Add `track list` to view recent entries

## 4. Build file watcher module to detect and log file system activity
**Effort**: Medium | **Dependencies**: Task 1, 2
- Integrate file watching library (chokedar or watchdog)
- Implement debouncing/throttling for rapid file changes
- Log activity with timestamps, file paths, and event types
- Run as background daemon or process
- Filter irrelevant directories (node_modules, .git, etc.)

## 5. Create project/task matching engine with configurable pattern rules
**Effort**: Medium | **Dependencies**: Task 2, 4
- Build pattern matching system (regex, glob patterns)
- Match file paths to projects based on directory structure
- Support hierarchical project organization
- Prioritize recently active files/projects
- Cache project matches for performance

## 6. Implement smart suggestion system based on recent file activity
**Effort**: High | **Dependencies**: Task 4, 5
- Analyze file activity patterns to infer current project
- Suggest projects when starting new time entry
- Suggest tasks based on recently modified files
- Learn from user confirmations/rejections (ML optional)
- Provide confidence scores for suggestions

## 7. Build report generator with multiple output formats (console, JSON, CSV)
**Effort**: Medium | **Dependencies**: Task 2, 3
- Implement time aggregation by project, task, date range
- Generate daily/weekly/monthly reports
- Support custom date range queries
- Output formats: table (console), JSON, CSV, Markdown
- Add filtering and sorting options
- Include git commit attribution in reports

## 8. Implement git commit integration (parse commits, match time entries)
**Effort**: High | **Dependencies**: Task 2, 3
- Parse git log to extract commits with timestamps
- Match commits to time entries based on time overlap
- Optionally add git hooks to auto-tag commits with time entry IDs
- Link commits to projects/tasks
- Display commit history in time reports
- Handle multiple git repositories

## 9. Add configuration file system for project mappings and user preferences
**Effort**: Low | **Dependencies**: Task 2, 5
- Support global and per-project config files
- Define project-to-directory mappings
- Configure git repositories
- Set user preferences (default projects, ignore patterns)
- Provide `track config` commands for management
- Validate configuration on load

## 10. Create comprehensive documentation
**Effort**: Low | **Dependencies**: Task 3, 7, 8
- Write README with installation instructions
- Document all CLI commands with examples
- Explain configuration file format
- Provide usage scenarios and workflows
- Create troubleshooting guide
- Add contribution guidelines if open source

## 11. Add error handling and edge case coverage
**Effort**: Medium | **Dependencies**: Task 3, 4, 8
- Handle background process crashes/restarts
- Validate time entries (no overlapping sessions)
- Handle git operations in non-git directories
- Manage file system permission errors
- Handle configuration file corruption
- Add graceful shutdown procedures

## 12. Write unit tests and integration tests
**Effort**: High | **Dependencies**: Tasks 3-11
- Unit tests for each module
- Integration tests for CLI commands
- Mock file system and git operations
- Test edge cases and error conditions
- Achieve >80% code coverage
- Add CI/CD configuration if applicable

# Approach and Strategy

## Recommended Tech Stack: **Node.js with TypeScript**
**Rationale**:
- **TypeScript**: Better type safety for complex data models
- **Chokidar**: Battle-tested file watcher with excellent performance
- **Commander.js**: Mature CLI framework with TypeScript support
- **Better ecosystem**: Rich npm packages for CLI tools (chalk, inquirer, ora)
- **Cross-platform**: Excellent Windows/Mac/Linux support

## Development Strategy:
1. **Start simple**: Build basic time tracking without file watching
2. **Iterative enhancement**: Add file watcher → suggestions → git integration
3. **MVP-first**: Get core functionality working before advanced features
4. **Configuration-driven**: Make behavior customizable without code changes
5. **Background service**: Design file watcher as separate daemon process

## Architecture Pattern:
```
CLI Layer (Commands)
    ↓
Core Logic (Time Tracker, State Machine)
    ↓
Services (File Watcher, Project Matcher, Git Bridge)
    ↓
Storage (SQLite/JSON)
```

# Assumptions and Potential Blockers

## Assumptions:
- User has Node.js v18+ installed
- User works in git repositories (for git integration)
- User can install CLI globally via npm
- File system monitoring is permitted (may require permissions on some systems)
- Single user per machine (no multi-user concerns)

## Potential Blockers:
1. **File system permissions**: Corporate environments may restrict file watching
   - *Mitigation*: Fallback to manual project selection
   
2. **Background process management**: Different OS requirements (launchd, systemd)
   - *Mitigation*: Use cross-platform libraries like PM2
   
3. **Git integration complexity**: Matching commits to time entries is tricky
   - *Mitigation*: Use time windows and fuzzy matching, provide manual override
   
4. **Multiple simultaneous projects**: User may work on multiple projects at once
   - *Mitigation*: Support multiple concurrent time entries
   
5. **Performance**: High-frequency file changes could overwhelm system
   - *Mitigation*: Implement aggressive debouncing and throttling

## Risk Mitigation:
- Start with manual project selection, add auto-detection later
- Make all features opt-in via configuration
- Provide "safe mode" without file watching for production environments
- Extensive logging for debugging file watcher issues

## TODO List
(Updated by worker agent)

## Status: PARTIAL

## Outstanding Items
(None)

## Recommendations
(None)

## Execution Summary

### Execution 2026-01-19 14:07:30
- Status: ✅ COMPLETED
- Files Modified: 92
- Duration: 874s

## Execution Summary
