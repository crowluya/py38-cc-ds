use std::fmt;

/// Custom error type for the system monitoring dashboard
#[derive(Debug, thiserror::Error)]
pub enum DashboardError {
    /// IO-related errors
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),

    /// Serialization/deserialization errors
    #[error("Serialization error: {0}")]
    Serialization(String),

    /// Configuration errors
    #[error("Configuration error: {0}")]
    Config(String),

    /// System information collection errors
    #[error("System info error: {0}")]
    SystemInfo(String),

    /// Terminal UI errors
    #[error("Terminal error: {0}")]
    Terminal(String),

    /// Export errors
    #[error("Export error: {0}")]
    Export(String),

    /// Invalid input
    #[error("Invalid input: {0}")]
    InvalidInput(String),
}

/// Result type alias for convenience
pub type Result<T> = std::result::Result<T, DashboardError>;

impl From<serde_json::Error> for DashboardError {
    fn from(err: serde_json::Error) -> Self {
        DashboardError::Serialization(err.to_string())
    }
}

impl From<toml::de::Error> for DashboardError {
    fn from(err: toml::de::Error) -> Self {
        DashboardError::Config(err.to_string())
    }
}

impl From<csv::Error> for DashboardError {
    fn from(err: csv::Error) -> Self {
        DashboardError::Export(err.to_string())
    }
}
