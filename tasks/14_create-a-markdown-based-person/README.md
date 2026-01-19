# PK - Personal Knowledge Management System

A Markdown-based personal knowledge management system with a CLI interface that supports tagging, bidirectional linking, and full-text search across notes.

## Features

- **Markdown Notes**: Store notes in standard Markdown format with YAML frontmatter
- **Tagging System**: Organize notes with tags (#tag) for easy filtering and discovery
- **Bidirectional Linking**: Create wiki-style [[links]] between notes with automatic backlink tracking
- **Full-Text Search**: Search across note titles, content, and tags with relevance ranking
- **CLI Interface**: Simple, intuitive command-line interface for all operations
- **Link Validation**: Detect broken links and orphan notes
- **Rich Output**: Beautiful terminal output with syntax highlighting and formatting

## Installation

### Prerequisites

- Python 3.10 or higher
- pip package manager

### Install from source

```bash
# Navigate to the project directory
cd workspace/tasks/14_create-a-markdown-based-person

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install the package in development mode
pip install -e .
```

## Quick Start

### 1. Initialize PK

```bash
pk init
```

This creates:
- Configuration file at `~/.config/pk/config.toml`
- Notes directory at `~/notes` (or custom path)

### 2. Create your first note

```bash
pk new "Getting Started with PK" --tag productivity --tag knowledge
```

This opens your default editor (vim, or set `$EDITOR`).

### 3. Add content and links

In your note, create links to other notes using wiki-style syntax:

```markdown
# Getting Started with PK

PK is a great tool for managing your personal knowledge base.

Related concepts:
- [[Zettelkasten Method]]
- [[Note-taking Best Practices]]
```

### 4. Search and explore

```bash
# Search for notes
pk search "productivity"

# List all notes
pk list

# Show all tags
pk tags

# Filter by tag
pk tag productivity
```

## Usage

### Core Commands

#### Create a new note
```bash
pk new <title> [--tag TAG] [--content CONTENT]
```

Example:
```bash
pk new "Python Best Practices" --tag python --tag programming
```

#### List all notes
```bash
pk list [--tag TAG] [--limit N]
```

Example:
```bash
pk list --tag python --limit 10
```

#### Show a note
```bash
pk show <title>
```

Example:
```bash
pk show "Python Best Practices"
```

#### Edit a note
```bash
pk edit <title>
```

Opens the note in your configured editor.

#### Delete a note
```bash
pk delete <title> [--force]
```

Example:
```bash
pk delete "Old Note"
pk delete "Old Note" --force  # Skip confirmation
```

### Search Commands

#### Full-text search
```bash
pk search <query> [--limit N]
```

Searches across titles, content, and tags.

Example:
```bash
pk search "async programming"
```

#### List all tags
```bash
pk tags
```

Shows all tags with usage counts.

#### Show notes with a tag
```bash
pk tag <tagname>
```

Example:
```bash
pk tag python
```

### Link Commands

#### Show backlinks
```bash
pk backlinks <title>
```

Shows all notes that link to the specified note.

Example:
```bash
pk backlinks "Python Best Practices"
```

#### Check link integrity
```bash
pk check-links
```

Reports:
- Broken links (links to non-existent notes)
- Orphan notes (no other notes link to them)

### Configuration Commands

#### Initialize/reinitialize configuration
```bash
pk init
```

Creates/updates configuration file.

#### Show system information
```bash
pk info
```

Displays configuration and statistics.

## Note Format

### Frontmatter

Each note has YAML frontmatter:

```yaml
---
title: Note Title
created: 2024-01-19T12:00:00
modified: 2024-01-19T12:00:00
tags: [tag1, tag2, tag3]
---

Note content here...
```

### Linking Syntax

Create links using double brackets:

```markdown
# My Note

This links to [[Another Note]].

You can also use aliases: [[Another Note|display text]]
```

### Tagging Syntax

Tags can be specified in two ways:

1. **In frontmatter**:
```yaml
tags: [python, programming, tutorial]
```

2. **Inline in content**:
```markdown
This note covers #python and #programming concepts.
```

Both methods work together and are merged automatically.

## Features in Detail

### Bidirectional Linking

When you create a link `[[Note B]]` in `Note A`:
- `Note A` shows `Note B` as an outgoing link
- `Note B` automatically shows `Note A` as a backlink

View backlinks:
```bash
pk backlinks "Note B"
```

### Full-Text Search

Search ranks results by relevance:
- **Title matches**: Highest weight (10 points)
- **Tag matches**: High weight (5 points)
- **Content matches**: Medium weight (1 point per occurrence)
- **Fuzzy matches**: Lower weight based on similarity

### Tag Management

- Tags are automatically normalized (lowercase, hyphens for spaces)
- View all tags: `pk tags`
- Filter notes by tag: `pk tag <tagname>`
- Combine tags: `pk list --tag python --tag tutorial`

### Link Validation

Keep your knowledge base healthy:
```bash
pk check-links
```

This identifies:
- **Broken links**: References to notes that don't exist
- **Orphan notes**: Notes that no other notes reference

## Configuration

PK stores configuration in `~/.config/pk/config.toml`:

```toml
notes_directory = "/home/user/notes"
default_editor = "vim"
tag_syntax = "#tag"
auto_index = true
index_file = ".pk_index.json"
```

### Environment Variables

- `EDITOR`: Sets your preferred text editor

Example:
```bash
export EDITOR=nano
pk edit "My Note"  # Opens in nano
```

## Examples

### Create a Zettelkasten-style Knowledge Base

```bash
# Create atomic notes
pk new "Atomic Design Principle" --tag design
pk new "Component-Driven Development" --tag programming

# Link related concepts
pk edit "Atomic Design Principle"
# Add: Related to [[Component-Driven Development]]

pk edit "Component-Driven Development"
# Add: Builds on [[Atomic Design Principle]]

# Check connections
pk backlinks "Atomic Design Principle"
pk backlinks "Component-Driven Development"
```

### Research Notes

```bash
# Create research notes
pk new "LLM Architecture Research" --tag ai --tag research --tag paper
pk new "Transformer Attention Mechanism" --tag ai --tag technical

# Link to sources
pk edit "LLM Architecture Research"
# Add:
# Key paper: [[Attention Is All You Need]]
# Implementation: [[Transformer Attention Mechanism]]

# Search your research
pk search "attention mechanism"
pk tag research
```

### Project Documentation

```bash
# Create project docs
pk new "Project Architecture" --tag project-alpha --tag docs
pk new "API Endpoints" --tag project-alpha --tag api
pk new "Database Schema" --tag project-alpha --tag database

# Link documentation
pk edit "Project Architecture"
# Add:
# See [[API Endpoints]] for integration points
# See [[Database Schema]] for data model

# Filter by project
pk list --tag project-alpha
```

## Tips and Best Practices

1. **Use descriptive titles**: Titles become your primary navigation
2. **Create atomic notes**: One concept per note for better linkability
3. **Link liberally**: Create connections between related concepts
4. **Use tags consistently**: Establish a personal tagging convention
5. **Check links regularly**: Run `pk check-links` to maintain integrity
6. **Search often**: Use `pk search` to discover forgotten connections
7. **Keep notes focused**: Long notes are hard to link and reference

## File Structure

```
~/.config/pk/
  └── config.toml          # Configuration file

~/notes/                   # Default notes directory
  ├── my-first-note.md
  ├── another-note.md
  └── project-notes.md

Each note file:
  - YAML frontmatter with metadata
  - Markdown content body
  - Standard .md file format
```

## Troubleshooting

### Editor not opening

Set the `EDITOR` environment variable:
```bash
export EDITOR=vim  # or nano, code, etc.
```

### Notes not showing

Rebuild the index:
```bash
pk info
```

The index is automatically rebuilt on each command.

### Broken links after renaming

PK uses note titles as identifiers. If you rename a note:
1. Update all links pointing to it
2. Or use `pk edit` to update the title in frontmatter

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Project Structure

```
src/pk/
  ├── __init__.py       # Package init
  ├── cli.py            # Command-line interface
  ├── config.py         # Configuration management
  ├── display.py        # Output formatting
  ├── models.py         # Data models
  ├── parser.py         # Markdown parsing
  ├── search.py         # Search engine
  └── storage.py        # Storage and indexing

tests/
  ├── test_parser.py    # Parser tests
  ├── test_search.py    # Search tests
  └── test_storage.py   # Storage tests
```

## License

MIT License - feel free to use and modify for your needs.

## Contributing

This is a personal knowledge management tool designed for individual use. Feel free to extend it with features that suit your workflow!

## Future Enhancements

Potential features for future versions:
- Web interface for browsing notes
- Graph visualization of note connections
- Note templates
- Image and attachment support
- Export to HTML/PDF
- Version history
- Collaboration features
- Plugin system
