use thiserror::Error;

/// Main error type for VaultKeeper
#[derive(Error, Debug)]
pub enum VaultError {
    #[error("Vault not found. Create a new vault with 'vaultkeeper init'")]
    VaultNotFound,

    #[error("Vault already exists. Use 'vaultkeeper unlock' to open it")]
    VaultAlreadyExists,

    #[error("Incorrect master password")]
    IncorrectPassword,

    #[error("Password is too weak. {strength_required}")]
    PasswordTooWeak { strength_required: String },

    #[error("Entry not found: {0}")]
    EntryNotFound(String),

    #[error("Entry already exists: {0}")]
    EntryAlreadyExists(String),

    #[error("Invalid input: {0}")]
    InvalidInput(String),

    #[error("Encryption error: {0}")]
    EncryptionError(String),

    #[error("Decryption error: {0}")]
    DecryptionError(String),

    #[error("Storage error: {0}")]
    StorageError(String),

    #[error("Clipboard error: {0}")]
    ClipboardError(String),

    #[error("Configuration error: {0}")]
    ConfigError(String),

    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),

    #[error("Serialization error: {0}")]
    SerializationError(String),

    #[error("Operation cancelled by user")]
    Cancelled,
}

/// Result type alias for VaultKeeper operations
pub type Result<T> = std::result::Result<T, VaultError>;

impl From<anyhow::Error> for VaultError {
    fn from(err: anyhow::Error) -> Self {
        VaultError::StorageError(err.to_string())
    }
}

impl From<serde_json::Error> for VaultError {
    fn from(err: serde_json::Error) -> Self {
        VaultError::SerializationError(err.to_string())
    }
}

impl From<toml::de::Error> for VaultError {
    fn from(err: toml::de::Error) -> Self {
        VaultError::SerializationError(err.to_string())
    }
}

impl From<toml::ser::Error> for VaultError {
    fn from(err: toml::ser::Error) -> Self {
        VaultError::SerializationError(err.to_string())
    }
}
