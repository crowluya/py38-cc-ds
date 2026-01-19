//! Password management module
//!
//! This module provides secure password storage and key derivation using Argon2id.
//!
//! # Security Model
//! - Master password is hashed using Argon2id (OWASP recommended)
//! - Derived key is used for note encryption
//! - Password hash is stored in .password file (hidden, restricted permissions)
//! - Master key is cached in memory while unlocked

use super::crypto::KEY_SIZE;
use anyhow::{anyhow, Result};
use argon2::{
    password_hash::{rand_core::OsRng, PasswordHash, PasswordHasher, PasswordVerifier, SaltString},
    Argon2, Algorithm, Params, Version,
};
use rand::RngCore;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;

/// Argon2id parameters (OWASP recommendations for 2024)
/// - Memory: 64 MiB (resistant to GPU/ASIC attacks)
/// - Iterations: 3 (balanced between security and performance)
/// - Parallelism: 4 lanes (utilizes multi-core CPUs)
/// - Output length: 32 bytes (256 bits for AES-256)
const ARGON2_MEMLIMIT: u32 = 64 * 1024; // 64 MiB in KiB
const ARGON2_ITERATIONS: u32 = 3;
const ARGON2_PARALLELISM: u32 = 4;

/// Stored password hash with metadata
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PasswordHash {
    /// PHC format string containing algorithm, parameters, salt, and hash
    pub hash_string: String,
    /// Timestamp when password was set
    pub created_at: chrono::DateTime<chrono::Utc>,
}

impl PasswordHash {
    /// Create new password hash from plaintext password
    pub fn create(password: &str) -> Result<Self> {
        // Generate random salt
        let salt = SaltString::generate(&mut OsRng);

        // Configure Argon2id with secure parameters
        let params = Params::new(ARGON2_MEMLIMIT, ARGON2_ITERATIONS, ARGON2_PARALLELISM, Some(KEY_SIZE))
            .map_err(|e| anyhow!("Failed to create Argon2 params: {}", e))?;

        let argon2 = Argon2::new(Algorithm::Argon2id, Version::V0x13, params);

        // Hash the password
        let password_hash = argon2
            .hash_password(password.as_bytes(), &salt)
            .map_err(|e| anyhow!("Password hashing failed: {}", e))?;

        Ok(Self {
            hash_string: password_hash.to_string(),
            created_at: chrono::Utc::now(),
        })
    }

    /// Verify password against stored hash
    pub fn verify(&self, password: &str) -> Result<()> {
        let parsed_hash = PasswordHash::new(&self.hash_string)
            .map_err(|e| anyhow!("Invalid password hash format: {}", e))?;

        Argon2::default()
            .verify_password(password.as_bytes(), &parsed_hash)
            .map_err(|e| anyhow!("Password verification failed: {}", e))
    }

    /// Load password hash from file
    pub fn load(path: &PathBuf) -> Result<Self> {
        let content = fs::read_to_string(path)
            .map_err(|e| anyhow!("Failed to read password file: {}", e))?;

        serde_json::from_str(&content)
            .map_err(|e| anyhow!("Failed to parse password file: {}", e))
    }

    /// Save password hash to file with restricted permissions (600)
    pub fn save(&self, path: &PathBuf) -> Result<()> {
        let content = serde_json::to_string_pretty(self)
            .map_err(|e| anyhow!("Failed to serialize password hash: {}", e))?;

        fs::write(path, content)
            .map_err(|e| anyhow!("Failed to write password file: {}", e))?;

        // Set file permissions to 600 (user read/write only)
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            let mut perms = fs::metadata(path)
                .map_err(|e| anyhow!("Failed to get file metadata: {}", e))?
                .permissions();
            perms.set_mode(0o600);
            fs::set_permissions(path, perms)
                .map_err(|e| anyhow!("Failed to set password file permissions: {}", e))?;
        }

        Ok(())
    }
}

/// Derive encryption key from password using Argon2id
///
/// This function derives a cryptographic key from the password using
/// the same parameters as the password hash, ensuring compatibility.
///
/// # Arguments
/// * `password` - User's master password
/// * `salt` - Salt for key derivation (use password hash's salt)
///
/// # Returns
/// 32-byte encryption key suitable for AES-256-GCM
pub fn derive_key(password: &str, salt: &str) -> Result<[u8; KEY_SIZE]> {
    let params = Params::new(ARGON2_MEMLIMIT, ARGON2_ITERATIONS, ARGON2_PARALLELISM, Some(KEY_SIZE))
        .map_err(|e| anyhow!("Failed to create Argon2 params: {}", e))?;

    let argon2 = Argon2::new(Algorithm::Argon2id, Version::V0x13, params);

    // Derive key using the salt from stored password hash
    let mut key = [0u8; KEY_SIZE];
    let salt_bytes = base64_decode(salt)?;

    argon2
        .hash_password_into(password.as_bytes(), &salt_bytes, &mut key)
        .map_err(|e| anyhow!("Key derivation failed: {}", e))?;

    Ok(key)
}

/// Extract salt from PHC-formatted hash string
pub fn extract_salt_from_hash(hash_string: &str) -> Result<String> {
    let hash = PasswordHash::new(hash_string)
        .map_err(|e| anyhow!("Invalid hash format: {}", e))?;

    let salt = hash
        .salt
        .ok_or_else(|| anyhow!("Hash does not contain salt"))?;

    Ok(base64_encode(salt.as_bytes()))
}

/// Password manager for handling master password lifecycle
pub struct PasswordManager {
    /// Path to password file
    password_file: PathBuf,
    /// Cached derived key (while unlocked)
    master_key: Option<[u8; KEY_SIZE]>,
    /// Whether currently unlocked
    unlocked: bool,
}

impl PasswordManager {
    /// Create new password manager
    pub fn new(notes_dir: PathBuf) -> Self {
        let password_file = notes_dir.join(".password");
        Self {
            password_file,
            master_key: None,
            unlocked: false,
        }
    }

    /// Check if password is set
    pub fn is_password_set(&self) -> bool {
        self.password_file.exists()
    }

    /// Check if currently unlocked
    pub fn is_unlocked(&self) -> bool {
        self.unlocked
    }

    /// Set new master password
    pub fn set_password(&self, password: &str) -> Result<()> {
        let hash = PasswordHash::create(password)?;
        hash.save(&self.password_file)?;
        Ok(())
    }

    /// Change master password (requires being unlocked)
    pub fn change_password(&mut self, old_password: &str, new_password: &str) -> Result<()> {
        // Verify old password
        if !self.unlocked {
            return Err(anyhow!("Must be unlocked to change password"));
        }

        let hash = PasswordHash::load(&self.password_file)?;
        hash.verify(old_password)?;

        // Set new password
        let new_hash = PasswordHash::create(new_password)?;
        new_hash.save(&self.password_file)?;

        // Update cached key
        self.master_key = None;
        self.unlocked = false;

        Ok(())
    }

    /// Unlock with password and derive master key
    pub fn unlock(&mut self, password: &str) -> Result<()> {
        let hash = PasswordHash::load(&self.password_file)?;
        hash.verify(password)?;

        // Extract salt and derive key
        let salt = extract_salt_from_hash(&hash.hash_string)?;
        let key = derive_key(password, &salt)?;

        self.master_key = Some(key);
        self.unlocked = true;

        Ok(())
    }

    /// Lock and clear master key from memory
    pub fn lock(&mut self) {
        if let Some(mut key) = self.master_key.take() {
            // Zero out sensitive data
            super::crypto::zero_bytes(&mut key);
        }
        self.unlocked = false;
    }

    /// Get master key (only if unlocked)
    pub fn get_master_key(&self) -> Result<&[u8; KEY_SIZE]> {
        self.master_key
            .as_ref()
            .ok_or_else(|| anyhow!("Not unlocked. Use 'unlock' command first."))
    }

    /// Remove password file
    pub fn remove_password(&self) -> Result<()> {
        if self.password_file.exists() {
            fs::remove_file(&self.password_file)
                .map_err(|e| anyhow!("Failed to remove password file: {}", e))?;
        }
        Ok(())
    }
}

impl Drop for PasswordManager {
    fn drop(&mut self) {
        // Clear sensitive data on drop
        self.lock();
    }
}

// Helper functions for base64 encoding/decoding
fn base64_encode(data: &[u8]) -> String {
    use base64::prelude::*;
    BASE64_STANDARD.encode(data)
}

fn base64_decode(encoded: &str) -> Result<Vec<u8>> {
    use base64::prelude::*;
    BASE64_STANDARD
        .decode(encoded)
        .map_err(|e| anyhow!("Base64 decode failed: {}", e))
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn test_password_hash_create_verify() {
        let password = "secure_password_123";
        let hash = PasswordHash::create(password).unwrap();

        // Correct password should verify
        assert!(hash.verify(password).is_ok());

        // Wrong password should fail
        assert!(hash.verify("wrong_password").is_err());
    }

    #[test]
    fn test_password_hash_save_load() {
        let temp_dir = TempDir::new().unwrap();
        let password_file = temp_dir.path().join(".password");
        let password = "test_password";

        let hash = PasswordHash::create(password).unwrap();
        hash.save(&password_file).unwrap();

        let loaded = PasswordHash::load(&password_file).unwrap();
        assert!(loaded.verify(password).is_ok());
    }

    #[test]
    fn test_derive_key_deterministic() {
        let password = "test_password";
        let salt = "dGVzdHNhbHQ"; // base64 encoded "testsalt"

        let key1 = derive_key(password, salt).unwrap();
        let key2 = derive_key(password, salt).unwrap();

        assert_eq!(key1, key2);
    }

    #[test]
    fn test_derive_key_different_passwords() {
        let salt = "dGVzdHNhbHQ";

        let key1 = derive_key("password1", salt).unwrap();
        let key2 = derive_key("password2", salt).unwrap();

        assert_ne!(key1, key2);
    }

    #[test]
    fn test_password_manager() {
        let temp_dir = TempDir::new().unwrap();
        let mut manager = PasswordManager::new(temp_dir.path().to_path_buf());

        // Initially no password
        assert!(!manager.is_password_set());
        assert!(!manager.is_unlocked());

        // Set password
        manager.set_password("test123").unwrap();
        assert!(manager.is_password_set());

        // Unlock
        manager.unlock("test123").unwrap();
        assert!(manager.is_unlocked());
        assert!(manager.get_master_key().is_ok());

        // Lock
        manager.lock();
        assert!(!manager.is_unlocked());
        assert!(manager.get_master_key().is_err());
    }

    #[test]
    fn test_wrong_password_fails() {
        let temp_dir = TempDir::new().unwrap();
        let mut manager = PasswordManager::new(temp_dir.path().to_path_buf());

        manager.set_password("correct").unwrap();

        // Wrong password should fail
        assert!(manager.unlock("wrong").is_err());
        assert!(!manager.is_unlocked());
    }
}
