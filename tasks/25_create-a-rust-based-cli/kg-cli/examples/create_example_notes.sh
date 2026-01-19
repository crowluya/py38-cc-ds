#!/bin/bash
# Script to create example notes for testing the KG CLI tool

# Initialize the knowledge graph
cargo run -- init

echo "Creating example notes..."

# Create note 1
cargo run -- new "Rust Programming" \
  --content "Rust is a systems programming language that runs blazingly fast, prevents segfaults, and guarantees thread safety.

Key features:
- Memory safety without garbage collection
- Concurrency without data races
- Zero-cost abstractions

See also [[rust-ownership]] and [[rust-cli-tools]]" \
  --tags "rust,programming"

# Create note 2
cargo run -- new "Rust Ownership" \
  --content "Ownership is Rust's most unique feature and enables memory safety guarantees.

Rules:
1. Each value has an owner
2. There can only be one owner at a time
3. When the owner goes out of scope, the value is dropped

Related: [[rust-programming]]" \
  --tags "rust,concepts"

# Create note 3
cargo run -- new "Rust CLI Tools" \
  --content "Building CLI tools in Rust is easy with great crates:

- [[clap]]: Command-line argument parsing
- [[tokio]]: Async runtime
- [[anyhow]]: Error handling

See [[rust-programming]] for basics." \
  --tags "rust,cli"

# Create note 4
cargo run -- new "Knowledge Graphs" \
  --content "A knowledge graph is a way to represent information as a network of interconnected concepts.

Benefits:
- See connections between ideas
- Discover related topics automatically
- Build on existing knowledge

This tool uses [[rust-cli-tools]] to manage [[personal-knowledge]]." \
  --tags "productivity,learning"

# Create note 5
cargo run -- new "Personal Knowledge Management" \
  --content "Personal Knowledge Management (PKM) helps you organize and connect your thoughts.

Popular methods:
- Zettelkasten
- PARA method
- Building a Second Brain

Tool: [[kg-cli]] for managing [[knowledge-graphs]]" \
  --tags "productivity,pkm"

# Create note 6
cargo run -- new "KG CLI" \
  --content "KG is a command-line tool for managing personal knowledge graphs.

Features:
- [[bi-directional-linking]]
- [[backlink-discovery]]
- [[graph-visualization]]
- [[full-text-search]]

Created with [[rust-cli-tools]]" \
  --tags "tool,rust"

# Create note 7
cargo run -- new "Bi-directional Linking" \
  --content "Bi-directional linking means that when you link from Note A to Note B, Note B automatically shows a backlink to Note A.

This makes it easy to:
- Discover connections you forgot about
- See all references to a concept
- Navigate your knowledge graph organically

Implemented in [[kg-cli]]" \
  --tags "feature,pkm"

# Create note 8
cargo run -- new "Backlink Discovery" \
  --content "Backlink discovery automatically finds all notes that reference the current note.

In [[kg-cli]], use:
\`kg backlinks <note>\`

This is part of [[bi-directional-linking]]" \
  --tags "feature"

# Create note 9
cargo run -- new "Graph Visualization" \
  --content "Export your knowledge graph to visualize connections.

Formats supported:
- DOT (Graphviz)
- JSON

Use [[kg-cli]] to export and visualize your [[knowledge-graphs]]" \
  --tags "feature,visualization"

# Create note 10
cargo run -- new "Full Text Search" \
  --content "Search across all note content to find relevant information.

[[kg-cli]] supports:
- Exact match search
- Fuzzy search
- Relevance ranking

Part of [[knowledge-graphs]] functionality" \
  --tags "feature,search"

echo "Example notes created!"
echo "Try: cargo run -- list"
echo "Try: cargo run -- search 'rust'"
echo "Try: cargo run -- show 'rust-programming' --backlinks"
