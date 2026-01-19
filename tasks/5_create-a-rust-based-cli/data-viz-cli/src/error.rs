use thiserror::Error;

#[derive(Error, Debug)]
pub enum DataVizError {
    #[error("Failed to read file: {0}")]
    FileReadError(String),

    #[error("Failed to write file: {0}")]
    FileWriteError(String),

    #[error("Invalid data format: {0}")]
    InvalidDataFormat(String),

    #[error("Unsupported chart type: {0}")]
    UnsupportedChartType(String),

    #[error("Missing required field: {0}")]
    MissingField(String),

    #[error("Parse error: {0}")]
    ParseError(String),

    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),

    #[error("CSV error: {0}")]
    CsvError(#[from] csv::Error),

    #[error("JSON error: {0}")]
    JsonError(#[from] serde_json::Error),
}

pub type Result<T> = std::result::Result<T, DataVizError>;
