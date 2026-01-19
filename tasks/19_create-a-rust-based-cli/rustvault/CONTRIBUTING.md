# Contributing to RustVault

Thank you for your interest in contributing to RustVault! This document provides guidelines for contributing to the project.

## Development Setup

### Prerequisites

- Rust 1.70 or later
- Git
- A text editor or IDE

### Setting Up Your Development Environment

1. Fork the repository on GitHub
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/rustvault.git
   cd rustvault
   ```

3. Install dependencies:
   ```bash
   cargo fetch
   ```

4. Run tests to verify everything works:
   ```bash
   cargo test
   ```

5. Build the project:
   ```bash
   cargo build
   ```

## Development Workflow

### Making Changes

1. Create a new branch for your feature or bugfix:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bugfix-name
   ```

2. Make your changes following the code style guidelines below

3. Write tests for your changes (see Testing section)

4. Ensure all tests pass:
   ```bash
   cargo test --all
   ```

5. Format your code:
   ```bash
   cargo fmt --all
   ```

6. Run clippy to catch common mistakes:
   ```bash
   cargo clippy --all-targets --all-features -- -D warnings
   ```

7. Commit your changes with a descriptive message:
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

8. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

9. Open a pull request on GitHub

## Code Style Guidelines

### Rust Conventions

- Follow standard Rust naming conventions:
  - Types: `PascalCase`
  - Functions and variables: `snake_case`
  - Constants: `SCREAMING_SNAKE_CASE`

- Use `rustfmt` for consistent formatting (configured in `rustfmt.toml` if present)
- Prefer `Result<T>` over panics for error handling
- Use `anyhow::Context` for error context in application code
- Use `thiserror` for library error types

### Documentation

- Document all public items with `///` doc comments
- Include examples in documentation
- Run `cargo doc` to check documentation:
  ```bash
  cargo doc --no-deps --open
  ```

Example:
```rust
/// Encrypts data using AES-256-GCM
///
/// # Arguments
///
/// * `plaintext` - The data to encrypt
/// * `key` - The encryption key (32 bytes)
///
/// # Returns
///
/// Encrypted data with nonce
///
/// # Example
///
/// ```rust
/// let encrypted = encrypt(b"hello", &key)?;
/// ```
pub fn encrypt(plaintext: &[u8], key: &[u8]) -> Result<EncryptedData> {
    // ...
}
```

### Security Considerations

- **Never log passwords or secrets**
- Use `zeroize::Zeroize` to clear sensitive data from memory
- Validate all user input
- Use constant-time comparisons for secret data
- Follow cryptographic best practices
- Add security tests for crypto operations

## Testing

### Unit Tests

- Write unit tests alongside your code in the same module
- Use the `#[cfg(test)]` module pattern
- Test both success and error cases
- Test edge cases (empty inputs, invalid data, etc.)

Example:
```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_encryption_decryption() {
        let plaintext = b"test data";
        let key = vec![0u8; 32];

        let encrypted = encrypt(plaintext, &key).unwrap();
        let decrypted = decrypt(&encrypted, &key).unwrap();

        assert_eq!(plaintext.to_vec(), decrypted);
    }

    #[test]
    fn test_invalid_key_length() {
        let result = encrypt(b"data", &[0u8; 16]);
        assert!(result.is_err());
    }
}
```

### Integration Tests

- Add integration tests in the `tests/` directory
- Test end-to-end workflows
- Test module interactions
- Use temporary directories for file operations

### Running Tests

```bash
# Run all tests
cargo test

# Run tests with output
cargo test -- --nocapture

# Run only unit tests
cargo test --lib

# Run only integration tests
cargo test --test integration_tests

# Run specific test
cargo test test_encryption_decryption
```

## Project Structure

```
rustvault/
├── src/
│   ├── main.rs          # CLI entry point
│   ├── lib.rs           # Library exports
│   ├── cli.rs           # Command-line parsing
│   ├── crypto.rs        # Cryptography operations
│   ├── vault.rs         # Data structures
│   ├── storage.rs       # File I/O
│   ├── generator.rs     # Password generation
│   ├── otp.rs           # TOTP functionality
│   └── error.rs         # Error types
├── tests/
│   └── integration_tests.rs
├── examples/
│   └── basic_usage.sh
├── Cargo.toml
├── README.md
└── LICENSE
```

## Feature Guidelines

### Adding New Features

1. Discuss the feature in an issue first
2. Get approval from maintainers
3. Create a design document for major features
4. Implement the feature following the guidelines above
5. Update documentation (README, usage examples)
6. Add tests

### Breaking Changes

- Avoid breaking changes if possible
- If necessary, increment version appropriately
- Document migration paths
- Deprecate old functionality before removing

## Pull Request Guidelines

### PR Title Format

Use conventional commits format:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `security:` - Security fixes

Examples:
- `feat: add support for custom vault locations`
- `fix: handle empty passwords in entry creation`
- `docs: update installation instructions`

### PR Description

Include:
- Summary of changes
- Motivation for the change
- Related issues
- Testing performed
- Breaking changes (if any)
- Screenshots (if applicable)

### Review Process

1. Automated checks must pass (CI/CD)
2. Code review by at least one maintainer
3. Address all review comments
4. Squash commits if requested
5. Merge approval required

## Issue Reporting

### Bug Reports

Include:
- Rust and RustVault version
- Operating system
- Steps to reproduce
- Expected behavior
- Actual behavior
- Error messages or logs
- Minimal reproducible example if possible

### Feature Requests

Include:
- Clear description of the feature
- Use case/motivation
- Proposed implementation (if you have ideas)
- Alternative approaches considered

## Security Issues

**Do not open public issues for security vulnerabilities!**

Email security issues to: security@example.com

Include:
- Description of the vulnerability
- Steps to reproduce
- Impact assessment
- Suggested fix (if known)

## Getting Help

- Check existing documentation and issues
- Ask questions in GitHub Discussions (if enabled)
- Be patient - maintainers are volunteers

## Code of Conduct

Be respectful, inclusive, and constructive:
- Use respectful language
- Welcome newcomers
- Focus on what is best for the community
- Show empathy towards other community members

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Acknowledgments

Thank you for contributing to RustVault! Your contributions help make password security accessible to everyone.
