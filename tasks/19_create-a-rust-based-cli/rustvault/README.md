# RustVault 🔐

A secure, feature-rich CLI password manager written in Rust with strong encryption, hierarchical vault organization, password generation, and TOTP support.

## Features

- 🔒 **Strong Encryption**: AES-256-GCM encryption with Argon2id key derivation
- 📁 **Hierarchical Organization**: Organize passwords in folders and subfolders
- 🔑 **Password Generation**: Generate secure passwords with configurable policies
- 🔐 **TOTP Support**: Built-in two-factor authentication code generation
- 🔍 **Search**: Quickly find entries across your entire vault
- 📋 **Clipboard Integration**: Copy passwords and TOTP codes securely
- 💾 **Secure Storage**: Encrypted file-based storage with automatic backups
- 🚀 **Fast & Lightweight**: Built with Rust for performance and safety

## Installation

### Prerequisites

- Rust 1.70 or later
- Cargo package manager

### Build from Source

```bash
git clone https://github.com/example/rustvault.git
cd rustvault
cargo build --release
```

The binary will be available at `target/release/rustvault`.

### Install System-Wide

```bash
cargo install --path .
```

## Quick Start

### Initialize a New Vault

```bash
rustvault init
```

You'll be prompted to create a master password. **Remember this password** - it cannot be recovered!

### Add Your First Password Entry

```bash
rustvault entry add --title "GitHub" --username "myusername"
```

You'll be prompted for the password, or use `--generate-password` to auto-generate one.

### Retrieve a Password

```bash
rustvault entry show GitHub --copy-password
```

## Usage

### Vault Management

#### Initialize
```bash
rustvault init
```
Create a new encrypted vault with a master password.

#### Unlock
```bash
rustvault unlock
```
Unlock the vault for a session (auto-locks after 5 minutes).

#### Status
```bash
rustvault status
```
View vault information and statistics.

### Entry Management

#### Add Entry
```bash
# Interactive prompts
rustvault entry add

# With flags
rustvault entry add --title "MyService" \
  --username "user@example.com" \
  --url "https://example.com" \
  --tags "work,social"

# With auto-generated password
rustvault entry add --title "MyService" --generate-password --password-length 24
```

#### List Entries
```bash
# List all entries in root folder
rustvault entry list

# List entries in a specific folder
rustvault entry list --folder "work"

# Show passwords in list
rustvault entry list --show-passwords
```

#### Show Entry Details
```bash
# Show entry
rustvault entry show "MyService"

# Show with password
rustvault entry show "MyService" --show-password

# Copy password to clipboard
rustvault entry show "MyService" --copy-password

# Copy TOTP code to clipboard
rustvault entry show "MyService" --copy-totp
```

#### Delete Entry
```bash
rustvault entry delete "MyService"

# Skip confirmation
rustvault entry delete "MyService" --force
```

### Folder Management

#### Create Folder
```bash
# Create in root
rustvault folder add "Personal"

# Create subfolder
rustvault folder add "Projects" --parent "work"
```

#### List Folders
```bash
rustvault folder list
```

#### Delete Folder
```bash
rustvault folder delete "Personal" --recursive
```

### Password Generation

#### Generate Password
```bash
# Default (16 characters, all types)
rustvault generate password

# Custom length
rustvault generate password --length 32

# Exclude ambiguous characters
rustvault generate password --exclude-ambiguous

# Only letters and numbers
rustvault generate password --no-symbols

# Copy to clipboard
rustvault generate password --copy

# Show strength estimate
rustvault generate password --show-strength
```

#### Generate Passphrase
```bash
# Default (5 words)
rustvault generate passphrase

# Custom word count
rustvault generate passphrase --words 8

# Use spaces as separator
rustvault generate passphrase --separator " "

# Capitalize words and add number
rustvault generate passphrase --capitalize --include-number
```

### TOTP (2FA)

#### Show TOTP Code
```bash
rustvault totp "MyService"
```

**Note**: TOTP secrets are configured per-entry. When adding an entry, you'll be prompted for a TOTP secret if needed.

### Search

#### Search Entries
```bash
# Basic search
rustvault search "github"

# Full details
rustvault search "github" --full
```

Searches through titles, usernames, URLs, tags, and notes.

### Import/Export

#### Export Vault
```bash
# Plaintext export (use with caution!)
rustvault export --plaintext /path/to/backup.json
```

⚠️ **Warning**: Plaintext exports are not encrypted!

#### Import Vault
```bash
rustvault import /path/to/backup.json
```

## Security Features

### Encryption

- **Algorithm**: AES-256-GCM (Galois/Counter Mode)
- **Key Derivation**: Argon2id (memory-hard, resistant to GPU attacks)
- **Salt**: Unique random salt per vault
- **Nonce**: 96-bit random nonce per encryption

### Key Derivation Parameters

- Memory Cost: 64 MiB
- Time Cost: 3 iterations
- Parallelism: 4 lanes
- Output Length: 256 bits

### File Security

- Automatic backups before saves
- Secure file permissions (user read/write only on Unix)
- File locking to prevent concurrent access
- Atomic writes (temp file → rename)

### Memory Security

- Sensitive data zeroed after use
- Master password never logged
- Clipboard auto-clear after 30 seconds (optional)

## Vault File Format

Vaults are stored as encrypted JSON files with the following structure:

```
~/.config/rustvault/
├── vault.rustvault          # Main encrypted vault
└── backups/                 # Automatic backups
    ├── vault_20240101_120000.backup
    └── vault_20240102_153045.backup
```

### Encrypted Format

```
[Header (plaintext)]
├── Magic bytes: "RSTVLTV1"
├── Version: 1
├── Salt: (base64)
└── KDF config

[Encrypted Data]
└── Vault JSON (AES-256-GCM encrypted)
```

### Vault Structure

```json
{
  "version": 1,
  "folders": {
    "": {
      "name": "",
      "entries": {
        "entry_id": {
          "id": "...",
          "title": "GitHub",
          "username": "myuser",
          "password": "encrypted",
          "url": "https://github.com",
          "notes": "...",
          "tags": ["dev", "work"],
          "totp_secret": "...",
          "created_at": "2024-01-01T00:00:00Z",
          "updated_at": "2024-01-01T00:00:00Z",
          "custom_fields": {}
        }
      },
      "subfolders": ["work", "personal"]
    }
  },
  "metadata": {
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z",
    "entry_count": 1,
    "version": 1
  }
}
```

## Configuration

### Environment Variables

- `RUSTVAULT_PATH`: Custom vault path
- `RUSTVAULT_LOG`: Log level (debug, info, warn, error)

### Command-Line Options

- `--vault-path <PATH>`: Specify custom vault location
- `--verbose, -v`: Enable verbose output
- `--help, -h`: Show help
- `--version, -V`: Show version

## Best Practices

### Master Password

- Use a **long, memorable** passphrase (4+ random words)
- Minimum 8 characters (enforced)
- Don't reuse passwords from other sites
- **Never share or store it plaintext**

### Password Policies

Recommended password generation settings:
- **High security**: 24+ characters, all character types
- **Medium security**: 16 characters, letters + numbers + symbols
- **Passphrases**: 5-7 words, easy to remember but strong

### Backups

- Vaults are **automatically backed up** before saves
- Keep **offline backups** in secure locations
- Test restores periodically
- Consider using encrypted exports for backup

### TOTP Setup

1. When setting up 2FA on a service, choose "manual setup" or "show secret"
2. Copy the base32 secret (typically shown as a QR code alternative)
3. Add entry with `--totp-secret <SECRET>`
4. Verify the code matches your authenticator app

### Clipboard Security

- Passwords/TOTP codes are copied with **30-second auto-clear**
- Manually clear clipboard after use if needed
- Be aware of clipboard managers that may log history

## Troubleshooting

### Vault Locked by Another Process

```bash
# Wait a few seconds and try again, or:
# Find and kill the locking process
lsof ~/.config/rustvault/vault.rustvault
```

### Incorrect Master Password

- Check caps lock
- Try recent variations if you changed it
- **No recovery mechanism** - this is by design for security

### Vault Corruption

- Automatic backups are created before each save
- Restore from backup:
  ```bash
  cp ~/.config/rustvault/backups/vault_*.backup ~/.config/rustvault/vault.rustvault
  ```

### Clipboard Not Working

- Install system clipboard dependencies:
  - Linux: `xclip` or `xsel`
  - macOS: included
  - Windows: included

## Development

### Build

```bash
cargo build
```

### Run Tests

```bash
cargo test
```

### Run with Debug Output

```bash
RUST_LOG=debug cargo run -- --verbose status
```

## Architecture

### Module Structure

```
src/
├── main.rs          # CLI entry point and command handlers
├── lib.rs           # Library exports and session management
├── cli.rs           # Command-line argument parsing
├── crypto.rs        # Encryption and key derivation
├── vault.rs         # Vault data structures
├── storage.rs       # File I/O and persistence
├── generator.rs     # Password generation
├── otp.rs           # TOTP functionality
└── error.rs         # Error types
```

### Dependencies

- `clap` - CLI argument parsing
- `aes-gcm` - AES-256-GCM encryption
- `argon2` - Key derivation
- `serde` - Serialization
- `totp-lite` - TOTP generation
- `inquire` - Interactive prompts
- `zeroize` - Secure memory clearing

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - See LICENSE file for details

## Security Disclosure

For security vulnerabilities, please email: security@example.com

## Acknowledgments

- Built with [Rust](https://www.rust-lang.org/)
- Cryptography by [RustCrypto](https://github.com/RustCrypto)
- Inspired by [KeePassXC](https://keepassxc.org/), [Bitwarden](https://bitwarden.com/)

## Disclaimer

**RustVault is provided as-is without warranty.** While we've made every effort to implement secure cryptography, no software is perfectly secure. Always:

- Keep backups of your vault
- Use a strong, unique master password
- Keep the software updated
- Audit the code if you have high-security requirements

**Don't forget your master password** - there is no recovery mechanism!

---

**Made with ❤️ and Rust**
