use std::io;
use thiserror::Error;

/// Main error type for the markdown analysis tool
#[derive(Error, Debug)]
pub enum AnalysisError {
    #[error("Failed to read file: {0}")]
    FileReadError(#[from] io::Error),

    #[error("Failed to parse markdown: {0}")]
    MarkdownParseError(String),

    #[error("Invalid output format: {0}")]
    InvalidOutputFormat(String),

    #[error("Analysis failed: {0}")]
    AnalysisError(String),

    #[error("Failed to write output: {0}")]
    WriteError(#[from] csv::Error),

    #[error("JSON serialization error: {0}")]
    JsonError(#[from] serde_json::Error),
}

/// Result type alias for AnalysisError
pub type Result<T> = std::result::Result<T, AnalysisError>;
