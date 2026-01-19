use crate::types::{KnowledgeGraph, Note};
use anyhow::{Context, Result};
use std::fs;
use std::path::{Path, PathBuf};

/// Default notes directory name
pub const NOTES_DIR: &str = ".kg";

/// Storage manager for notes
pub struct Storage {
    notes_dir: PathBuf,
}

impl Storage {
    /// Create a new storage manager with the given base directory
    pub fn new(base_dir: Option<PathBuf>) -> Result<Self> {
        let notes_dir = if let Some(dir) = base_dir {
            dir.join(NOTES_DIR)
        } else {
            // Use current directory
            std::env::current_dir()
                .context("Failed to get current directory")?
                .join(NOTES_DIR)
        };

        Ok(Storage { notes_dir })
    }

    /// Initialize the notes directory
    pub fn initialize(&self) -> Result<()> {
        if !self.notes_dir.exists() {
            fs::create_dir_all(&self.notes_dir)
                .context("Failed to create notes directory")?;
        }
        Ok(())
    }

    /// Get the path to a note file
    fn note_path(&self, note_id: &str) -> PathBuf {
        self.notes_dir.join(format!("{}.md", note_id))
    }

    /// Save a note to disk
    pub fn save_note(&self, note: &Note) -> Result<()> {
        let path = self.note_path(&note.id);
        let content = self.serialize_note(note)?;
        fs::write(&path, content).context("Failed to write note file")?;
        Ok(())
    }

    /// Load a note from disk
    pub fn load_note(&self, note_id: &str) -> Result<Note> {
        let path = self.note_path(note_id);
        let content = fs::read_to_string(&path).context("Failed to read note file")?;
        self.deserialize_note(&content, note_id)
    }

    /// Delete a note from disk
    pub fn delete_note(&self, note_id: &str) -> Result<()> {
        let path = self.note_path(note_id);
        fs::remove_file(&path).context("Failed to delete note file")?;
        Ok(())
    }

    /// Check if a note exists
    pub fn note_exists(&self, note_id: &str) -> bool {
        self.note_path(note_id).exists()
    }

    /// List all note IDs
    pub fn list_notes(&self) -> Result<Vec<String>> {
        if !self.notes_dir.exists() {
            return Ok(Vec::new());
        }

        let mut note_ids = Vec::new();
        for entry in fs::read_dir(&self.notes_dir)
            .context("Failed to read notes directory")?
        {
            let entry = entry.context("Failed to read directory entry")?;
            let path = entry.path();
            if path.extension().and_then(|s| s.to_str()) == Some("md") {
                if let Some(stem) = path.file_stem().and_then(|s| s.to_str()) {
                    note_ids.push(stem.to_string());
                }
            }
        }

        note_ids.sort();
        Ok(note_ids)
    }

    /// Load all notes into a knowledge graph
    pub fn load_all(&self) -> Result<KnowledgeGraph> {
        let mut graph = KnowledgeGraph::new();
        let note_ids = self.list_notes()?;

        for note_id in note_ids {
            match self.load_note(&note_id) {
                Ok(note) => {
                    graph.add_note(note);
                }
                Err(e) => {
                    eprintln!("Warning: Failed to load note '{}': {}", note_id, e);
                }
            }
        }

        graph.rebuild_links();
        Ok(graph)
    }

    /// Serialize a note to markdown with frontmatter
    fn serialize_note(&self, note: &Note) -> Result<String> {
        let frontmatter = serde_json::to_string_pretty(note)?;
        let content = format!("---\n{}\n---\n{}\n", frontmatter, note.content);
        Ok(content)
    }

    /// Deserialize a note from markdown with frontmatter
    fn deserialize_note(&self, content: &str, note_id: &str) -> Result<Note> {
        // Parse frontmatter
        if !content.starts_with("---") {
            return Err(anyhow::anyhow!("Invalid note format: missing frontmatter"));
        }

        let parts: Vec<&str> = content.splitn(3, "---").collect();
        if parts.len() < 3 {
            return Err(anyhow::anyhow!("Invalid note format: incomplete frontmatter"));
        }

        let frontmatter = parts[1].trim();
        let mut note: Note = serde_json::from_str(frontmatter)
            .context("Failed to parse note frontmatter")?;

        // Update content (without frontmatter)
        note.content = parts[2].to_string();

        Ok(note)
    }

    /// Export the knowledge graph to a file
    pub fn export_graph(&self, graph: &KnowledgeGraph, format: ExportFormat, output: &Path) -> Result<()> {
        let content = match format {
            ExportFormat::Dot => crate::export::to_dot(graph)?,
            ExportFormat::Json => crate::export::to_json(graph)?,
        };

        fs::write(output, content).context("Failed to write export file")?;
        Ok(())
    }
}

/// Export format options
#[derive(Debug, Clone, Copy)]
pub enum ExportFormat {
    Dot,
    Json,
}
