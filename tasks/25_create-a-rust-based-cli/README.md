# Task Workspace

Task #25: Create a Rust-based CLI tool for managing personal

## Summary
- Priority: THOUGHT
- Project: None
- Created: 2026-01-19T12:31:09.396564

## Description
Create a Rust-based CLI tool for managing personal knowledge graphs with bi-directional linking, backlink discovery, graph visualization export (DOT/JSON), and full-text search across interconnected notes.

## Plan & Analysis
# Executive Summary
This task requires building a Rust CLI tool from scratch for personal knowledge management with core features like bi-directional linking, backlink discovery, graph visualization exports, and full-text search. The project will need proper project structure, note storage format, CLI argument parsing, and visualization capabilities. This is a moderately complex application that combines data structures, text processing, file I/O, and graph algorithms.

# Task Analysis

## Core Requirements
1. **CLI Interface**: Command-line tool with subcommands for different operations
2. **Note Management**: Create, read, update, delete notes
3. **Bi-directional Linking**: Support `[[link]]` syntax with automatic backlink tracking
4. **Backlink Discovery**: Automatically discover and display notes linking to current note
5. **Graph Visualization**: Export knowledge graph in DOT (Graphviz) and JSON formats
6. **Full-text Search**: Search across all note content with relevance ranking
7. **Storage**: Persistent storage of notes on filesystem

## Technical Stack Considerations
- **Language**: Rust (required)
- **CLI Framework**: `clap` for argument parsing
- **Serialization**: `serde` for JSON operations
- **Storage**: Filesystem-based (simple text files or database)
- **Search**: Basic string matching or more advanced indexing
- **Graph Export**: DOT format generation and JSON serialization

# Structured TODO List

## Phase 1: Project Setup & Foundation
1. **Initialize Rust project structure** - Create new Cargo project with proper directory layout
2. **Add core dependencies** - Add `clap`, `serde`, `serde_json`, `regex`, and other required crates to Cargo.toml
3. **Define core data structures** - Create `Note`, `Link`, `KnowledgeGraph` structs with necessary fields
4. **Design note storage format** - Decide on file format (Markdown with frontmatter, JSON, or custom format)

## Phase 2: Core Note Operations
5. **Implement note creation** - Command to create new notes with title and content
6. **Implement note reading** - Display note content with formatted links
7. **Implement note listing** - List all available notes with metadata
8. **Implement note updating/editing** - Modify existing note content
9. **Implement note deletion** - Remove notes with confirmation

## Phase 3: Linking System
10. **Implement link parsing** - Parse `[[note_name]]` syntax from note content using regex
11. **Implement forward links extraction** - Extract all links from a note
12. **Implement backlink discovery** - Find all notes that link to the current note
13. **Create link validation** - Check if linked notes exist, warn about broken links
14. **Display backlinks command** - CLI command to show backlinks for a note

## Phase 4: Search Functionality
15. **Implement basic content search** - Search note titles and content for query string
16. **Add search result ranking** - Simple relevance scoring based on matches
17. **Create search CLI command** - Expose search functionality via CLI
18. **Add fuzzy search support** - Optional: Implement fuzzy matching for better UX

## Phase 5: Graph Visualization
19. **Implement graph data structure** - Internal representation of the knowledge graph
20. **Create DOT format exporter** - Generate Graphviz DOT format for visualization
21. **Create JSON format exporter** - Export graph structure as JSON
22. **Add export CLI commands** - Commands to export graph in different formats
23. **Implement graph statistics** - Display graph metrics (node count, edge count, orphaned notes)

## Phase 6: Testing & Polish
24. **Write unit tests** - Test core functions (link parsing, backlink discovery, search)
25. **Write integration tests** - Test CLI commands end-to-end
26. **Add error handling** - Proper error messages and graceful failure handling
27. **Create example notes** - Sample notes demonstrating linking functionality
28. **Write README documentation** - Usage instructions, examples, and feature overview
29. **Add man page or help text** - Comprehensive CLI help documentation

## Phase 7: Advanced Features (Optional)
30. **Implement tag system** - Add tags to notes and enable tag-based filtering
31. **Add graph filtering** - Filter exported graph by tags or date ranges
32. **Implement incremental search** - Real-time search as user types
33. **Add note templates** - Predefined templates for common note types
34. **Implement note aliasing** - Allow notes to have multiple names/aliases

# Approach & Strategy

## Architecture Decisions
1. **Storage Approach**: Use plain text Markdown files with `[[link]]` syntax - simple, human-readable, and version-control friendly
2. **File Structure**: Store notes in a `.kg` or `notes` directory in user's home or current directory
3. **Index Generation**: On startup or command, scan all notes and build in-memory graph index
4. **CLI Structure**: Use subcommands (`kg new`, `kg show`, `kg search`, `kg export`, etc.)

## Development Order
- Start with basic CRUD operations
- Add link parsing and backlink discovery (core differentiator)
- Implement search functionality
- Add graph visualization
- Polish with testing and documentation

## Key Technical Challenges
- **Link Resolution**: Handling case sensitivity, special characters in note names
- **Incremental Updates**: Efficiently updating graph index when notes change
- **Search Performance**: Scaling full-text search as note count grows
- **DOT Format**: Properly escaping special characters in generated DOT files

# Assumptions & Potential Blockers

## Assumptions
1. User has Rust toolchain installed (1.70+)
2. Notes will be stored locally (no cloud sync initially)
3. Standard `[[wiki-style]]` linking syntax is acceptable
4. CLI tool will be run from terminal (no TUI initially)

## Potential Blockers
1. **Regex Complexity**: Parsing links with escaped brackets or nested brackets could be tricky
2. **Circular References**: Graph visualization needs to handle cycles gracefully
3. **Filesystem Permissions**: Need proper error handling for read/write failures
4. **Special Characters**: Note names with slashes or special characters may need sanitization
5. **Search Performance**: For large note collections (>1000), naive search may be slow

## Risk Mitigation
- Use well-tested crates (`regex`, `clap`, `serde`) to avoid reimplementation
- Start with simple search, optimize later if needed
- Add comprehensive error messages for user guidance
- Create example notes for testing edge cases

# Effort Estimates
- **Phase 1**: 2-3 hours (setup, data structures, dependencies)
- **Phase 2**: 4-5 hours (CRUD operations)
- **Phase 3**: 4-6 hours (linking system - most complex core feature)
- **Phase 4**: 3-4 hours (search functionality)
- **Phase 5**: 3-4 hours (graph visualization)
- **Phase 6**: 4-5 hours (testing, documentation, polish)
- **Phase 7**: 5-8 hours (optional advanced features)

**Total Core Implementation**: ~20-27 hours for Phases 1-6
**Total with Advanced Features**: ~25-35 hours for all phases

## TODO List
(Updated by worker agent)

## Status: PARTIAL

## Outstanding Items
(None)

## Recommendations
(None)

## Execution Summary

### Execution 2026-01-19 12:36:52
- Status: ✅ COMPLETED
- Files Modified: 34
- Duration: 342s

## Execution Summary
