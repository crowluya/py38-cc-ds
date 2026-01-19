#!/bin/bash
# Quick Start Script for KG CLI

set -e

echo "🚀 KG CLI - Quick Start"
echo "======================="
echo ""

# Check if Rust is installed
if ! command -v cargo &> /dev/null; then
    echo "❌ Cargo not found. Please install Rust first:"
    echo "   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
    exit 1
fi

echo "✅ Rust toolchain found"
echo ""

# Build the project
echo "📦 Building KG CLI..."
cargo build --release
echo "✅ Build complete"
echo ""

# Initialize knowledge graph
echo "🔧 Initializing knowledge graph..."
./target/release/kg init
echo "✅ Knowledge graph initialized in .kg/"
echo ""

# Create sample notes
echo "📝 Creating sample notes..."
./target/release/kg new "Welcome to KG CLI" --content "
# Welcome to KG CLI!

This is your first note. KG CLI is a personal knowledge graph management tool.

## Features
- Bi-directional linking: [[bi-directional-linking]]
- Full-text search: [[search-features]]
- Graph visualization: [[graph-visualization]]

Try creating a new note with:
  kg new \"My Note\" --content \"Some content\"
" --tags "welcome,tutorial"

./target/release/kg new "Bi-directional Linking" --content "
# Bi-directional Linking

When you link from Note A to Note B, Note B automatically shows a backlink to Note A.

## Syntax
Use [[wiki-style]] links in your notes.

## Example
This note is linked from [[welcome-to-kg-cli]], so it has a backlink.

Check backlinks with:
  kg backlinks \"bi-directional-linking\"
" --tags "feature,linking"

./target/release/kg new "Search Features" --content "
# Search Features

KG CLI supports powerful full-text search across all your notes.

## Search Types
- Exact search: Finds exact matches
- Fuzzy search: Finds partial matches

## Usage
\`\`\`bash
kg search \"query\"
kg search \"query\" --fuzzy
\`\`\`

Search looks through titles, content, and tags.

This note is linked from [[welcome-to-kg-cli]].
" --tags "feature,search"

./target/release/kg new "Graph Visualization" --content "
# Graph Visualization

Export your knowledge graph to visualize connections between notes.

## Export Formats
- **DOT**: Graphviz format for visualization
- **JSON**: Machine-readable format

## Usage
\`\`\`bash
# Export to DOT
kg export --format dot --output graph.dot

# Visualize with Graphviz
dot -Tpng graph.dot -o graph.png
\`\`\`

This note is linked from [[welcome-to-kg-cli]].
" --tags "feature,visualization"

echo "✅ Sample notes created"
echo ""

# Show list
echo "📚 Your notes:"
./target/release/kg list
echo ""

# Show statistics
echo "📊 Graph statistics:"
./target/release/kg stats
echo ""

echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "  1. View a note:           ./target/release/kg show \"welcome-to-kg-cli\""
echo "  2. Search notes:          ./target/release/kg search \"feature\""
echo "  3. Create a new note:     ./target/release/kg new \"My Note\""
echo "  4. See backlinks:         ./target/release/kg backlinks \"bi-directional-linking\""
echo "  5. View documentation:    cat README.md"
echo ""
echo "For more usage examples, see USAGE.md"
echo ""
