//! Error types for the password manager
//!
//! This module defines custom error types for better error handling and user messaging.

use thiserror::Error;

/// Main error type for the password manager
#[derive(Error, Debug)]
pub enum VaultError {
    #[error("Vault not found at {0}")]
    VaultNotFound(String),

    #[error("Vault already exists at {0}")]
    VaultAlreadyExists(String),

    #[error("Incorrect master password")]
    IncorrectPassword,

    #[error("Vault is corrupted or invalid format")]
    CorruptedVault,

    #[error("Vault is locked by another process")]
    VaultLocked,

    #[error("Entry not found: {0}")]
    EntryNotFound(String),

    #[error("Folder not found: {0}")]
    FolderNotFound(String),

    #[error("Folder already exists: {0}")]
    FolderAlreadyExists(String),

    #[error("Invalid password: {0}")]
    InvalidPassword(String),

    #[error("Encryption failed: {0}")]
    EncryptionFailed(String),

    #[error("Decryption failed: {0}")]
    DecryptionFailed(String),

    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),

    #[error("Serialization error: {0}")]
    SerializationError(String),

    #[error("Invalid TOTP secret: {0}")]
    InvalidTotpSecret(String),

    #[error("TOTP generation failed: {0}")]
    TotpGenerationFailed(String),
}

impl From<serde_json::Error> for VaultError {
    fn from(err: serde_json::Error) -> Self {
        VaultError::SerializationError(err.to_string())
    }
}

/// Result type alias for convenience
pub type Result<T> = std::result::Result<T, VaultError>;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_error_display() {
        let err = VaultError::VaultNotFound("/path/to/vault".to_string());
        assert_eq!(err.to_string(), "Vault not found at /path/to/vault");
    }

    #[test]
    fn test_incorrect_password() {
        let err = VaultError::IncorrectPassword;
        assert_eq!(err.to_string(), "Incorrect master password");
    }
}
