# Plan: Add Encryption, Password Protection, and Backup Functionality

## Executive Summary

This plan details the implementation of three major security and data protection features for the existing Rust-based CLI note-taking tool: (1) AES-256-GCM encryption for secure note storage, (2) Argon2-based password protection with key derivation, and (3) automated backup/restore functionality with periodic scheduling. These enhancements will transform the tool from a basic note-taking application into a secure, enterprise-grade personal knowledge management system with robust data loss prevention capabilities.

## Current State Analysis

The existing codebase provides a solid foundation with:
- ✅ Well-structured modular architecture (types, storage, cli, config, error)
- ✅ Frontmatter-based note storage with YAML metadata
- ✅ Date-based directory structure (`notes/YYYY/MM/DD-HHMMSS-title.md`)
- ✅ Comprehensive CLI with clap derive API
- ✅ Tag system, search functionality, and notebook organization
- ✅ Hierarchical note relationships

**Missing Security Features:**
- ❌ No encryption - all notes stored in plaintext
- ❌ No password protection or authentication
- ❌ No backup mechanism - data loss risk from accidental deletion
- ❌ No restore capabilities for disaster recovery

## Technical Requirements

### 1. Encryption Implementation

**Algorithm**: AES-256-GCM (Galois/Counter Mode)
- **Why AES-256-GCM**: Provides both confidentiality (encryption) and integrity (authentication)
- NIST-approved and widely adopted
- Built-in authentication prevents tampering
- 256-bit key length meets military-grade security standards
- Performance: Hardware-accelerated on most modern CPUs (AES-NI)

**Key Derivation**: Argon2id (winner of Password Hashing Competition 2015)
- **Why Argon2**: Memory-hard algorithm resistant to GPU/ASIC attacks
- Configurable time cost, memory cost, and parallelism
- Superior to PBKDF2, bcrypt, or scrypt for password-based key derivation
- Recommended by OWASP for password hashing

**Encryption Strategy**:
- Encrypt note content only (metadata remains searchable)
- Use unique nonce per encryption operation
- Store encrypted notes with `.enc` extension
- Maintain salt for each note to prevent rainbow table attacks

### 2. Password Management System

**Features Required**:
- Set master password for encryption/decryption
- Change existing master password (re-encrypt all notes)
- Remove encryption (decrypt all notes, remove password)
- Check encryption status
- Secure password prompt (no echo to terminal)
- Password validation (minimum length, complexity optional)

**Security Considerations**:
- Never store password in plaintext or logs
- Use zeroing buffers for password storage in memory
- Limit password attempts to prevent brute force
- Secure password prompt using `rpassword` crate

### 3. Backup & Restore System

**Backup Features**:
- Manual backup creation on demand
- Automatic periodic backups (configurable interval)
- Incremental vs full backup options
- Backup metadata (timestamp, note count, checksum)
- Configurable retention policy (keep last N backups)
- Compression support to reduce storage

**Restore Features**:
- List available backups with metadata
- Selective restore (specific backup)
- Full workspace restore
- Validation before restore (backup integrity check)
- Conflict resolution (merge vs replace)

**Backup Storage Strategy**:
- Separate backup directory from notes directory
- Timestamped backup filenames: `backup-YYYYMMDD-HHMMSS.tar.gz`
- Backup manifest with metadata
- Optional: Cloud storage integration (future enhancement)

## Implementation Plan

### Phase 1: Cryptography Foundation (EFFORT: MEDIUM)

#### 1.1 Add Dependencies
**File**: `Cargo.toml`

```toml
[dependencies]
# Add to existing dependencies:
aes-gcm = "0.10"          # AES-256-GCM encryption
argon2 = "0.5"            # Password-based key derivation
rand = "0.8"              # Secure random number generation
rpassword = "7.3"         # Secure password prompt
flate2 = "1.0"            # Compression for backups
tar = "0.4"               # Tar archive creation
sha2 = "0.10"             # SHA-256 for checksums
```

**Rationale**:
- `aes-gcm`: Pure Rust implementation, no OpenSSL dependency
- `argon2`: Modern, memory-hard KDF
- `rand`: Cryptographically secure random for salts/nonces
- `rpassword`: Cross-platform secure password input
- `flate2` + `tar`: Standard backup format
- `sha2`: Backup integrity verification

#### 1.2 Create Crypto Module
**New File**: `src/crypto.rs`

**Components**:
```rust
// Key derivation using Argon2id
pub fn derive_key(password: &str, salt: &[u8; 32]) -> [u8; 32]

// Encrypt plaintext with AES-256-GCM
pub fn encrypt(plaintext: &[u8], key: &[u8; 32]) -> Result<EncryptedData>

// Decrypt ciphertext with AES-256-GCM
pub fn decrypt(ciphertext: &[u8], nonce: &[u8; 12], key: &[u8; 32]) -> Result<Vec<u8>>

// Generate secure random salt
pub fn generate_salt() -> [u8; 32]

// Generate secure random nonce
pub fn generate_nonce() -> [u8; 12]

// Encrypted data structure
pub struct EncryptedData {
    pub ciphertext: Vec<u8>,
    pub nonce: [u8; 12],
}
```

**Argon2 Parameters**:
- **Algorithm**: Argon2id (hybrid of Argon2d and Argon2i)
- **Time cost**: 3 iterations
- **Memory cost**: 64 MiB (65,536 KiB)
- **Parallelism**: 4 lanes
- **Output length**: 256 bits (32 bytes)
- **Salt length**: 256 bits (32 bytes)

**Security Trade-offs**:
- Higher memory cost = better security but slower
- 64 MiB balances security and performance for desktop use
- 3 iterations provide adequate resistance to brute force

#### 1.3 Add Crypto Error Types
**File**: `src/error.rs`

Add to `NotesError` enum:
```rust
#[error("Encryption error: {0}")]
EncryptionError(String),

#[error("Decryption error: {0}")]
DecryptionError(String),

#[error("Invalid password")]
InvalidPassword,

#[error("Password not set")]
PasswordNotSet,

#[error("Password already set")]
PasswordAlreadySet,

#[error("Backup error: {0}")]
BackupError(String),

#[error("Restore error: {0}")]
RestoreError(String),
```

### Phase 2: Password Management (EFFORT: MEDIUM)

#### 2.1 Create Password Manager Module
**New File**: `src/password.rs`

**Components**:
```rust
pub struct PasswordManager {
    password_file: PathBuf,
}

impl PasswordManager {
    // Create new password manager
    pub fn new(notes_dir: PathBuf) -> Result<Self>;

    // Check if password is set
    pub fn is_password_set(&self) -> Result<bool>;

    // Set master password (creates password file)
    pub fn set_password(&self, password: &str) -> Result<()>;

    // Verify password (for login)
    pub fn verify_password(&self, password: &str) -> Result<bool>;

    // Change master password (re-encrypts all notes)
    pub fn change_password(&self, old_password: &str, new_password: &str) -> Result<()>;

    // Remove password (decrypts all notes)
    pub fn remove_password(&self, password: &str) -> Result<()>;

    // Load password hash for verification
    fn load_password_hash(&self) -> Result<Option<Vec<u8>>>;
}
```

**Password Storage Format**:
- File: `.password` in notes directory (hidden, 600 permissions)
- Format: Argon2id hash with embedded salt and parameters
- Never store plaintext password
- Include version number for future algorithm updates

#### 2.2 Add Encryption Status to Note Types
**File**: `src/types.rs`

Modify `Note` struct:
```rust
pub struct Note {
    // ... existing fields ...
    /// Whether the note content is encrypted
    #[serde(default)]
    pub encrypted: bool,
    /// Salt used for encryption (if encrypted)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub salt: Option<[u8; 32]>,
    /// Nonce used for encryption (if encrypted)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub nonce: Option<[u8; 12]>,
}
```

Modify `NoteFrontmatter`:
```rust
pub struct NoteFrontmatter {
    // ... existing fields ...
    #[serde(default)]
    pub encrypted: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub salt: Option<String>,  // Base64 encoded
    #[serde(skip_serializing_if = "Option::is_none")]
    pub nonce: Option<String>, // Base64 encoded
}
```

### Phase 3: Encrypted Storage Layer (EFFORT: MEDIUM-HIGH)

#### 3.1 Modify Storage Module for Encryption
**File**: `src/storage.rs`

**Key Changes**:

1. **Add encryption field to Storage**:
```rust
pub struct Storage {
    pub notes_dir: PathBuf,
    password_manager: Option<PasswordManager>,
    master_key: Option<[u8; 32]>,  // Cached derived key
}
```

2. **Modify save_note to encrypt if password set**:
```rust
pub fn save_note(&mut self, note: &mut Note) -> Result<()> {
    // If password is set, encrypt content before saving
    if let Some(key) = &self.master_key {
        if !note.content.is_empty() {
            let encrypted = crypto::encrypt(note.content.as_bytes(), key)?;
            note.content = base64::encode(&encrypted.ciphertext);
            note.salt = Some(crypto::generate_salt());
            note.nonce = Some(encrypted.nonce);
            note.encrypted = true;
        }
    }

    // ... rest of existing save logic ...
}
```

3. **Modify load_note to decrypt if needed**:
```rust
pub fn load_note(&self, id: &str) -> Result<Note> {
    let mut note = /* existing load logic */;

    // Decrypt if encrypted
    if note.encrypted {
        if let Some(key) = &self.master_key {
            let ciphertext = base64::decode(&note.content)?;
            let nonce = note.nonce.ok_or_else(|| NotesError::DecryptionError(
                "Missing nonce".to_string()
            ))?;

            let decrypted = crypto::decrypt(&ciphertext, &nonce, key)?;
            note.content = String::from_utf8(decrypted)?;
        } else {
            return Err(NotesError::PasswordNotSet);
        }
    }

    Ok(note)
}
```

4. **Add password authentication**:
```rust
pub fn unlock(&mut self, password: &str) -> Result<()> {
    let password_manager = self.password_manager.as_ref()
        .ok_or_else(|| NotesError::PasswordNotSet)?;

    if password_manager.verify_password(password)? {
        // Derive and cache master key
        let salt = self.get_master_salt()?;
        self.master_key = Some(crypto::derive_key(password, &salt)?);
        Ok(())
    } else {
        Err(NotesError::InvalidPassword)
    }
}

pub fn lock(&mut self) {
    self.master_key = None;  // Clear from memory
}
```

### Phase 4: CLI Commands for Encryption (EFFORT: MEDIUM)

#### 4.1 Add Encryption Commands
**File**: `src/cli.rs`

Add to `Commands` enum:
```rust
/// Manage encryption and passwords
Encrypt {
    #[command(subcommand)]
    encrypt_command: EncryptCommands,
},
```

Add new enum:
```rust
#[derive(Subcommand)]
enum EncryptCommands {
    /// Set or change master password
    Set {
        /// New password (will prompt if not provided)
        #[arg(short, long)]
        password: Option<String>,
    },

    /// Remove encryption (decrypt all notes)
    Remove {
        /// Confirm removal (required safety measure)
        #[arg(short, long)]
        confirm: bool,
    },

    /// Check encryption status
    Status,

    /// Unlock notes with password (required before accessing encrypted notes)
    Unlock {
        /// Password (will prompt if not provided)
        #[arg(short, long)]
        password: Option<String>,
    },

    /// Lock notes (clear password from memory)
    Lock,
}
```

#### 4.2 Implement Command Handlers

**Set Password**:
```rust
Commands::Encrypt(EncryptCommands::Set { password }) => {
    let pwd = password.unwrap_or_else(|| {
        rpassword::prompt_password("Enter new password: ").unwrap()
    });

    let confirm = if password.is_none() {
        rpassword::prompt_password("Confirm password: ").unwrap()
    } else {
        pwd.clone()
    };

    if pwd != confirm {
        eprintln!("Passwords do not match");
        return Ok(());
    }

    if let Err(e) = storage.set_password(&pwd) {
        eprintln!("Error setting password: {}", e);
    } else {
        println!("Password set successfully. All notes will be encrypted.");
    }
}
```

**Status**:
```rust
Commands::Encrypt(EncryptCommands::Status) => {
    match storage.is_encrypted()? {
        true => println!("🔒 Encryption is enabled"),
        false => println!("🔓 Encryption is disabled"),
    }

    let total_notes = storage.list_notes()?.len();
    let encrypted_count = storage.list_notes()?.iter()
        .filter(|n| storage.is_note_encrypted(&n.id).unwrap_or(false))
        .count();

    println!("Encrypted notes: {}/{}", encrypted_count, total_notes);
}
```

### Phase 5: Backup System Foundation (EFFORT: MEDIUM)

#### 5.1 Create Backup Module
**New File**: `src/backup.rs`

**Components**:
```rust
pub struct BackupManager {
    notes_dir: PathBuf,
    backup_dir: PathBuf,
}

pub struct BackupMetadata {
    pub id: String,
    pub created_at: DateTime<Utc>,
    pub note_count: usize,
    pub total_size: u64,
    pub checksum: String,
    pub compressed: bool,
    pub file_path: PathBuf,
}

impl BackupManager {
    // Create new backup manager
    pub fn new(notes_dir: PathBuf, backup_dir: PathBuf) -> Result<Self>;

    // Create backup
    pub fn create_backup(&self, name: Option<String>) -> Result<BackupMetadata>;

    // List all backups
    pub fn list_backups(&self) -> Result<Vec<BackupMetadata>>;

    // Restore from backup
    pub fn restore_backup(&self, backup_id: &str) -> Result<()>;

    // Delete backup
    pub fn delete_backup(&self, backup_id: &str) -> Result<()>;

    // Verify backup integrity
    pub fn verify_backup(&self, backup_id: &str) -> Result<bool>;

    // Get backup metadata
    pub fn get_backup(&self, backup_id: &str) -> Result<BackupMetadata>;
}
```

**Backup Format**:
- File naming: `backup-YYYYMMDD-HHMMSS-{name}.tar.gz`
- Internal structure:
  ```
  backup.tar.gz
  ├── notes/              # All note files
  ├── .notebooks.json     # Notebook metadata
  ├── manifest.json       # Backup metadata
  └── checksum.txt        # SHA-256 checksum
  ```

**Manifest Format**:
```json
{
  "id": "backup-20240119-143000",
  "name": "daily-backup",
  "created_at": "2024-01-19T14:30:00Z",
  "note_count": 42,
  "total_size": 1048576,
  "checksum": "a1b2c3d4...",
  "version": "1.0"
}
```

#### 5.2 Backup Implementation Details

**Create Backup**:
```rust
pub fn create_backup(&self, name: Option<String>) -> Result<BackupMetadata> {
    let timestamp = Utc::now().format("%Y%m%d-%H%M%S").to_string();
    let backup_name = name.unwrap_or_else(|| format!("backup-{}", timestamp));
    let filename = format!("backup-{}.tar.gz", timestamp);
    let backup_path = self.backup_dir.join(&filename);

    // Create temporary directory
    let temp_dir = tempfile::tempdir()?;

    // Copy notes directory
    let notes_temp = temp_dir.path().join("notes");
    fs_extra::dir::copy(&self.notes_dir, &notes_temp, &Default::default())?;

    // Create manifest
    let note_count = fs_extra::dir::get_size(&notes_temp)? as usize;
    let total_size = fs_extra::dir::get_size(&notes_temp)?;

    let manifest = serde_json::to_vec(&BackupManifest {
        id: backup_name.clone(),
        created_at: Utc::now(),
        note_count,
        total_size,
        checksum: String::new(),  // Will calculate
        version: "1.0".to_string(),
    })?;

    fs::write(temp_dir.path().join("manifest.json"), &manifest)?;

    // Calculate checksum
    let checksum = self.calculate_checksum(temp_dir.path())?;

    // Create tar.gz archive
    let tar_gz = File::create(&backup_path)?;
    let enc = GzEncoder::new(tar_gz, Compression::default());
    let mut tar = Builder::new(enc);

    tar.append_dir_all(".", temp_dir.path())?;
    tar.finish()?;

    Ok(BackupMetadata {
        id: backup_name,
        created_at: Utc::now(),
        note_count,
        total_size,
        checksum,
        compressed: true,
        file_path: backup_path,
    })
}
```

**Restore Backup**:
```rust
pub fn restore_backup(&self, backup_id: &str) -> Result<()> {
    // Find backup
    let backup = self.get_backup(backup_id)?;

    // Verify backup integrity
    if !self.verify_backup(backup_id)? {
        return Err(NotesError::BackupError(
            "Backup integrity check failed".to_string()
        ));
    }

    // Create backup of current state (safety measure)
    let safety_backup = self.create_backup(Some("pre-restore-safety".to_string()))?;
    println!("Created safety backup: {}", safety_backup.id);

    // Extract backup
    let tar_gz = File::open(&backup.file_path)?;
    let dec = GzDecoder::new(tar_gz)?;
    let mut archive = Archive::new(dec);

    // Clear current notes directory (with confirmation)
    fs::remove_dir_all(&self.notes_dir)?;
    fs::create_dir_all(&self.notes_dir)?;

    archive.unpack(&self.notes_dir)?;

    println!("Restored backup: {}", backup_id);
    Ok(())
}
```

### Phase 6: Automated Backup Scheduler (EFFORT: MEDIUM-HIGH)

#### 6.1 Add Backup Configuration
**File**: `src/types.rs`

Extend `Config` struct:
```rust
pub struct Config {
    // ... existing fields ...

    /// Backup configuration
    #[serde(default)]
    pub backup: BackupConfig,
}

pub struct BackupConfig {
    /// Enable automatic backups
    pub enabled: bool,

    /// Backup directory (default: ~/notes/backups)
    pub backup_dir: PathBuf,

    /// Backup interval in seconds (default: 86400 = daily)
    pub interval_seconds: u64,

    /// Number of backups to retain (0 = unlimited)
    pub retention_count: usize,

    /// Whether to compress backups
    pub compress: bool,
}

impl Default for BackupConfig {
    fn default() -> Self {
        Self {
            enabled: false,
            backup_dir: dirs::home_dir()
                .unwrap_or_else(|| PathBuf::from("."))
                .join("notes")
                .join("backups"),
            interval_seconds: 86400,  // 24 hours
            retention_count: 7,  // Keep last 7 backups
            compress: true,
        }
    }
}
```

#### 6.2 Implement Backup Scheduler

**Options**:
1. **Simple approach**: Cron job that calls `notes backup create`
2. **Integrated approach**: Background thread in the application
3. **Hybrid approach**: External scheduler triggered by last backup timestamp

**Recommended**: Hybrid approach using filesystem timestamps

```rust
pub fn check_and_create_automatic_backup(&self) -> Result<bool> {
    let config = self.load_config()?;

    if !config.backup.enabled {
        return Ok(false);
    }

    // Check if backup is needed
    let last_backup = self.get_last_backup_time()?;
    let now = Utc::now();
    let elapsed = now.timestamp() - last_backup.timestamp();

    if elapsed >= config.backup.interval_seconds as i64 {
        println!("Creating automatic backup...");

        // Create backup
        let backup = self.create_backup(Some("auto".to_string()))?;

        // Apply retention policy
        self.apply_retention_policy(config.backup.retention_count)?;

        println!("Automatic backup created: {}", backup.id);
        Ok(true)
    } else {
        Ok(false)
    }
}

fn get_last_backup_time(&self) -> Result<DateTime<Utc>> {
    let backups = self.list_backups()?;

    if let Some(latest) = backups.first() {
        Ok(latest.created_at)
    } else {
        // No backups exist, return very old timestamp
        Ok(DateTime::parse_from_rfc3339("1970-01-01T00:00:00Z")?
            .with_timezone(&Utc))
    }
}

fn apply_retention_policy(&self, retain_count: usize) -> Result<()> {
    if retain_count == 0 {
        return Ok(());  // Unlimited retention
    }

    let mut backups = self.list_backups()?;

    // Sort by creation date (newest first)
    backups.sort_by(|a, b| b.created_at.cmp(&a.created_at));

    // Delete old backups beyond retention count
    for old_backup in backups.into_iter().skip(retain_count) {
        println!("Deleting old backup: {}", old_backup.id);
        self.delete_backup(&old_backup.id)?;
    }

    Ok(())
}
```

**Integration with CLI**:
```rust
// Add to main command execution
if let Err(e) = storage.check_and_create_automatic_backup() {
    eprintln!("Warning: Automatic backup failed: {}", e);
}
```

### Phase 7: CLI Commands for Backup (EFFORT: MEDIUM)

#### 7.1 Add Backup Commands
**File**: `src/cli.rs`

Add to `Commands` enum:
```rust
/// Manage backups
Backup {
    #[command(subcommand)]
    backup_command: BackupCommands,
},
```

Add new enum:
```rust
#[derive(Subcommand)]
enum BackupCommands {
    /// Create a backup manually
    Create {
        /// Optional backup name
        #[arg(short, long)]
        name: Option<String>,
    },

    /// List all backups
    List {
        /// Show detailed information
        #[arg(short, long)]
        verbose: bool,
    },

    /// Restore from a backup
    Restore {
        /// Backup ID to restore
        id: String,
        /// Skip confirmation prompt
        #[arg(short, long)]
        force: bool,
    },

    /// Delete a backup
    Delete {
        /// Backup ID to delete
        id: String,
        /// Skip confirmation prompt
        #[arg(short, long)]
        force: bool,
    },

    /// Configure automatic backups
    Schedule {
        /// Enable automatic backups
        #[arg(short, long)]
        enable: bool,

        /// Backup interval in hours
        #[arg(short, long)]
        interval_hours: Option<u64>,

        /// Number of backups to retain
        #[arg(short, long)]
        retain: Option<usize>,
    },

    /// Verify backup integrity
    Verify {
        /// Backup ID to verify
        id: String,
    },
}
```

#### 7.2 Implement Backup Command Handlers

**Create Backup**:
```rust
Commands::Backup(BackupCommands::Create { name }) => {
    let backup = storage.create_backup(name)?;
    println!("✓ Backup created: {}", backup.id);
    println!("  Notes: {} | Size: {} bytes | Checksum: {}",
        backup.note_count,
        backup.total_size,
        backup.checksum);
}
```

**List Backups**:
```rust
Commands::Backup(BackupCommands::List { verbose }) => {
    let backups = storage.list_backups()?;

    if backups.is_empty() {
        println!("No backups found");
        return Ok(());
    }

    println!("Backups ({} total):\n", backups.len());

    for backup in backups {
        if verbose {
            println!("📦 {}", backup.id);
            println!("  Created: {}", backup.created_at.format("%Y-%m-%d %H:%M:%S"));
            println!("  Notes: {} | Size: {} MB", backup.note_count,
                backup.total_size / 1_048_576);
            println!("  Checksum: {}", backup.checksum);
            println!();
        } else {
            println!("  {} - {} notes ({})",
                backup.created_at.format("%Y-%m-%d %H:%M"),
                backup.note_count,
                backup.id);
        }
    }
}
```

**Restore Backup**:
```rust
Commands::Backup(BackupCommands::Restore { id, force }) => {
    if !force {
        println!("⚠️  This will replace all current notes with the backup.");
        print!("Continue? [y/N]: ");
        io::stdout().flush()?;

        let mut confirm = String::new();
        io::stdin().read_line(&mut confirm)?;

        if !confirm.trim().eq_ignore_ascii_case("y") {
            println!("Restore cancelled");
            return Ok(());
        }
    }

    match storage.restore_backup(&id) {
        Ok(_) => println!("✓ Backup restored successfully"),
        Err(e) => eprintln!("✗ Restore failed: {}", e),
    }
}
```

**Configure Schedule**:
```rust
Commands::Backup(BackupCommands::Schedule { enable, interval_hours, retain }) => {
    let mut config = config_manager.load_or_create()?;

    if let Some(interval) = interval_hours {
        config.backup.interval_seconds = interval * 3600;
        println!("Backup interval set to {} hours", interval);
    }

    if let Some(retention) = retain {
        config.backup.retention_count = retention;
        println!("Retention set to {} backups", retention);
    }

    if enable {
        config.backup.enabled = true;
        println!("Automatic backups enabled");
    }

    config_manager.save(&config)?;
    println!("Backup configuration updated");
}
```

### Phase 8: Testing (EFFORT: MEDIUM)

#### 8.1 Unit Tests for Crypto Module

**File**: `src/crypto.rs` (tests module)

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_encryption_decryption_roundtrip() {
        let plaintext = b"Secret note content";
        let key = [0u8; 32];  // Test key

        let encrypted = encrypt(plaintext, &key).unwrap();
        let decrypted = decrypt(&encrypted.ciphertext, &encrypted.nonce, &key).unwrap();

        assert_eq!(plaintext.to_vec(), decrypted);
    }

    #[test]
    fn test_different_nonce_produces_different_ciphertext() {
        let plaintext = b"Same content";
        let key = [0u8; 32];

        let enc1 = encrypt(plaintext, &key).unwrap();
        let enc2 = encrypt(plaintext, &key).unwrap();

        assert_ne!(enc1.ciphertext, enc2.ciphertext);
        assert_ne!(enc1.nonce, enc2.nonce);
    }

    #[test]
    fn test_wrong_key_fails_decryption() {
        let plaintext = b"Secret";
        let key1 = [1u8; 32];
        let key2 = [2u8; 32];

        let encrypted = encrypt(plaintext, &key1).unwrap();
        let result = decrypt(&encrypted.ciphertext, &encrypted.nonce, &key2);

        assert!(result.is_err());
    }

    #[test]
    fn test_key_derivation_deterministic() {
        let password = "test-password";
        let salt = [42u8; 32];

        let key1 = derive_key(password, &salt).unwrap();
        let key2 = derive_key(password, &salt).unwrap();

        assert_eq!(key1, key2);
    }

    #[test]
    fn test_key_derivation_different_salt() {
        let password = "test-password";
        let salt1 = [1u8; 32];
        let salt2 = [2u8; 32];

        let key1 = derive_key(password, &salt1).unwrap();
        let key2 = derive_key(password, &salt2).unwrap();

        assert_ne!(key1, key2);
    }
}
```

#### 8.2 Integration Tests for Encryption Workflow

**File**: `tests/encryption_tests.rs`

```rust
#[test]
fn test_password_protection_workflow() {
    let temp_dir = TempDir::new().unwrap();
    let mut storage = Storage::new(temp_dir.path().to_path_buf()).unwrap();

    // Create a note
    let mut note = Note::new("Secret Note".to_string(), "Sensitive content".to_string());
    storage.save_note(&mut note).unwrap();

    // Set password
    storage.set_password("my-password").unwrap();

    // Note should now be encrypted
    let loaded = storage.load_note(&note.id).unwrap();
    assert!(loaded.encrypted);
    assert_ne!(loaded.content, "Sensitive content");  // Content is encrypted

    // Load with password
    storage.unlock("my-password").unwrap();
    let decrypted = storage.load_note(&note.id).unwrap();
    assert_eq!(decrypted.content, "Sensitive content");
}

#[test]
fn test_password_change_workflow() {
    // Setup notes with old password
    let temp_dir = TempDir::new().unwrap();
    let mut storage = Storage::new(temp_dir.path().to_path_buf()).unwrap();

    // Set initial password and create encrypted notes
    storage.set_password("old-password").unwrap();
    // ... create notes ...

    // Change password
    storage.change_password("old-password", "new-password").unwrap();

    // Old password should not work
    assert!(storage.unlock("old-password").is_err());

    // New password should work
    assert!(storage.unlock("new-password").is_ok());
}
```

#### 8.3 Integration Tests for Backup Workflow

**File**: `tests/backup_tests.rs`

```rust
#[test]
fn test_backup_restore_workflow() {
    let temp_dir = TempDir::new().unwrap();
    let notes_dir = temp_dir.path().join("notes");
    let backup_dir = temp_dir.path().join("backups");

    let mut storage = Storage::new(notes_dir.clone()).unwrap();
    let backup_mgr = BackupManager::new(notes_dir, backup_dir).unwrap();

    // Create some notes
    let mut note1 = Note::new("Note 1".to_string(), "Content 1".to_string());
    let mut note2 = Note::new("Note 2".to_string(), "Content 2".to_string());
    storage.save_note(&mut note1).unwrap();
    storage.save_note(&mut note2).unwrap();

    // Create backup
    let backup = backup_mgr.create_backup(Some("test-backup".to_string())).unwrap();
    assert_eq!(backup.note_count, 2);

    // Modify notes
    note1.update_content("Modified content".to_string());
    storage.save_note(&mut note1).unwrap();

    // Delete a note
    storage.delete_note(&note2.id).unwrap();

    // Restore from backup
    backup_mgr.restore_backup(&backup.id).unwrap();

    // Verify restoration
    let restored_note1 = storage.load_note(&note1.id).unwrap();
    assert_eq!(restored_note1.content, "Content 1");  // Original content

    let restored_note2 = storage.load_note(&note2.id).unwrap();
    assert_eq!(restored_note2.title, "Note 2");  // Deleted note restored
}

#[test]
fn test_retention_policy() {
    let temp_dir = TempDir::new().unwrap();
    let backup_mgr = /* ... setup ... */;

    // Create 10 backups
    for i in 0..10 {
        backup_mgr.create_backup(Some(format!("backup-{}", i))).unwrap();
    }

    // Apply retention policy of 5
    backup_mgr.apply_retention_policy(5).unwrap();

    // Should have only 5 backups
    let backups = backup_mgr.list_backups().unwrap();
    assert_eq!(backups.len(), 5);
}
```

### Phase 9: Documentation & Polish (EFFORT: LOW)

#### 9.1 Update README

Add sections to `README.md`:

```markdown
## Encryption

Your notes can be encrypted using AES-256-GCM, a military-grade encryption algorithm.

### Setting Up Encryption

```bash
# Set a master password
notes encrypt set

# All notes will now be automatically encrypted when saved
# You must unlock before accessing notes:
notes encrypt unlock
```

### Encryption Commands

- `notes encrypt set` - Set or change master password
- `notes encrypt unlock` - Unlock notes with password (required before accessing encrypted notes)
- `notes encrypt lock` - Lock notes (clear password from memory)
- `notes encrypt status` - Check encryption status
- `notes encrypt remove` - Remove encryption (decrypt all notes)

### Security Notes

- Password is never stored in plain text
- Uses Argon2id for password-based key derivation (memory-hard, resistant to GPU attacks)
- Each note uses unique salt and nonce
- Master key is cached in memory only while unlocked
- Lock notes when not in use for maximum security

## Backup & Restore

Automatic and manual backup functionality prevents data loss.

### Manual Backup

```bash
# Create a backup
notes backup create

# Create a named backup
notes backup create --name "before-refactor"

# List all backups
notes backup list

# Detailed backup information
notes backup list --verbose
```

### Automatic Backups

```bash
# Enable daily automatic backups
notes backup schedule --enable --interval-hours 24

# Keep last 7 backups
notes backup schedule --retain 7

# Check status
notes backup list
```

### Restore from Backup

```bash
# List backups to find the ID
notes backup list

# Restore from backup
notes backup restore <backup-id>

# Restore without confirmation
notes backup restore <backup-id> --force
```

### Backup Configuration

Backups are stored in `~/notes/backups` by least. Backup settings in config file:

```json
{
  "backup": {
    "enabled": true,
    "backup_dir": "/home/user/notes/backups",
    "interval_seconds": 86400,
    "retention_count": 7,
    "compress": true
  }
}
```

### Backup Integrity

Each backup includes a SHA-256 checksum for integrity verification:

```bash
# Verify a backup
notes backup verify <backup-id>
```

## Security Best Practices

1. **Use strong passwords** - Minimum 12 characters with mixed case, numbers, and symbols
2. **Lock notes when not in use** - `notes encrypt lock` clears password from memory
3. **Enable automatic backups** - Prevents data loss from accidental deletion
4. **Regular backup testing** - Verify backups with `notes backup verify` periodically
5. **Secure backup location** - Consider encrypting backups or storing them separately
6. **Never share your password** - Password cannot be recovered, only reset (by decrypting all notes)
```

#### 9.2 Add Usage Examples

Create `examples/` directory with example scripts:

- `examples/encryption.sh` - Demonstrate encryption workflow
- `examples/backup.sh` - Demonstrate backup workflow
- `examples/automated_backup.sh` - Setup cron job for automated backups

## Assumptions & Considerations

### Security Assumptions
1. **Single-user system**: No multi-user authentication or access control
2. **Local threat model**: Protection against file theft, not remote attacks
3. **Trusted environment**: Application runs on trusted system (no keyloggers, malware)
4. **Password management**: User is responsible for remembering password (no recovery mechanism)

### Design Decisions

**Why encrypt content only, not metadata?**
- Allows search and indexing without decryption
- Metadata (title, tags, dates) is less sensitive than content
- Performance: No decryption needed for listing notes

**Why use Argon2id instead of simpler algorithms?**
- Memory-hard algorithm resists GPU/ASIC attacks
- Industry standard recommended by OWASP
- Configurable security parameters

**Why manual unlock instead of auto-prompt?**
- Explicit security model (user knows when notes are unlocked)
- Allows batch operations without prompting for each note
- Supports automation and scripting

**Why tar.gz for backups instead of database format?**
- Standard format, widely supported
- Can be extracted manually if needed
- Transparent and inspectable
- No dependency on specific backup tool

### Potential Blockers & Mitigations

**Blocker 1: Cross-platform password prompt**
- **Issue**: Terminal handling differs between Windows/Linux/macOS
- **Mitigation**: Use `rpassword` crate (cross-platform support)
- **Fallback**: Environment variable for password in automated scripts

**Blocker 2: Large note encryption performance**
- **Issue**: Encrypting large notes may be slow
- **Mitigation**: Show progress indicator, consider chunking for very large files
- **Alternative**: Stream encryption (not implemented in MVP)

**Blocker 3: Backup scheduling without background process**
- **Issue**: No daemon/background thread for automatic backups
- **Mitigation**: Check on every CLI invocation, recommend cron/scheduled task
- **Future**: Add optional background daemon

**Blocker 4: Password recovery**
- **Issue**: Lost password = lost data (by design, no backdoor)
- **Mitigation**: Clear warning during password setup, recommend password manager
- **Documentation**: Emphasize importance of password backup

**Blocker 5: Encrypted search**
- **Issue**: Cannot search encrypted note content without decryption
- **Mitigation**: Search works on metadata only, or prompt to unlock first
- **Future**: Searchable encryption (advanced feature)

## Effort Estimation

| Phase | Description | Effort | Dependencies |
|-------|-------------|--------|--------------|
| 1 | Cryptography Foundation | MEDIUM (4-6 hours) | - |
| 2 | Password Management | MEDIUM (4-6 hours) | Phase 1 |
| 3 | Encrypted Storage Layer | MEDIUM-HIGH (6-8 hours) | Phase 1, 2 |
| 4 | CLI Encryption Commands | MEDIUM (4-6 hours) | Phase 3 |
| 5 | Backup System Foundation | MEDIUM (6-8 hours) | - |
| 6 | Automated Backup Scheduler | MEDIUM-HIGH (6-8 hours) | Phase 5 |
| 7 | CLI Backup Commands | MEDIUM (4-6 hours) | Phase 5, 6 |
| 8 | Testing | MEDIUM (6-8 hours) | All phases |
| 9 | Documentation & Polish | LOW (2-4 hours) | All phases |

**Total Estimated Effort**: 42-60 hours of development time

**Critical Path**: Phase 1 → 2 → 3 → 4 (Encryption) can be developed in parallel with Phase 5 → 6 → 7 (Backup)

**Recommended Order**:
1. Complete encryption first (Phases 1-4) - core security feature
2. Add backup functionality (Phases 5-7) - data protection feature
3. Comprehensive testing (Phase 8) - ensure quality
4. Documentation (Phase 9) - user-facing

## Success Criteria

### Encryption Feature
- ✅ Notes can be encrypted with AES-256-GCM
- ✅ Master password system with Argon2 key derivation
- ✅ Password can be set, changed, and removed
- ✅ Encrypted notes are stored separately with `.enc` marker
- ✅ CLI commands for all encryption operations
- ✅ Unit tests for crypto operations
- ✅ Integration tests for encryption workflow

### Backup Feature
- ✅ Manual backup creation
- ✅ Backup listing with metadata
- ✅ Restore from backup with integrity check
- ✅ Automatic periodic backups
- ✅ Configurable retention policy
- ✅ CLI commands for all backup operations
- ✅ Unit tests for backup operations
- ✅ Integration tests for backup/restore workflow

### Quality Criteria
- ✅ All tests passing
- ✅ No security vulnerabilities (cargo audit)
- ✅ Documentation complete with examples
- ✅ Error messages are user-friendly
- ✅ Performance acceptable (<1s for encryption of typical note)

## Future Enhancements (Out of Scope)

1. **Searchable encryption** - Allow search without full decryption
2. **Cloud backup integration** - AWS S3, Google Drive, Dropbox
3. **Multiple password profiles** - Different passwords for different note sets
4. **Two-factor authentication** - YubiKey or TOTP integration
5. **End-to-end sharing** - Encrypt notes for sharing with public key crypto
6. **Backup encryption** - Encrypt backups with separate password
7. **Deduplication** - Reduce backup size with deduplication
8. **Continuous backup** - Real-time backup on every save
9. **Version history** - Keep multiple versions of each note
10. **Key rotation** - Automatic periodic re-encryption with new keys

## References

- **AES-GCM**: NIST Special Publication 800-38D
- **Argon2**: PHC Winner 2015, RFC 9106
- **Password Security**: OWASP Password Storage Cheat Sheet
- **Backup Best Practices**: NIST SP 800-34 (Contingency Planning Guide)

---

*Document Version: 1.0*
*Last Updated: 2024-01-19*
*Author: Planning Agent*
