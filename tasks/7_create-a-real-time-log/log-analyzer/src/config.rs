//! Configuration management.

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;

/// Main application configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    /// Log sources configuration
    pub sources: SourcesConfig,

    /// Anomaly detector configuration
    pub detectors: DetectorsConfig,

    /// Alert configuration
    pub alerts: AlertsConfig,

    /// General settings
    pub general: GeneralConfig,
}

/// Configuration for log sources.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SourcesConfig {
    /// List of file paths to monitor
    pub files: Vec<String>,

    /// Whether to read from stdin
    pub stdin: bool,

    /// Parser configuration
    pub parser: ParserConfig,
}

/// Parser configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ParserConfig {
    /// Parser type: "generic", "json", or "pattern"
    #[serde(default = "default_parser_type")]
    pub parser_type: String,

    /// Custom regex pattern (only for pattern parser)
    pub pattern: Option<String>,
}

fn default_parser_type() -> String {
    "generic".to_string()
}

/// Configuration for anomaly detectors.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DetectorsConfig {
    /// Rate spike detector configuration
    #[serde(default)]
    pub rate_spike: RateSpikeConfig,

    /// New pattern detector configuration
    #[serde(default)]
    pub new_pattern: NewPatternConfig,

    /// Error rate detector configuration
    #[serde(default)]
    pub error_rate: ErrorRateConfig,

    /// Enable/disable specific detectors
    #[serde(default = "default_enabled_detectors")]
    pub enabled: Vec<String>,
}

fn default_enabled_detectors() -> Vec<String> {
    vec![
        "rate_spike".to_string(),
        "error_rate".to_string(),
        "new_pattern".to_string(),
    ]
}

/// Rate spike detector configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RateSpikeConfig {
    /// Window size in seconds
    #[serde(default = "default_window_size")]
    pub window_size_secs: u64,

    /// Number of standard deviations for threshold
    #[serde(default = "default_std_dev_threshold")]
    pub std_dev_threshold: f64,

    /// Minimum rate to consider (entries per second)
    #[serde(default = "default_min_rate")]
    pub min_rate: f64,
}

impl Default for RateSpikeConfig {
    fn default() -> Self {
        Self {
            window_size_secs: default_window_size(),
            std_dev_threshold: default_std_dev_threshold(),
            min_rate: default_min_rate(),
        }
    }
}

fn default_window_size() -> u64 {
    60
}

fn default_std_dev_threshold() -> f64 {
    2.0
}

fn default_min_rate() -> f64 {
    1.0
}

/// New pattern detector configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NewPatternConfig {
    /// Learning period (number of entries before detecting new patterns)
    #[serde(default = "default_learning_period")]
    pub learning_period: u64,
}

impl Default for NewPatternConfig {
    fn default() -> Self {
        Self {
            learning_period: default_learning_period(),
        }
    }
}

fn default_learning_period() -> u64 {
    100
}

/// Error rate detector configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ErrorRateConfig {
    /// Window size in seconds
    #[serde(default = "default_error_window_size")]
    pub window_size_secs: u64,

    /// Error threshold (percentage)
    #[serde(default = "default_error_threshold")]
    pub threshold_percent: f64,
}

impl Default for ErrorRateConfig {
    fn default() -> Self {
        Self {
            window_size_secs: default_error_window_size(),
            threshold_percent: default_error_threshold(),
        }
    }
}

fn default_error_window_size() -> u64 {
    60
}

fn default_error_threshold() -> f64 {
    10.0
}

/// Alert configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AlertsConfig {
    /// Console alerter configuration
    #[serde(default)]
    pub console: ConsoleAlertConfig,

    /// Webhook alerter configuration
    #[serde(default)]
    pub webhook: WebhookAlertConfig,

    /// File alerter configuration
    #[serde(default)]
    pub file: FileAlertConfig,
}

/// Console alert configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConsoleAlertConfig {
    /// Enable console alerts
    #[serde(default = "default_console_enabled")]
    pub enabled: bool,

    /// Use colored output
    #[serde(default = "default_colored")]
    pub colored: bool,

    /// Verbose output
    #[serde(default)]
    pub verbose: bool,

    /// Minimum severity level
    #[serde(default = "default_min_severity")]
    pub min_severity: String,
}

impl Default for ConsoleAlertConfig {
    fn default() -> Self {
        Self {
            enabled: default_console_enabled(),
            colored: default_colored(),
            verbose: false,
            min_severity: default_min_severity(),
        }
    }
}

fn default_console_enabled() -> bool {
    true
}

fn default_colored() -> bool {
    true
}

fn default_min_severity() -> String {
    "info".to_string()
}

/// Webhook alert configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WebhookAlertConfig {
    /// Enable webhook alerts
    #[serde(default)]
    pub enabled: bool,

    /// Webhook URL
    pub url: Option<String>,

    /// Request timeout in seconds
    #[serde(default = "default_timeout")]
    pub timeout_secs: u64,
}

impl Default for WebhookAlertConfig {
    fn default() -> Self {
        Self {
            enabled: false,
            url: None,
            timeout_secs: default_timeout(),
        }
    }
}

fn default_timeout() -> u64 {
    10
}

/// File alert configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FileAlertConfig {
    /// Enable file alerts
    #[serde(default)]
    pub enabled: bool,

    /// Output file path
    pub path: Option<PathBuf>,

    /// Use JSON format
    #[serde(default)]
    pub json_format: bool,
}

/// General application configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GeneralConfig {
    /// Log level for the application itself
    #[serde(default = "default_log_level")]
    pub log_level: String,

    /// State file for persisting statistics
    pub state_file: Option<PathBuf>,

    /// Metrics reporting interval in seconds
    #[serde(default = "default_metrics_interval")]
    pub metrics_interval_secs: u64,
}

impl Default for GeneralConfig {
    fn default() -> Self {
        Self {
            log_level: default_log_level(),
            state_file: None,
            metrics_interval_secs: default_metrics_interval(),
        }
    }
}

fn default_log_level() -> String {
    "info".to_string()
}

fn default_metrics_interval() -> u64 {
    60
}

impl Default for Config {
    fn default() -> Self {
        Self {
            sources: SourcesConfig {
                files: vec![],
                stdin: false,
                parser: ParserConfig {
                    parser_type: "generic".to_string(),
                    pattern: None,
                },
            },
            detectors: DetectorsConfig {
                rate_spike: RateSpikeConfig::default(),
                new_pattern: NewPatternConfig::default(),
                error_rate: ErrorRateConfig::default(),
                enabled: default_enabled_detectors(),
            },
            alerts: AlertsConfig {
                console: ConsoleAlertConfig::default(),
                webhook: WebhookAlertConfig::default(),
                file: FileAlertConfig {
                    enabled: false,
                    path: None,
                    json_format: false,
                },
            },
            general: GeneralConfig::default(),
        }
    }
}

/// Load configuration from a TOML file.
pub fn load_config(path: &PathBuf) -> Result<Config> {
    let contents = fs::read_to_string(path)
        .with_context(|| format!("Failed to read config file: {:?}", path))?;

    let config: Config = toml::from_str(&contents)
        .with_context(|| format!("Failed to parse config file: {:?}", path))?;

    Ok(config)
}

/// Save configuration to a TOML file.
pub fn save_config(path: &PathBuf, config: &Config) -> Result<()> {
    let contents = toml::to_string_pretty(config)
        .context("Failed to serialize configuration")?;

    fs::write(path, contents)
        .with_context(|| format!("Failed to write config file: {:?}", path))?;

    Ok(())
}

/// Merge CLI arguments with file configuration.
pub fn merge_config(mut file_config: Config, cli_args: &CliArgs) -> Config {
    // Override with CLI arguments
    if !cli_args.files.is_empty() {
        file_config.sources.files = cli_args.files.clone();
    }

    if cli_args.stdin {
        file_config.sources.stdin = true;
    }

    if cli_args.verbose {
        file_config.alerts.console.verbose = true;
    }

    if let Some(severity) = &cli_args.min_severity {
        file_config.alerts.console.min_severity = severity.clone();
    }

    if let Some(webhook_url) = &cli_args.webhook_url {
        file_config.alerts.webhook.enabled = true;
        file_config.alerts.webhook.url = Some(webhook_url.clone());
    }

    file_config
}

/// CLI arguments that can override configuration.
#[derive(Debug, Clone)]
pub struct CliArgs {
    pub files: Vec<String>,
    pub stdin: bool,
    pub verbose: bool,
    pub min_severity: Option<String>,
    pub webhook_url: Option<String>,
    pub config: Option<PathBuf>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_config() {
        let config = Config::default();
        assert_eq!(config.sources.files.len(), 0);
        assert_eq!(config.sources.stdin, false);
    }

    #[test]
    fn test_config_serialization() {
        let config = Config::default();
        let toml = toml::to_string_pretty(&config).unwrap();
        assert!(toml.contains("sources"));
        assert!(toml.contains("detectors"));
        assert!(toml.contains("alerts"));
    }
}
