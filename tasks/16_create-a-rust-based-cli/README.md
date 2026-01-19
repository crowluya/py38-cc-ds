# Task Workspace

Task #16: Create a Rust-based CLI productivity tool that man

## Summary
- Priority: THOUGHT
- Project: None
- Created: 2026-01-19T11:27:47.842011

## Description
Create a Rust-based CLI productivity tool that manages project templates with customizable scaffolding, supporting multiple frameworks/languages, file generation from templates, and git integration for rapid project initialization.

## Plan & Analysis
# Project Template Manager CLI - Implementation Plan

## Executive Summary
Building a Rust-based CLI tool for managing project templates with scaffolding capabilities. This tool will streamline project initialization by supporting multiple frameworks/languages, customizable templates, file generation with variable substitution, and Git integration for rapid development setup.

## Task Analysis

The project requires creating a command-line interface tool with the following core capabilities:
1. **Template Management**: Store, list, add, and remove project templates
2. **Scaffolding Engine**: Generate files and directory structures from templates
3. **Variable Substitution**: Replace placeholders (like `{{project_name}}`) with actual values
4. **Multi-Language Support**: Built-in presets for popular frameworks (React, Rust, Node.js, Python, etc.)
5. **Git Integration**: Auto-initialize Git repos, add remotes, create initial commits
6. **Interactive CLI**: User-friendly commands with helpful prompts and validation

## Structured TODO List

1. **Initialize Rust project structure with Cargo**
   - Create new Cargo project with appropriate name (e.g., `scaffold` or `project-init`)
   - Set up dependencies: `clap` for CLI, `serde` for serialization, `handlebars` or `tera` for templates, `git2` for Git integration
   - Configure `Cargo.toml` with metadata and dependencies

2. **Define core data models and configuration schema**
   - Design `Template` struct (name, description, language, files/directories structure)
   - Design `ProjectConfig` struct (variables, default values, git settings)
   - Create configuration file format (TOML/YAML) for storing templates
   - Implement serialization/deserialization with serde

3. **Implement template engine for file generation**
   - Choose and integrate template engine (Handlebars or Tera)
   - Implement file/directory tree generation logic
   - Add variable substitution and validation
   - Handle conditional file creation based on variables

4. **Create CLI argument parser with subcommands**
   - Define subcommands: `init`, `template add/remove/list`, `new`, `config`
   - Add flags and options for customization
   - Implement help text and usage examples
   - Add shell completion support

5. **Build template management system**
   - Implement `template list` - show available templates
   - Implement `template add` - add new templates from local path or remote URL
   - Implement `template remove` - delete templates
   - Implement template validation and conflict detection

6. **Implement scaffolding logic with variable substitution**
   - Parse template files and identify variables
   - Create interactive prompts for user input
   - Substitute variables across all files and directories
   - Validate generated output before writing

7. **Add multi-language/framework support with presets**
   - Create built-in templates for: React, Vue, Svelte, Rust, Node.js, Python FastAPI, Go, etc.
   - Define template-specific variables (e.g., `use_typescript` for JS frameworks)
   - Allow custom template discovery and management

8. **Implement Git integration**
   - Add `git init` functionality after project creation
   - Support optional remote repository setup
   - Create initial commit with generated files
   - Add `.gitignore` generation based on language/framework

9. **Create interactive configuration wizard**
   - Build step-by-step prompts for creating custom templates
   - Validate user inputs and provide feedback
   - Save new templates to local template store

10. **Add project initialization command**
    - Implement `new` command to create projects from templates
    - Support both interactive and flag-based modes
    - Handle overwriting existing directories
    - Show progress indicators for file generation

11. **Test CLI functionality and error handling**
    - Write unit tests for core functions
    - Test error cases (missing templates, invalid variables, file system errors)
    - Add integration tests for full workflow
    - Ensure cross-platform compatibility (Windows, macOS, Linux)

12. **Write documentation and usage examples**
    - Create comprehensive README with installation instructions
    - Provide examples for common use cases
    - Document template configuration format
    - Add man pages or help documentation

## Approach and Strategy

### Architecture
- **CLI Layer**: `clap` for command parsing and user interaction
- **Core Logic**: Template engine, file generation, Git operations
- **Data Layer**: Template storage, configuration management
- **Utilities**: Path handling, validation, progress indicators

### Technology Choices
- **CLI Framework**: `clap` v4 for robust argument parsing
- **Template Engine**: `handlebars` for flexible templating with partials and helpers
- **Git Integration**: `git2` for pure Rust Git operations
- **Serialization**: `serde` with `serde_yaml` for human-readable configs
- **Interactive Prompts**: `dialoguer` for user-friendly CLI interactions
- **Error Handling**: `anyhow` for ergonomic error messages, `thiserror` for custom error types

### File Structure
```
project-init/
├── Cargo.toml
├── src/
│   ├── main.rs           # CLI entry point
│   ├── cli.rs            # Command definitions
│   ├── templates.rs      # Template management
│   ├── scaffolding.rs    # File generation logic
│   ├── git.rs            # Git operations
│   └── config.rs         # Configuration handling
├── templates/            # Built-in templates
│   ├── rust/
│   ├── react/
│   └── node/
└── README.md
```

## Assumptions and Potential Blockers

### Assumptions
- Users have Rust and Cargo installed for development
- Templates will be stored locally (possibly in `~/.project-init/templates`)
- Git should be optional - not all projects need it
- Templates should be shareable via git repos or file archives

### Potential Blockers
1. **Cross-platform path handling**: Need careful handling of Windows vs Unix paths
2. **Template complexity**: Very complex templates with conditional logic may require advanced templating features
3. **Git authentication**: For setting up remotes, may need SSH/HTTPS credential handling
4. **Conflict resolution**: Handling template updates and user modifications
5. **Performance**: Large templates with many files may need progress indicators

### Mitigation Strategies
- Use `dirs` crate for cross-platform home directory resolution
- Start with simple variable substitution, add conditionals if needed
- Use Git credential helpers or ask users to set up remotes manually
- Implement template versioning and upgrade paths
- Add `indicatif` for progress bars on large operations

## Effort Estimation
- **Core functionality**: 8-12 hours
- **Template engine and scaffolding**: 6-8 hours
- **CLI and user experience**: 4-6 hours
- **Git integration**: 2-4 hours
- **Testing and refinement**: 4-6 hours
- **Documentation**: 2-4 hours

**Total Estimated Effort**: 26-40 hours for a fully functional MVP

This plan provides a clear roadmap for building a production-ready project scaffolding tool that will significantly improve developer productivity and project initialization workflows.

## TODO List
(Updated by worker agent)

## Status: PARTIAL

## Outstanding Items
- **File**: `src/plugin/api.rs`
- **Implemented**:
- `Plugin` trait with lifecycle methods (`manifest()`, `initialize()`, `cleanup()`)
- `TemplateProvider` trait for template discovery
- `ScaffoldingHook` trait for custom file generation
- `PluginInterface` with C-compatible ABI
- `TemplateMetadata` struct
- **Quality**: Well-designed with comprehensive documentation
- **File**: `src/plugin/loader.rs`
- **Implemented**:
- `PluginLoader` struct using `libloading`
- Platform-safe library loading with extension detection
- Symbol resolution for `_plugin_create` and `_plugin_abi_version`
- ABI version validation
- Plugin initialization and cleanup
- **Dependencies Added**: `libloading = "0.8"`, `once_cell = "1.19"`
- **File**: `src/plugin/registry.rs`
- **Implemented**:
- `PluginRegistry` with global singleton
- Default plugin directories (`~/.project-init/plugins`, system paths)
- Plugin discovery and auto-loading
- Template indexing by provider
- `global_registry()` accessor function
- **File**: `src/plugin/manifest.rs`
- **Implemented**:
- `PluginManifest` with all required fields
- `Capability` enum (FsRead, FsWrite, Network, Execute, Environment, Git)
- `PluginDependency` struct
- Semantic version validation
- ABI version checking (`PLUGIN_ABI_VERSION = 1`)
- JSON/YAML serialization support
- **File**: `src/plugin/package.rs`
- **Implemented**:
- `PluginPackageManager` struct
- `install_from_file()` with capability permission prompts
- `install_from_url()` with download support
- `remove()` with confirmation dialog
- `list_installed()`, `get_plugin_info()`
- `update()` and `verify()` methods
- `InstalledPluginInfo` struct
- **File**: `src/plugin/error.rs`
- **Implemented**: Comprehensive `PluginError` enum with all error types
- `src/templates.rs` does not import or use `plugin::registry`
- `list_templates()` function only reads from filesystem, not from plugins
- No priority system for template conflicts (built-in vs plugin)
- No procedural macros crate for `#[plugin]`
- No example plugins in `examples/plugins/`
- No plugin development documentation
- No WASM sandboxing
- No capability enforcement system
- Permission prompts exist but no actual permission checking
- No integration tests with mock plugins
- No tests for concurrent plugin loading
- No security tests for malicious plugin rejection
- No API reference documentation
- No packaging tutorial
- No Git repository installation support
- No plugin index format

## Recommendations
(None)

## Execution Summary

### Execution 2026-01-19 12:07:33
- Status: ✅ COMPLETED
- Files Modified: 17
- Duration: 206s

## Execution Summary

### Execution 2026-01-19 11:44:37
- Status: ✅ COMPLETED
- Files Modified: 19
- Duration: 453s

## Execution Summary

### Execution 2026-01-19 12:07:33
- Status: ✅ COMPLETED
- Files Modified: 17
- Duration: 206s

## Execution Summary

### Execution 2026-01-19 11:36:54
- Status: ✅ COMPLETED
- Files Modified: 34
- Duration: 546s

## Execution Summary

### Execution 2026-01-19 12:07:33
- Status: ✅ COMPLETED
- Files Modified: 17
- Duration: 206s

## Execution Summary

### Execution 2026-01-19 11:44:37
- Status: ✅ COMPLETED
- Files Modified: 19
- Duration: 453s

## Execution Summary

### Execution 2026-01-19 12:07:33
- Status: ✅ COMPLETED
- Files Modified: 17
- Duration: 206s

## Execution Summary
