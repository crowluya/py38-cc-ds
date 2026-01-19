# Task Workspace

Task #22: Create a Rust-based CLI password manager that uses

## Summary
- Priority: THOUGHT
- Project: None
- Created: 2026-01-19T12:14:07.695693

## Description
Create a Rust-based CLI password manager that uses AES-256-GCM encryption, supports secure credential storage with master password protection, and includes features like password generation, credential categorization, and secure clipboard integration.

## Plan & Analysis
Based on my analysis of the task and workspace, here is my comprehensive planning output:

---

## Executive Summary

Build a secure Rust CLI password manager from scratch implementing AES-256-GCM encryption, master password authentication, and credential management capabilities. The project requires approximately 8-10 major components spanning cryptography, CLI interaction, file I/O, and secure clipboard operations.

---

## Task Analysis

**Core Requirements:**
1. **Security**: AES-256-GCM encryption for stored credentials, master password protection
2. **Storage**: Secure credential storage (file-based with encrypted format)
3. **Features**:
   - Password generation (customizable length, character sets)
   - Credential categorization (folders/tags)
   - Secure clipboard integration
   - CRUD operations for credentials

**Technical Stack:**
- Language: Rust (2021 edition)
- Crypto library: `aes-gcm` + `argon2` for key derivation
- CLI: `clap` for argument parsing
- Serialization: `serde` + `serde_json` or `bincode`
- Clipboard: `clipboard` or `x11-clipboard`

**Architecture Approach:**
- Modular design with separate crates/modules
- Memory security (zeroing sensitive data)
- Lock file for concurrent access protection
- Encrypted storage format with metadata header

---

## Structured TODO List

### Phase 1: Project Setup & Dependencies

1. **Initialize Rust project structure** [Easy, 5 min]
   - Create new cargo project with `cargo init`
   - Set `edition = "2021"` in Cargo.toml
   - Create directory structure: `src/`, `tests/`, `data/`

2. **Add dependencies to Cargo.toml** [Easy, 5 min]
   - `aes-gcm` - AES-256-GCM encryption
   - `argon2` - Password-based key derivation
   - `clap` { features = ["derive"] } - CLI parsing
   - `serde`, `serde_json` - Serialization
   - `clipboard` - Clipboard access
   - `rand` - Password generation
   - `zeroize` - Secure memory handling
   - `thiserror` - Error handling
   - `colored` - Terminal styling (optional)

3. **Create module structure** [Easy, 5 min]
   - `src/crypto.rs` - Encryption/decryption
   - `src/storage.rs` - File I/O & data persistence
   - `src/password.rs` - Password generation
   - `src/clipboard.rs` - Clipboard operations
   - `src/models.rs` - Data structures
   - `src/error.rs` - Error types
   - `src/cli.rs` - Command definitions
   - `src/main.rs` - Entry point

### Phase 2: Core Data Models & Errors

4. **Define data structures in models.rs** [Medium, 15 min]
   - `Credential` struct: id, title, username, password, url, category, created_at, modified_at
   - `Vault` struct: version, credentials vector, metadata
   - `VaultHeader` struct: magic bytes, version, nonce, salt
   - Implement `Serialize`, `Deserialize` for all structs

5. **Implement error types in error.rs** [Medium, 15 min]
   - `PasswordManagerError` enum with variants:
     - `VaultNotFound`, `VaultCorrupted`
     - `EncryptionFailed`, `DecryptionFailed`
     - `InvalidMasterPassword`, `CredentialNotFound`
     - `ClipboardError`, `IoError`
   - Implement `From` traits for std::io::Error
   - Add helpful error messages and display formatting

### Phase 3: Cryptography Module

6. **Implement key derivation function** [Medium, 20 min]
   - Use Argon2id with secure parameters (t=3, m=64MB, p=4)
   - Generate unique salt for each vault
   - Convert master password + salt → 256-bit encryption key

7. **Implement encryption/decryption functions** [Medium, 25 min]
   - `encrypt_vault(data: &[u8], key: &[u8]) -> Result<(Vec<u8>, Nonce)>`
   - `decrypt_vault(encrypted_data: &[u8], nonce: &Nonce, key: &[u8]) -> Result<Vec<u8>>`
   - Use AES-256-GCM with 96-bit nonce
   - Include authentication tag verification

8. **Add secure memory utilities** [Medium, 15 min]
   - Use `zeroize` to wipe sensitive data after use
   - Implement `SecureString` wrapper for passwords
   - Ensure no password data remains in logs or stack traces

### Phase 4: Storage Module

9. **Implement vault file format** [Medium, 20 min]
   - Header: magic bytes (4), version (2), salt (32), nonce (12), tag (16)
   - Body: encrypted JSON/MessagePack vault data
   - Implement `read_vault_file(path: &Path) -> Result<VaultHeader, Vec<u8>>`
   - Implement `write_vault_file(path: &Path, header: VaultHeader, encrypted_data: &[u8])`

10. **Implement vault CRUD operations** [Medium, 25 min]
    - `create_vault(path: &Path, master_password: &str) -> Result<()>`
    - `unlock_vault(path: &Path, master_password: &str) -> Result<Vault>`
    - `save_vault(path: &Path, vault: &Vault, key: &[u8]) -> Result<()>`
    - Add lock file mechanism to prevent concurrent access

11. **Implement credential management** [Medium, 20 min]
    - `add_credential(vault: &mut Vault, cred: Credential)`
    - `get_credential(vault: &Vault, id: &str) -> Option<&Credential>`
    - `update_credential(vault: &mut Vault, id: &str, updates: Credential) -> Result<()>`
    - `delete_credential(vault: &mut Vault, id: &str) -> Result<()>`
    - `list_credentials(vault: &Vault, category: Option<&str>) -> Vec<&Credential>`
    - `search_credentials(vault: &Vault, query: &str) -> Vec<&Credential>`

### Phase 5: Password Generation

12. **Implement password generator** [Easy, 15 min]
    - `generate_password(length: usize, options: PasswordOptions) -> String`
    - Options: uppercase, lowercase, numbers, symbols, exclude_ambiguous
    - Use cryptographically secure `rand` crate
    - Ensure minimum entropy requirements
    - Add password strength checker (optional)

### Phase 6: Clipboard Integration

13. **Implement secure clipboard functions** [Medium, 15 min]
    - `copy_to_password(text: &str, clear_after: Duration) -> Result<()>`
    - Copy password to system clipboard
    - Spawn background thread to clear clipboard after N seconds
    - Handle platform-specific clipboard APIs (Linux/X11, macOS, Windows)

### Phase 7: CLI Interface

14. **Define CLI commands using clap** [Medium, 20 min]
    - Global arguments: `--vault <path>`, `-v` (verbose)
    - Subcommands:
      - `init` - Create new vault
      - `unlock` - Verify master password
      - `add` - Add new credential (interactive or flags)
      - `get <id>` - Retrieve credential by ID
      - `list [category]` - List all credentials
      - `search <query>` - Search credentials
      - `update <id>` - Update credential
      - `delete <id>` - Delete credential
      - `generate` - Generate password
      - `export` - Export to CSV/JSON (unencrypted)
      - `import` - Import from CSV/JSON

15. **Implement command handlers** [Hard, 45 min]
    - Interactive mode for sensitive data entry (passwords hidden)
    - Implement `handle_init()`
    - Implement `handle_add()` with prompts for title, username, password, url, category
    - Implement `handle_get()` with clipboard option
    - Implement `handle_list()` with table formatting
    - Implement `handle_search()` with fuzzy matching
    - Implement `handle_update()` and `handle_delete()`
    - Add confirmation prompts for destructive operations

### Phase 8: Testing & Security

16. **Write unit tests** [Medium, 30 min]
    - Test encryption/decryption round-trip
    - Test password generation entropy
    - Test credential CRUD operations
    - Test error handling paths
    - Add property-based tests using `proptest` (optional)

17. **Add integration tests** [Medium, 30 min]
    - Test full workflow: init → add → list → get → delete
    - Test vault file corruption handling
    - Test concurrent access (lock files)
    - Test clipboard clearing

18. **Security hardening** [Hard, 30 min]
    - Audit for timing attacks (use constant-time comparisons)
    - Ensure no secrets in debug output
    - Add vault file permissions (0600 on Unix)
    - Implement password strength requirements for master password
    - Add memory cleanup on drop for sensitive structs

### Phase 9: Polish & Documentation

19. **Create man pages and help text** [Easy, 15 min]
    - Document all commands and flags
    - Add usage examples
    - Create README with installation and usage instructions

20. **Build and package** [Easy, 10 min]
    - Create `release` profile builds
    - Strip binaries for smaller size
    - Add installation script or Homebrew formula (optional)

---

## Approach & Strategy

**Design Philosophy:**
- **Security first**: Zero-trust approach, secure memory handling
- **Simplicity**: Single-file vault format, no database dependencies
- **Portability**: Cross-platform support (Linux, macOS, Windows)
- **Usability**: Clear error messages, sensible defaults, interactive mode

**Key Implementation Decisions:**
1. Argon2id for key derivation (resistant to GPU/ASIC attacks)
2. Single encrypted JSON file (simpler than SQLite, easier to audit)
3. In-memory vault after unlock (balance between security and UX)
4. File locking to prevent corruption from concurrent writes
5. Clipboard auto-clear as security measure

**Potential Blockers/Risks:**
- Rust toolchain availability on user's system (requires approval to verify)
- Clipboard platform compatibility (may need conditional compilation)
- Master password recovery (intentionally impossible - document this)
- Vault migration strategy for future format changes

---

## Effort Estimates

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| Phase 1 | 1-3 | ~15 minutes |
| Phase 2 | 4-5 | ~30 minutes |
| Phase 3 | 6-8 | ~60 minutes |
| Phase 4 | 9-11 | ~65 minutes |
| Phase 5 | 12 | ~15 minutes |
| Phase 6 | 13 | ~15 minutes |
| Phase 7 | 14-15 | ~65 minutes |
| Phase 8 | 16-18 | ~90 minutes |
| Phase 9 | 19-20 | ~25 minutes |
| **Total** | **20 tasks** | **~5 hours** |

---

## Assumptions

1. User has Rust toolchain installed (will need to verify with approval)
2. Standard Unix permissions available (will use conditional compilation for Windows)
3. Single-user environment (no multiuser vault sharing)
4. No cloud sync required (local-only storage)
5. Vault file location is user-configurable
6. Terminal supports UTF-8 and basic ANSI colors

## TODO List
(Updated by worker agent)

## Status: PARTIAL

## Outstanding Items
(None)

## Recommendations
(None)

## Execution Summary

### Execution 2026-01-19 12:21:04
- Status: ✅ COMPLETED
- Files Modified: 727
- Duration: 416s

## Execution Summary
