//! Core data structures and types for log analysis.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Represents a single log entry with metadata.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct LogEntry {
    /// The timestamp of the log entry
    pub timestamp: DateTime<Utc>,

    /// The log level (severity)
    pub level: LogLevel,

    /// The raw log message
    pub message: String,

    /// The source file or stream this log came from
    pub source: String,

    /// Additional structured data (e.g., parsed fields)
    pub metadata: HashMap<String, String>,

    /// Line number in the source file (if applicable)
    pub line_number: Option<usize>,
}

impl LogEntry {
    /// Create a new log entry.
    pub fn new(
        timestamp: DateTime<Utc>,
        level: LogLevel,
        message: String,
        source: String,
    ) -> Self {
        Self {
            timestamp,
            level,
            message,
            source,
            metadata: HashMap::new(),
            line_number: None,
        }
    }

    /// Add metadata to the log entry.
    pub fn with_metadata(mut self, key: impl Into<String>, value: impl Into<String>) -> Self {
        self.metadata.insert(key.into(), value.into());
        self
    }

    /// Set the line number.
    pub fn with_line_number(mut self, line: usize) -> Self {
        self.line_number = Some(line);
        self
    }
}

/// Log level/severity enumeration.
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum LogLevel {
    Trace = 0,
    Debug = 1,
    Info = 2,
    Warn = 3,
    Error = 4,
    Fatal = 5,
}

impl LogLevel {
    /// Parse a log level from a string.
    pub fn from_str(s: &str) -> Option<Self> {
        match s.to_lowercase().as_str() {
            "trace" => Some(LogLevel::Trace),
            "debug" => Some(LogLevel::Debug),
            "info" => Some(LogLevel::Info),
            "warn" | "warning" => Some(LogLevel::Warn),
            "error" | "err" => Some(LogLevel::Error),
            "fatal" | "critical" => Some(LogLevel::Fatal),
            _ => None,
        }
    }

    /// Get the color code for terminal output.
    pub fn color_code(&self) -> &str {
        match self {
            LogLevel::Trace => "\x1b[90m",    // Grey
            LogLevel::Debug => "\x1b[36m",    // Cyan
            LogLevel::Info => "\x1b[32m",     // Green
            LogLevel::Warn => "\x1b[33m",     // Yellow
            LogLevel::Error => "\x1b[31m",    // Red
            LogLevel::Fatal => "\x1b[35m",    // Magenta
        }
    }

    /// Reset color code.
    pub fn reset_color() -> &'static str {
        "\x1b[0m"
    }
}

impl std::fmt::Display for LogLevel {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            LogLevel::Trace => write!(f, "TRACE"),
            LogLevel::Debug => write!(f, "DEBUG"),
            LogLevel::Info => write!(f, "INFO"),
            LogLevel::Warn => write!(f, "WARN"),
            LogLevel::Error => write!(f, "ERROR"),
            LogLevel::Fatal => write!(f, "FATAL"),
        }
    }
}

/// Statistics collected about log processing.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogStatistics {
    /// Total number of log entries processed
    pub total_entries: u64,

    /// Count of entries per log level
    pub level_counts: HashMap<LogLevel, u64>,

    /// Number of unique log messages seen
    pub unique_messages: u64,

    /// Current processing rate (entries per second)
    pub processing_rate: f64,

    /// Time since last entry
    pub time_since_last_entry: Option<chrono::Duration>,

    /// Most recent log entry timestamp
    pub last_entry_timestamp: Option<DateTime<Utc>>,
}

impl Default for LogStatistics {
    fn default() -> Self {
        Self {
            total_entries: 0,
            level_counts: HashMap::new(),
            unique_messages: 0,
            processing_rate: 0.0,
            time_since_last_entry: None,
            last_entry_timestamp: None,
        }
    }
}

impl LogStatistics {
    /// Update statistics with a new log entry.
    pub fn update(&mut self, entry: &LogEntry) {
        self.total_entries += 1;
        *self.level_counts.entry(entry.level).or_insert(0) += 1;
        self.last_entry_timestamp = Some(entry.timestamp);
    }

    /// Get the count for a specific log level.
    pub fn get_level_count(&self, level: LogLevel) -> u64 {
        self.level_counts.get(&level).copied().unwrap_or(0)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_log_level_parsing() {
        assert_eq!(LogLevel::from_str("info"), Some(LogLevel::Info));
        assert_eq!(LogLevel::from_str("ERROR"), Some(LogLevel::Error));
        assert_eq!(LogLevel::from_str("warning"), Some(LogLevel::Warn));
        assert_eq!(LogLevel::from_str("invalid"), None);
    }

    #[test]
    fn test_log_level_ordering() {
        assert!(LogLevel::Error > LogLevel::Info);
        assert!(LogLevel::Fatal >= LogLevel::Error);
    }

    #[test]
    fn test_statistics_update() {
        let mut stats = LogStatistics::default();
        let entry = LogEntry::new(
            Utc::now(),
            LogLevel::Info,
            "test message".to_string(),
            "test.log".to_string(),
        );

        stats.update(&entry);
        assert_eq!(stats.total_entries, 1);
        assert_eq!(stats.get_level_count(LogLevel::Info), 1);
    }
}
