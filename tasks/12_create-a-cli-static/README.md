# Task Workspace

Task #12: Create a CLI static site generator that transforms

## Summary
- Priority: THOUGHT
- Project: None
- Created: 2026-01-19T10:56:43.558438

## Description
Create a CLI static site generator that transforms Markdown files into fast, SEO-optimized HTML websites with built-in sitemap generation, RSS feeds, and custom theme support.

## Plan & Analysis
# Executive Summary
I'll design and implement a CLI static site generator that converts Markdown files into SEO-optimized HTML websites. The tool will include sitemap generation, RSS feeds, and themeable templates, following patterns from successful static site generators like Hugo and Jekyll while maintaining simplicity and performance.

# Task Analysis

## Core Requirements
1. **CLI Interface**: Command-line tool with clear subcommands
2. **Markdown Processing**: Parse Markdown files and convert to HTML
3. **HTML Generation**: Fast, SEO-optimized output
4. **Sitemap Generation**: Automatic XML sitemap creation
5. **RSS Feeds**: Generate RSS/Atom feeds for content
6. **Theme Support**: Customizable templates and styling
7. **Static Assets**: Copy and manage CSS, JS, images

## Technical Approach
- **Language**: Python 3.8+ (excellent CLI libraries, Markdown parsing)
- **Key Libraries**: 
  - `click` for CLI interface
  - `markdown` or `mistune` for parsing
  - `jinja2` for templating
  - `feedgenerator` for RSS
  - `pyyaml` for configuration
- **Architecture**: Modular pipeline design (content → parse → render → output)

## Project Structure
```
static-gen/
├── src/
│   ├── staticgen/
│   │   ├── __init__.py
│   │   ├── cli.py              # Click commands
│   │   ├── config.py           # Config handling
│   │   ├── processor.py        # Markdown processor
│   │   ├── renderer.py         # HTML renderer
│   │   ├── sitemap.py          # Sitemap generator
│   │   ├── feed.py             # RSS/Atom generator
│   │   └── theme.py            # Theme manager
├── templates/
│   └── default/                # Default theme
├── tests/
├── pyproject.toml
└── README.md
```

# Structured TODO List

## Phase 1: Project Setup & Core Infrastructure
1. **Create project structure and virtual environment** (Effort: Low)
   - Initialize Python project with pyproject.toml
   - Set up directory structure (src/, templates/, tests/)
   - Configure dependencies (click, jinja2, markdown, pyyaml, feedgenerator)

2. **Implement configuration system** (Effort: Medium)
   - Create config.py with YAML parsing
   - Support global config (site title, URL, description)
   - Handle per-page frontmatter (title, date, tags, draft status)
   - Default configuration schema

3. **Build CLI interface with Click** (Effort: Medium)
   - Create cli.py with main command group
   - Subcommands: `init`, `build`, `serve`, `new`
   - Options: `--input`, `--output`, `--config`, `--verbose`
   - Help text and usage examples

## Phase 2: Content Processing
4. **Implement Markdown processor** (Effort: Medium)
   - Parse Markdown files with frontmatter
   - Extract metadata (title, date, tags, description)
   - Convert Markdown to HTML with syntax highlighting
   - Handle internal links and relative paths
   - Support draft posts (exclude from builds)

5. **Create content discovery system** (Effort: Medium)
   - Scan input directory for .md files
   - Build content tree (posts, pages, categories)
   - Sort by date for posts
   - Generate permalinks/slug patterns
   - Handle content collections

## Phase 3: HTML Generation & Theming
6. **Implement Jinja2 template renderer** (Effort: High)
   - Create base templates (layout, post, page, index)
   - Theme manager to switch between themes
   - Template inheritance and blocks
   - Custom filters for dates, slugs, excerpts
   - Default theme with responsive CSS

7. **Build HTML generation pipeline** (Effort: High)
   - Render individual posts/pages
   - Generate index pages (homepage, archive)
   - Create pagination for post lists
   - Generate category/tag pages
   - Minify HTML output (optional)

## Phase 4: SEO & Distribution Features
8. **Implement XML sitemap generator** (Effort: Medium)
   - Generate sitemap.xml with all pages
   - Include lastmod dates
   - Support sitemap splitting (for large sites)
   - Add to robots.txt

9. **Create RSS/Atom feed generator** (Effort: Medium)
   - Generate RSS/Atom feeds
   - Configurable feed settings (item count, format)
   - Separate feeds for categories/tags
   - Include full content or excerpts

10. **Add SEO optimization features** (Effort: Medium)
    - Auto-generate meta tags (description, OG tags)
    - Add JSON-LD structured data
    - Generate canonical URLs
    - Create robots.txt
    - Add favicons

## Phase 5: Asset Management & Development Tools
11. **Implement static asset copier** (Effort: Low)
    - Copy CSS, JS, images to output
    - Process and minify assets (optional)
    - Handle theme assets
    - Asset versioning/cache busting

12. **Create development server** (Effort: Medium)
    - Live reload with file watching
    - Simple HTTP server
    - Auto-rebuild on changes
    - Browser sync (optional)

13. **Add content creation helpers** (Effort: Low)
    - `new` command to create posts with frontmatter
    - Interactive prompts for metadata
    - Create draft posts

## Phase 6: Testing & Documentation
14. **Write unit tests** (Effort: High)
    - Test Markdown parsing
    - Test template rendering
    - Test sitemap/feed generation
    - Test CLI commands
    - Test configuration handling

15. **Create example project** (Effort: Medium)
    - Sample site with content
    - Example configuration
    - Demo of different features

16. **Write documentation** (Effort: High)
    - README with installation/usage
    - Configuration reference
    - Theme development guide
    - Deployment instructions
    - CLI command reference

## Phase 7: Polish & Packaging
17. **Package for distribution** (Effort: Medium)
    - Configure entry points in pyproject.toml
    - Test installation via pip
    - Create distribution packages
    - Publish to PyPI (optional)

18. **Add error handling & validation** (Effort: Medium)
    - Validate configuration files
    - Clear error messages for common issues
    - Graceful handling of missing files
    - Logging system

# Notes on Approach & Strategy

## Development Strategy
1. **Incremental Development**: Start with basic Markdown → HTML conversion, then add features
2. **MVP First**: Get a working site generator quickly (Phases 1-3), then enhance
3. **Test-Driven**: Write tests alongside core functionality
4. **Default Theme**: Provide a production-ready default theme that looks good out of the box

## Key Design Decisions
- **Configuration-over-code**: Use YAML config files instead of requiring programming
- **Convention-over-configuration**: Sensible defaults for file structure (e.g., `_posts/` directory)
- **Frontmatter Standard**: Use YAML frontmatter compatible with Jekyll/Hugo
- **Template Flexibility**: Jinja2 allows custom themes without coding
- **Performance**: Generate sites in seconds, not minutes

## SEO Priorities
- Semantic HTML5 markup
- Proper heading hierarchy
- Meta descriptions and Open Graph tags
- Structured data (JSON-LD)
- Fast loading times (minified assets)
- Mobile-responsive default theme

## Potential Extensions (Future)
- Plugin system for custom processors
- Image optimization pipeline
- CSS/JS bundling
- Multi-language support
- Shortcode system (like Hugo)
- Data files (JSON/YAML → templates)

# Assumptions & Potential Blockers

## Assumptions
1. Users have Python 3.8+ installed
2. Sites are relatively small (<1000 pages) - no database needed
3. Content is primarily Markdown (HTML also supported)
4. Hosting on static file servers (GitHub Pages, Netlify, S3)
5. Single user/author per site (multi-author support later)

## Potential Blockers
1. **Template Design Complexity**: Creating a good default theme takes time
   - Mitigation: Start with simple, clean Bootstrap/Tailwind-based theme
2. **Dependency Management**: Keeping library versions compatible
   - Mitigation: Pin versions in pyproject.toml, use virtual environments
3. **Markdown Parser Differences**: Different parsers handle edge cases differently
   - Mitigation: Choose mature parser (Python-Markdown), document behavior
4. **Windows Compatibility**: Path handling on different OS
   - Mitigation: Use pathlib for cross-platform paths
5. **Performance with Large Sites**: Generation time with 1000+ pages
   - Mitigation: Profile and optimize, parallel processing if needed

## Riskiest Items
1. **Theme System** (TODO #6): Template inheritance and theming is complex
2. **Live Reload** (TODO #12): File watching across platforms can be tricky
3. **Sitemap/Feed Generation** (TODO #8-9): Getting all edge cases right

## Recommended Starting Point
Begin with **TODOs 1-3** (setup, config, CLI), then **TODO #4** (Markdown processor). This gives you a working pipeline: read Markdown → parse metadata → output HTML. Build incrementally from there.

## TODO List
(Updated by worker agent)

## Status: PARTIAL

## Outstanding Items
(None)

## Recommendations
(None)

## Execution Summary

### Execution 2026-01-19 11:05:34
- Status: ✅ COMPLETED
- Files Modified: 39
- Duration: 530s

## Execution Summary
