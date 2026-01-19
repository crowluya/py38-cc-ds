# Usage Examples

This document provides practical examples for using the Notes CLI tool.

## Table of Contents
- [Basic Workflow](#basic-workflow)
- [Tag Management](#tag-management)
- [Search Operations](#search-operations)
- [Advanced Use Cases](#advanced-use-cases)

## Basic Workflow

### 1. Initialize Your Notes Directory

```bash
$ notes init
Initializing notes directory...
Notes directory initialized at: "/home/user/notes"
```

### 2. Create Your First Note

```bash
$ notes create "Getting Started with Rust" --tags rust,programming
Creating new note...
Enter note content (press Enter when done):
> Rust is a systems programming language focused on safety and performance.
Note created successfully!
ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890
Title: Getting Started with Rust
Tags: rust, programming
```

### 3. List All Notes

```bash
$ notes list
Found 1 note(s):

1. Getting Started with Rust - a1b2c3d4-e5f6-7890-abcd-ef1234567890
   Tags: rust, programming | Created: 2024-01-15 10:30
```

### 4. View a Note

```bash
$ notes view a1b2c3d4-e5f6-7890-abcd-ef1234567890

Getting Started with Rust
──────────────────────────────────────────────────────────────────────────────────
Tags: rust, programming

Created: 2024-01-15 10:30:45
Updated: 2024-01-15 10:30:45
──────────────────────────────────────────────────────────────────────────────────

Rust is a systems programming language focused on safety and performance.
```

## Tag Management

### Add Tags to a Note

```bash
$ notes tag add a1b2c3d4-e5f6-7890-abcd-ef1234567890 tutorial
Tag 'tutorial' added to note successfully!
```

### Remove Tags from a Note

```bash
$ notes tag remove a1b2c3d4-e5f6-7890-abcd-ef1234567890 programming
Tag 'programming' removed from note successfully!
```

### List All Tags

```bash
$ notes tag list
All tags:
  beginner (1 notes)
  cli (3 notes)
  personal (2 notes)
  rust (5 notes)
  tutorial (2 notes)
  work (4 notes)
```

### Filter Notes by Tag

```bash
$ notes list --tag rust
Found 5 note(s):

1. Rust Ownership Model - b2c3d4e5-f6a7-8901-bcde-f23456789012
   Tags: rust, advanced | Created: 2024-01-14 15:20

2. Error Handling in Rust - c3d4e5f6-a7b8-9012-cdef-345678901234
   Tags: rust, tutorial | Created: 2024-01-13 09:15
```

## Search Operations

### Search by Title or Content

```bash
$ notes search "ownership"
Found 2 note(s) matching 'ownership':

1. Rust Ownership Model
   ID: b2c3d4e5-f6a7-8901-bcde-f23456789012
   Tags: rust, advanced | Created: 2024-01-14

2. Memory Management Basics
   ID: d4e5f6a7-b8c9-0123-def0-456789012345
   Tags: systems, programming | Created: 2024-01-10
```

### Case-Insensitive Search

```bash
# Search is case-insensitive
$ notes search "RUST"
$ notes search "rust"
# Both commands return the same results
```

## Advanced Use Cases

### Daily Journaling

```bash
# Create a journal entry
$ notes create "2024-01-15 - Monday" --tags journal,daily
Creating new note...
Enter note content:
> Today I learned about Rust's ownership system.
> Also started working on a CLI project.
> Feeling productive!

# View journal entries
$ notes list --tag journal

# Search journal for specific topics
$ notes search "productive"
```

### Project Notes

```bash
# Create project-specific notes
$ notes create "Project Ideas" --tags ideas,work
$ notes create "Meeting Notes - Q1 Planning" --tags work,meetings

# Add related tags
$ notes tag add <project-note-id> backend
$ notes tag add <project-note-id> api

# Review all work-related notes
$ notes list --tag work
```

### Learning Notes

```bash
# Track learning progress
$ notes create "Rust Enums" --tags rust,learning,todo
$ notes create "Rust Pattern Matching" --tags rust,learning,done
$ notes create "Rust Lifetimes" --tags rust,learning,in-progress

# Track what's to learn
$ notes list --tag todo

# Review completed topics
$ notes list --tag done
```

### Task Management

```bash
# Create task notes
$ notes create "Fix bug in authentication" --tags tasks,bug,high-priority
$ notes create "Refactor database layer" --tags tasks,refactor,medium-priority
$ notes create "Update documentation" --tags tasks,docs,low-priority

# List all tasks
$ notes list --tag tasks

# Focus on high-priority items
$ notes list --tag high-priority

# Mark as completed
$ notes tag remove <task-id> high-priority
$ notes tag add <task-id> completed
```

### Research Organization

```bash
# Create research notes
$ notes create "WebAssembly Performance" --tags research,wasm,performance
$ notes create "Rust vs C++ Benchmark" --tags research,benchmarking
$ notes create "CLI Best Practices" --tags research,cli,ux

# Search research topics
$ notes search "benchmarking"

# Review all research
$ notes list --tag research

# Cross-reference topics
$ notes tag add <note-id> performance-optimization
```

## Editing and Updating

### Edit Note Content

```bash
$ notes edit a1b2c3d4-e5f6-7890-abcd-ef1234567890
Editing note: Getting Started with Rust
Current content:
Rust is a systems programming language focused on safety and performance.
──────────────────────────────────────────────────────────────────────────────────

Enter new content (press Enter when done):
> Rust is a systems programming language focused on safety, concurrency, and performance.
Note updated successfully!
```

## Deletion

### Delete with Confirmation

```bash
$ notes delete a1b2c3d4-e5f6-7890-abcd-ef1234567890
Are you sure you want to delete note: Getting Started with Rust?
This action cannot be undone. Continue? [y/N]: y
Note deleted successfully!
```

### Force Delete (Skip Confirmation)

```bash
$ notes delete a1b2c3d4-e5f6-7890-abcd-ef1234567890 --force
Note deleted successfully!
```

## Tips and Tricks

### 1. Use Descriptive Titles

```bash
# Good
$ notes create "2024-01-15 - Rust Ownership Study Session"

# Less useful
$ notes create "Notes"
```

### 2. Consistent Tagging

```bash
# Use consistent tag names
$ notes create "API Design" --tags work,api,design
$ notes create "Database Schema" --tags work,database,design

# Avoid inconsistent tagging
$ notes create "API Design" --tags "API", "Work"
$ notes create "Database" --tags "work", "db"
```

### 3. Tag Hierarchies

```bash
# Use hierarchical tags
project-alpha/backend
project-alpha/frontend
project-alpha/database

# This makes filtering easier
$ notes list --tag project-alpha
```

### 4. Search Before Creating

```bash
# Check if you already have notes on a topic
$ notes search "rust ownership"

# If found, you might want to update instead of creating new
$ notes edit <existing-note-id>
```

### 5. Regular Tag Maintenance

```bash
# Review your tags periodically
$ notes tag list

# Remove unused tags
$ notes tag remove <note-id> old-tag

# Consolidate similar tags
$ notes tag add <note-id> new-consistent-tag
$ notes tag remove <note-id> old-inconsistent-tag
```

## Integration with Other Tools

### Git Integration

```bash
# Version control your notes
cd ~/notes
git init
git add .
git commit -m "Initial notes import"

# Push to remote
git remote add origin <your-repo-url>
git push -u origin main
```

### Backup Strategy

```bash
# Create periodic backups
cp -r ~/notes ~/backup/notes-$(date +%Y%m%d)

# Or use rsync for incremental backups
rsync -av ~/notes/ ~/backup/notes/
```

### Note Templates

```bash
# Create template notes
$ notes create "Meeting Template" --tags template

# Use as reference when creating new meeting notes
$ notes view <template-id>
$ notes create "Team Standup - 2024-01-15" --tags meetings,work
```

## Troubleshooting Examples

### Find a Note When You Forgot the ID

```bash
# Search by content
$ notes search "specific content from the note"

# List notes by tag
$ notes list --tag <remembered-tag>

# List all notes to scan
$ notes list --limit 100
```

### Recover from Accidental Deletion

```bash
# If you have git version control
cd ~/notes
git log --diff-filter=D --summary
git checkout <commit-hash>~ -- <note-file.md>
```

---

For more information, see the main [README.md](README.md).
