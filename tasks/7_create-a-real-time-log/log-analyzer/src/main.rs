//! Log Analyzer - Real-time log analysis CLI tool

use anyhow::{Context, Result};
use clap::Parser;
use log_analyzer::{
    alerts::{Alert, AlertSeverity, Alerter, ConsoleAlerter, FileAlerter, MultiAlerter},
    config::{load_config, merge_config, CliArgs},
    core::{LogEntry, LogLevel},
    detectors::{AnomalyDetector, DetectionResult},
    input::LogSource,
    parsers::{GenericLogParser, JsonLogParser, LogParser, PatternLogParser},
};
use std::path::PathBuf;
use std::sync::Arc;
use tokio::sync::mpsc;
use tracing::{error, info, warn};

/// Log Analyzer - Real-time log analysis with anomaly detection
#[derive(Parser, Debug)]
#[command(name = "log-analyzer")]
#[command(author = "Log Analyzer Team")]
#[command(version = "0.1.0")]
#[command(about = "Monitor application logs and detect anomalies in real-time", long_about = None)]
struct Args {
    /// Log files to monitor
    #[arg(short, long, value_name = "FILE")]
    file: Vec<String>,

    /// Read from stdin
    #[arg(short, long)]
    stdin: bool,

    /// Configuration file path
    #[arg(short, long, value_name = "CONFIG")]
    config: Option<PathBuf>,

    /// Log parser type (generic, json, pattern)
    #[arg(long, value_name = "TYPE")]
    parser: Option<String>,

    /// Custom regex pattern for pattern parser
    #[arg(long, value_name = "PATTERN")]
    pattern: Option<String>,

    /// Verbose output
    #[arg(short, long)]
    verbose: bool,

    /// Minimum alert severity (info, warning, critical)
    #[arg(long, value_name = "SEVERITY")]
    min_severity: Option<String>,

    /// Webhook URL for alerts
    #[arg(long, value_name = "URL")]
    webhook_url: Option<String>,

    /// Alert output file
    #[arg(long, value_name = "FILE")]
    alert_file: Option<PathBuf>,

    /// Disable colored output
    #[arg(long)]
    no_color: bool,
}

#[tokio::main]
async fn main() -> Result<()> {
    let args = Args::parse();

    // Initialize tracing
    let env_filter = tracing_subscriber::EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new("info"));

    tracing_subscriber::fmt()
        .with_env_filter(env_filter)
        .with_target(false)
        .init();

    // Load or create default configuration
    let config = if let Some(config_path) = &args.config {
        load_config(config_path).with_context(|| {
            format!("Failed to load configuration from: {:?}", config_path)
        })?
    } else {
        log_analyzer::config::Config::default()
    };

    // Merge CLI arguments with config
    let cli_args = CliArgs {
        files: args.file.clone(),
        stdin: args.stdin,
        verbose: args.verbose,
        min_severity: args.min_severity.clone(),
        webhook_url: args.webhook_url.clone(),
        config: args.config.clone(),
    };

    let config = merge_config(config, &cli_args);

    // Validate configuration
    if config.sources.files.is_empty() && !config.sources.stdin {
        warn!("No log sources specified. Use --file or --stdin");
        return Ok(());
    }

    // Create the appropriate parser
    let parser_type = args.parser.as_ref().unwrap_or(&config.sources.parser.parser_type);
    let parser: Box<dyn LogParser> = match parser_type.as_str() {
        "json" => Box::new(JsonLogParser::new()),
        "pattern" => {
            let pattern = args.pattern
                .as_ref()
                .or(config.sources.parser.pattern.as_ref())
                .context("Pattern parser requires a --pattern argument")?;
            Box::new(PatternLogParser::new(pattern)?)
        }
        _ => Box::new(GenericLogParser::new()),
    };

    // Setup alerters
    let mut multi_alerter = MultiAlerter::new();

    // Console alerter
    let colored = !args.no_color && config.alerts.console.colored;
    let min_severity = parse_severity(
        args.min_severity.as_ref().unwrap_or(&config.alerts.console.min_severity),
    );

    if config.alerts.console.enabled {
        multi_alerter.add(Box::new(ConsoleAlerter::new(
            colored,
            config.alerts.console.verbose,
            min_severity,
        )));
    }

    // File alerter
    if let Some(alert_file) = args.alert_file.as_ref().or(config.alerts.file.path.as_ref()) {
        multi_alerter.add(Box::new(FileAlerter::new(
            alert_file.clone(),
            config.alerts.file.json_format,
        )));
    }

    // Webhook alerter (would require reqwest feature)
    #[cfg(feature = "webhooks")]
    {
        if config.alerts.webhook.enabled {
            if let Some(url) = config.alerts.webhook.url.as_ref() {
                match log_analyzer::alerts::WebhookAlerter::new(
                    url.clone(),
                    std::time::Duration::from_secs(config.alerts.webhook.timeout_secs),
                ) {
                    Ok(alerter) => multi_alerter.add(Box::new(alerter)),
                    Err(e) => error!("Failed to create webhook alerter: {}", e),
                }
            }
        }
    }

    // Create channel for log entries
    let (tx, mut rx) = mpsc::unbounded_channel::<LogEntry>();

    // Start log sources
    info!("Starting log analyzer...");

    for file_path in &config.sources.files {
        info!("Monitoring file: {}", file_path);
        // In a full implementation, you would create and start FileLogSource here
    }

    if config.sources.stdin {
        info!("Reading from stdin...");
        // In a full implementation, you would create and start StdinLogSource here
    }

    // Process log entries
    let mut detectors: Vec<Box<dyn AnomalyDetector>> = vec![];

    // Add enabled detectors
    for detector_name in &config.detectors.enabled {
        match detector_name.as_str() {
            "rate_spike" => {
                detectors.push(Box::new(log_analyzer::detectors::RateSpikeDetector::new(
                    config.detectors.rate_spike.window_size_secs,
                    config.detectors.rate_spike.std_dev_threshold,
                    config.detectors.rate_spike.min_rate,
                )));
                info!("Enabled rate spike detector");
            }
            "error_rate" => {
                detectors.push(Box::new(log_analyzer::detectors::ErrorRateDetector::new(
                    config.detectors.error_rate.window_size_secs,
                    config.detectors.error_rate.threshold_percent,
                )));
                info!("Enabled error rate detector");
            }
            "new_pattern" => {
                detectors.push(Box::new(log_analyzer::detectors::NewPatternDetector::new()));
                info!("Enabled new pattern detector");
            }
            _ => {
                warn!("Unknown detector: {}", detector_name);
            }
        }
    }

    // Main processing loop
    let mut entry_count = 0u64;
    let mut alert_count = 0u64;

    while let Some(entry) = rx.recv().await {
        entry_count += 1;

        // Run all detectors
        for detector in &mut detectors {
            let result = detector.detect(&entry);

            if result.is_anomaly {
                alert_count += 1;

                let severity = match result.anomaly_type {
                    log_analyzer::detectors::AnomalyType::ErrorRateSpike => AlertSeverity::Critical,
                    log_analyzer::detectors::AnomalyType::RateSpike => AlertSeverity::Warning,
                    _ => AlertSeverity::Info,
                };

                let alert = Alert::new(
                    severity,
                    result.anomaly_type.to_string(),
                    result.description,
                    entry.clone(),
                    result.confidence,
                    detector.name().to_string(),
                );

                if let Err(e) = multi_alerter.send(&alert).await {
                    error!("Failed to send alert: {}", e);
                }
            }
        }

        // Print progress every 1000 entries
        if entry_count % 1000 == 0 {
            info!("Processed {} entries, generated {} alerts", entry_count, alert_count);
        }
    }

    info!(
        "Log analyzer stopped. Processed {} entries, generated {} alerts",
        entry_count, alert_count
    );

    Ok(())
}

/// Parse a severity string into AlertSeverity.
fn parse_severity(s: &str) -> AlertSeverity {
    match s.to_lowercase().as_str() {
        "critical" => AlertSeverity::Critical,
        "warning" | "warn" => AlertSeverity::Warning,
        _ => AlertSeverity::Info,
    }
}
