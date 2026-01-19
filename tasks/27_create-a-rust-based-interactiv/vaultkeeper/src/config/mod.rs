use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::{Path, PathBuf};

const CONFIG_FILE_NAME: &str = "config.toml";

/// Application configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    /// Clipboard clear timeout in seconds
    pub clipboard_timeout_secs: u64,

    /// Whether to show password strength indicators
    pub show_password_strength: bool,

    /// Minimum acceptable password strength (0-4)
    pub min_password_strength: u8,

    /// Number of search results to show
    pub max_search_results: usize,

    /// Theme setting
    pub theme: Theme,

    /// Editor to use for editing notes
    pub editor: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum Theme {
    Light,
    Dark,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            clipboard_timeout_secs: 15,
            show_password_strength: true,
            min_password_strength: 2,
            max_search_results: 50,
            theme: Theme::Dark,
            editor: None,
        }
    }
}

/// Configuration manager
pub struct ConfigManager {
    config_path: PathBuf,
    config: Config,
}

impl ConfigManager {
    /// Creates a new ConfigManager with default configuration
    pub fn new(config_dir: &Path) -> Result<Self> {
        let config_path = config_dir.join(CONFIG_FILE_NAME);
        let config = if config_path.exists() {
            Self::load_config(&config_path)?
        } else {
            let default_config = Config::default();
            Self::save_config(&config_path, &default_config)?;
            default_config
        };

        Ok(Self {
            config_path,
            config,
        })
    }

    /// Loads configuration from the user's config directory
    pub fn in_config_dir() -> Result<Self> {
        let config_dir = dirs::config_dir()
            .ok_or_else(|| anyhow::anyhow!("Could not determine config directory"))?;

        let app_config_dir = config_dir.join("vaultkeeper");

        // Create config directory if it doesn't exist
        fs::create_dir_all(&app_config_dir)
            .context("Failed to create config directory")?;

        Self::new(&app_config_dir)
    }

    /// Returns the current configuration
    pub fn config(&self) -> &Config {
        &self.config
    }

    /// Updates the configuration
    pub fn update_config<F>(&mut self, updater: F) -> Result<()>
    where
        F: FnOnce(&mut Config),
    {
        updater(&mut self.config);
        Self::save_config(&self.config_path, &self.config)?;
        Ok(())
    }

    /// Loads configuration from file
    fn load_config(path: &Path) -> Result<Config> {
        let contents = fs::read_to_string(path)
            .context("Failed to read config file")?;

        let config: Config = toml::from_str(&contents)
            .context("Failed to parse config file")?;

        Ok(config)
    }

    /// Saves configuration to file
    fn save_config(path: &Path, config: &Config) -> Result<()> {
        let toml = toml::to_string_pretty(config)
            .context("Failed to serialize config")?;

        fs::write(path, toml)
            .context("Failed to write config file")?;

        Ok(())
    }

    /// Returns the config file path
    pub fn config_path(&self) -> &Path {
        &self.config_path
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn test_default_config() {
        let config = Config::default();
        assert_eq!(config.clipboard_timeout_secs, 15);
        assert_eq!(config.min_password_strength, 2);
        assert!(config.show_password_strength);
    }

    #[test]
    fn test_save_and_load_config() {
        let temp_dir = TempDir::new().unwrap();

        let config_path = temp_dir.path().join("config.toml");
        let original_config = Config {
            clipboard_timeout_secs: 30,
            show_password_strength: false,
            min_password_strength: 3,
            max_search_results: 100,
            theme: Theme::Light,
            editor: Some("vim".to_string()),
        };

        ConfigManager::save_config(&config_path, &original_config).unwrap();

        let loaded_config = ConfigManager::load_config(&config_path).unwrap();

        assert_eq!(loaded_config.clipboard_timeout_secs, 30);
        assert_eq!(loaded_config.min_password_strength, 3);
        assert_eq!(loaded_config.max_search_results, 100);
    }

    #[test]
    fn test_config_manager() {
        let temp_dir = TempDir::new().unwrap();
        let config_dir = temp_dir.path();

        let mut manager = ConfigManager::new(config_dir).unwrap();

        // Verify default config
        assert_eq!(manager.config().clipboard_timeout_secs, 15);

        // Update config
        manager.update_config(|config| {
            config.clipboard_timeout_secs = 20;
        }).unwrap();

        // Verify update
        assert_eq!(manager.config().clipboard_timeout_secs, 20);

        // Create new manager and verify persistence
        let manager2 = ConfigManager::new(config_dir).unwrap();
        assert_eq!(manager2.config().clipboard_timeout_secs, 20);
    }
}
