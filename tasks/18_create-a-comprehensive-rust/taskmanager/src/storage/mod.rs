pub mod json_store;

pub use json_store::JsonStorage;

use crate::models::Task;

/// Storage version for migration support
pub const STORAGE_VERSION: u32 = 1;

/// Data structure for serialization
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct TaskData {
    pub version: u32,
    pub tasks: Vec<Task>,
}

impl TaskData {
    pub fn new(tasks: Vec<Task>) -> Self {
        Self {
            version: STORAGE_VERSION,
            tasks,
        }
    }
}

/// Trait defining the storage backend interface
pub trait Storage: Send + Sync {
    /// Load all tasks from storage
    fn load_tasks(&self) -> Result<Vec<Task>, StorageError>;

    /// Save all tasks to storage
    fn save_tasks(&self, tasks: &[Task]) -> Result<(), StorageError>;

    /// Get the storage path for display purposes
    fn path(&self) -> &std::path::Path;
}

/// Errors that can occur during storage operations
#[derive(Debug, thiserror::Error)]
pub enum StorageError {
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),

    #[error("Serialization error: {0}")]
    Serialization(#[from] serde_json::Error),

    #[error("Storage file not found at {0}")]
    NotFound(String),

    #[error("Storage version mismatch: expected {expected}, found {found}")]
    VersionMismatch { expected: u32, found: u32 },

    #[error("Storage data corrupted: {0}")]
    Corrupted(String),

    #[error("Permission denied: {0}")]
    PermissionDenied(String),
}

/// Result type for storage operations
pub type StorageResult<T> = Result<T, StorageError>;
