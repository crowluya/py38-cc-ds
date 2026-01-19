# Contributing to KG CLI

Thank you for your interest in contributing to KG CLI! This document provides guidelines for contributing to the project.

## Development Setup

### Prerequisites

- Rust 1.70 or later
- Git
- A text editor or IDE

### Getting Started

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/your-username/kg-cli.git
   cd kg-cli
   ```

3. Build the project:
   ```bash
   cargo build
   ```

4. Run tests:
   ```bash
   cargo test
   ```

5. Run the CLI:
   ```bash
   cargo run -- --help
   ```

## Code Style

### Rust Conventions

- Follow standard Rust naming conventions:
  - Types: `PascalCase`
  - Functions: `snake_case`
  - Constants: `SCREAMING_SNAKE_CASE`
- Use `cargo fmt` for formatting
- Use `cargo clippy` for linting

### Documentation

- Document all public APIs with Rustdoc comments
- Include examples in documentation
- Update relevant documentation when making changes

### Error Handling

- Use `Result<T, E>` for fallible operations
- Use `anyhow` for application errors
- Provide clear, actionable error messages

## Running Tests

### Unit Tests

```bash
cargo test
```

### Integration Tests

```bash
cargo test --test integration_tests
```

### With Output

```bash
cargo test -- --nocapture
```

### Specific Test

```bash
cargo test test_name
```

## Project Structure

```
src/
├── main.rs       # CLI entry point
├── lib.rs        # Library exports
├── types.rs      # Core data structures
├── linking.rs    # Link parsing
├── storage.rs    # File I/O
├── search.rs     # Search algorithms
└── export.rs     # Graph visualization
```

When adding features:

1. **New commands**: Add to `main.rs` Commands enum
2. **Data structures**: Add to `types.rs`
3. **Algorithms**: Create new module or add to existing appropriate module
4. **Tests**: Add to `tests/integration_tests.rs` or module-specific tests

## Making Changes

### Workflow

1. Create a new branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes

3. Test thoroughly:
   ```bash
   cargo test
   cargo clippy
   cargo fmt --check
   ```

4. Commit your changes:
   ```bash
   git add .
   git commit -m "Brief description of changes"
   ```

5. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

6. Create a Pull Request

### Commit Message Format

```
<type>: <subject>

<body>

<footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Example:
```
feat: add note tagging support

Add ability to add tags to notes and filter by tags.

Closes #42
```

## Feature Ideas

Looking for something to work on? Here are some ideas:

### High Priority
- [ ] Note templates system
- [ ] Improved search ranking
- [ ] Incremental graph indexing
- [ ] Note aliasing

### Medium Priority
- [ ] Git integration
- [ ] Import from other tools (Obsidian, Roam)
- [ ] Note attachments
- [ ] Calendar integration

### Low Priority
- [ ] Web UI
- [ ] Mobile app
- [ ] Plugin system
- [ ] Note encryption

## Testing Guidelines

### Writing Tests

1. **Unit tests**: Test individual functions
   ```rust
   #[cfg(test)]
   mod tests {
       use super::*;

       #[test]
       fn test_function() {
           assert_eq!(function(), expected);
       }
   }
   ```

2. **Integration tests**: Test complete workflows
   ```rust
   #[test]
   fn test_complete_workflow() {
       // Setup
       // Execute
       // Verify
   }
   ```

### Test Coverage

- Aim for >80% code coverage
- Test edge cases
- Test error conditions
- Test with realistic data

## Pull Request Guidelines

### Before Submitting

- [ ] Code compiles without warnings
- [ ] All tests pass
- [ ] Code is formatted with `cargo fmt`
- [ ] No clippy warnings
- [ ] Documentation updated
- [ ] Tests added for new features

### PR Description

Include:
- Summary of changes
- Motivation for the change
- How it was tested
- Screenshots (if applicable)
- Breaking changes (if any)

### Review Process

1. Automated checks must pass
2. At least one maintainer approval
3. No unresolved conversations
4. Squash and merge when approved

## Release Process

Maintainers follow this process for releases:

1. Update version in `Cargo.toml`
2. Update CHANGELOG.md
3. Create git tag
4. Push to crates.io
5. Create GitHub release

## Questions?

- Open an issue for bugs or feature requests
- Start a discussion for questions
- Check existing issues and discussions first

## Code of Conduct

Be respectful, inclusive, and constructive. We're all here to build something great together.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to KG CLI! 🎉
