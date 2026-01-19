use crate::crypto::{encrypt_vault, decrypt_vault, EncryptedData};
use crate::vault::Vault;
use anyhow::{Context, Result};
use std::fs::{self, File, OpenOptions};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use thiserror::Error;

#[derive(Error, Debug)]
pub enum StorageError {
    #[error("Vault not found at {0}")]
    VaultNotFound(PathBuf),

    #[error("Vault already exists at {0}")]
    VaultAlreadyExists(PathBuf),

    #[error("Failed to read vault: {0}")]
    ReadError(String),

    #[error("Failed to write vault: {0}")]
    WriteError(String),

    #[error("Invalid vault format: {0}")]
    InvalidFormat(String),
}

/// Default vault filename
const VAULT_FILE_NAME: &str = "vault.vault";

/// Backup directory name
const BACKUP_DIR_NAME: &str = "backups";

/// Maximum number of backups to keep
const MAX_BACKUPS: usize = 5;

/// Storage manager for vault files
pub struct VaultStorage {
    vault_path: PathBuf,
    backup_dir: PathBuf,
}

impl VaultStorage {
    /// Creates a new VaultStorage with the specified vault directory
    pub fn new(vault_dir: &Path) -> Self {
        let vault_path = vault_dir.join(VAULT_FILE_NAME);
        let backup_dir = vault_dir.join(BACKUP_DIR_NAME);

        Self {
            vault_path,
            backup_dir,
        }
    }

    /// Creates a storage manager in the user's config directory
    pub fn in_config_dir() -> Result<Self> {
        let config_dir = dirs::config_dir()
            .ok_or_else(|| anyhow::anyhow!("Could not determine config directory"))?;

        let vault_dir = config_dir.join("vaultkeeper");

        // Create directories if they don't exist
        fs::create_dir_all(&vault_dir)
            .context("Failed to create vault directory")?;

        Ok(Self::new(&vault_dir))
    }

    /// Checks if a vault exists
    pub fn vault_exists(&self) -> bool {
        self.vault_path.exists()
    }

    /// Creates a new encrypted vault file
    pub fn create_vault(&self, vault: &Vault, password: &str) -> Result<()> {
        if self.vault_exists() {
            return Err(StorageError::VaultAlreadyExists(self.vault_path.clone()).into());
        }

        self.save_vault(vault, password)?;
        Ok(())
    }

    /// Loads and decrypts a vault from disk
    pub fn load_vault(&self, password: &str) -> Result<Vault> {
        if !self.vault_exists() {
            return Err(StorageError::VaultNotFound(self.vault_path.clone()).into());
        }

        // Read encrypted data
        let encrypted_data = self.read_encrypted_data()?;

        // Decrypt vault
        let vault = decrypt_vault(&encrypted_data, password)
            .map_err(|e| anyhow::anyhow!("Failed to decrypt vault: {}", e))?;

        Ok(vault)
    }

    /// Saves and encrypts a vault to disk
    pub fn save_vault(&self, vault: &Vault, password: &str) -> Result<()> {
        // Create backup if vault already exists
        if self.vault_exists() {
            self.create_backup()?;
        }

        // Encrypt vault
        let encrypted_data = encrypt_vault(vault, password)
            .map_err(|e| anyhow::anyhow!("Failed to encrypt vault: {}", e))?;

        // Write encrypted data
        self.write_encrypted_data(&encrypted_data)?;

        Ok(())
    }

    /// Changes the master password for a vault
    pub fn change_password(&self, old_password: &str, new_password: &str) -> Result<()> {
        // Load vault with old password
        let vault = self.load_vault(old_password)?;

        // Save with new password
        self.save_vault(&vault, new_password)?;

        Ok(())
    }

    /// Creates a backup of the current vault
    fn create_backup(&self) -> Result<()> {
        // Create backup directory if it doesn't exist
        fs::create_dir_all(&self.backup_dir)
            .context("Failed to create backup directory")?;

        // Generate backup filename with timestamp
        let timestamp = chrono::Utc::now().format("%Y%m%d_%H%M%S");
        let backup_filename = format!("vault_{}.backup", timestamp);
        let backup_path = self.backup_dir.join(&backup_filename);

        // Copy vault file to backup location
        fs::copy(&self.vault_path, &backup_path)
            .context("Failed to create backup")?;

        // Clean up old backups
        self.cleanup_old_backups()?;

        Ok(())
    }

    /// Removes old backups, keeping only the most recent ones
    fn cleanup_old_backups(&self) -> Result<()> {
        if !self.backup_dir.exists() {
            return Ok(());
        }

        // Get all backup files with their metadata
        let mut backups: Vec<(PathBuf, std::time::SystemTime)> = Vec::new();

        for entry in fs::read_dir(&self.backup_dir)
            .context("Failed to read backup directory")?
        {
            let entry = entry?;
            let path = entry.path();

            if path.extension().and_then(|s| s.to_str()) == Some("backup") {
                let metadata = fs::metadata(&path)?;
                let modified = metadata.modified()?;
                backups.push((path, modified));
            }
        }

        // Sort by modification time (newest first)
        backups.sort_by(|a, b| b.1.cmp(&a.1));

        // Remove old backups beyond MAX_BACKUPS
        for (path, _) in backups.into_iter().skip(MAX_BACKUPS) {
            fs::remove_file(path).ok();
        }

        Ok(())
    }

    /// Lists available backups
    pub fn list_backups(&self) -> Result<Vec<PathBuf>> {
        if !self.backup_dir.exists() {
            return Ok(Vec::new());
        }

        let mut backups = Vec::new();

        for entry in fs::read_dir(&self.backup_dir)
            .context("Failed to read backup directory")?
        {
            let entry = entry?;
            let path = entry.path();

            if path.extension().and_then(|s| s.to_str()) == Some("backup") {
                backups.push(path);
            }
        }

        backups.sort();
        backups.reverse();

        Ok(backups)
    }

    /// Restores a vault from a backup
    pub fn restore_backup(&self, backup_path: &Path) -> Result<()> {
        if !backup_path.exists() {
            return Err(anyhow::anyhow!("Backup file not found: {:?}", backup_path));
        }

        // Create backup of current vault before restoring
        if self.vault_exists() {
            self.create_backup()?;
        }

        // Copy backup to vault location
        fs::copy(backup_path, &self.vault_path)
            .context("Failed to restore backup")?;

        Ok(())
    }

    /// Reads encrypted data from vault file
    fn read_encrypted_data(&self) -> Result<EncryptedData> {
        let mut file = File::open(&self.vault_path)
            .map_err(|e| StorageError::ReadError(e.to_string()))?;

        let mut contents = Vec::new();
        file.read_to_end(&mut contents)
            .map_err(|e| StorageError::ReadError(e.to_string()))?;

        // Deserialize encrypted data
        let encrypted_data: EncryptedData = serde_json::from_slice(&contents)
            .map_err(|e| StorageError::InvalidFormat(e.to_string()))?;

        Ok(encrypted_data)
    }

    /// Writes encrypted data to vault file
    fn write_encrypted_data(&self, data: &EncryptedData) -> Result<()> {
        // Serialize encrypted data
        let json = serde_json::to_vec_pretty(data)
            .map_err(|e| StorageError::WriteError(e.to_string()))?;

        // Write to temporary file first
        let temp_path = self.vault_path.with_extension("tmp");

        {
            let mut file = OpenOptions::new()
                .write(true)
                .create(true)
                .truncate(true)
                .open(&temp_path)
                .map_err(|e| StorageError::WriteError(e.to_string()))?;

            file.write_all(&json)
                .map_err(|e| StorageError::WriteError(e.to_string()))?;

            file.flush()
                .map_err(|e| StorageError::WriteError(e.to_string()))?;
        }

        // Atomic rename
        fs::rename(&temp_path, &self.vault_path)
            .map_err(|e| StorageError::WriteError(e.to_string()))?;

        Ok(())
    }

    /// Deletes the vault file
    pub fn delete_vault(&self) -> Result<()> {
        if !self.vault_exists() {
            return Err(StorageError::VaultNotFound(self.vault_path.clone()).into());
        }

        fs::remove_file(&self.vault_path)
            .context("Failed to delete vault")?;

        Ok(())
    }

    /// Returns the vault path
    pub fn vault_path(&self) -> &Path {
        &self.vault_path
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::vault::VaultEntry;
    use tempfile::TempDir;

    #[test]
    fn test_create_and_load_vault() {
        let temp_dir = TempDir::new().unwrap();
        let storage = VaultStorage::new(temp_dir.path());

        let mut vault = Vault::new();
        vault.add_entry(VaultEntry::new(
            "Test".to_string(),
            "user".to_string(),
            "pass".to_string(),
        ));

        let password = "test_password";

        storage.create_vault(&vault, password).unwrap();
        assert!(storage.vault_exists());

        let loaded_vault = storage.load_vault(password).unwrap();
        assert_eq!(loaded_vault.entry_count(), 1);
        assert_eq!(loaded_vault.entries[0].title, "Test");
    }

    #[test]
    fn test_save_vault_creates_backup() {
        let temp_dir = TempDir::new().unwrap();
        let storage = VaultStorage::new(temp_dir.path());

        let mut vault = Vault::new();
        vault.add_entry(VaultEntry::new(
            "Test".to_string(),
            "user".to_string(),
            "pass".to_string(),
        ));

        let password = "test_password";

        storage.create_vault(&vault, password).unwrap();

        // Modify and save again
        vault.add_entry(VaultEntry::new(
            "Test2".to_string(),
            "user2".to_string(),
            "pass2".to_string(),
        ));

        storage.save_vault(&vault, password).unwrap();

        // Check that backup was created
        let backups = storage.list_backups().unwrap();
        assert!(!backups.is_empty());
    }

    #[test]
    fn test_change_password() {
        let temp_dir = TempDir::new().unwrap();
        let storage = VaultStorage::new(temp_dir.path());

        let vault = Vault::new();

        let old_password = "old_password";
        let new_password = "new_password";

        storage.create_vault(&vault, old_password).unwrap();

        storage.change_password(old_password, new_password).unwrap();

        // Old password should not work
        assert!(storage.load_vault(old_password).is_err());

        // New password should work
        let loaded_vault = storage.load_vault(new_password).unwrap();
        assert_eq!(loaded_vault.entry_count(), 0);
    }
}
