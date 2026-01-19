use crate::error::{NotesError, Result};
use crate::types::SemanticConfig;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::io::{BufReader, BufWriter};
use std::time::SystemTime;
use chrono::{DateTime, Utc};

/// Metadata for the embedding index
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EmbeddingMetadata {
    /// Model used to generate embeddings
    pub model: String,
    /// Embedding dimensions
    pub dimensions: usize,
    /// Number of embeddings stored
    pub count: usize,
    /// Last update timestamp
    pub updated_at: DateTime<Utc>,
    /// Version of the index format
    pub version: u32,
}

impl Default for EmbeddingMetadata {
    fn default() -> Self {
        Self {
            model: "text-embedding-3-small".to_string(),
            dimensions: 1536,
            count: 0,
            updated_at: Utc::now(),
            version: 1,
        }
    }
}

/// Single embedding entry
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EmbeddingEntry {
    /// Note ID
    pub note_id: String,
    /// Embedding vector
    pub embedding: Vec<f32>,
    /// Hash of note content (for cache invalidation)
    pub content_hash: String,
    /// Timestamp when embedding was created
    pub created_at: DateTime<Utc>,
}

/// Main embedding index
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EmbeddingIndex {
    /// Index metadata
    pub metadata: EmbeddingMetadata,
    /// Map of note ID to embedding
    pub entries: HashMap<String, EmbeddingEntry>,
}

impl Default for EmbeddingIndex {
    fn default() -> Self {
        Self {
            metadata: EmbeddingMetadata::default(),
            entries: HashMap::new(),
        }
    }
}

/// Storage manager for embeddings
pub struct EmbeddingStore {
    notes_dir: PathBuf,
    index_path: PathBuf,
    index: EmbeddingIndex,
    dirty: bool,
}

impl EmbeddingStore {
    /// Create a new embedding store
    pub fn new(notes_dir: PathBuf) -> Result<Self> {
        let embeddings_dir = notes_dir.join(".embeddings");
        fs::create_dir_all(&embeddings_dir)?;

        let index_path = embeddings_dir.join("index.bin");

        let index = if index_path.exists() {
            Self::load_index(&index_path)?
        } else {
            EmbeddingIndex::default()
        };

        Ok(Self {
            notes_dir,
            index_path,
            index,
            dirty: false,
        })
    }

    /// Load index from disk
    fn load_index(path: &Path) -> Result<EmbeddingIndex> {
        let file = fs::File::open(path)
            .map_err(|e| NotesError::IoError(format!("Failed to open index file: {}", e)))?;

        let reader = BufReader::new(file);
        let index: EmbeddingIndex = bincode::deserialize_from(reader)
            .map_err(|e| NotesError::IoError(format!("Failed to deserialize index: {}", e)))?;

        Ok(index)
    }

    /// Save index to disk
    pub fn save(&mut self) -> Result<()> {
        if !self.dirty {
            return Ok(());
        }

        // Update metadata
        self.index.metadata.count = self.index.entries.len();
        self.index.metadata.updated_at = Utc::now();

        // Create temporary file first
        let temp_path = self.index_path.with_extension("tmp");

        let file = fs::File::create(&temp_path)
            .map_err(|e| NotesError::IoError(format!("Failed to create temp file: {}", e)))?;

        let writer = BufWriter::new(file);
        bincode::serialize_into(writer, &self.index)
            .map_err(|e| NotesError::IoError(format!("Failed to serialize index: {}", e)))?;

        // Atomic rename
        fs::rename(&temp_path, &self.index_path)
            .map_err(|e| NotesError::IoError(format!("Failed to save index: {}", e)))?;

        self.dirty = false;
        Ok(())
    }

    /// Add or update an embedding for a note
    pub fn upsert(&mut self, note_id: String, embedding: Vec<f32>, content_hash: String) {
        let entry = EmbeddingEntry {
            note_id: note_id.clone(),
            embedding,
            content_hash,
            created_at: Utc::now(),
        };

        self.index.entries.insert(note_id, entry);
        self.dirty = true;
    }

    /// Remove embedding for a note
    pub fn remove(&mut self, note_id: &str) {
        if self.index.entries.remove(note_id).is_some() {
            self.dirty = true;
        }
    }

    /// Get embedding for a note
    pub fn get(&self, note_id: &str) -> Option<&EmbeddingEntry> {
        self.index.entries.get(note_id)
    }

    /// Get all embeddings
    pub fn get_all(&self) -> &HashMap<String, EmbeddingEntry> {
        &self.index.entries
    }

    /// Check if embedding exists and is up to date
    pub fn is_valid(&self, note_id: &str, content_hash: &str) -> bool {
        if let Some(entry) = self.index.entries.get(note_id) {
            entry.content_hash == content_hash
        } else {
            false
        }
    }

    /// Get index metadata
    pub fn metadata(&self) -> &EmbeddingMetadata {
        &self.index.metadata
    }

    /// Get the number of embeddings stored
    pub fn len(&self) -> usize {
        self.index.entries.len()
    }

    /// Check if the index is empty
    pub fn is_empty(&self) -> bool {
        self.index.entries.is_empty()
    }

    /// Clear all embeddings
    pub fn clear(&mut self) {
        self.index.entries.clear();
        self.dirty = true;
    }
}

impl Drop for EmbeddingStore {
    fn drop(&mut self) {
        // Auto-save on drop if dirty
        if self.dirty {
            let _ = self.save();
        }
    }
}

/// Compute hash of note content for cache validation
pub fn compute_content_hash(content: &str) -> String {
    use sha2::{Sha256, Digest};
    let mut hasher = Sha256::new();
    hasher.update(content.as_bytes());
    format!("{:x}", hasher.finalize())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_content_hash() {
        let hash1 = compute_content_hash("test content");
        let hash2 = compute_content_hash("test content");
        let hash3 = compute_content_hash("different content");

        assert_eq!(hash1, hash2);
        assert_ne!(hash1, hash3);
    }

    #[test]
    fn test_embedding_entry_creation() {
        let entry = EmbeddingEntry {
            note_id: "test-id".to_string(),
            embedding: vec![0.1, 0.2, 0.3],
            content_hash: "abc123".to_string(),
            created_at: Utc::now(),
        };

        assert_eq!(entry.note_id, "test-id");
        assert_eq!(entry.embedding.len(), 3);
    }
}
