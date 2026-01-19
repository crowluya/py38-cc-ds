//! Anomaly detection algorithms and traits.

use crate::core::LogEntry;
use crate::statistics::StreamingStats;
use std::fmt;

/// Result of an anomaly detection check.
#[derive(Debug, Clone)]
pub struct DetectionResult {
    /// Whether an anomaly was detected
    pub is_anomaly: bool,

    /// Confidence score (0.0 to 1.0)
    pub confidence: f64,

    /// Human-readable description of the anomaly
    pub description: String,

    /// The type of anomaly detected
    pub anomaly_type: AnomalyType,
}

/// Types of anomalies that can be detected.
#[derive(Debug, Clone, PartialEq)]
pub enum AnomalyType {
    /// Unusually high log rate
    RateSpike,

    /// New pattern never seen before
    NewPattern,

    /// High error rate
    ErrorRateSpike,

    /// Statistical outlier in log patterns
    StatisticalOutlier,

    /// Specific matched pattern (e.g., stack trace)
    PatternMatch,

    /// Distribution shift in log levels
    DistributionShift,
}

impl fmt::Display for AnomalyType {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            AnomalyType::RateSpike => write!(f, "Rate Spike"),
            AnomalyType::NewPattern => write!(f, "New Pattern"),
            AnomalyType::ErrorRateSpike => write!(f, "Error Rate Spike"),
            AnomalyType::StatisticalOutlier => write!(f, "Statistical Outlier"),
            AnomalyType::PatternMatch => write!(f, "Pattern Match"),
            AnomalyType::DistributionShift => write!(f, "Distribution Shift"),
        }
    }
}

/// Trait for anomaly detection algorithms.
pub trait AnomalyDetector: Send + Sync {
    /// Process a log entry and determine if it's anomalous.
    fn detect(&mut self, entry: &LogEntry) -> DetectionResult;

    /// Reset the detector's internal state.
    fn reset(&mut self);

    /// Get the detector's name.
    fn name(&self) -> &str;
}

/// Detector that monitors log entry rates for spikes.
pub struct RateSpikeDetector {
    /// Statistical tracking of rates
    stats: StreamingStats,

    /// Window size in seconds
    window_size_secs: u64,

    /// Number of standard deviations for threshold
    std_dev_threshold: f64,

    /// Minimum rate to consider (entries per second)
    min_rate: f64,

    /// Track entries in current window
    window_entries: Vec<chrono::DateTime<chrono::Utc>>,
}

impl RateSpikeDetector {
    /// Create a new rate spike detector.
    pub fn new(window_size_secs: u64, std_dev_threshold: f64, min_rate: f64) -> Self {
        Self {
            stats: StreamingStats::new(),
            window_size_secs,
            std_dev_threshold,
            min_rate,
            window_entries: Vec::new(),
        }
    }

    /// Calculate current rate (entries per second).
    fn calculate_rate(&mut self, now: chrono::DateTime<chrono::Utc>) -> f64 {
        // Remove entries outside the window
        let window_start = now - chrono::Duration::seconds(self.window_size_secs as i64);
        self.window_entries.retain(|&ts| ts > window_start);

        if self.window_entries.is_empty() {
            return 0.0;
        }

        // Calculate rate
        let duration_sec = if let Some(&first) = self.window_entries.first() {
            (now - first).num_seconds().max(1) as f64
        } else {
            1.0
        };

        self.window_entries.len() as f64 / duration_sec
    }
}

impl AnomalyDetector for RateSpikeDetector {
    fn detect(&mut self, entry: &LogEntry) -> DetectionResult {
        self.window_entries.push(entry.timestamp);
        let current_rate = self.calculate_rate(entry.timestamp);

        // Update statistics
        self.stats.update(current_rate);

        // Check if we have enough data
        if self.stats.count() < 10 {
            return DetectionResult {
                is_anomaly: false,
                confidence: 0.0,
                description: "Insufficient data for rate detection".to_string(),
                anomaly_type: AnomalyType::RateSpike,
            };
        }

        // Check if rate exceeds threshold
        let mean = self.stats.mean();
        let std_dev = self.stats.std_dev();

        if current_rate < self.min_rate {
            return DetectionResult {
                is_anomaly: false,
                confidence: 0.0,
                description: format!("Rate {:.2} below minimum threshold", current_rate),
                anomaly_type: AnomalyType::RateSpike,
            };
        }

        let z_score = if std_dev > 0.0 {
            (current_rate - mean) / std_dev
        } else {
            0.0
        };

        let is_anomaly = z_score > self.std_dev_threshold;
        let confidence = (z_score / self.std_dev_threshold).min(1.0).max(0.0);

        DetectionResult {
            is_anomaly,
            confidence,
            description: format!(
                "Rate: {:.2} entries/sec (μ={:.2}, σ={:.2}, z-score={:.2})",
                current_rate, mean, std_dev, z_score
            ),
            anomaly_type: AnomalyType::RateSpike,
        }
    }

    fn reset(&mut self) {
        self.stats = StreamingStats::new();
        self.window_entries.clear();
    }

    fn name(&self) -> &str {
        "Rate Spike Detector"
    }
}

/// Detector that identifies new, never-before-seen log patterns.
pub struct NewPatternDetector {
    /// Hash set of seen message patterns
    seen_patterns: std::collections::HashSet<u64>,

    /// Total entries processed
    total_entries: u64,

    /// Number of unique patterns seen
    unique_patterns: u64,
}

impl NewPatternDetector {
    /// Create a new pattern detector.
    pub fn new() -> Self {
        Self {
            seen_patterns: std::collections::HashSet::new(),
            total_entries: 0,
            unique_patterns: 0,
        }
    }

    /// Generate a simple hash of the log message.
    fn hash_message(message: &str) -> u64 {
        use std::hash::{Hash, Hasher};
        let mut hasher = std::collections::hash_map::DefaultHasher::new();
        message.hash(&mut hasher);
        hasher.finish()
    }
}

impl Default for NewPatternDetector {
    fn default() -> Self {
        Self::new()
    }
}

impl AnomalyDetector for NewPatternDetector {
    fn detect(&mut self, entry: &LogEntry) -> DetectionResult {
        self.total_entries += 1;
        let pattern_hash = Self::hash_message(&entry.message);
        let is_new = self.seen_patterns.insert(pattern_hash);

        if is_new {
            self.unique_patterns += 1;
        }

        let is_anomaly = is_new && self.total_entries > 100; // Only after learning period

        DetectionResult {
            is_anomaly,
            confidence: if is_anomaly { 0.8 } else { 0.0 },
            description: if is_anomaly {
                format!(
                    "New pattern detected ({} unique patterns seen out of {} total entries)",
                    self.unique_patterns, self.total_entries
                )
            } else {
                "Previously seen pattern".to_string()
            },
            anomaly_type: AnomalyType::NewPattern,
        }
    }

    fn reset(&mut self) {
        self.seen_patterns.clear();
        self.total_entries = 0;
        self.unique_patterns = 0;
    }

    fn name(&self) -> &str {
        "New Pattern Detector"
    }
}

/// Detector that monitors error rate spikes.
pub struct ErrorRateDetector {
    /// Window size in seconds
    window_size_secs: u64,

    /// Error threshold (percentage)
    error_threshold: f64,

    /// Track errors in current window
    error_window: Vec<chrono::DateTime<chrono::Utc>>,

    /// Track all entries in current window
    total_window: Vec<chrono::DateTime<chrono::Utc>>,
}

impl ErrorRateDetector {
    /// Create a new error rate detector.
    pub fn new(window_size_secs: u64, error_threshold: f64) -> Self {
        Self {
            window_size_secs,
            error_threshold,
            error_window: Vec::new(),
            total_window: Vec::new(),
        }
    }

    /// Check if the log level is an error.
    fn is_error(&self, level: &crate::core::LogLevel) -> bool {
        matches!(level, crate::core::LogLevel::Error | crate::core::LogLevel::Fatal)
    }
}

impl AnomalyDetector for ErrorRateDetector {
    fn detect(&mut self, entry: &LogEntry) -> DetectionResult {
        let window_start = entry.timestamp - chrono::Duration::seconds(self.window_size_secs as i64);

        // Clean old entries
        self.error_window.retain(|&ts| ts > window_start);
        self.total_window.retain(|&ts| ts > window_start);

        // Add current entry
        if self.is_error(&entry.level) {
            self.error_window.push(entry.timestamp);
        }
        self.total_window.push(entry.timestamp);

        // Calculate error rate
        let total_count = self.total_window.len();
        let error_count = self.error_window.len();

        if total_count < 10 {
            return DetectionResult {
                is_anomaly: false,
                confidence: 0.0,
                description: "Insufficient data for error rate detection".to_string(),
                anomaly_type: AnomalyType::ErrorRateSpike,
            };
        }

        let error_rate = (error_count as f64 / total_count as f64) * 100.0;
        let is_anomaly = error_rate > self.error_threshold;
        let confidence = (error_rate / self.error_threshold).min(1.0).max(0.0);

        DetectionResult {
            is_anomaly,
            confidence,
            description: format!(
                "Error rate: {:.1}% ({}/{} entries)",
                error_rate, error_count, total_count
            ),
            anomaly_type: AnomalyType::ErrorRateSpike,
        }
    }

    fn reset(&mut self) {
        self.error_window.clear();
        self.total_window.clear();
    }

    fn name(&self) -> &str {
        "Error Rate Detector"
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::core::LogLevel;

    #[test]
    fn test_rate_spike_detector() {
        let mut detector = RateSpikeDetector::new(60, 2.0, 1.0);

        // Add baseline entries
        let mut timestamp = Utc::now();
        for _ in 0..20 {
            timestamp = timestamp + chrono::Duration::milliseconds(100);
            let entry = LogEntry::new(timestamp, LogLevel::Info, "normal".to_string(), "test".to_string());
            detector.detect(&entry);
        }

        // Add a spike
        for _ in 0..50 {
            timestamp = timestamp + chrono::Duration::milliseconds(10);
            let entry = LogEntry::new(timestamp, LogLevel::Info, "spike".to_string(), "test".to_string());
            let result = detector.detect(&entry);
            if result.is_anomaly {
                assert!(result.confidence > 0.0);
                return;
            }
        }

        panic!("Expected to detect rate spike");
    }

    #[test]
    fn test_new_pattern_detector() {
        let mut detector = NewPatternDetector::new();

        // Learning phase
        for i in 0..101 {
            let entry = LogEntry::new(
                Utc::now(),
                LogLevel::Info,
                format!("message {}", i % 10),
                "test".to_string(),
            );
            detector.detect(&entry);
        }

        // New pattern should be detected
        let entry = LogEntry::new(
            Utc::now(),
            LogLevel::Info,
            "completely new message".to_string(),
            "test".to_string(),
        );
        let result = detector.detect(&entry);
        assert!(result.is_anomaly);
    }

    #[test]
    fn test_error_rate_detector() {
        let mut detector = ErrorRateDetector::new(60, 50.0);

        // Add mixed entries
        let mut timestamp = Utc::now();
        for i in 0..20 {
            timestamp = timestamp + chrono::Duration::milliseconds(100);
            let level = if i % 2 == 0 { LogLevel::Error } else { LogLevel::Info };
            let entry = LogEntry::new(timestamp, level, "test".to_string(), "test".to_string());
            detector.detect(&entry);
        }

        // 50% error rate should trigger with threshold of 50%
        let entry = LogEntry::new(timestamp, LogLevel::Error, "error".to_string(), "test".to_string());
        let result = detector.detect(&entry);
        assert!(result.is_anomaly);
    }
}
