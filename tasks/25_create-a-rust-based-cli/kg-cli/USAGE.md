# KG CLI - Usage Guide

## Table of Contents
1. [Getting Started](#getting-started)
2. [Creating Notes](#creating-notes)
3. [Linking Notes](#linking-notes)
4. [Searching](#searching)
5. [Managing Notes](#managing-notes)
6. [Graph Visualization](#graph-visualization)
7. [Advanced Features](#advanced-features)
8. [Tips and Tricks](#tips-and-tricks)

## Getting Started

### Installation

After building the project, you can either:
1. Add `target/release/kg` to your PATH
2. Use `cargo run --` from the project directory
3. Install globally with `cargo install --path .`

### First Steps

```bash
# Initialize your knowledge graph
kg init

# Create your first note
kg new "Welcome" --content "My first note!"

# List all notes
kg list

# Show a note
kg show "welcome"
```

## Creating Notes

### Basic Note Creation

```bash
kg new "Note Title"
```
This will prompt you to enter the note content.

### With Content

```bash
kg new "Quick Note" --content "This is the content"
```

### With Tags

```bash
kg new "Tagged Note" --content "Content here" --tags "tag1,tag2,tag3"
```

### Multi-line Content

```bash
kg new "Long Note" --content "Line 1
Line 2
Line 3"
```

## Linking Notes

### Basic Links

Use `[[note-name]]` syntax in your note content:

```markdown
Check out [[rust-tips]] for more information.
```

### Link Aliases

Display different text than the note ID:

```markdown
See [[rust-tips|Rust Tips]] for details.
```

The link will point to "rust-tips" but display as "Rust Tips".

### Automatic Backlinks

When Note A links to Note B, Note B automatically gets a backlink to Note A.

View backlinks:
```bash
kg show "note-b" --backlinks

# Or use the dedicated command
kg backlinks "note-b"
```

### Link Resolution

Notes are identified by their ID (lowercase, hyphenated). The system matches:
1. Exact ID match
2. Case-insensitive title match
3. Partial title match

Examples:
- `kg show "rust-tips"` - Exact ID match
- `kg show "Rust Tips"` - Title match (case-insensitive)
- `kg show "rust"` - Partial match (if unique)

## Searching

### Basic Search

```bash
kg search "query"
```

Searches through:
- Note titles (highest weight)
- Note content
- Tags

### Fuzzy Search

```bash
kg search "query" --fuzzy
```

Fuzzy search finds matches even if characters aren't consecutive.

### Limit Results

```bash
kg search "query" --limit 5
```

### Search Scoring

Results are ranked by relevance:
- Exact title match: +30 points
- Title contains query: +10 points
- Tag contains query: +5 points
- Content match: +1 point per occurrence

## Managing Notes

### View Notes

```bash
# Basic view
kg show "note-id"

# With forward links
kg show "note-id" --links

# With backlinks
kg show "note-id" --backlinks

# With both
kg show "note-id" --links --backlinks
```

### Edit Notes

```bash
# Interactive edit
kg edit "note-id"

# Replace content
kg edit "note-id" --content "New content"
```

### Delete Notes

```bash
# With confirmation
kg delete "note-id"

# Force delete (no confirmation)
kg delete "note-id" --force
```

### List Notes

```bash
# Simple list
kg list

# Detailed view
kg list --detailed
```

## Graph Visualization

### Export to DOT Format

```bash
kg export --format dot --output graph.dot
```

Then visualize with Graphviz:
```bash
dot -Tpng graph.dot -o graph.png
dot -Tsvg graph.dot -o graph.svg
```

### Export to JSON

```bash
kg export --format json --output graph.json
```

Use with other tools:
```bash
# Pretty print
jq '.' graph.json

# Extract note titles
jq '.notes | .[].title' graph.json

# Count links
jq '.forward_links | to_entries | map(.value | length) | add' graph.json
```

### Graph Statistics

```bash
kg stats
```

Output includes:
- Total note count
- Total link count
- Orphaned notes (no links)
- Most connected notes

View top N most connected:
```bash
kg stats --top 20
```

## Advanced Features

### Custom Notes Directory

By default, notes are stored in `.kg/` in the current directory. Use a custom location:

```bash
kg --dir ~/my-knowledge list
kg --dir ~/my-knowledge new "Test"
```

Or set an alias:
```bash
alias kg='kg --dir ~/my-knowledge'
```

### Combining with Other Tools

#### Edit with Your Favorite Editor

```bash
kg new "Draft" --content "$(vim -)"
kg edit "existing-note" --content "$(nano -)"
```

#### Search and Process

```bash
# Count matches
kg search "rust" | wc -l

# Extract note IDs
kg search "rust" | grep -oP '\(\K[^)]+(?=\))'

# Grep through notes
kg list --detailed | grep "rust"
```

#### Pipeline Operations

```bash
# Export and analyze
kg export --format json --output - | jq '.notes | length'

# Create backup
tar czf backup-$(date +%Y%m%d).tar.gz .kg/

# Find broken links
kg export --format json --output - | \
  jq '.forward_links | to_entries[] | select(.value | length > 0)' | \
  grep -oP '"to":"\K[^"]+' | \
  sort -u | \
  comm -23 <(cat) <(jq -r '.notes | keys[]' <(kg export --format json --output -))
```

## Tips and Tricks

### Organizing Your Knowledge

1. **Use tags consistently**:
   ```bash
   kg new "Concept" --tags "category,sub-category,status"
   ```

2. **Create index notes**:
   ```bash
   kg new "Rust Resources" --content "
   ## Learning
   - [[rust-basics]]
   - [[rust-ownership]]

   ## Tools
   - [[cargo-guide]]
   - [[rust-cli-tools]]
   "
   ```

3. **Use atomic notes**: Keep each note focused on a single concept.

### Building a Zettelkasten

1. Create permanent notes for concepts
2. Link freely between notes
3. Use backlinks to discover connections
4. Regularly review orphaned notes

```bash
# Find orphaned notes
kg stats | grep "Orphaned"

# Review a random note
NOTE_ID=$(kg list | grep -oP '\d+\. \K[\w-]+' | shuf -n 1)
kg show "$NOTE_ID" --links --backlinks
```

### Daily Workflow

```bash
# Daily note
DATE=$(date +%Y-%m-%d)
kg new "Daily-$DATE" --tags "daily,$(date +%Y-%m)"

# Review yesterday's links
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d)
kg backlinks "daily-$YESTERDAY"
```

### Backup and Sync

```bash
# Backup
cp -r .kg/ .kg.backup/

# Sync to remote
rsync -av .kg/ user@server:backups/kg/

# Git tracking
cd .kg
git init
git add .
git commit -m "Update notes"
git push origin main
```

### Performance Tips

1. **Keep notes focused**: Split large notes into smaller, linked notes
2. **Use search effectively**: Specific queries are faster than fuzzy search
3. **Export regularly**: Large graphs export faster to JSON than DOT
4. **Clean up**: Regularly review and delete outdated notes

## Troubleshooting

### "Knowledge graph not initialized"

```bash
kg init
```

### "Note not found"

1. Check the note ID with `kg list`
2. Try a partial match: `kg show "partial-title"`
3. Verify the note exists: `ls .kg/`

### Links not showing

1. Rebuild the graph:
   ```bash
   rm .kg/*.md  # Don't do this if you want to keep notes!
   # Instead, the graph rebuilds automatically on load
   ```

2. Verify link syntax: `[[note-name]]`

3. Check if target note exists: `kg list`

### Search returns no results

1. Try fuzzy search: `kg search "query" --fuzzy`
2. Use shorter queries
3. Check spelling: `kg list | grep -i "query"`

## Examples

### Create a Learning Path

```bash
# Create topic
kg new "Rust Async" --tags "rust,async"

# Create prerequisites
kg new "Rust Futures" --content "Prerequisite for [[rust-async]]" --tags "rust"
kg new "Tokio Runtime" --content="Async runtime, see [[rust-async]]" --tags "rust,tokio"

# View the path
kg backlinks "rust-async"
kg show "rust-futures" --links
```

### Build a Project Log

```bash
# Project note
kg new "Project X" --content "Project overview" --tags "project,active"

# Daily updates
kg new "Project X - 2024-01-15" --content "
Progress on [[project-x]]:
- Implemented feature A
- Fixed bug B
" --tags "project-x,daily"

# View all project notes
kg search "project-x"
```

### Create a Reading List

```bash
kg new "Books to Read" --content "
## Technical
- [[the-rust-book]]
- [[clean-code]]

## Fiction
- [[dune]]
- [[three-body-problem]]
"

kg new "The Rust Book" --content "
Official Rust programming book.
Part of [[books-to-read]].
" --tags "book,rust,reading"
```
