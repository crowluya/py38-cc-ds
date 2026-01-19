# Notes CLI 📝

A powerful, efficient CLI note-taking tool written in Rust with markdown support, full-text search, and tag-based organization.

## Features ✨

- **📝 Markdown Support**: Create and manage notes in markdown format
- **🔍 Full-Text Search**: Quickly search through all your notes
- **🏷️ Tag System**: Organize notes with tags for easy filtering
- **💾 Local Storage**: Notes stored efficiently in a local directory structure
- **🎨 Colorized Output**: Beautiful terminal output with colored formatting
- **⚡ Fast**: Built with Rust for speed and efficiency
- **📅 Date Organization**: Notes automatically organized by date

## Installation 📦

### Prerequisites

- Rust 1.70 or higher
- Cargo (comes with Rust)

### Build from Source

```bash
# Clone or navigate to the project directory
cd notes-cli

# Build the project
cargo build --release

# The binary will be available at target/release/notes
```

### Install System-Wide (Optional)

```bash
# Install to ~/.cargo/bin
cargo install --path .

# Make sure ~/.cargo/bin is in your PATH
export PATH="$HOME/.cargo/bin:$PATH"
```

## Quick Start 🚀

### Initialize Notes Directory

```bash
notes init
```

This creates a notes directory at `~/notes` (or your configured location).

### Create Your First Note

```bash
notes create "My First Note" --tags rust,cli
```

You'll be prompted to enter the note content.

### List All Notes

```bash
notes list
```

### View a Note

```bash
notes view <note-id>
```

### Search Notes

```bash
notes search "rust"
```

### Edit a Note

```bash
notes edit <note-id>
```

### Delete a Note

```bash
notes delete <note-id>
```

## Usage 📖

### Commands

#### `notes create <title> [--tags <tags>]`

Create a new note with the given title.

**Options:**
- `--tags, -t <tags>`: Comma-separated list of tags to add

**Examples:**
```bash
notes create "Rust Basics" --tags rust,programming
notes create "Shopping List" --tags personal
```

#### `notes list [--tag <tag>] [--limit <n>]`

List all notes or filter by tag.

**Options:**
- `--tag, -t <tag>`: Filter notes by tag
- `--limit, -l <n>`: Maximum number of notes to display (default: 50)

**Examples:**
```bash
notes list
notes list --tag rust
notes list --limit 10
```

#### `notes view <id>`

Display a note's full content with metadata.

**Example:**
```bash
notes view 123e4567-e89b-12d3-a456-426614174000
```

#### `notes edit <id>`

Edit an existing note's content.

**Example:**
```bash
notes edit 123e4567-e89b-12d3-a456-426614174000
```

#### `notes delete <id> [--force]`

Delete a note. Requires confirmation unless `--force` is used.

**Options:**
- `--force, -f`: Skip confirmation prompt

**Examples:**
```bash
notes delete 123e4567-e89b-12d3-a456-426614174000
notes delete 123e4567-e89b-12d3-a456-426614174000 --force
```

#### `notes search <query>`

Search for notes by title or content.

**Example:**
```bash
notes search "rust programming"
notes search "shopping"
```

#### `notes tag <subcommand>`

Manage tags on notes.

**Subcommands:**

- `notes tag add <id> <tag>`: Add a tag to a note
  ```bash
  notes tag add 123e4567-e89b-12d3-a456-426614174000 important
  ```

- `notes tag remove <id> <tag>`: Remove a tag from a note
  ```bash
  notes tag remove 123e4567-e89b-12d3-a456-426614174000 important
  ```

- `notes tag list`: List all tags with note counts
  ```bash
  notes tag list
  ```

## Configuration ⚙️

Configuration is stored in `~/.config/notes/config.json`.

**Default Configuration:**

```json
{
  "notes_dir": "~/notes",
  "editor": null,
  "render_markdown": true,
  "list_limit": 50
}
```

**Options:**

- `notes_dir`: Directory where notes are stored
- `editor`: Default editor (uses `$EDITOR` environment variable if set)
- `render_markdown`: Enable markdown rendering in terminal
- `list_limit`: Maximum number of notes to display in list command

You can edit the configuration file manually to change these settings.

## Storage Structure 📁

Notes are organized by date in the following structure:

```
notes/
├── 2024/
│   ├── 01/
│   │   ├── 15-093012-my-note-title.md
│   │   └── 15-143045-another-note.md
│   └── 02/
│       └── 01-103000-february-note.md
```

Each note file contains:

1. **Frontmatter** (YAML format):
   ```yaml
   ---
   id: 123e4567-e89b-12d3-a456-426614174000
   title: My Note Title
   tags:
     - rust
     - cli
   created_at: 2024-01-15T09:30:12Z
   updated_at: 2024-01-15T09:30:12Z
   ---
   ```

2. **Markdown Content**:
   ```markdown
   This is the note content in markdown format.

   You can use any markdown formatting:
   - **Bold text**
   - *Italic text*
   - `Code snippets`
   - Lists
   - And more!
   ```

## Examples 💡

### Workflow Example: Daily Journal

```bash
# Create a journal entry
notes create "2024-01-15 Journal Entry" --tags journal,personal

# List all journal entries
notes list --tag journal

# Search for specific topics in your journal
notes search "meeting notes"

# Add an additional tag to a specific entry
notes tag add <note-id> work

# View yesterday's entry
notes view <yesterday-note-id>
```

### Workflow Example: Research Notes

```bash
# Create research notes with relevant tags
notes create "Rust Ownership Model" --tags rust,research,programming
notes create "CLI Design Patterns" --tags rust,cli,design

# Find all research notes
notes list --tag research

# Search for specific topics
notes search "ownership"

# List all programming-related tags
notes tag list
```

## Development 🔧

### Running Tests

```bash
# Run all tests
cargo test

# Run tests with output
cargo test -- --nocapture

# Run specific test
cargo test test_note_lifecycle
```

### Building Documentation

```bash
# Generate and open documentation
cargo doc --open
```

### Code Structure

- `src/main.rs`: Application entry point
- `src/cli.rs`: CLI command definitions and handlers
- `src/types.rs`: Core data structures (Note, Config, etc.)
- `src/storage.rs`: File storage and I/O operations
- `src/config.rs`: Configuration management
- `src/error.rs`: Error types and handling

## Performance 🚀

- **Fast Search**: Efficient file-based search through notes
- **Lazy Loading**: Notes loaded on-demand
- **Minimal Memory**: Efficient data structures
- **Concurrent Safe**: Thread-safe operations

## Roadmap 🗺️

Future enhancements planned:

- [ ] Markdown rendering in terminal
- [ ] Note templates
- [ ] Version control integration
- [ ] Cloud sync support
- [ ] Interactive mode with REPL
- [ ] Note pinning/favoriting
- [ ] Advanced search filters (date ranges, regex)
- [ ] Import/export from other note formats

## Contributing 🤝

Contributions are welcome! Please feel free to submit a Pull Request.

## License 📄

This project is open source and available under the MIT License.

## Troubleshooting 🔍

### Issue: "Notes directory not found"

**Solution:** Run `notes init` to initialize the notes directory.

### Issue: "Note not found"

**Solution:** Use `notes list` to see all available note IDs.

### Issue: "Permission denied"

**Solution:** Check that you have write permissions for the notes directory.

## Acknowledgments 🙏

Built with:
- [Clap](https://github.com/clap-rs/clap) - CLI argument parsing
- [Chrono](https://github.com/chronotope/chrono) - Date and time handling
- [Serde](https://github.com/serde-rs/serde) - Serialization
- [Colored](https://github.com/mackwic/colored) - Terminal colors
- [Pulldown-cmark](https://github.com/raphlinus/pulldown-cmark) - Markdown parsing

---

**Happy Note-Taking! 📝✨**
