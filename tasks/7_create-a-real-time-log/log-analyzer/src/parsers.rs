//! Log parsing utilities.

use crate::core::{LogEntry, LogLevel};
use chrono::{DateTime, Utc};
use regex::Regex;
use serde::{Deserialize, Serialize};

/// Trait for parsing log lines into structured entries.
pub trait LogParser: Send + Sync {
    /// Parse a log line into a LogEntry, or return None if parsing fails.
    fn parse(&self, line: &str, source: String) -> Option<LogEntry>;

    /// Clone the parser in a box.
    fn clone_box(&self) -> Box<dyn LogParser>;
}

impl Clone for Box<dyn LogParser> {
    fn clone(&self) -> Self {
        self.clone_box()
    }
}

/// Generic log parser that handles common log formats.
#[derive(Debug, Clone)]
pub struct GenericLogParser {
    /// Regex pattern for parsing log lines
    timestamp_pattern: Regex,

    /// Regex pattern for log level
    level_pattern: Regex,
}

impl GenericLogParser {
    /// Create a new generic log parser.
    pub fn new() -> Self {
        // Common timestamp patterns
        let timestamp_pattern = Regex::new(
            r"(?x)
            ^(?P<timestamp>
                \d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?|
                \d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2}|
                \w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}
            )
            "
        ).unwrap();

        // Log level patterns
        let level_pattern = Regex::new(
            r"(?i)\b(DEBUG|INFO|WARN|WARNING|ERROR|ERR|FATAL|CRITICAL|TRACE)\b"
        ).unwrap();

        Self {
            timestamp_pattern,
            level_pattern,
        }
    }

    /// Parse a timestamp from a string.
    fn parse_timestamp(&self, s: &str) -> Option<DateTime<Utc>> {
        // Try various formats
        let formats = [
            "%Y-%m-%d %H:%M:%S%.f",
            "%Y-%m-%dT%H:%M:%S%.f",
            "%Y-%m-%dT%H:%M:%S%.fZ",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%m/%d/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
        ];

        for format in &formats {
            if let Ok(dt) = DateTime::parse_from_str(s, format) {
                return Some(dt.with_timezone(&Utc));
            }
            if let Ok(dt) = DateTime::parse_from_str(&format!("{}Z", s), format) {
                return Some(dt.with_timezone(&Utc));
            }
        }

        // Default to current time if parsing fails
        Some(Utc::now())
    }

    /// Extract log level from a string.
    fn extract_level(&self, line: &str) -> Option<LogLevel> {
        self.level_pattern
            .find(line)
            .and_then(|m| LogLevel::from_str(m.as_str()))
    }
}

impl Default for GenericLogParser {
    fn default() -> Self {
        Self::new()
    }
}

impl LogParser for GenericLogParser {
    fn parse(&self, line: &str, source: String) -> Option<LogEntry> {
        if line.trim().is_empty() {
            return None;
        }

        // Try to extract timestamp
        let timestamp = self
            .timestamp_pattern
            .find(line)
            .and_then(|m| self.parse_timestamp(m.as_str()))
            .unwrap_or_else(Utc::now);

        // Try to extract log level
        let level = self.extract_level(line).unwrap_or(LogLevel::Info);

        // Remove timestamp from the message for cleaner output
        let message = self
            .timestamp_pattern
            .replace(line, "")
            .trim()
            .to_string();

        let mut entry = LogEntry::new(timestamp, level, message, source);

        // Add line number if available (would be passed in from caller)
        // entry = entry.with_line_number(line_num);

        Some(entry)
    }

    fn clone_box(&self) -> Box<dyn LogParser> {
        Box::new(self.clone())
    }
}

/// JSON log parser for structured logging.
#[derive(Debug, Clone)]
pub struct JsonLogParser;

impl JsonLogParser {
    /// Create a new JSON log parser.
    pub fn new() -> Self {
        Self
    }
}

impl Default for JsonLogParser {
    fn default() -> Self {
        Self::new()
    }
}

impl LogParser for JsonLogParser {
    fn parse(&self, line: &str, source: String) -> Option<LogEntry> {
        let json: serde_json::Value = serde_json::from_str(line).ok()?;

        // Extract timestamp
        let timestamp = json
            .get("timestamp")
            .or_else(|| json.get("time"))
            .or_else(|| json.get("@timestamp"))
            .and_then(|v| v.as_str())
            .and_then(|s| DateTime::parse_from_rfc3339(s).ok())
            .map(|dt| dt.with_timezone(&Utc))
            .unwrap_or_else(Utc::now());

        // Extract log level
        let level = json
            .get("level")
            .or_else(|| json.get("severity"))
            .and_then(|v| v.as_str())
            .and_then(|s| LogLevel::from_str(s))
            .unwrap_or(LogLevel::Info);

        // Extract message
        let message = json
            .get("message")
            .or_else(|| json.get("msg"))
            .or_else(|| json.get("text"))
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();

        let mut entry = LogEntry::new(timestamp, level, message, source);

        // Add all JSON fields as metadata
        if let Some(obj) = json.as_object() {
            for (key, value) in obj {
                if key != "timestamp" && key != "time" && key != "level" && key != "message" && key != "msg" {
                    if let Some(s) = value.as_str() {
                        entry = entry.with_metadata(key, s);
                    } else {
                        entry = entry.with_metadata(key, value.to_string());
                    }
                }
            }
        }

        Some(entry)
    }

    fn clone_box(&self) -> Box<dyn LogParser> {
        Box::new(self.clone())
    }
}

/// Pattern-based log parser using custom regex.
#[derive(Debug, Clone)]
pub struct PatternLogParser {
    /// Compiled regex pattern
    pattern: Regex,

    /// Field names for capture groups
    field_names: Vec<String>,
}

impl PatternLogParser {
    /// Create a new pattern log parser.
    ///
    /// # Arguments
    /// * `pattern` - Regex pattern with named capture groups
    ///
    /// Supported capture groups:
    /// - `timestamp`: Log timestamp
    /// - `level`: Log level
    /// - `message`: Log message
    pub fn new(pattern: &str) -> Result<Self, regex::Error> {
        let regex = Regex::new(pattern)?;

        // Extract field names from the pattern
        let field_names = regex
            .capture_names()
            .filter_map(|n| n.map(String::from))
            .collect();

        Ok(Self {
            pattern: regex,
            field_names,
        })
    }
}

impl LogParser for PatternLogParser {
    fn parse(&self, line: &str, source: String) -> Option<LogEntry> {
        let captures = self.pattern.captures(line)?;

        // Extract timestamp
        let timestamp = captures
            .name("timestamp")
            .and_then(|m| DateTime::parse_from_rfc3339(m.as_str()).ok())
            .map(|dt| dt.with_timezone(&Utc))
            .unwrap_or_else(Utc::now());

        // Extract level
        let level = captures
            .name("level")
            .and_then(|m| LogLevel::from_str(m.as_str()))
            .unwrap_or(LogLevel::Info);

        // Extract message
        let message = captures
            .name("message")
            .map(|m| m.as_str().to_string())
            .unwrap_or_else(|| line.to_string());

        let mut entry = LogEntry::new(timestamp, level, message, source);

        // Add other capture groups as metadata
        for name in &self.field_names {
            if name != "timestamp" && name != "level" && name != "message" {
                if let Some(cap) = captures.name(name) {
                    entry = entry.with_metadata(name, cap.as_str());
                }
            }
        }

        Some(entry)
    }

    fn clone_box(&self) -> Box<dyn LogParser> {
        Box::new(self.clone())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_generic_parser() {
        let parser = GenericLogParser::new();
        let line = "2024-01-15 10:30:45 INFO User logged in successfully";

        let entry = parser.parse(line, "test.log".to_string()).unwrap();

        assert_eq!(entry.level, LogLevel::Info);
        assert!(entry.message.contains("User logged in"));
    }

    #[test]
    fn test_json_parser() {
        let parser = JsonLogParser::new();
        let line = r#"{"timestamp":"2024-01-15T10:30:45Z","level":"ERROR","message":"Database connection failed","service":"api"}"#;

        let entry = parser.parse(line, "test.log".to_string()).unwrap();

        assert_eq!(entry.level, LogLevel::Error);
        assert_eq!(entry.message, "Database connection failed");
        assert_eq!(entry.metadata.get("service"), Some(&"api".to_string()));
    }

    #[test]
    fn test_pattern_parser() {
        let pattern = r#"(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[(?P<level>\w+)\] (?P<message>.+)"#;
        let parser = PatternLogParser::new(pattern).unwrap();
        let line = "2024-01-15 10:30:45 [ERROR] Database connection failed";

        let entry = parser.parse(line, "test.log".to_string()).unwrap();

        assert_eq!(entry.level, LogLevel::Error);
        assert_eq!(entry.message, "Database connection failed");
    }
}
