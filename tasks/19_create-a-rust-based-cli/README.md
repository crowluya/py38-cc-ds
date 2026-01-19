# Task Workspace

Task #19: Create a Rust-based CLI password manager with secu

## Summary
- Priority: THOUGHT
- Project: None
- Created: 2026-01-19T11:49:38.972544

## Description
Create a Rust-based CLI password manager with secure encryption, hierarchical vault organization, password generation with configurable policies, and TOTP support for two-factor authentication codes.

## Plan & Analysis
I'll analyze this task and create a comprehensive plan for building a Rust-based CLI password manager.

## Executive Summary
This project requires building a full-featured password manager in Rust with core security features including encryption (likely using AES-256-GCM), a hierarchical vault structure for organizing credentials, a flexible password generator, and TOTP functionality for 2FA codes. The architecture needs to balance security, usability, and performance while following Rust best practices for CLI applications.

## Task Analysis

**Core Requirements:**
1. **Security**: Strong encryption for data at rest (master password-based key derivation)
2. **Storage**: Hierarchical organization (folders/categories → entries)
3. **Utilities**: Password generation with configurable policies (length, character sets)
4. **2FA Integration**: TOTP code generation and display
5. **CLI Interface**: Intuitive command structure for all operations

**Technical Considerations:**
- Use `argon2` for key derivation (master password → encryption key)
- Use `aes-gcm` or `chacha20poly1305` for authenticated encryption
- File-based storage with JSON or bincode serialization
- `totp-rs` or custom TOTP implementation (RFC 6238)
- `clap` for CLI argument parsing
- `crossterm` or `inquire` for interactive CLI elements

**Key Design Decisions Needed:**
- Storage format (plaintext JSON vs binary)
- Whether to support multiple vaults or single vault
- Clipboard integration strategy
- Password visibility/interaction model

---

## Structured TODO List

### Phase 1: Project Foundation & Core Cryptography

1. **Initialize Rust project structure with dependencies**
   - Create new Cargo project with appropriate name (e.g., `rustvault`)
   - Add dependencies: `clap`, `serde`, `anyhow`, `dirs`, `argon2`, `aes-gcm`, `rand`
   - Set up basic project structure (src/lib.rs, src/main.rs, src/cli.rs, src/crypto.rs, src/vault.rs, src/otp.rs)
   - Configure Cargo.toml with proper metadata and license
   - *Effort: Low | Dependencies: None*

2. **Implement cryptographic core module**
   - Create master password encryption key derivation using Argon2id
   - Implement AES-256-GCM encryption/decryption functions
   - Add secure random salt generation
   - Create nonce/IV handling for encryption
   - Implement password validation with configurable key derivation parameters
   - Add unit tests for crypto operations
   - *Effort: High | Dependencies: #1*

3. **Design and implement vault data structures**
   - Define `Vault`, `Folder`, and `Entry` structs with Serde serialization
   - Implement hierarchical organization (vault → folders → entries)
   - Add entry fields: title, username, password, url, notes, tags, created_at, updated_at
   - Implement folder navigation and path resolution
   - Add serde serialization/deserialization for persistence
   - *Effort: Medium | Dependencies: #1*

### Phase 2: Storage & Persistence

4. **Implement vault storage layer**
   - Create vault file management (location in user config directory)
   - Implement save/load with encryption/decryption
   - Add file locking to prevent concurrent access
   - Implement backup/restore functionality
   - Add vault initialization (create new vault with master password)
   - Add vault unlocking (verify master password)
   - *Effort: High | Dependencies: #2, #3*

5. **Implement vault in-memory operations**
   - Add CRUD operations for entries (create, read, update, delete)
   - Add CRUD operations for folders (create, rename, move, delete)
   - Implement search functionality across entries (by title, username, url, tags)
   - Add listing functionality (list folders, list entries in folder)
   - Implement password visibility toggling
   - *Effort: Medium | Dependencies: #3, #4*

### Phase 3: Password Generation & Utilities

6. **Build password generator module**
   - Implement configurable password policies:
     - Length (default 16, min 8, max 128)
     - Character sets: uppercase, lowercase, digits, symbols
     - Exclude ambiguous characters (e.g., 0/O, 1/l/I)
     - Exclude similar characters (e.g., i, l, 1, L, o, 0, O)
   - Add passphrase generation option (word-based, diceware-style)
   - Implement password strength estimation
   - Add CLI command for standalone password generation
   - *Effort: Medium | Dependencies: #1*

### Phase 4: TOTP/2FA Support

7. **Implement TOTP functionality**
   - Add TOTP secret field to Entry struct
   - Implement TOTP code generation (RFC 6238) using HMAC-SHA1/256
   - Handle base32 encoding/decoding for TOTP secrets
   - Calculate time-based codes with proper step interval (default 30s)
   - Add time remaining display for code expiration
   - Support QR code generation (optional, for enrollment)
   - *Effort: Medium | Dependencies: #1, #3*

### Phase 5: CLI Interface

8. **Design and implement CLI structure with clap**
   - Define command hierarchy:
     ```
     rustvault init
     rustvault unlock
     rustvault lock
     rustvault entry <add|list|show|edit|delete>
     rustvault folder <add|list|rename|delete>
     rustvault generate [--length] [--policy]
     rustvault totp <service-name>
     rustvault search <query>
     rustvault export [--format]
     ```
   - Add global options: --vault-path, --timeout, --verbose
   - Implement argument parsing and validation
   - Add help text and usage examples
   - *Effort: Medium | Dependencies: #1*

9. **Implement interactive CLI elements**
   - Add secure password prompting (hidden input)
   - Implement confirmation prompts for destructive operations
   - Add interactive mode for multi-step operations
   - Implement clipboard integration (copy password/totp code)
   - Add optional TUI for listing/selecting entries (using `inquire` or `dialoguer`)
   - Add auto-lock timer functionality
   - *Effort: Medium | Dependencies: #8*

10. **Implement all CLI command handlers**
    - `init`: Create new vault with master password and confirmation
    - `unlock`: Decrypt vault and keep in memory for session
    - `lock`: Encrypt and clear vault from memory
    - `entry add`: Add new entry with interactive prompts or flags
    - `entry list`: List entries in current folder with filters
    - `entry show`: Display entry details with password visibility toggle
    - `entry edit`: Edit entry fields
    - `entry delete`: Delete entry with confirmation
    - `folder add/list/rename/delete`: Folder management
    - `generate`: Generate password with specified policy
    - `totp`: Display TOTP code with countdown
    - `search`: Search across all entries
    - `export`: Export vault (encrypted or decrypted format)
    - *Effort: High | Dependencies: #5, #8, #9*

### Phase 6: Testing & Quality Assurance

11. **Write comprehensive unit tests**
    - Test crypto operations (encryption, decryption, key derivation)
    - Test vault CRUD operations
    - Test folder operations and hierarchy
    - Test password generation with various policies
    - Test TOTP code generation and validation
    - Test edge cases (empty vault, missing entries, invalid paths)
    - *Effort: Medium | Dependencies: #2, #5, #6, #7*

12. **Write integration tests**
    - Test full CLI workflows (init → unlock → add → retrieve → lock)
    - Test vault file corruption handling
    - Test concurrent access prevention
    - Test export/import round-trip
    - Test search functionality across large vaults
    - *Effort: Medium | Dependencies: #10*

### Phase 7: Polish & Documentation

13. **Create comprehensive documentation**
    - Write README with installation, usage, and examples
    - Add inline documentation for all public APIs
    - Create man pages or comprehensive help text
    - Document security considerations and best practices
    - Add example vault usage workflows
    - *Effort: Low | Dependencies: #10*

14. **Add error handling and user-friendly messages**
    - Implement proper error types with `anyhow` or custom error enum
    - Add user-friendly error messages (not just cryptic error codes)
    - Add warnings for weak passwords, insecure vault location
    - Implement graceful handling of interrupted operations
    - Add detailed logging with --verbose flag
    - *Effort: Medium | Dependencies: #10*

15. **Security hardening and review**
    - Ensure master password is never logged or stored in plaintext
    - Implement secure memory clearing for sensitive data
    - Add vault integrity checks (HMAC or authenticated encryption)
    - Review crypto implementation for common pitfalls
    - Add constant-time comparison for password verification
    - Consider adding key stretching for brute-force protection
    - *Effort: High | Dependencies: #2, #4*

---

## Approach & Strategy

**Development Approach:**
- **Iterative**: Build and test each module before moving to the next
- **Security-first**: Cryptography and storage security are critical - get these right early
- **Test-driven**: Write tests alongside implementation, especially for crypto operations
- **User-focused**: Prioritize intuitive CLI UX with helpful error messages

**Architecture Strategy:**
- **Modular design**: Separate crypto, storage, CLI, and utility modules
- **Single vault model**: Start with one vault per user, can extend to multiple later
- **File-based storage**: Simple encrypted JSON file, easy to backup and migrate
- **Session-based**: Unlock vault for session duration, auto-lock after timeout

**Security Considerations:**
- Use Argon2id for key derivation (memory-hard, resistant to GPU attacks)
- Always use authenticated encryption (AES-GCM or ChaCha20-Poly1305)
- Never log or display sensitive data (master password, entry passwords)
- Clear sensitive data from memory when no longer needed
- Use proper file permissions for vault storage (user-read-only)

**Technology Stack:**
- **Language**: Rust 2021 edition
- **Crypto**: `argon2` + `aes-gcm` or `chacha20poly1305`
- **CLI**: `clap` v4 for argument parsing
- **Serialization**: `serde` + `serde_json`
- **Interactive**: `inquire` or `dialoguer` for prompts
- **TOTP**: `totp-rs` or custom implementation
- **Clipboard**: `clipboard` crate (optional, platform-specific)

---

## Assumptions & Potential Blockers

**Assumptions:**
1. Single-user, local-only vault (no cloud sync initially)
2. Master password is the only authentication method (no biometrics, hardware keys)
3. Platform compatibility: Linux, macOS, Windows (via Rust's cross-platform support)
4. User has basic familiarity with CLI tools
5. TOTP secrets will be manually entered (no QR scanning in CLI)

**Potential Blockers:**
1. **Clipboard integration complexity**: Platform-specific clipboard access may be tricky
   - *Mitigation*: Make clipboard optional, fallback to displaying password
2. **TOTP QR code generation**: Complex for CLI environment
   - *Mitigation*: Skip QR generation initially, focus on manual secret entry
3. **Secure memory handling**: Rust doesn't guarantee memory clearing
   - *Mitigation*: Use `zeroize` crate for sensitive data, best-effort clearing
4. **Concurrent access**: File locking can be platform-dependent
   - *Mitigation*: Use `fs2` crate for cross-platform file locking
5. **Vault migration**: Future format changes may break existing vaults
   - *Mitigation*: Include version number in vault format, design for backward compatibility

**Risks:**
- **Crypto bugs**: Incorrect implementation could compromise security
  - *Mitigation*: Use well-audited crates, extensive testing, security review
- **Data loss**: Vault corruption could lose all passwords
  - *Mitigation*: Implement automatic backups before saves, export functionality
- **User error**: Users forgetting master passwords
  - *Mitigation*: Clear warnings during setup, no password recovery mechanism (by design)

**Future Enhancements** (not in scope):
- Multiple vaults support
- Cloud sync integration
- Browser extension companion
- Password import from other managers (1Password, Bitwarden)
- Shared entries/vaults
- Password health audit (weak, duplicate, old passwords)
- Biometric unlock integration

---

## Estimated Timeline

- **Phase 1-2** (Foundation + Storage): 3-4 days
- **Phase 3-4** (Utilities + TOTP): 2-3 days
- **Phase 5** (CLI Interface): 3-4 days
- **Phase 6** (Testing): 2-3 days
- **Phase 7** (Polish): 1-2 days

**Total Estimate**: 11-16 days for a complete, production-ready CLI password manager

This plan provides a clear roadmap from project initialization to a fully functional, secure password manager with all requested features.

## TODO List
(Updated by worker agent)

## Status: PARTIAL

## Outstanding Items
(None)

## Recommendations
(None)

## Execution Summary

### Execution 2026-01-19 12:03:58
- Status: ✅ COMPLETED
- Files Modified: 21
- Duration: 859s

## Execution Summary
