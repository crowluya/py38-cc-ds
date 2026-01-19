//! RustVault - A secure CLI password manager
//!
//! This library provides the core functionality for the RustVault password manager,
//! including encryption, vault management, password generation, and TOTP support.

pub mod cli;
pub mod crypto;
pub mod error;
pub mod generator;
pub mod otp;
pub mod storage;
pub mod vault;

// Re-export commonly used types
pub use error::{Result, VaultError};
pub use generator::{generate_passphrase, generate_password, PasswordPolicy, PassphrasePolicy};
pub use otp::{generate_totp, generate_totp_default, TotpCode, TotpConfig};
pub use storage::VaultStorage;
pub use vault::{Entry, Folder, SearchResult, Vault};

use anyhow::Context;
use std::sync::{Arc, Mutex};
use std::time::Duration;

/// Vault session manager for handling unlocked vault state
pub struct VaultSession {
    storage: VaultStorage,
    vault: Arc<Mutex<Option<Vault>>>,
    master_password: Arc<Mutex<Option<String>>>,
    auto_lock_duration: Duration,
}

impl VaultSession {
    /// Creates a new vault session
    pub fn new(storage: VaultStorage, auto_lock_minutes: u64) -> Self {
        Self {
            storage,
            vault: Arc::new(Mutex::new(None)),
            master_password: Arc::new(Mutex::new(None)),
            auto_lock_duration: Duration::from_secs(auto_lock_minutes * 60),
        }
    }

    /// Checks if the vault is currently unlocked
    pub fn is_unlocked(&self) -> bool {
        self.vault.lock().unwrap().is_some()
    }

    /// Unlocks the vault with a master password
    pub fn unlock(&self, master_password: &str) -> Result<()> {
        let vault = self.storage.load_vault(master_password)?;

        *self.vault.lock().unwrap() = Some(vault);
        *self.master_password.lock().unwrap() = Some(master_password.to_string());

        Ok(())
    }

    /// Locks the vault, clearing it from memory
    pub fn lock(&self) -> Result<()> {
        let mut vault_guard = self.vault.lock().unwrap();
        let mut password_guard = self.master_password.lock().unwrap();

        if let Some(mut vault) = vault_guard.take() {
            // Clear sensitive data
            for (_path, folder) in vault.folders.iter_mut() {
                for (_id, entry) in folder.entries.iter_mut() {
                    entry.password.zeroize();
                }
            }
        }

        if let Some(mut password) = password_guard.take() {
            password.zeroize();
        }

        Ok(())
    }

    /// Saves the vault to disk
    pub fn save(&self) -> Result<()> {
        let vault = self.vault.lock().unwrap();
        let master_password = self.master_password.lock().unwrap();

        match (vault.as_ref(), master_password.as_ref()) {
            (Some(v), Some(p)) => {
                self.storage.save_vault(v, p)?;
                Ok(())
            }
            _ => Err(VaultError::VaultLocked.into()),
        }
    }

    /// Gets a reference to the vault
    pub fn vault(&self) -> Result<Arc<Mutex<Option<Vault>>>> {
        if self.is_unlocked() {
            Ok(self.vault.clone())
        } else {
            Err(VaultError::VaultLocked.into())
        }
    }

    /// Gets the master password (use with caution!)
    pub fn master_password(&self) -> Result<String> {
        let password_guard = self.master_password.lock().unwrap();
        password_guard
            .as_ref()
            .map(|p| p.clone())
            .ok_or_else(|| VaultError::VaultLocked.into())
    }

    /// Executes an operation on the vault, ensuring it's unlocked
    pub fn with_vault<F, R>(&self, f: F) -> Result<R>
    where
        F: FnOnce(&Vault) -> Result<R>,
    {
        let vault_guard = self.vault.lock().unwrap();
        let vault = vault_guard
            .as_ref()
            .ok_or_else(|| anyhow::anyhow!("Vault is locked"))?;

        f(vault)
    }

    /// Executes an operation on the vault with mutable access
    pub fn with_vault_mut<F, R>(&self, f: F) -> Result<R>
    where
        F: FnOnce(&mut Vault) -> Result<R>,
    {
        let mut vault_guard = self.vault.lock().unwrap();
        let vault = vault_guard
            .as_mut()
            .ok_or_else(|| anyhow::anyhow!("Vault is locked"))?;

        let result = f(vault)?;

        // Auto-save after modifications
        drop(vault_guard);
        self.save()?;

        Ok(result)
    }
}

/// Configuration for the password manager
#[derive(Debug, Clone)]
pub struct Config {
    pub vault_path: std::path::PathBuf,
    pub auto_lock_minutes: u64,
    pub clipboard_timeout_seconds: u64,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            vault_path: VaultStorage::default_vault_path()
                .unwrap_or_else(|_| std::path::PathBuf::from("vault.rustvault")),
            auto_lock_minutes: 5,
            clipboard_timeout_seconds: 30,
        }
    }
}

/// Utility function to copy text to clipboard
pub fn copy_to_clipboard(text: &str) -> Result<()> {
    let mut ctx = clipboard::ClipboardContext::new()
        .context("Failed to access clipboard")?;

    ctx.set_contents(text.to_string())
        .context("Failed to copy to clipboard")?;

    Ok(())
}

/// Utility function to clear clipboard
pub fn clear_clipboard() -> Result<()> {
    let mut ctx = clipboard::ClipboardContext::new()
        .context("Failed to access clipboard")?;

    ctx.set_contents(String::new())
        .context("Failed to clear clipboard")?;

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn test_session_creation() {
        let temp_dir = TempDir::new().unwrap();
        let vault_path = temp_dir.path().join("test_vault");
        let storage = VaultStorage::new(vault_path);
        let session = VaultSession::new(storage, 5);

        assert!(!session.is_unlocked());
    }

    #[test]
    fn test_session_unlock_lock() {
        let temp_dir = TempDir::new().unwrap();
        let vault_path = temp_dir.path().join("test_vault");
        let storage = VaultStorage::new(vault_path);

        // Create a vault first
        let master_password = "test_password_123";
        storage.create_vault(master_password).unwrap();

        let session = VaultSession::new(storage, 5);
        session.unlock(master_password).unwrap();
        assert!(session.is_unlocked());

        session.lock().unwrap();
        assert!(!session.is_unlocked());
    }

    #[test]
    fn test_with_vault_operation() {
        let temp_dir = TempDir::new().unwrap();
        let vault_path = temp_dir.path().join("test_vault");
        let storage = VaultStorage::new(vault_path);

        let master_password = "test_password_123";
        storage.create_vault(master_password).unwrap();

        let session = VaultSession::new(storage, 5);
        session.unlock(master_password).unwrap();

        let result = session.with_vault(|v| Ok(v.metadata.entry_count));
        assert_eq!(result.unwrap(), 0);
    }
}
