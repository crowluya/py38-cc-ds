# Contributing to Project Init

Thank you for your interest in contributing to Project Init! This document provides guidelines and instructions for contributing.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Workflow](#development-workflow)
4. [Coding Standards](#coding-standards)
5. [Testing](#testing)
6. [Documentation](#documentation)
7. [Submitting Changes](#submitting-changes)

## Code of Conduct

Please be respectful and constructive in all interactions. We aim to maintain a welcoming and inclusive community.

## Getting Started

### Prerequisites

- Rust 1.70 or later
- Git
- A code editor (VS Code, IntelliJ IDEA, etc.)

### Setting Up Development Environment

```bash
# Clone the repository
git clone https://github.com/yourusername/project-init.git
cd project-init

# Install development dependencies
cargo build

# Run tests to verify setup
cargo test

# Install the CLI locally
cargo install --path .
```

### Development Tools

Recommended VS Code extensions:
- rust-analyzer
- CodeLLDB
- Even Better TOML
- Error Lens

## Development Workflow

### 1. Fork and Clone

```bash
# Fork the repository on GitHub
# Clone your fork
git clone https://github.com/yourusername/project-init.git
cd project-init
```

### 2. Create a Branch

```bash
# Create a feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/bug-description
```

### 3. Make Changes

- Write code following the coding standards
- Add tests for new functionality
- Update documentation as needed
- Ensure all tests pass

### 4. Test Your Changes

```bash
# Run all tests
cargo test

# Run with logging
RUST_LOG=debug cargo run -- new --template rust --name test-project

# Test specific functionality
cargo test --test scaffolding_tests
```

### 5. Commit Changes

```bash
# Stage changes
git add .

# Commit with clear message
git commit -m "feat: add support for custom template variables"
```

### 6. Push and Create PR

```bash
# Push to your fork
git push origin feature/your-feature-name

# Create Pull Request on GitHub
```

## Coding Standards

### Rust Code Style

- Use `cargo fmt` for formatting
- Follow Rust naming conventions
- Use `cargo clippy` for linting

```bash
# Format code
cargo fmt

# Check for issues
cargo clippy -- -D warnings
```

### Code Organization

- **Modules**: Keep modules focused and single-purpose
- **Functions**: Keep functions short and focused
- **Error Handling**: Use `Result` types for proper error handling
- **Documentation**: Document public APIs with rustdoc comments

Example:

```rust
/// Creates a new project from a template.
///
/// # Arguments
///
/// * `template_name` - The name of the template to use
/// * `project_name` - The name for the new project
///
/// # Returns
///
/// Returns a `Result` indicating success or failure.
///
/// # Examples
///
/// ```
/// use project_init::create_project;
/// create_project("rust", "my-project", None, true, &HashMap::new()).await?;
/// ```
pub async fn create_project(
    template_name: &str,
    project_name: &str,
    custom_path: Option<&str>,
    init_git: bool,
    user_variables: &HashMap<String, String>,
) -> Result<()> {
    // Implementation
}
```

### Error Handling

Use proper error types from `error.rs`:

```rust
use crate::error::{ProjectInitError, Result};

pub fn load_template(path: &Path) -> Result<Template> {
    if !path.exists() {
        return Err(ProjectInitError::TemplateNotFound(
            path.display().to_string(),
        ));
    }
    // Continue...
}
```

## Testing

### Unit Tests

Write unit tests for all modules:

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_to_kebab_case() {
        assert_eq!(to_kebab_case("MyString"), "my-string");
        assert_eq!(to_kebab_case("my_string"), "my-string");
    }

    #[test]
    fn test_template_variable_substitution() {
        let mut vars = HashMap::new();
        vars.insert("name".to_string(), "test".to_string());

        let result = substitute_path_variables("{{name}}-project", &vars);
        assert_eq!(result, "test-project");
    }
}
```

### Integration Tests

Add integration tests in `tests/` directory:

```rust
// tests/integration_tests.rs
use project_init::create_project;

#[tokio::test]
async fn test_create_rust_project() {
    let result = create_project(
        "rust",
        "test-project",
        Some("/tmp/test-project"),
        false,
        &HashMap::new(),
    ).await;

    assert!(result.is_ok());
    // Verify files exist, etc.
}
```

### Test Coverage

```bash
# Run tests with coverage
cargo install cargo-tarpaulin
cargo tarpaulin --out Html
```

## Documentation

### Code Documentation

- Document all public APIs
- Include examples in documentation
- Update relevant docs when changing functionality

### README and Guides

When adding new features:
- Update README.md with new commands/options
- Add examples to EXAMPLES.md
- Update changelog

### Template Documentation

When adding new templates:
1. Create template.yaml with proper description
2. Include README.md in template if needed
3. Document any special variables or requirements

## Submitting Changes

### Pull Request Checklist

Before submitting a PR:

- [ ] Code follows style guidelines (`cargo fmt`)
- [ ] Code passes clippy checks (`cargo clippy`)
- [ ] All tests pass (`cargo test`)
- [ ] New tests added for new features
- [ ] Documentation updated
- [ ] Commit messages follow conventions

### Commit Message Format

Use conventional commit messages:

```
feat: add support for remote templates
fix: resolve path handling on Windows
docs: update installation instructions
test: add integration tests for scaffolding
refactor: simplify template loading logic
```

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How changes were tested

## Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No linting errors
```

## Feature Development

### Proposing New Features

1. Open an issue to discuss the feature
2. Get feedback from maintainers
3. Implement feature in a branch
4. Submit PR with tests and documentation

### Adding New Templates

Templates should follow these guidelines:

1. **Structure**: Must include `template.yaml`
2. **Documentation**: Clear description and usage
3. **Variables**: Document all variables
4. **Testing**: Test template generation
5. **Maintenance**: Keep templates updated

Template submission checklist:

```yaml
name: template-name
description: Clear, concise description
language: Language/Framework
version: 1.0.0

variables:
  # Required variables documented
  - name: important_var
    description: What this variable does
    default: "sensible-default"
    required: true

files:
  # All files included
  - path: "important-file.ext"
    content: |
      File content here
    template: true

directories:
  # Required directories
  - "src"
  - "tests"
```

## Debugging

### Logging

Enable debug logging:

```bash
RUST_LOG=debug project-init new --template rust --name test-project
```

### Common Issues

**Build Errors:**
```bash
# Clean build
cargo clean
cargo build
```

**Test Failures:**
```bash
# Run tests with output
cargo test -- --nocapture

# Run specific test
cargo test test_name
```

## Release Process

(For maintainers)

1. Update version in Cargo.toml
2. Update CHANGELOG.md
3. Create git tag
4. Publish to crates.io
5. Create GitHub release

## Questions?

- Open an issue for bugs or feature requests
- Start a discussion for questions
- Check existing documentation first

## Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project README

Thank you for contributing to Project Init! 🚀
