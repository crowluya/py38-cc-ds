use thiserror::Error;

/// Error type for the notes application
#[derive(Error, Debug)]
pub enum NotesError {
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),

    #[error("Serialization error: {0}")]
    Serialization(#[from] serde_json::Error),

    #[error("Note not found: {0}")]
    NoteNotFound(String),

    #[error("Tag not found: {0}")]
    TagNotFound(String),

    #[error("Invalid note title: {0}")]
    InvalidTitle(String),

    #[error("Editor error: {0}")]
    EditorError(String),

    #[error("Configuration error: {0}")]
    ConfigError(String),

    #[error("Search error: {0}")]
    SearchError(String),

    #[error("Path error: {0}")]
    PathError(String),
}

pub type Result<T> = std::result::Result<T, NotesError>;
