use crate::types::{AppConfig, DisplayMode};
use anyhow::{Context, Result};
use std::path::{Path, PathBuf};

const DEFAULT_CONFIG_NAME: &str = "sysmonitor.yaml";

/// Load configuration from file, falling back to defaults
pub fn load_config(config_path: Option<PathBuf>) -> Result<AppConfig> {
    let path = config_path.or_else(find_default_config());

    if let Some(path) = path {
        if path.exists() {
            load_config_from_file(&path)
        } else {
            log::warn!("Config file not found: {:?}, using defaults", path);
            Ok(AppConfig::default())
        }
    } else {
        Ok(AppConfig::default())
    }
}

/// Load configuration from a specific file
fn load_config_from_file(path: &Path) -> Result<AppConfig> {
    let content = std::fs::read_to_string(path)
        .with_context(|| format!("Failed to read config file: {:?}", path))?;

    let config: AppConfig = serde_yaml::from_str(&content)
        .with_context(|| format!("Failed to parse config file: {:?}", path))?;

    log::info!("Loaded configuration from: {:?}", path);
    Ok(config)
}

/// Find default configuration file in standard locations
fn find_default_config() -> Option<PathBuf> {
    let locations = vec![
        // Current directory
        PathBuf::from(DEFAULT_CONFIG_NAME),
        // .config directory
        dirs::config_dir()?.join("sysmonitor").join(DEFAULT_CONFIG_NAME),
        // /etc/sysmonitor.yaml
        PathBuf::from("/etc/sysmonitor.yaml"),
    ];

    locations.into_iter().find(|p| p.exists())
}

/// Create a default configuration file
pub fn create_default_config(output_path: Option<PathBuf>) -> Result<PathBuf> {
    let path = output_path.unwrap_or_else(|| PathBuf::from(DEFAULT_CONFIG_NAME));
    let default_config = AppConfig::default();
    let yaml = serde_yaml::to_string(&default_config)
        .context("Failed to serialize default config")?;

    std::fs::write(&path, yaml)
        .with_context(|| format!("Failed to write config to: {:?}", path))?;

    log::info!("Created default configuration at: {:?}", path);
    Ok(path)
}

/// Parse display mode from string
pub fn parse_display_mode(s: &str) -> Result<DisplayMode, String> {
    match s.to_lowercase().as_str() {
        "minimal" => Ok(DisplayMode::Minimal),
        "normal" => Ok(DisplayMode::Normal),
        "detailed" => Ok(DisplayMode::Detailed),
        "json" => Ok(DisplayMode::Json),
        "tui" => Ok(DisplayMode::Tui),
        _ => Err(format!("Invalid display mode: {}. Valid options: minimal, normal, detailed, json, tui", s)),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_display_mode() {
        assert!(matches!(parse_display_mode("minimal"), Ok(DisplayMode::Minimal)));
        assert!(matches!(parse_display_mode("NORMAL"), Ok(DisplayMode::Normal)));
        assert!(matches!(parse_display_mode("Json"), Ok(DisplayMode::Json)));
        assert!(parse_display_mode("invalid").is_err());
    }

    #[test]
    fn test_default_config() {
        let config = AppConfig::default();
        assert_eq!(config.interval_ms, 1000);
        assert_eq!(config.history_size, 1000);
        assert!(config.alerts.cpu.enabled);
        assert_eq!(config.alerts.cpu.usage_threshold_percent, 80.0);
    }
}
