use thiserror::Error;

#[derive(Error, Debug)]
pub enum ProjectInitError {
    #[error("Template not found: {0}")]
    TemplateNotFound(String),

    #[error("Invalid template configuration: {0}")]
    InvalidTemplate(String),

    #[error("File system error: {0}")]
    FileSystemError(String),

    #[error("Git error: {0}")]
    GitError(String),

    #[error("Template engine error: {0}")]
    TemplateEngineError(String),

    #[error("Configuration error: {0}")]
    ConfigError(String),

    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),

    #[error("Serialization error: {0}")]
    SerializationError(#[from] serde_json::Error),

    #[error("YAML error: {0}")]
    YamlError(#[from] serde_yaml::Error),
}

pub type Result<T> = std::result::Result<T, ProjectInitError>;
