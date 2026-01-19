# Task Workspace

Task #32: Create a portable note search utility that indexes

## Summary
- Priority: THOUGHT
- Project: None
- Created: 2026-01-19T13:16:03.246437

## Description
Create a portable note search utility that indexes markdown files into an in-memory SQLite database with full-text search, supports tagging, filtering by date ranges, and exports results to JSON/HTML reports.

## Plan & Analysis
I'll analyze the task and create a comprehensive plan for building this portable note search utility.
Now I'll create a comprehensive plan for this portable note search utility project.

## Executive Summary

Build a self-contained Python CLI tool that scans markdown files, builds an in-memory SQLite FTS (Full-Text Search) index, and provides powerful search capabilities including tag filtering, date ranges, and exportable reports. The utility will be portable, dependency-light, and optimized for quick ad-hoc searching of personal knowledge bases.

## Task Analysis

This project requires building a complete search utility with the following core components:

1. **Markdown Parser**: Extract content, metadata (tags, dates), and structure from .md files
2. **SQLite FTS Engine**: In-memory database with full-text search indexing
3. **Tag System**: Parse and index tags from frontmatter or content
4. **Date Extraction**: Handle various date formats (file dates, frontmatter dates, content dates)
5. **Search Interface**: CLI with query syntax for text, tags, and date ranges
6. **Export System**: Generate JSON and HTML reports with highlighting
7. **Portability**: Single-file or minimal-dependency distribution

## Technical Approach

**Language**: Python (excellent SQLite support, rich text processing libraries)

**Key Libraries**:
- `sqlite3` (built-in) for FTS5
- `pathlib` for file system operations
- `argparse` for CLI
- `json` for exports
- `html` template for HTML reports
- Optional: `python-dateutil` for flexible date parsing

**Architecture**:
- Single-file portable script (`notesearch.py`)
- Modular functions: `indexer`, `searcher`, `exporter`
- In-memory SQLite database (`:memory:`)
- FTS5 for fast full-text search
- Tag indexing in separate table
- Date metadata extraction and storage

## Structured TODO List

### Phase 1: Foundation & Project Setup
1. **Create project structure and basic CLI skeleton**
   - Effort: Low
   - Create `notesearch.py` with argparse setup
   - Define command structure: `index`, `search`, `export`
   - Add --help and basic usage documentation
   - Output: Working CLI skeleton with 3 subcommands

2. **Implement markdown file discovery and validation**
   - Effort: Low
   - Add recursive directory scanning with glob patterns
   - Filter by .md extension
   - Handle symlinks and permission errors gracefully
   - Output: File list generator function

3. **Create SQLite database schema with FTS5**
   - Effort: Medium
   - Design schema: notes table, tags table, FTS virtual table
   - Implement in-memory database initialization
   - Create indexes for tags, dates, file paths
   - Output: `init_db()` function with complete schema

### Phase 2: Indexing Engine
4. **Implement markdown metadata extraction**
   - Effort: Medium
   - Parse YAML frontmatter (if present) for tags, dates, title
   - Extract headings (#) as section markers
   - Handle date formats: ISO 8601, RFC 2822, common variants
   - Output: `parse_markdown_metadata()` function

5. **Build full-text content extraction and tokenization**
   - Effort: Medium
   - Strip markdown syntax but preserve content structure
   - Extract code blocks (tag separately for optional search)
   - Preserve line numbers for result highlighting
   - Output: `extract_content()` with cleaned text and line map

6. **Implement database indexing pipeline**
   - Effort: High
   - Batch insert notes with metadata
   - FTS5 index population with triggers
   - Tag normalization (lowercase, deduplicate)
   - Progress tracking for large directories
   - Output: `index_directory()` function with progress bar

### Phase 3: Search Engine
7. **Implement FTS5 full-text search**
   - Effort: Medium
   - Build FTS5 query parser for boolean operators (AND, OR, NOT)
   - Phrase search with quotes
   - Ranking by relevance (bm25 or custom)
   - Output: `search_text()` function with results sorted by relevance

8. **Add tag filtering system**
   - Effort: Low
   - Tag query parser: `tag:important` or `#tag`
   - Multiple tags: AND/OR logic
   - Negation: `-tag:todo`
   - Output: `filter_by_tags()` function

9. **Implement date range filtering**
   - Effort: Medium
   - Date query parser: `after:2024-01-01`, `before:2024-12`
   - Relative dates: `last:7days`, `this:month`
   - Fallback to file modification dates if no metadata date
   - Output: `filter_by_date_range()` function

10. **Combine search filters and result scoring**
    - Effort: Medium
    - Unified search function combining text + tags + dates
    - Result ranking: text relevance + recency bonus
    - Context extraction (snippet generation around matches)
    - Output: `search()` function with multi-criteria filtering

### Phase 4: Export & Reporting
11. **Implement JSON export functionality**
    - Effort: Low
    - Serialize search results to JSON
    - Include metadata, snippets, scores
    - Configurable output fields
    - Output: `export_json()` function

12. **Create HTML report generator**
    - Effort: High
    - Template-based HTML generation
    - Highlight matched terms in snippets
    - Responsive design with CSS
    - Summary statistics (total results, filters used)
    - Output: `export_html()` with styled template

13. **Add interactive HTML features (optional)**
    - Effort: Medium
    - JavaScript for expand/collapse results
    - Filter sidebar for refining searches
    - Copy snippets to clipboard
    - Output: Enhanced HTML template with interactivity

### Phase 5: CLI Polish & User Experience
14. **Implement rich CLI output formatting**
    - Effort: Medium
    - Colored terminal output (titles, snippets, tags)
    - Pager support (less) for long results
    - Compact vs detailed view modes
    - Output: Formatted terminal display

15. **Add configuration file support**
    - Effort: Low
    - Support `.notesearchrc` or `notesearch.yml`
    - Default directories to index
    - Preferred date formats
    - Custom export templates
    - Output: Config parser and defaults

16. **Implement caching and incremental updates**
    - Effort: Medium
    - Store index fingerprint (file hashes, sizes)
    - Reindex only changed files
    - Optional persistent cache file
    - Output: Incremental index mode

### Phase 6: Testing & Documentation
17. **Create test suite with sample markdown files**
    - Effort: Medium
    - Unit tests for parser, search, export
    - Integration tests with sample note collection
    - Edge cases: empty files, malformed dates, unicode
    - Output: Test directory with `pytest` suite

18. **Write comprehensive documentation**
    - Effort: Medium
    - README with installation and usage
    - Query syntax reference (tags, dates, boolean search)
    - Example workflows and use cases
    - Output: Complete README.md

19. **Add packaging and installation script**
    - Effort: Low
    - Single-file distribution option
    - Optional `setup.py` for pip install
    - Shebang for direct execution
    - Output: Installable package

## Notes on Approach & Strategy

### Design Decisions

1. **In-Memory vs Persistent Database**
   - In-memory for speed and simplicity (as specified)
   - Trade-off: must rebuild index on each run
   - Mitigation: Fast FTS5 indexing makes rebuild acceptable for <10k notes

2. **Tag Extraction Strategy**
   - Multi-source: YAML frontmatter > inline hashtags > filename
   - Normalize to lowercase for consistent matching
   - Store both original and normalized forms

3. **Date Handling**
   - Priority: Frontmatter date > file created date > file modified date
   - Support multiple formats with fallback parsing
   - Store as ISO 8601 for consistent comparison

4. **Search Syntax Design**
   - Follow common patterns: `term tag:work after:2024-01`
   - Boolean operators: `term1 AND term2`, `term1 OR term2`
   - Phrase search: `"exact phrase"`
   - Negation: `-unwanted`

### Performance Optimizations

1. **Batch Processing**: Insert notes in batches (100-1000 at a time)
2. **FTS5 Triggers**: Auto-update FTS index on content changes
3. **Lazy Loading**: Only load full content for displayed results
4. **Context Snippets**: Extract small snippets around matches, not full content

### Portability Considerations

1. **Minimal Dependencies**: Use Python stdlib where possible
2. **Single File**: Distribute as standalone script
3. **Cross-Platform**: Handle Windows/Unix path differences
4. **No External Database**: SQLite is embedded

## Assumptions & Potential Blockers

### Assumptions

1. Python 3.8+ available (for pathlib improvements)
2. Markdown files use common conventions (GitHub-style, standard frontmatter)
3. Typical personal knowledge base size: 100-10,000 notes
4. Most notes under 100KB (larger files may need special handling)

### Potential Blockers

1. **Complex Markdown**: Tables, nested lists may lose formatting in plain text extraction
   - Mitigation: Preserve structural markers in separate field
   
2. **Unicode & Special Characters**: Path encoding issues on Windows
   - Mitigation: Use pathlib for cross-platform handling

3. **Very Large Note Collections**: Reindexing time for 50k+ notes
   - Mitigation: Incremental indexing (Phase 5, Task 16)

4. **Date Format Ambiguity**: MM/DD vs DD/MM confusion
   - Mitigation: Prefer ISO 8601, add format detection

5. **Memory Constraints**: In-memory database for massive collections
   - Mitigation: Optional persistent mode (future enhancement)

### Dependencies to Resolve

- **Optional**: `python-dateutil` for robust date parsing (fallback to datetime)
- **Optional**: `tqdm` for progress bars (fallback to simple counter)
- **Optional**: `rich` or `colorama` for colored terminal (fallback to plain text)

---

**Total Estimated Effort**: ~40-50 hours for complete implementation
**Critical Path**: Tasks 3 → 6 → 7 → 10 → 12 (core functionality)
**MVP (Minimum Viable Product)**: Tasks 1-7, 10-11, 14 (basic search with JSON export)

## TODO List
(Updated by worker agent)

## Status: PARTIAL

## Outstanding Items
(None)

## Recommendations
(None)

## Execution Summary

### Execution 2026-01-19 13:21:58
- Status: ✅ COMPLETED
- Files Modified: 6
- Duration: 354s

## Execution Summary
