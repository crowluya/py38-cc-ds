//! # Log Analyzer
//!
//! A real-time log analysis CLI tool that monitors application logs,
//! detects anomalies using statistical analysis and pattern matching,
//! and sends alerts when unusual patterns are discovered.

pub mod alerts;
pub mod config;
pub mod core;
pub mod detectors;
pub mod input;
pub mod parsers;
pub mod statistics;

// Re-export core types for convenience
pub use core::{LogEntry, LogLevel};
pub use alerts::{Alert, AlertSeverity};
pub use detectors::{AnomalyDetector, DetectionResult};
pub use input::LogSource;
