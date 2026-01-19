use super::{Storage, StorageError, StorageResult, TaskData, STORAGE_VERSION};
use crate::models::Task;
use std::fs;
use std::path::{Path, PathBuf};

/// JSON file-based storage backend
#[derive(Debug, Clone)]
pub struct JsonStorage {
    file_path: PathBuf,
}

impl JsonStorage {
    /// Create a new JsonStorage with the specified path
    pub fn new(file_path: PathBuf) -> Self {
        Self { file_path }
    }

    /// Create JsonStorage with default location (~/.taskmanager/tasks.json)
    pub fn default_location() -> Result<Self, StorageError> {
        let home_dir = dirs::home_dir()
            .ok_or_else(|| StorageError::Io(std::io::Error::new(
                std::io::ErrorKind::NotFound,
                "Could not determine home directory",
            )))?;

        let taskmanager_dir = home_dir.join(".taskmanager");
        let file_path = taskmanager_dir.join("tasks.json");

        // Ensure directory exists
        if !taskmanager_dir.exists() {
            fs::create_dir_all(&taskmanager_dir).map_err(|e| {
                StorageError::Io(std::io::Error::new(
                    e.kind(),
                    format!("Failed to create directory {}: {}", taskmanager_dir.display(), e),
                ))
            })?;
        }

        Ok(Self { file_path })
    }

    /// Create a backup of the current task file
    pub fn create_backup(&self) -> StorageResult<PathBuf> {
        if !self.file_path.exists() {
            return Err(StorageError::NotFound(self.file_path.display().to_string()));
        }

        let backup_path = self.file_path.with_extension(format!(
            "json.bak.{}",
            chrono::Utc::now().format("%Y%m%d_%H%M%S")
        ));

        fs::copy(&self.file_path, &backup_path).map_err(|e| {
            StorageError::Io(std::io::Error::new(
                e.kind(),
                format!("Failed to create backup: {}", e),
            ))
        })?;

        Ok(backup_path)
    }

    /// Import tasks from a backup file
    pub fn import_backup(&self, backup_path: &Path) -> StorageResult<Vec<Task>> {
        if !backup_path.exists() {
            return Err(StorageError::NotFound(backup_path.display().to_string()));
        }

        let content = fs::read_to_string(backup_path).map_err(|e| {
            StorageError::Io(std::io::Error::new(
                e.kind(),
                format!("Failed to read backup file: {}", e),
            ))
        })?;

        let task_data: TaskData = serde_json::from_str(&content)?;

        Ok(task_data.tasks)
    }
}

impl Storage for JsonStorage {
    fn load_tasks(&self) -> Result<Vec<Task>, StorageError> {
        if !self.file_path.exists() {
            // Return empty list if file doesn't exist yet
            return Ok(Vec::new());
        }

        let content = fs::read_to_string(&self.file_path).map_err(|e| {
            StorageError::Io(std::io::Error::new(
                e.kind(),
                format!(
                    "Failed to read task file at {}: {}",
                    self.file_path.display(),
                    e
                ),
            ))
        })?;

        if content.trim().is_empty() {
            return Ok(Vec::new());
        }

        let task_data: TaskData = serde_json::from_str(&content).map_err(|e| {
            StorageError::Corrupted(format!(
                "Failed to parse task file at {}: {}",
                self.file_path.display(),
                e
            ))
        })?;

        // Check version
        if task_data.version != STORAGE_VERSION {
            return Err(StorageError::VersionMismatch {
                expected: STORAGE_VERSION,
                found: task_data.version,
            });
        }

        Ok(task_data.tasks)
    }

    fn save_tasks(&self, tasks: &[Task]) -> Result<(), StorageError> {
        let task_data = TaskData::new(tasks.to_vec());

        let json = serde_json::to_string_pretty(&task_data).map_err(|e| {
            StorageError::Serialization(serde_json::Error::new(
                e.line(),
                e.column(),
                &format!("Failed to serialize tasks: {}", e),
            ))
        })?;

        // Write to a temporary file first, then rename to avoid corruption
        let temp_path = self.file_path.with_extension("json.tmp");

        fs::write(&temp_path, &json).map_err(|e| {
            StorageError::Io(std::io::Error::new(
                e.kind(),
                format!(
                    "Failed to write temporary file at {}: {}",
                    temp_path.display(),
                    e
                ),
            ))
        })?;

        // Rename temp file to actual file (atomic operation)
        fs::rename(&temp_path, &self.file_path).map_err(|e| {
            StorageError::Io(std::io::Error::new(
                e.kind(),
                format!(
                    "Failed to save tasks to {}: {}",
                    self.file_path.display(),
                    e
                ),
            ))
        })?;

        Ok(())
    }

    fn path(&self) -> &Path {
        &self.file_path
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::Priority;
    use tempfile::TempDir;

    #[test]
    fn test_json_storage_save_and_load() {
        let temp_dir = TempDir::new().unwrap();
        let file_path = temp_dir.path().join("tasks.json");
        let storage = JsonStorage::new(file_path);

        let tasks = vec![Task::new("Test task".to_string())];
        storage.save_tasks(&tasks).unwrap();

        let loaded = storage.load_tasks().unwrap();
        assert_eq!(loaded.len(), 1);
        assert_eq!(loaded[0].title, "Test task");
    }

    #[test]
    fn test_json_storage_empty() {
        let temp_dir = TempDir::new().unwrap();
        let file_path = temp_dir.path().join("tasks.json");
        let storage = JsonStorage::new(file_path);

        let loaded = storage.load_tasks().unwrap();
        assert_eq!(loaded.len(), 0);
    }

    #[test]
    fn test_json_storage_with_tags() {
        let temp_dir = TempDir::new().unwrap();
        let file_path = temp_dir.path().join("tasks.json");
        let storage = JsonStorage::new(file_path);

        let tasks = vec![Task::new("Test task".to_string())
            .with_tags(vec!["work".to_string(), "urgent".to_string()])
            .with_priority(Priority::High)];

        storage.save_tasks(&tasks).unwrap();

        let loaded = storage.load_tasks().unwrap();
        assert_eq!(loaded[0].tags, vec!["work", "urgent"]);
        assert_eq!(loaded[0].priority, Priority::High);
    }
}
