//! Plugin-specific error types

use std::path::PathBuf;
use thiserror::Error;

/// Result type for plugin operations
pub type PluginResult<T> = Result<T, PluginError>;

/// Errors that can occur during plugin operations
#[derive(Error, Debug)]
pub enum PluginError {
    /// Error loading the plugin library
    #[error("Failed to load plugin library '{0}': {1}")]
    LoadError(String, String),

    /// Plugin symbol not found
    #[error("Required symbol '{0}' not found in plugin")]
    SymbolNotFound(String),

    /// Plugin ABI version mismatch
    #[error("Plugin ABI version mismatch: expected {0}, found {1}")]
    AbiVersionMismatch(u32, u32),

    /// Plugin initialization failed
    #[error("Plugin initialization failed: {0}")]
    InitializationFailed(String),

    /// Plugin cleanup failed
    #[error("Plugin cleanup failed: {0}")]
    CleanupFailed(String),

    /// Plugin not found
    #[error("Plugin '{0}' not found")]
    NotFound(String),

    /// Plugin already exists
    #[error("Plugin '{0}' already exists")]
    AlreadyExists(String),

    /// Invalid plugin manifest
    #[error("Invalid plugin manifest: {0}")]
    InvalidManifest(String),

    /// Template not found in plugin
    #[error("Template '{0}' not found in plugin '{1}'")]
    TemplateNotFound(String, String),

    /// Operation not supported by plugin
    #[error("Operation not supported by plugin")]
    NotSupported,

    /// Permission denied for plugin operation
    #[error("Permission denied: {0}")]
    PermissionDenied(String),

    /// Plugin validation failed
    #[error("Plugin validation failed: {0}")]
    ValidationFailed(String),

    /// Plugin dependencies not satisfied
    #[error("Plugin dependencies not satisfied: {0}")]
    DependenciesNotSatisfied(String),

    /// IO error during plugin operation
    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),

    /// Serialization/deserialization error
    #[error("Serialization error: {0}")]
    SerializationError(#[from] serde_json::Error),

    /// YAML parsing error
    #[error("YAML error: {0}")]
    YamlError(#[from] serde_yaml::Error),

    /// Generic plugin error
    #[error("Plugin error: {0}")]
    Generic(String),
}

impl PluginError {
    /// Create a load error with context
    pub fn load_error(path: impl Into<String>, msg: impl Into<String>) -> Self {
        PluginError::LoadError(path.into(), msg.into())
    }

    /// Create a symbol not found error
    pub fn symbol_not_found(symbol: impl Into<String>) -> Self {
        PluginError::SymbolNotFound(symbol.into())
    }

    /// Create an initialization failed error
    pub fn init_failed(msg: impl Into<String>) -> Self {
        PluginError::InitializationFailed(msg.into())
    }

    /// Create a validation failed error
    pub fn validation_failed(msg: impl Into<String>) -> Self {
        PluginError::ValidationFailed(msg.into())
    }

    /// Check if this error is recoverable
    pub fn is_recoverable(&self) -> bool {
        matches!(
            self,
            PluginError::TemplateNotFound(_, _)
                | PluginError::NotSupported
                | PluginError::PermissionDenied(_)
        )
    }

    /// Check if this error is a critical failure
    pub fn is_critical(&self) -> bool {
        matches!(
            self,
            PluginError::LoadError(_, _)
                | PluginError::AbiVersionMismatch(_, _)
                | PluginError::InitializationFailed(_)
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_error_recoverable() {
        assert!(PluginError::TemplateNotFound("test".into(), "plugin".into()).is_recoverable());
        assert!(PluginError::NotSupported.is_recoverable());
        assert!(!PluginError::LoadError("test".into(), "error".into()).is_recoverable());
    }

    #[test]
    fn test_error_critical() {
        assert!(PluginError::LoadError("test".into(), "error".into()).is_critical());
        assert!(PluginError::AbiVersionMismatch(1, 2).is_critical());
        assert!(!PluginError::TemplateNotFound("test".into(), "plugin".into()).is_critical());
    }
}
