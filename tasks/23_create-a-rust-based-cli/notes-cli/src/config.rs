use crate::error::{NotesError, Result};
use crate::types::Config;
use std::fs;
use std::path::{Path, PathBuf};

/// Configuration manager for the notes application
pub struct ConfigManager {
    config_path: PathBuf,
}

impl ConfigManager {
    /// Create a new config manager
    pub fn new() -> Result<Self> {
        let config_dir = dirs::config_dir()
            .ok_or_else(|| NotesError::ConfigError("Could not find config directory".to_string()))?
            .join("notes");

        // Ensure config directory exists
        fs::create_dir_all(&config_dir)?;

        let config_path = config_dir.join("config.json");

        Ok(Self { config_path })
    }

    /// Load the configuration from file, or create default if it doesn't exist
    pub fn load_or_create(&self) -> Result<Config> {
        if self.config_path.exists() {
            self.load()
        } else {
            let config = Config::default();
            self.save(&config)?;
            Ok(config)
        }
    }

    /// Load configuration from file
    pub fn load(&self) -> Result<Config> {
        let content = fs::read_to_string(&self.config_path)?;
        let config: Config = serde_json::from_str(&content)?;
        Ok(config)
    }

    /// Save configuration to file
    pub fn save(&self, config: &Config) -> Result<()> {
        let content = serde_json::to_string_pretty(config)?;
        fs::write(&self.config_path, content)?;
        Ok(())
    }

    /// Get the configuration file path
    pub fn config_path(&self) -> &Path {
        &self.config_path
    }
}

impl Default for ConfigManager {
    fn default() -> Self {
        Self::new().expect("Failed to create ConfigManager")
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn test_config_creation() {
        let config = Config::default();
        assert!(config.notes_dir.ends_with("notes"));
        assert_eq!(config.list_limit, 50);
    }

    #[test]
    fn test_config_save_and_load() {
        let temp_dir = TempDir::new().unwrap();
        let config_path = temp_dir.path().join("config.json");

        let mut config = Config::default();
        config.notes_dir = temp_dir.path().join("my_notes");
        config.list_limit = 100;

        // Save config
        let content = serde_json::to_string_pretty(&config).unwrap();
        fs::write(&config_path, content).unwrap();

        // Load config
        let loaded_content = fs::read_to_string(&config_path).unwrap();
        let loaded: Config = serde_json::from_str(&loaded_content).unwrap();

        assert_eq!(loaded.notes_dir, config.notes_dir);
        assert_eq!(loaded.list_limit, 100);
    }
}
