use std::io;
use thiserror::Error;

/// Error type for the password manager
#[derive(Error, Debug)]
pub enum PasswordManagerError {
    #[error("Vault not found at path: {0}")]
    VaultNotFound(String),

    #[error("Vault is corrupted or invalid: {0}")]
    VaultCorrupted(String),

    #[error("Encryption failed: {0}")]
    EncryptionFailed(String),

    #[error("Decryption failed: {0}")]
    DecryptionFailed(String),

    #[error("Invalid master password")]
    InvalidMasterPassword,

    #[error("Credential not found: {0}")]
    CredentialNotFound(String),

    #[error("Clipboard error: {0}")]
    ClipboardError(String),

    #[error("IO error: {0}")]
    IoError(#[from] io::Error),

    #[error("Serialization error: {0}")]
    SerializationError(#[from] serde_json::Error),

    #[error("Invalid input: {0}")]
    InvalidInput(String),

    #[error("Password generation failed: {0}")]
    PasswordGenerationError(String),

    #[error("Vault file locked by another process")]
    VaultLocked,

    #[error("Operation cancelled by user")]
    Cancelled,
}

impl From<base64::DecodeError> for PasswordManagerError {
    fn from(err: base64::DecodeError) -> Self {
        PasswordManagerError::VaultCorrupted(format!("Base64 decode error: {}", err))
    }
}

/// Result type alias for convenience
pub type Result<T> = std::result::Result<T, PasswordManagerError>;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_error_display() {
        let err = PasswordManagerError::VaultNotFound("test.vault".to_string());
        assert!(err.to_string().contains("test.vault"));
    }

    #[test]
    fn test_invalid_master_password() {
        let err = PasswordManagerError::InvalidMasterPassword;
        assert_eq!(err.to_string(), "Invalid master password");
    }
}
