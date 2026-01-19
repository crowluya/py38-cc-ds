//! Alert generation and delivery system.

use crate::core::LogEntry;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::time::Duration;

/// Severity levels for alerts.
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq, PartialOrd, Ord)]
pub enum AlertSeverity {
    Info = 0,
    Warning = 1,
    Critical = 2,
}

impl AlertSeverity {
    /// Get color code for terminal output.
    pub fn color_code(&self) -> &str {
        match self {
            AlertSeverity::Info => "\x1b[36m",     // Cyan
            AlertSeverity::Warning => "\x1b[33m",  // Yellow
            AlertSeverity::Critical => "\x1b[31m", // Red
        }
    }
}

impl std::fmt::Display for AlertSeverity {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            AlertSeverity::Info => write!(f, "INFO"),
            AlertSeverity::Warning => write!(f, "WARNING"),
            AlertSeverity::Critical => write!(f, "CRITICAL"),
        }
    }
}

/// An alert representing a detected anomaly.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Alert {
    /// Unique alert ID
    pub id: String,

    /// Severity level
    pub severity: AlertSeverity,

    /// Timestamp when the alert was generated
    pub timestamp: DateTime<Utc>,

    /// Type of anomaly
    pub anomaly_type: String,

    /// Human-readable description
    pub description: String,

    /// The log entry that triggered this alert
    pub log_entry: LogEntry,

    /// Confidence score (0.0 to 1.0)
    pub confidence: f64,

    /// Additional context data
    pub context: serde_json::Value,

    /// Source detector name
    pub detector: String,
}

impl Alert {
    /// Create a new alert.
    pub fn new(
        severity: AlertSeverity,
        anomaly_type: String,
        description: String,
        log_entry: LogEntry,
        confidence: f64,
        detector: String,
    ) -> Self {
        Self {
            id: uuid::Uuid::new_v4().to_string(),
            severity,
            timestamp: Utc::now(),
            anomaly_type,
            description,
            log_entry,
            confidence,
            context: serde_json::json!({}),
            detector,
        }
    }

    /// Add context to the alert.
    pub fn with_context(mut self, key: impl Into<String>, value: serde_json::Value) -> Self {
        if let Some(obj) = self.context.as_object_mut() {
            obj.insert(key.into(), value);
        }
        self
    }

    /// Get a formatted summary of the alert.
    pub fn summary(&self) -> String {
        format!(
            "[{}] {} - {} (confidence: {:.2})",
            self.severity, self.anomaly_type, self.description, self.confidence
        )
    }
}

/// Trait for alert delivery mechanisms.
pub trait Alerter: Send + Sync {
    /// Send an alert.
    async fn send(&self, alert: &Alert) -> Result<(), Box<dyn std::error::Error + Send + Sync>>;

    /// Get the alerter name.
    fn name(&self) -> &str;
}

/// Console alerter that prints to stdout/stderr with colors.
#[derive(Debug, Clone)]
pub struct ConsoleAlerter {
    /// Use colored output
    colored: bool,

    /// Include full log entry in output
    verbose: bool,

    /// Minimum severity to output
    min_severity: AlertSeverity,
}

impl ConsoleAlerter {
    /// Create a new console alerter.
    pub fn new(colored: bool, verbose: bool, min_severity: AlertSeverity) -> Self {
        Self {
            colored,
            verbose,
            min_severity,
        }
    }
}

#[async_trait::async_trait]
impl Alerter for ConsoleAlerter {
    async fn send(&self, alert: &Alert) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        // Check severity threshold
        if alert.severity < self.min_severity {
            return Ok(());
        }

        let color = if self.colored {
            alert.severity.color_code()
        } else {
            ""
        };
        let reset = if self.colored { "\x1b[0m" } else { "" };

        eprintln!(
            "{}[ALERT {}]{} {} - {}",
            color, alert.severity, reset, alert.timestamp.format("%Y-%m-%d %H:%M:%S"), alert.description
        );

        if self.verbose {
            eprintln!("  Confidence: {:.2}", alert.confidence);
            eprintln!("  Detector: {}", alert.detector);
            eprintln!("  Source: {}", alert.log_entry.source);
            eprintln!("  Level: {}", alert.log_entry.level);
            eprintln!("  Message: {}", alert.log_entry.message);
            if !alert.log_entry.metadata.is_empty() {
                eprintln!("  Metadata: {:?}", alert.log_entry.metadata);
            }
        }

        Ok(())
    }

    fn name(&self) -> &str {
        "Console Alerter"
    }
}

/// Webhook alerter for sending HTTP notifications.
#[derive(Debug, Clone)]
pub struct WebhookAlerter {
    /// Webhook URL
    url: String,

    /// HTTP client
    client: reqwest::Client,

    /// Request timeout
    timeout: Duration,
}

impl WebhookAlerter {
    /// Create a new webhook alerter.
    pub fn new(url: String, timeout: Duration) -> Result<Self, Box<dyn std::error::Error>> {
        Ok(Self {
            url,
            client: reqwest::Client::builder()
                .timeout(timeout)
                .build()?,
            timeout,
        })
    }
}

#[async_trait::async_trait]
impl Alerter for WebhookAlerter {
    async fn send(&self, alert: &Alert) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        let response = self.client
            .post(&self.url)
            .header("Content-Type", "application/json")
            .json(alert)
            .send()
            .await?;

        if response.status().is_success() {
            Ok(())
        } else {
            let status = response.status();
            let body = response.text().await.unwrap_or_default();
            Err(format!("Webhook failed: {} - {}", status, body).into())
        }
    }

    fn name(&self) -> &str {
        "Webhook Alerter"
    }
}

/// File alerter that writes alerts to a log file.
#[derive(Debug, Clone)]
pub struct FileAlerter {
    /// File path
    path: std::path::PathBuf,

    /// Use JSON format
    json_format: bool,
}

impl FileAlerter {
    /// Create a new file alerter.
    pub fn new(path: std::path::PathBuf, json_format: bool) -> Self {
        Self { path, json_format }
    }

    /// Write the alert to the file.
    fn write_to_file(&self, alert: &Alert) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        use std::fs::OpenOptions;
        use std::io::Write;

        let mut file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&self.path)?;

        if self.json_format {
            writeln!(file, "{}", serde_json::to_string(alert)?)?;
        } else {
            writeln!(file, "[{}] {} - {}", alert.timestamp, alert.severity, alert.description)?;
        }

        Ok(())
    }
}

#[async_trait::async_trait]
impl Alerter for FileAlerter {
    async fn send(&self, alert: &Alert) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        // Note: In a real implementation, you'd want to use async file I/O
        self.write_to_file(alert)
    }

    fn name(&self) -> &str {
        "File Alerter"
    }
}

/// Composite alerter that sends to multiple destinations.
#[derive(Debug)]
pub struct MultiAlerter {
    /// List of alerters
    alerters: Vec<Box<dyn Alerter>>,
}

impl MultiAlerter {
    /// Create a new multi-alerter.
    pub fn new() -> Self {
        Self {
            alerters: Vec::new(),
        }
    }

    /// Add an alerter.
    pub fn add(&mut self, alerter: Box<dyn Alerter>) {
        self.alerters.push(alerter);
    }
}

impl Default for MultiAlerter {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait::async_trait]
impl Alerter for MultiAlerter {
    async fn send(&self, alert: &Alert) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        let mut errors = Vec::new();

        for alerter in &self.alerters {
            if let Err(e) = alerter.send(alert).await {
                errors.push(format!("{}: {}", alerter.name(), e));
            }
        }

        if errors.is_empty() {
            Ok(())
        } else {
            Err(format!("Multiple alerter errors: {}", errors.join(", ")).into())
        }
    }

    fn name(&self) -> &str {
        "Multi Alerter"
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::core::LogLevel;

    #[test]
    fn test_alert_creation() {
        let entry = LogEntry::new(
            Utc::now(),
            LogLevel::Error,
            "test error".to_string(),
            "test.log".to_string(),
        );

        let alert = Alert::new(
            AlertSeverity::Critical,
            "Test Anomaly".to_string(),
            "Test description".to_string(),
            entry,
            0.9,
            "TestDetector".to_string(),
        );

        assert_eq!(alert.severity, AlertSeverity::Critical);
        assert_eq!(alert.confidence, 0.9);
    }

    #[test]
    fn test_alert_with_context() {
        let entry = LogEntry::new(
            Utc::now(),
            LogLevel::Error,
            "test".to_string(),
            "test.log".to_string(),
        );

        let alert = Alert::new(
            AlertSeverity::Warning,
            "Test".to_string(),
            "Test".to_string(),
            entry,
            0.5,
            "Test".to_string(),
        )
        .with_context("key", serde_json::json!("value"));

        assert!(alert.context.as_object().unwrap().contains_key("key"));
    }
}
