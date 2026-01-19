//! Vault storage and persistence layer
//!
//! This module handles loading, saving, and managing vault files on disk.

use crate::crypto::{decrypt, encrypt, derive_key, generate_salt, EncryptedData, KdfConfig};
use crate::vault::Vault;
use anyhow::{anyhow, Context, Result};
use serde::{Deserialize, Serialize};
use std::fs;
use std::io::{Read, Write};
use std::path::{Path, PathBuf};

/// Header stored at the beginning of the vault file
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VaultHeader {
    /// Magic bytes to identify vault files
    pub magic: [u8; 8],

    /// Vault format version
    pub version: u32,

    /// Salt for key derivation
    pub salt: String,

    /// Key derivation function parameters
    pub kdf_config: KdfConfig,
}

impl VaultHeader {
    /// Creates a new vault header with random salt
    pub fn new() -> Self {
        Self {
            magic: *b"RSTVLTV1", // Magic: "RustVault v1"
            version: 1,
            salt: generate_salt(),
            kdf_config: KdfConfig::default(),
        }
    }

    /// Validates the magic bytes
    pub fn validate(&self) -> Result<()> {
        if self.magic != *b"RSTVLTV1" {
            return Err(anyhow!("Invalid vault file format"));
        }
        Ok(())
    }
}

impl Default for VaultHeader {
    fn default() -> Self {
        Self::new()
    }
}

/// Encrypted vault file structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EncryptedVault {
    pub header: VaultHeader,
    pub encrypted_data: EncryptedData,
}

/// Manages vault storage operations
pub struct VaultStorage {
    vault_path: PathBuf,
}

impl VaultStorage {
    /// Creates a new vault storage manager
    pub fn new(vault_path: PathBuf) -> Self {
        Self { vault_path }
    }

    /// Gets the default vault path
    pub fn default_vault_path() -> Result<PathBuf> {
        let config_dir = dirs::config_dir()
            .ok_or_else(|| anyhow!("Could not determine config directory"))?;

        let vault_dir = config_dir.join("rustvault");
        fs::create_dir_all(&vault_dir)
            .context("Failed to create vault directory")?;

        Ok(vault_dir.join("vault.rustvault"))
    }

    /// Checks if a vault exists
    pub fn vault_exists(&self) -> bool {
        self.vault_path.exists()
    }

    /// Creates a new vault file
    pub fn create_vault(&self, master_password: &str) -> Result<()> {
        if self.vault_exists() {
            return Err(anyhow!("Vault already exists at {:?}", self.vault_path));
        }

        let vault = Vault::new();
        let header = VaultHeader::new();
        let key = derive_key(master_password, &header.salt, &header.kdf_config)?;

        let vault_json = serde_json::to_vec(&vault)
            .context("Failed to serialize vault")?;

        let encrypted_data = encrypt(&vault_json, &key)?;

        let encrypted_vault = EncryptedVault {
            header,
            encrypted_data,
        };

        let vault_bytes = serde_json::to_vec(&encrypted_vault)
            .context("Failed to serialize encrypted vault")?;

        // Write with secure permissions (user read/write only)
        let mut file = fs::File::create(&self.vault_path)
            .context("Failed to create vault file")?;

        set_secure_permissions(&self.vault_path)?;

        file.write_all(&vault_bytes)
            .context("Failed to write vault data")?;

        file.sync_all()
            .context("Failed to sync vault to disk")?;

        Ok(())
    }

    /// Loads and decrypts a vault
    pub fn load_vault(&self, master_password: &str) -> Result<Vault> {
        if !self.vault_exists() {
            return Err(anyhow!("Vault not found at {:?}", self.vault_path));
        }

        // Acquire file lock to prevent concurrent access
        let _lock = acquire_file_lock(&self.vault_path)?;

        let vault_bytes = fs::read(&self.vault_path)
            .context("Failed to read vault file")?;

        let encrypted_vault: EncryptedVault = serde_json::from_slice(&vault_bytes)
            .context("Failed to parse vault file")?;

        encrypted_vault.header.validate()?;

        let key = derive_key(
            master_password,
            &encrypted_vault.header.salt,
            &encrypted_vault.header.kdf_config,
        )?;

        let decrypted_data = decrypt(&encrypted_vault.encrypted_data, &key)
            .map_err(|_| anyhow!("Incorrect master password or corrupted vault"))?;

        let vault: Vault = serde_json::from_slice(&decrypted_data)
            .context("Failed to deserialize vault")?;

        Ok(vault)
    }

    /// Saves an encrypted vault to disk
    pub fn save_vault(&self, vault: &Vault, master_password: &str) -> Result<()> {
        // Acquire file lock
        let _lock = acquire_file_lock(&self.vault_path)?;

        // Read existing header if vault exists, otherwise create new
        let header = if self.vault_exists() {
            let vault_bytes = fs::read(&self.vault_path)
                .context("Failed to read vault file")?;
            let encrypted_vault: EncryptedVault = serde_json::from_slice(&vault_bytes)
                .context("Failed to parse vault file")?;
            encrypted_vault.header
        } else {
            VaultHeader::new()
        };

        let key = derive_key(master_password, &header.salt, &header.kdf_config)?;

        let vault_json = serde_json::to_vec(vault)
            .context("Failed to serialize vault")?;

        let encrypted_data = encrypt(&vault_json, &key)?;

        let encrypted_vault = EncryptedVault {
            header,
            encrypted_data,
        };

        let vault_bytes = serde_json::to_vec(&encrypted_vault)
            .context("Failed to serialize encrypted vault")?;

        // Create backup before saving
        self.create_backup()?;

        // Write to temporary file first, then rename (atomic operation)
        let temp_path = self.vault_path.with_extension("tmp");
        {
            let mut file = fs::File::create(&temp_path)
                .context("Failed to create temporary vault file")?;

            set_secure_permissions(&temp_path)?;

            file.write_all(&vault_bytes)
                .context("Failed to write vault data")?;

            file.sync_all()
                .context("Failed to sync vault to disk")?;
        }

        // Atomic rename
        fs::rename(&temp_path, &self.vault_path)
            .context("Failed to move vault file")?;

        Ok(())
    }

    /// Creates a backup of the vault
    pub fn create_backup(&self) -> Result<()> {
        if !self.vault_exists() {
            return Ok(());
        }

        let backup_dir = self.vault_path.parent().unwrap().join("backups");
        fs::create_dir_all(&backup_dir)
            .context("Failed to create backup directory")?;

        let timestamp = chrono::Utc::now().format("%Y%m%d_%H%M%S");
        let backup_path = backup_dir.join(format!("vault_{}.backup", timestamp));

        fs::copy(&self.vault_path, &backup_path)
            .context("Failed to create backup")?;

        // Keep only the last 10 backups
        self.cleanup_old_backups(&backup_dir, 10)?;

        Ok(())
    }

    /// Cleans up old backups, keeping only the most recent ones
    fn cleanup_old_backups(&self, backup_dir: &Path, keep: usize) -> Result<()> {
        let mut backups: Vec<PathBuf> = fs::read_dir(backup_dir)
            .context("Failed to read backup directory")?
            .filter_map(|entry| entry.ok())
            .map(|entry| entry.path())
            .filter(|path| path.extension().map_or(false, |e| e == "backup"))
            .collect();

        // Sort by modification time (newest first)
        backups.sort_by(|a, b| {
            let a_time = fs::metadata(a).and_then(|m| m.modified()).unwrap_or(std::time::SystemTime::UNIX_EPOCH);
            let b_time = fs::metadata(b).and_then(|m| m.modified()).unwrap_or(std::time::SystemTime::UNIX_EPOCH);
            b_time.cmp(&a_time)
        });

        // Remove old backups
        for backup in backups.into_iter().skip(keep) {
            fs::remove_file(backup).ok();
        }

        Ok(())
    }

    /// Exports the vault to a decrypted JSON file
    pub fn export_decrypted(&self, master_password: &str, export_path: &Path) -> Result<()> {
        let vault = self.load_vault(master_password)?;

        let json = serde_json::to_string_pretty(&vault)
            .context("Failed to serialize vault")?;

        fs::write(export_path, json)
            .context("Failed to write export file")?;

        Ok(())
    }

    /// Imports a vault from a decrypted JSON file
    pub fn import_decrypted(&self, import_path: &Path, master_password: &str) -> Result<()> {
        let json = fs::read_to_string(import_path)
            .context("Failed to read import file")?;

        let vault: Vault = serde_json::from_str(&json)
            .context("Failed to parse import file")?;

        self.save_vault(&vault, master_password)?;

        Ok(())
    }
}

/// Sets secure file permissions (user read/write only)
#[cfg(unix)]
fn set_secure_permissions(path: &Path) -> Result<()> {
    use std::os::unix::fs::PermissionsExt;
    let mut perms = fs::metadata(path)
        .context("Failed to get file permissions")?
        .permissions();
    perms.set_mode(0o600); // user read/write only
    fs::set_permissions(path, perms)
        .context("Failed to set file permissions")?;
    Ok(())
}

/// Sets secure file permissions (Windows)
#[cfg(windows)]
fn set_secure_permissions(_path: &Path) -> Result<()> {
    // Windows ACLs are more complex, skip for now
    Ok(())
}

/// Acquires an exclusive file lock
fn acquire_file_lock(path: &Path) -> Result<fs2::FileLock> {
    let file = fs::File::open(path)
        .context("Failed to open vault for locking")?;

    // Try to acquire exclusive lock with timeout
    fs2::FileLock::try_lock_exclusive(&file, None, Some(std::time::Duration::from_secs(5)))
        .ok_or_else(|| anyhow!("Vault is locked by another process"))
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn test_header_creation() {
        let header = VaultHeader::new();
        assert_eq!(header.magic, *b"RSTVLTV1");
        assert_eq!(header.version, 1);
        assert!(!header.salt.is_empty());
    }

    #[test]
    fn test_header_validation() {
        let header = VaultHeader::new();
        assert!(header.validate().is_ok());

        let mut invalid_header = header.clone();
        invalid_header.magic = *b"INVALID";
        assert!(invalid_header.validate().is_err());
    }

    #[test]
    fn test_vault_roundtrip() {
        let temp_dir = TempDir::new().unwrap();
        let vault_path = temp_dir.path().join("test_vault");
        let storage = VaultStorage::new(vault_path);

        let master_password = "test_password_123";
        storage.create_vault(master_password).unwrap();
        assert!(storage.vault_exists());

        let loaded_vault = storage.load_vault(master_password).unwrap();
        assert_eq!(loaded_vault.version, 1);
    }

    #[test]
    fn test_wrong_password_fails() {
        let temp_dir = TempDir::new().unwrap();
        let vault_path = temp_dir.path().join("test_vault");
        let storage = VaultStorage::new(vault_path);

        let master_password = "test_password_123";
        storage.create_vault(master_password).unwrap();

        let result = storage.load_vault("wrong_password");
        assert!(result.is_err());
    }

    #[test]
    fn test_export_import() {
        let temp_dir = TempDir::new().unwrap();
        let vault_path = temp_dir.path().join("test_vault");
        let export_path = temp_dir.path().join("export.json");
        let storage = VaultStorage::new(vault_path);

        let master_password = "test_password_123";
        storage.create_vault(master_password).unwrap();

        storage.export_decrypted(master_password, &export_path).unwrap();
        assert!(export_path.exists());

        let import_path = temp_dir.path().join("import_vault");
        let import_storage = VaultStorage::new(import_path);
        import_storage.import_decrypted(&export_path, master_password).unwrap();

        let vault = import_storage.load_vault(master_password).unwrap();
        assert_eq!(vault.version, 1);
    }
}
