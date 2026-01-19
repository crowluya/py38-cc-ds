# KG CLI - Personal Knowledge Graph Management Tool

A powerful command-line tool for managing personal knowledge graphs with bi-directional linking, backlink discovery, graph visualization, and full-text search.

## Features

- 📝 **Note Management**: Create, read, update, and delete notes
- 🔗 **Bi-directional Linking**: Support for `[[wiki-style]]` links with automatic backlink tracking
- 🔍 **Full-text Search**: Search across all notes with relevance ranking
- 📊 **Graph Visualization**: Export to DOT (Graphviz) and JSON formats
- 📈 **Graph Statistics**: Analyze your knowledge graph structure
- 🏷️ **Tagging**: Organize notes with tags
- 💾 **Local Storage**: Markdown files with JSON frontmatter

## Installation

### Prerequisites

- Rust toolchain (1.70 or later)
- Cargo package manager

### Build from Source

```bash
git clone <repository-url>
cd kg-cli
cargo build --release
```

The compiled binary will be available at `target/release/kg`.

### Install System-wide

```bash
cargo install --path .
```

## Quick Start

### Initialize

```bash
kg init
```

This creates a `.kg` directory in your current folder to store notes.

### Create Your First Note

```bash
kg new "Getting Started" --content "Welcome to KG CLI!"
```

### List All Notes

```bash
kg list
```

### Show a Note

```bash
kg show "getting-started"
```

### Search Notes

```bash
kg search "welcome"
```

## Usage

### Commands

#### `kg init`

Initialize a new knowledge graph in the current directory.

```bash
kg init
```

#### `kg new`

Create a new note.

```bash
kg new <title> [OPTIONS]

Options:
  -c, --content <string>    Note content (prompts if not provided)
  -t, --tags <tags>         Comma-separated tags
```

Examples:

```bash
# Interactive
kg new "My Note"

# With content
kg new "Rust Tips" --content "Use cargo for package management"

# With tags
kg new "Learning" --content "Today I learned..." --tags "til,learning"
```

#### `kg show`

Display a note's content.

```bash
kg show <note-id> [OPTIONS]

Options:
  -b, --backlinks    Show backlinks
  -l, --links        Show forward links
```

Examples:

```bash
kg show "rust-tips"
kg show "rust-tips" --backlinks
kg show "rust-tips" --links
```

#### `kg list`

List all notes.

```bash
kg list [OPTIONS]

Options:
  -d, --detailed    Show detailed information
```

Examples:

```bash
kg list
kg list --detailed
```

#### `kg edit`

Edit an existing note.

```bash
kg edit <note-id> [OPTIONS]

Options:
  -c, --content <string>    New content (prompts if not provided)
```

Examples:

```bash
kg edit "rust-tips"
kg edit "rust-tips" --content "Updated content"
```

#### `kg delete`

Delete a note.

```bash
kg delete <note-id> [OPTIONS]

Options:
  -f, --force    Skip confirmation
```

Examples:

```bash
kg delete "old-note"
kg delete "old-note" --force
```

#### `kg search`

Search across all notes.

```bash
kg search <query> [OPTIONS]

Options:
  -f, --fuzzy        Use fuzzy search
  -l, --limit <n>    Maximum results (default: 10)
```

Examples:

```bash
kg search "rust"
kg search "programming" --fuzzy
kg search "todo" --limit 5
```

#### `kg backlinks`

Show all notes that link to the given note.

```bash
kg backlinks <note-id>
```

Example:

```bash
kg backlinks "rust-tips"
```

#### `kg export`

Export the knowledge graph.

```bash
kg export [OPTIONS] --output <file>

Options:
  -f, --format <format>    Output format: dot or json (default: dot)
  -o, --output <file>      Output file path
```

Examples:

```bash
# Export to Graphviz DOT format
kg export --format dot --output graph.dot

# Export to JSON
kg export --format json --output graph.json

# Visualize with Graphviz
kg export --format dot --output graph.dot
dot -Tpng graph.dot -o graph.png
```

#### `kg stats`

Display knowledge graph statistics.

```bash
kg stats [OPTIONS]

Options:
  -t, --top <n>    Show top N most connected notes
```

Examples:

```bash
kg stats
kg stats --top 10
```

## Linking Syntax

KG CLI uses `[[wiki-style]]` linking. Links are automatically converted to lowercase with hyphens.

### Basic Linking

```markdown
Check out [[rust-tips]] for more information.
```

### Link Aliases

You can use a different display text:

```markdown
See [[rust-tips|Rust Tips]] for more.
```

### Automatic Backlinks

When you create a link from Note A to Note B, Note B automatically gets a backlink to Note A.

## Storage Format

Notes are stored as Markdown files with JSON frontmatter in the `.kg` directory:

```markdown
---
{
  "id": "rust-tips",
  "title": "Rust Tips",
  "content": "Use cargo for package management",
  "created_at": "2024-01-15T10:30:00Z",
  "modified_at": "2024-01-15T10:30:00Z",
  "tags": ["rust", "programming"]
}
---
Use cargo for package management
```

## Examples

Create example notes to test all features:

```bash
cd examples
./create_example_notes.sh
```

This will create a sample knowledge graph with interconnected notes demonstrating:
- Bi-directional linking
- Backlink discovery
- Tag usage
- Graph visualization

## Workflow Example

1. **Initialize** your knowledge graph:
   ```bash
   kg init
   ```

2. **Create notes** with links:
   ```bash
   kg new "Rust Ownership" --content "Ownership is Rust's key feature"
   kg new "Rust Tips" --content="See [[rust-ownership]] for details"
   ```

3. **View backlinks** to see connections:
   ```bash
   kg show "rust-ownership" --backlinks
   ```

4. **Search** across your knowledge:
   ```bash
   kg search "rust"
   ```

5. **Export** your graph for visualization:
   ```bash
   kg export --format dot --output my-graph.dot
   dot -Tpng my-graph.dot -o my-graph.png
   ```

6. **View statistics** about your knowledge graph:
   ```bash
   kg stats --top 10
   ```

## Advanced Usage

### Custom Directory

Use a custom notes directory:

```bash
kg --dir ~/my-notes list
```

### Combining with Other Tools

```bash
# Edit notes with your favorite editor
kg new "Draft" --content "$(vim -)"

# Search and pipe to other tools
kg search "rust" | grep "Ownership"

# Export and process with jq
kg export --format json --output graph.json
jq '.notes | length' graph.json
```

## Development

### Running Tests

```bash
# Unit tests
cargo test

# Integration tests
cargo test --test integration_tests

# Run with coverage
cargo tarpaulin --out Html
```

### Project Structure

```
kg-cli/
├── src/
│   ├── main.rs          # CLI entry point and command handlers
│   ├── lib.rs           # Library exports
│   ├── types.rs         # Core data structures
│   ├── linking.rs       # Link parsing and validation
│   ├── storage.rs       # File I/O and persistence
│   ├── search.rs        # Search algorithms
│   └── export.rs        # Graph visualization exports
├── tests/
│   └── integration_tests.rs
├── examples/
│   └── create_example_notes.sh
└── Cargo.toml
```

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Roadmap

- [ ] Web UI for graph visualization
- [ ] Note templates
- [ ] Incremental search
- [ ] Git integration
- [ ] Note aliasing
- [ ] Attachment support
- [ ] Calendar integration
- [ ] Mobile app

## Related Projects

- [Obsidian](https://obsidian.md) - A powerful knowledge base that works on top of a local folder
- [Roam Research](https://roamresearch.com) - A note-taking tool for networked thought
- [Zettelkasten](https://en.wikipedia.org/wiki/Zettelkasten) - A method of note-taking and personal knowledge management
