use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

/// Represents a single note with all its metadata
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Note {
    /// Unique identifier for the note
    pub id: String,
    /// Title of the note
    pub title: String,
    /// Markdown content of the note
    pub content: String,
    /// Tags associated with the note
    #[serde(default)]
    pub tags: Vec<String>,
    /// Creation timestamp
    pub created_at: DateTime<Utc>,
    /// Last modification timestamp
    pub updated_at: DateTime<Utc>,
    /// File path where the note is stored
    #[serde(skip)]
    pub file_path: Option<PathBuf>,
    /// Parent note ID for hierarchical relationships
    #[serde(default)]
    pub parent_id: Option<String>,
    /// Child note IDs
    #[serde(default)]
    pub children: Vec<String>,
    /// Notebook ID
    #[serde(default)]
    pub notebook_id: Option<String>,
    /// Inherited tags from parent notes (computed, not stored)
    #[serde(skip)]
    pub inherited_tags: Vec<String>,
    /// Whether the note content is encrypted
    #[serde(default)]
    pub encrypted: bool,
}

impl Note {
    /// Create a new note with the given title and content
    pub fn new(title: String, content: String) -> Self {
        let now = Utc::now();
        Self {
            id: uuid::Uuid::new_v4().to_string(),
            title,
            content,
            tags: Vec::new(),
            created_at: now,
            updated_at: now,
            file_path: None,
            parent_id: None,
            children: Vec::new(),
            notebook_id: None,
            inherited_tags: Vec::new(),
        }
    }

    /// Get all effective tags (direct + inherited)
    pub fn effective_tags(&self) -> Vec<String> {
        let mut tags = self.tags.clone();
        tags.extend(self.inherited_tags.clone());
        tags.sort();
        tags.dedup();
        tags
    }

    /// Set parent note
    pub fn set_parent(&mut self, parent_id: String) {
        self.parent_id = Some(parent_id);
        self.updated_at = Utc::now();
    }

    /// Remove parent note
    pub fn remove_parent(&mut self) {
        self.parent_id = None;
        self.updated_at = Utc::now();
    }

    /// Add child note
    pub fn add_child(&mut self, child_id: String) {
        if !self.children.contains(&child_id) {
            self.children.push(child_id);
            self.updated_at = Utc::now();
        }
    }

    /// Remove child note
    pub fn remove_child(&mut self, child_id: &str) -> bool {
        if let Some(pos) = self.children.iter().position(|id| id == child_id) {
            self.children.remove(pos);
            self.updated_at = Utc::now();
            true
        } else {
            false
        }
    }

    /// Set notebook
    pub fn set_notebook(&mut self, notebook_id: String) {
        self.notebook_id = Some(notebook_id);
        self.updated_at = Utc::now();
    }

    /// Add a tag to the note
    pub fn add_tag(&mut self, tag: String) {
        if !self.tags.contains(&tag) {
            self.tags.push(tag);
            self.updated_at = Utc::now();
        }
    }

    /// Remove a tag from the note
    pub fn remove_tag(&mut self, tag: &str) -> bool {
        if let Some(pos) = self.tags.iter().position(|t| t == tag) {
            self.tags.remove(pos);
            self.updated_at = Utc::now();
            true
        } else {
            false
        }
    }

    /// Check if the note contains a specific tag
    pub fn has_tag(&self, tag: &str) -> bool {
        self.tags.iter().any(|t| t == tag)
    }

    /// Update the note content
    pub fn update_content(&mut self, content: String) {
        self.content = content;
        self.updated_at = Utc::now();
    }

    /// Generate a slug from the title for use in filenames
    pub fn slug(&self) -> String {
        self.title
            .to_lowercase()
            .chars()
            .map(|c| {
                if c.is_alphanumeric() {
                    c
                } else if c.is_whitespace() {
                    '-'
                } else {
                    ''
                }
            })
            .collect::<String>()
            .split('-')
            .filter(|s| !s.is_empty())
            .collect::<Vec<&str>>()
            .join("-")
    }
}

/// Lightweight metadata for indexing notes
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NoteMetadata {
    pub id: String,
    pub title: String,
    pub tags: Vec<String>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    pub file_path: PathBuf,
    pub parent_id: Option<String>,
    pub notebook_id: Option<String>,
}

impl From<&Note> for NoteMetadata {
    fn from(note: &Note) -> Self {
        Self {
            id: note.id.clone(),
            title: note.title.clone(),
            tags: note.tags.clone(),
            created_at: note.created_at,
            updated_at: note.updated_at,
            file_path: note.file_path.clone().unwrap_or_default(),
            parent_id: note.parent_id.clone(),
            notebook_id: note.notebook_id.clone(),
        }
    }
}

/// Represents a notebook container for organizing notes
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Notebook {
    /// Unique identifier for the notebook
    pub id: String,
    /// Name of the notebook
    pub name: String,
    /// Optional description
    #[serde(default)]
    pub description: String,
    /// Creation timestamp
    pub created_at: DateTime<Utc>,
    /// Last modification timestamp
    pub updated_at: DateTime<Utc>,
}

impl Notebook {
    /// Create a new notebook
    pub fn new(name: String, description: String) -> Self {
        let now = Utc::now();
        Self {
            id: uuid::Uuid::new_v4().to_string(),
            name,
            description,
            created_at: now,
            updated_at: now,
        }
    }

    /// Update the notebook description
    pub fn update_description(&mut self, description: String) {
        self.description = description;
        self.updated_at = Utc::now();
    }

    /// Generate a slug from the name for use in filenames
    pub fn slug(&self) -> String {
        self.name
            .to_lowercase()
            .chars()
            .map(|c| {
                if c.is_alphanumeric() {
                    c
                } else if c.is_whitespace() {
                    '-'
                } else {
                    ''
                }
            })
            .collect::<String>()
            .split('-')
            .filter(|s| !s.is_empty())
            .collect::<Vec<&str>>()
            .join("-")
    }
}

/// Workspace statistics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkspaceStats {
    pub total_notes: usize,
    pub total_notebooks: usize,
    pub total_tags: usize,
    pub most_used_tags: Vec<(String, usize)>,
    pub notes_by_notebook: Vec<(String, usize)>,
    pub storage_size_bytes: u64,
    pub largest_notebook: Option<String>,
    pub average_notes_per_notebook: f64,
}

/// Search query types for boolean search
#[derive(Debug, Clone, PartialEq)]
pub enum SearchOperator {
    And,
    Or,
    Not,
}

#[derive(Debug, Clone)]
pub enum SearchQuery {
    Text(String),
    Tag(String),
    And(Box<SearchQuery>, Box<SearchQuery>),
    Or(Box<SearchQuery>, Box<SearchQuery>),
    Not(Box<SearchQuery>),
}

/// Application configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    /// Directory where notes are stored
    pub notes_dir: PathBuf,
    /// Default editor for editing notes
    pub editor: Option<String>,
    /// Whether to use markdown rendering in terminal
    pub render_markdown: bool,
    /// Maximum number of notes to display in list
    pub list_limit: usize,
    /// Backup configuration
    #[serde(default)]
    pub backup: BackupConfig,
    /// Semantic search configuration
    #[serde(default)]
    pub semantic: SemanticConfig,
}

/// Backup configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BackupConfig {
    /// Directory where backups are stored
    pub backup_dir: PathBuf,
    /// Enable automatic periodic backups
    pub auto_backup_enabled: bool,
    /// Interval between automatic backups (in hours)
    pub auto_backup_interval_hours: u64,
    /// Maximum number of backups to keep (0 = unlimited)
    pub max_backups: usize,
    /// Whether to compress backups
    pub compress_backups: bool,
}

/// Semantic search configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SemanticConfig {
    /// Enable semantic search
    pub enabled: bool,
    /// OpenAI API key (or read from OPENAI_API_KEY env var)
    pub api_key: Option<String>,
    /// Embedding model to use
    pub model: String,
    /// Minimum similarity threshold (0.0 to 1.0)
    pub similarity_threshold: f32,
    /// Auto-index notes on create/update
    pub auto_index: bool,
    /// Maximum results to return
    pub max_results: usize,
}

impl Default for SemanticConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            api_key: None,
            model: "text-embedding-3-small".to_string(),
            similarity_threshold: 0.7,
            auto_index: true,
            max_results: 10,
        }
    }
}

impl Default for BackupConfig {
    fn default() -> Self {
        Self {
            backup_dir: dirs::home_dir()
                .unwrap_or_else(|| PathBuf::from("."))
                .join("notes")
                .join("backups"),
            auto_backup_enabled: true,
            auto_backup_interval_hours: 24,
            max_backups: 7,
            compress_backups: true,
        }
    }
}

impl Default for Config {
    fn default() -> Self {
        Self {
            notes_dir: dirs::home_dir()
                .unwrap_or_else(|| PathBuf::from("."))
                .join("notes"),
            editor: std::env::var("EDITOR").ok(),
            render_markdown: true,
            list_limit: 50,
            backup: BackupConfig::default(),
            semantic: SemanticConfig::default(),
        }
    }
}

/// Frontmatter metadata stored at the top of note files
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NoteFrontmatter {
    pub id: String,
    pub title: String,
    pub tags: Vec<String>,
    pub created_at: String,
    pub updated_at: String,
    #[serde(default)]
    pub parent_id: Option<String>,
    #[serde(default)]
    pub notebook_id: Option<String>,
    #[serde(default)]
    pub encrypted: bool,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_note_creation() {
        let note = Note::new("Test Note".to_string(), "Test content".to_string());
        assert_eq!(note.title, "Test Note");
        assert_eq!(note.content, "Test content");
        assert!(note.tags.is_empty());
        assert!(!note.id.is_empty());
    }

    #[test]
    fn test_tag_operations() {
        let mut note = Note::new("Test".to_string(), "Content".to_string());
        note.add_tag("rust".to_string());
        note.add_tag("cli".to_string());

        assert!(note.has_tag("rust"));
        assert!(note.has_tag("cli"));
        assert!(!note.has_tag("other"));

        assert!(note.remove_tag("rust"));
        assert!(!note.has_tag("rust"));
        assert!(!note.remove_tag("nonexistent"));
    }

    #[test]
    fn test_slug_generation() {
        let note = Note::new("Hello World Test".to_string(), "Content".to_string());
        assert_eq!(note.slug(), "hello-world-test");
    }
}
