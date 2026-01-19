use crate::config::{create_default_config, load_config, parse_display_mode};
use crate::types::DisplayMode;
use anyhow::Result;
use clap::Parser;
use std::path::PathBuf;

/// System resource monitoring tool with real-time statistics, alerts, and data export
#[derive(Parser, Debug)]
#[command(name = "sysmonitor")]
#[command(author = "System Monitor Team")]
#[command(version = "0.1.0")]
#[command(about = "A comprehensive CLI tool for system resource monitoring", long_about = None)]
pub struct Args {
    /// Monitoring interval in milliseconds (default: from config or 1000)
    #[arg(short, long)]
    pub interval: Option<u64>,

    /// Display mode: minimal, normal, detailed, json, tui
    #[arg(short, long, value_name = "MODE")]
    pub mode: Option<String>,

    /// Configuration file path (default: ~/.config/sysmonitor/sysmonitor.yaml)
    #[arg(short, long, value_name = "FILE")]
    pub config: Option<PathBuf>,

    /// Generate default configuration file
    #[arg(long, value_name = "FILE")]
    pub generate_config: Option<Option<PathBuf>>,

    /// Number of historical data points to keep
    #[arg(long, value_name = "N")]
    pub history: Option<usize>,

    /// Export historical data to file
    #[arg(long, value_name = "FILE")]
    pub export: Option<PathBuf>,

    /// Export format: csv, json
    #[arg(long, value_name = "FORMAT")]
    pub export_format: Option<String>,

    /// Disable alerts
    #[arg(long)]
    pub no_alerts: bool,

    /// Verbose output
    #[arg(short, long)]
    pub verbose: bool,

    /// Run for specified duration and exit (e.g., 10s, 5m, 1h)
    #[arg(long, value_name = "DURATION")]
    pub duration: Option<String>,

    /// Monitor specific disk mount points only
    #[arg(long, value_name = "MOUNTS")]
    pub mounts: Option<Vec<String>>,
}

impl Args {
    /// Parse command line arguments and load configuration
    pub fn load_configuration(&self) -> Result<RuntimeConfig> {
        // Handle config generation
        if self.generate_config.is_some() {
            let path = self.generate_config.as_ref().unwrap().clone().unwrap_or_else(|| {
                dirs::config_dir()
                    .unwrap_or_else(|| PathBuf::from("."))
                    .join("sysmonitor")
                    .join("sysmonitor.yaml")
            });

            // Ensure parent directory exists
            if let Some(parent) = path.parent() {
                std::fs::create_dir_all(parent)?;
            }

            let config_path = create_default_config(Some(path))?;
            return Ok(RuntimeConfig::GenerateConfig(config_path));
        }

        // Load configuration
        let mut config = load_config(self.config.clone())?;

        // Override with command line arguments
        if let Some(interval) = self.interval {
            config.interval_ms = interval;
        }

        if let Some(mode) = &self.mode {
            config.display_mode = parse_display_mode(mode)?;
        }

        if let Some(history) = self.history {
            config.history_size = history;
        }

        if let Some(mounts) = &self.mounts {
            config.monitored_mount_points = mounts.clone();
        }

        if self.no_alerts {
            config.alerts.cpu.enabled = false;
            config.alerts.memory.enabled = false;
            config.alerts.disk.enabled = false;
            config.alerts.network.enabled = false;
        }

        // Initialize logging
        let log_level = if self.verbose {
            log::LevelFilter::Debug
        } else {
            log::LevelFilter::Info
        };
        env_logger::Builder::new().filter_level(log_level).init();

        Ok(RuntimeConfig::Run(config))
    }

    /// Parse duration string to seconds
    pub fn parse_duration(&self) -> Result<Option<u64>> {
        if let Some(duration_str) = &self.duration {
            let duration_str = duration_str.to_lowercase();
            let (num_str, unit) = duration_str.split_at(duration_str.len() - 1);

            let num: u64 = num_str.parse()
                .map_err(|_| anyhow::anyhow!("Invalid duration number: {}", num_str))?;

            let seconds = match unit {
                "s" => num,
                "m" => num * 60,
                "h" => num * 60 * 60,
                _ => return Err(anyhow::anyhow!("Invalid duration unit: {}. Use s, m, or h", unit)),
            };

            Ok(Some(seconds))
        } else {
            Ok(None)
        }
    }

    /// Parse export format
    pub fn get_export_format(&self) -> ExportFormat {
        match self.export_format.as_deref() {
            Some("csv") => ExportFormat::Csv,
            Some("json") | None => ExportFormat::Json,
            Some(other) => {
                log::warn!("Unknown export format '{}', defaulting to json", other);
                ExportFormat::Json
            }
        }
    }
}

#[derive(Debug)]
pub enum RuntimeConfig {
    Run(crate::types::AppConfig),
    GenerateConfig(PathBuf),
}

#[derive(Debug, Clone, Copy)]
pub enum ExportFormat {
    Csv,
    Json,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_duration() {
        let args = Args {
            interval: None,
            mode: None,
            config: None,
            generate_config: None,
            history: None,
            export: None,
            export_format: None,
            no_alerts: false,
            verbose: false,
            duration: Some("30s".to_string()),
            mounts: None,
        };

        assert_eq!(args.parse_duration().unwrap(), Some(30));
    }

    #[test]
    fn test_parse_duration_minutes() {
        let args = Args {
            interval: None,
            mode: None,
            config: None,
            generate_config: None,
            history: None,
            export: None,
            export_format: None,
            no_alerts: false,
            verbose: false,
            duration: Some("5m".to_string()),
            mounts: None,
        };

        assert_eq!(args.parse_duration().unwrap(), Some(300));
    }
}
