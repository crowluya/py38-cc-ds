use crate::crypto;
use crate::error::{NotesError, Result};
use crate::types::{Note, NoteFrontmatter, NoteMetadata, Notebook, SearchQuery, WorkspaceStats};
use chrono::{DateTime, Utc};
use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::{Path, PathBuf};

/// Storage manager with encryption support
#[derive(Clone)]
pub struct Storage {
    pub notes_dir: PathBuf,
    /// Master encryption key (None = locked)
    master_key: Option<[u8; crypto::KEY_SIZE]>,
}

impl Storage {
    /// Create a new storage manager
    pub fn new(notes_dir: PathBuf) -> Result<Self> {
        // Ensure notes directory exists
        fs::create_dir_all(&notes_dir)?;
        Ok(Self {
            notes_dir,
            master_key: None,
        })
    }

    /// Set master encryption key
    pub fn set_master_key(&mut self, key: [u8; crypto::KEY_SIZE]) {
        self.master_key = Some(key);
    }

    /// Clear master encryption key
    pub fn clear_master_key(&mut self) {
        if let Some(mut key) = self.master_key.take() {
            crypto::zero_bytes(&mut key);
        }
    }

    /// Check if encryption is enabled (unlocked)
    pub fn is_unlocked(&self) -> bool {
        self.master_key.is_some()
    }

    /// Encrypt note content
    fn encrypt_content(&self, content: &str) -> Result<String> {
        let key = self.master_key
            .as_ref()
            .ok_or_else(|| anyhow::anyhow!("Storage is locked. Unlock to encrypt notes."))?;

        crypto::encrypt_to_base64(key, content)
    }

    /// Decrypt note content
    fn decrypt_content(&self, encrypted_content: &str) -> Result<String> {
        let key = self.master_key
            .as_ref()
            .ok_or_else(|| anyhow::anyhow!("Storage is locked. Unlock to decrypt notes."))?;

        crypto::decrypt_from_base64(key, encrypted_content)
    }

/// Helper function to find operator position (ignoring those inside quotes)
fn find_operator(query: &str, operator: &str) -> Option<usize> {
    let mut in_quotes = false;
    let chars: Vec<char> = query.chars().collect();
    let op_chars: Vec<char> = operator.chars().collect();

    for i in 0..chars.len() {
        if chars[i] == '"' {
            in_quotes = !in_quotes;
        }

        if !in_quotes && i + op_chars.len() <= chars.len() {
            let slice = &chars[i..i + op_chars.len()];
            if slice.iter().collect::<String>() == *operator {
                return Some(i);
            }
        }
    }

    None
}

/// Storage manager for notes
#[derive(Clone)]
pub struct Storage {
    pub notes_dir: PathBuf,
}

impl Storage {
    /// Create a new storage manager
    pub fn new(notes_dir: PathBuf) -> Result<Self> {
        // Ensure notes directory exists
        fs::create_dir_all(&notes_dir)?;
        Ok(Self { notes_dir })
    }

    /// Initialize the directory structure
    pub fn initialize(&self) -> Result<()> {
        // Create main notes directory
        fs::create_dir_all(&self.notes_dir)?;

        // Create yearly/monthly structure
        let now = Utc::now();
        let year = now.format("%Y").to_string();
        let month = now.format("%m").to_string();

        let year_dir = self.notes_dir.join(&year);
        let month_dir = year_dir.join(&month);

        fs::create_dir_all(&month_dir)?;

        Ok(())
    }

    /// Get the file path for a new note
    fn get_note_path(&self, note: &Note) -> Result<PathBuf> {
        let date = note.created_at.format("%Y/%m/%d").to_string();
        let date_dir = self.notes_dir.join(&date);

        // Create date directory if it doesn't exist
        fs::create_dir_all(&date_dir)?;

        let filename = format!("{}-{}.md", note.created_at.format("%H%M%S"), note.slug());
        Ok(date_dir.join(filename))
    }

    /// Save a note to disk
    pub fn save_note(&mut self, note: &mut Note) -> Result<()> {
        // Generate file path if not set
        if note.file_path.is_none() {
            note.file_path = Some(self.get_note_path(note)?);
        }

        let file_path = note.file_path.as_ref().ok_or_else(|| {
            NotesError::PathError("Note file path not set".to_string())
        })?;

        // Encrypt content if note should be encrypted
        let content_to_save = if note.encrypted {
            self.encrypt_content(&note.content)?
        } else {
            note.content.clone()
        };

        // Create frontmatter
        let frontmatter = NoteFrontmatter {
            id: note.id.clone(),
            title: note.title.clone(),
            tags: note.tags.clone(),
            created_at: note.created_at.to_rfc3339(),
            updated_at: note.updated_at.to_rfc3339(),
            parent_id: note.parent_id.clone(),
            notebook_id: note.notebook_id.clone(),
            encrypted: note.encrypted,
        };

        // Serialize frontmatter to YAML
        let frontmatter_yaml = serde_yaml::to_string(&frontmatter)
            .unwrap_or_else(|_| "---".to_string());

        // Write note with frontmatter
        let content = format!(
            "---\n{}---\n\n{}",
            frontmatter_yaml,
            content_to_save
        );

        fs::write(file_path, content)?;

        Ok(())
    }

    /// Load a note from disk by ID
    pub fn load_note(&self, id: &str) -> Result<Note> {
        let note_path = self.find_note_by_id(id)?;

        let content = fs::read_to_string(&note_path)?;

        // Parse frontmatter
        let (frontmatter_str, note_content) = self.parse_frontmatter(&content)?;

        let frontmatter: NoteFrontmatter = serde_yaml::from_str(frontmatter_str)
            .map_err(|_| NotesError::Serialization(
                "Failed to parse frontmatter".to_string()
            ))?;

        let created_at = DateTime::parse_from_rfc3339(&frontmatter.created_at)
            .map_err(|_| NotesError::Serialization("Invalid date format".to_string()))?
            .with_timezone(&Utc);

        let updated_at = DateTime::parse_from_rfc3339(&frontmatter.updated_at)
            .map_err(|_| NotesError::Serialization("Invalid date format".to_string()))?
            .with_timezone(&Utc);

        // Decrypt content if encrypted
        let decrypted_content = if frontmatter.encrypted {
            self.decrypt_content(note_content)?
        } else {
            note_content.to_string()
        };

        let note = Note {
            id: frontmatter.id,
            title: frontmatter.title,
            content: decrypted_content,
            tags: frontmatter.tags,
            created_at,
            updated_at,
            file_path: Some(note_path),
            parent_id: frontmatter.parent_id,
            notebook_id: frontmatter.notebook_id,
            children: Vec::new(),
            inherited_tags: Vec::new(),
            encrypted: frontmatter.encrypted,
        };

        Ok(note)
    }

    /// Find a note file by its ID
    fn find_note_by_id(&self, id: &str) -> Result<PathBuf> {
        // Search through all note files
        for entry in walkdir::WalkDir::new(&self.notes_dir)
            .into_iter()
            .filter_map(|e| e.ok())
        {
            let path = entry.path();

            if path.extension().and_then(|s| s.to_str()) == Some("md") {
                if let Ok(content) = fs::read_to_string(path) {
                    if let Ok((frontmatter, _)) = self.parse_frontmatter(&content) {
                        if let Ok(frontmatter_data) = serde_yaml::from_str::<serde_json::Value>(frontmatter) {
                            if frontmatter_data.get("id")
                                .and_then(|v| v.as_str())
                                .map(|s| s == id)
                                .unwrap_or(false)
                            {
                                return Ok(path.to_path_buf());
                            }
                        }
                    }
                }
            }
        }

        Err(NotesError::NoteNotFound(id.to_string()))
    }

    /// Parse frontmatter from note content
    fn parse_frontmatter<'a>(&self, content: &'a str) -> Result<(&'a str, &'a str)> {
        if !content.starts_with("---") {
            return Ok(("", content));
        }

        let rest = &content[3..];
        if let Some(end_pos) = rest.find("\n---") {
            let frontmatter = &rest[..end_pos];
            let note_content = &rest[end_pos + 5..];
            return Ok((frontmatter, note_content));
        }

        Ok(("", content))
    }

    /// Delete a note
    pub fn delete_note(&self, id: &str) -> Result<()> {
        let note_path = self.find_note_by_id(id)?;
        fs::remove_file(note_path)?;
        Ok(())
    }

    /// List all notes
    pub fn list_notes(&self) -> Result<Vec<NoteMetadata>> {
        let mut notes = Vec::new();

        for entry in walkdir::WalkDir::new(&self.notes_dir)
            .into_iter()
            .filter_map(|e| e.ok())
        {
            let path = entry.path();

            if path.extension().and_then(|s| s.to_str()) == Some("md") {
                if let Ok(content) = fs::read_to_string(path) {
                    if let Ok(metadata) = self.extract_metadata(path, &content) {
                        notes.push(metadata);
                    }
                }
            }
        }

        // Sort by updated_at descending
        notes.sort_by(|a, b| b.updated_at.cmp(&a.updated_at));

        Ok(notes)
    }

    /// Extract metadata from a note file
    fn extract_metadata(&self, path: &Path, content: &str) -> Result<NoteMetadata> {
        let (frontmatter_str, _) = self.parse_frontmatter(content)?;

        let frontmatter: NoteFrontmatter = serde_yaml::from_str(frontmatter_str)
            .map_err(|_| NotesError::Serialization(
                "Failed to parse frontmatter".to_string()
            ))?;

        let created_at = DateTime::parse_from_rfc3339(&frontmatter.created_at)
            .map_err(|_| NotesError::Serialization("Invalid date format".to_string()))?
            .with_timezone(&Utc);

        let updated_at = DateTime::parse_from_rfc3339(&frontmatter.updated_at)
            .map_err(|_| NotesError::Serialization("Invalid date format".to_string()))?
            .with_timezone(&Utc);

        Ok(NoteMetadata {
            id: frontmatter.id,
            title: frontmatter.title,
            tags: frontmatter.tags,
            created_at,
            updated_at,
            file_path: path.to_path_buf(),
            parent_id: frontmatter.parent_id,
            notebook_id: frontmatter.notebook_id,
        })
    }

    /// Search notes by content
    pub fn search_notes(&self, query: &str) -> Result<Vec<NoteMetadata>> {
        let all_notes = self.list_notes()?;
        let query_lower = query.to_lowercase();

        let matching_notes: Vec<NoteMetadata> = all_notes
            .into_iter()
            .filter(|metadata| {
                let title_matches = metadata.title.to_lowercase().contains(&query_lower);

                // Search in content if metadata doesn't suffice
                let content_matches = if let Ok(note) = self.load_note(&metadata.id) {
                    note.content.to_lowercase().contains(&query_lower)
                } else {
                    false
                };

                title_matches || content_matches
            })
            .collect();

        Ok(matching_notes)
    }

    /// Get notes by tag
    pub fn get_notes_by_tag(&self, tag: &str) -> Result<Vec<NoteMetadata>> {
        let all_notes = self.list_notes()?;

        let tagged_notes: Vec<NoteMetadata> = all_notes
            .into_iter()
            .filter(|metadata| metadata.tags.iter().any(|t| t == tag))
            .collect();

        Ok(tagged_notes)
    }

    // ============ Notebook Operations ============

    /// Get the path to the notebooks metadata file
    fn notebooks_file_path(&self) -> PathBuf {
        self.notes_dir.join(".notebooks.json")
    }

    /// Load all notebooks
    pub fn load_notebooks(&self) -> Result<Vec<Notebook>> {
        let path = self.notebooks_file_path();

        if !path.exists() {
            return Ok(Vec::new());
        }

        let content = fs::read_to_string(&path)?;
        let notebooks: Vec<Notebook> = serde_json::from_str(&content)
            .map_err(|_| NotesError::Serialization("Failed to parse notebooks".to_string()))?;

        Ok(notebooks)
    }

    /// Save all notebooks
    pub fn save_notebooks(&self, notebooks: &[Notebook]) -> Result<()> {
        let path = self.notebooks_file_path();
        let content = serde_json::to_string_pretty(notebooks)
            .map_err(|_| NotesError::Serialization)?;
        fs::write(path, content)?;
        Ok(())
    }

    /// Create a new notebook
    pub fn create_notebook(&self, name: String, description: String) -> Result<Notebook> {
        let mut notebooks = self.load_notebooks()?;

        // Check for duplicate names
        if notebooks.iter().any(|n| n.name == name) {
            return Err(NotesError::ConfigError(format!("Notebook '{}' already exists", name)));
        }

        let notebook = Notebook::new(name, description);
        notebooks.push(notebook.clone());
        self.save_notebooks(&notebooks)?;

        Ok(notebook)
    }

    /// Delete a notebook
    pub fn delete_notebook(&self, id: &str) -> Result<()> {
        let mut notebooks = self.load_notebooks()?;
        notebooks.retain(|n| n.id != id);
        self.save_notebooks(&notebooks)?;
        Ok(())
    }

    /// Get a notebook by ID
    pub fn get_notebook(&self, id: &str) -> Result<Notebook> {
        let notebooks = self.load_notebooks()?;
        notebooks
            .into_iter()
            .find(|n| n.id == id)
            .ok_or_else(|| NotesError::NoteNotFound(format!("Notebook {}", id)))
    }

    /// Get notes in a specific notebook
    pub fn get_notes_in_notebook(&self, notebook_id: &str) -> Result<Vec<NoteMetadata>> {
        let all_notes = self.list_notes()?;

        let notebook_notes: Vec<NoteMetadata> = all_notes
            .into_iter()
            .filter(|metadata| metadata.notebook_id.as_ref().map(|id| id == notebook_id).unwrap_or(false))
            .collect();

        Ok(notebook_notes)
    }

    // ============ Hierarchy & Tag Inheritance ============

    /// Build a mapping of parent-child relationships
    fn build_parent_map(&self) -> Result<HashMap<String, Vec<String>>> {
        let notes = self.list_notes()?;
        let mut parent_map: HashMap<String, Vec<String>> = HashMap::new();

        for note in &notes {
            if let Some(parent_id) = &note.parent_id {
                parent_map
                    .entry(parent_id.clone())
                    .or_insert_with(Vec::new)
                    .push(note.id.clone());
            }
        }

        Ok(parent_map)
    }

    /// Get inherited tags by traversing parent hierarchy
    pub fn get_inherited_tags(&self, note_id: &str, depth_limit: Option<usize>) -> Result<Vec<String>> {
        let mut inherited_tags = Vec::new();
        let mut visited = HashSet::new();
        let mut current_id = Some(note_id.to_string());
        let mut depth = 0;

        while let Some(id) = current_id {
            if depth_limit.map_or(false, |limit| depth >= limit) {
                break;
            }

            // Check for circular references
            if !visited.insert(id.clone()) {
                return Err(NotesError::SearchError("Circular reference detected in note hierarchy".to_string()));
            }

            // Load the current note
            let note = self.load_note(&id)?;

            // Add parent's direct tags to inherited tags
            if let Some(parent_id) = &note.parent_id {
                let parent_note = self.load_note(parent_id)?;
                inherited_tags.extend(parent_note.tags);
                current_id = parent_note.parent_id.clone();
                depth += 1;
            } else {
                current_id = None;
            }
        }

        // Remove duplicates and sort
        inherited_tags.sort();
        inherited_tags.dedup();

        Ok(inherited_tags)
    }

    /// Load a note with inherited tags computed
    pub fn load_note_with_inheritance(&self, id: &str) -> Result<Note> {
        let mut note = self.load_note(id)?;
        note.inherited_tags = self.get_inherited_tags(id, Some(10))?;
        Ok(note)
    }

    /// Set parent of a note
    pub fn set_note_parent(&mut self, child_id: &str, parent_id: &str) -> Result<()> {
        // Check for circular reference
        if self.would_create_circular_reference(child_id, parent_id)? {
            return Err(NotesError::SearchError("This would create a circular reference".to_string()));
        }

        let mut child_note = self.load_note(child_id)?;
        let mut parent_note = self.load_note(parent_id)?;

        // Remove from old parent if exists
        if let Some(old_parent_id) = &child_note.parent_id {
            let mut old_parent = self.load_note(old_parent_id)?;
            old_parent.remove_child(child_id);
            self.save_note(&mut old_parent)?;
        }

        // Set new parent
        child_note.set_parent(parent_id.to_string());
        parent_note.add_child(child_id.to_string());

        self.save_note(&mut child_note)?;
        self.save_note(&mut parent_note)?;

        Ok(())
    }

    /// Remove parent from a note
    pub fn remove_note_parent(&mut self, child_id: &str) -> Result<()> {
        let mut child_note = self.load_note(child_id)?;

        if let Some(parent_id) = &child_note.parent_id {
            let mut parent_note = self.load_note(parent_id)?;
            parent_note.remove_child(child_id);
            self.save_note(&mut parent_note)?;
        }

        child_note.remove_parent();
        self.save_note(&mut child_note)?;

        Ok(())
    }

    /// Check if setting parent would create a circular reference
    fn would_create_circular_reference(&self, child_id: &str, parent_id: &str) -> Result<bool> {
        let mut current_id = Some(parent_id.to_string());
        let mut visited = HashSet::new();

        while let Some(id) = current_id {
            if id == child_id {
                return Ok(true); // Circular reference detected
            }

            if !visited.insert(id.clone()) {
                return Ok(true); // Circular reference in existing hierarchy
            }

            let note = self.load_note(&id)?;
            current_id = note.parent_id.clone();
        }

        Ok(false)
    }

    // ============ Advanced Search ============

    /// Parse a boolean search query
    pub fn parse_search_query(&self, query: &str) -> Result<SearchQuery> {
        // Simple parser implementation
        // Supports: tag:xxx, "quoted phrases", AND, OR, NOT
        let query = query.trim();

        // Check for NOT operator
        if let Some(rest) = query.strip_prefix("NOT ") {
            let inner_query = self.parse_search_query(rest)?;
            return Ok(SearchQuery::Not(Box::new(inner_query)));
        }

        // Check for OR operator (lowest precedence)
        if let Some(pos) = find_operator(query, " OR ") {
            let left = self.parse_search_query(&query[..pos])?;
            let right = self.parse_search_query(&query[pos + 4..])?;
            return Ok(SearchQuery::Or(Box::new(left), Box::new(right)));
        }

        // Check for AND operator (higher precedence)
        if let Some(pos) = find_operator(query, " AND ") {
            let left = self.parse_search_query(&query[..pos])?;
            let right = self.parse_search_query(&query[pos + 5..])?;
            return Ok(SearchQuery::And(Box::new(left), Box::new(right)));
        }

        // Check for tag filter
        if let Some(tag) = query.strip_prefix("tag:") {
            return Ok(SearchQuery::Tag(tag.to_string()));
        }

        // Treat as text search
        Ok(SearchQuery::Text(query.to_string()))
    }

    /// Execute a boolean search query
    pub fn execute_search(&self, query: &SearchQuery) -> Result<Vec<NoteMetadata>> {
        match query {
            SearchQuery::Text(text) => {
                self.search_notes(text)
            }
            SearchQuery::Tag(tag) => {
                self.get_notes_by_tag(tag)
            }
            SearchQuery::And(left, right) => {
                let left_results = self.execute_search(left)?;
                let right_results = self.execute_search(right)?;

                // Intersection
                let left_ids: HashSet<_> = left_results.iter().map(|n| &n.id).collect();
                let and_results: Vec<NoteMetadata> = right_results
                    .into_iter()
                    .filter(|n| left_ids.contains(&n.id))
                    .collect();

                Ok(and_results)
            }
            SearchQuery::Or(left, right) => {
                let left_results = self.execute_search(left)?;
                let mut right_results = self.execute_search(right)?;

                // Union
                let mut id_map = HashMap::new();
                for note in left_results {
                    id_map.insert(note.id.clone(), note);
                }
                for note in right_results {
                    id_map.insert(note.id.clone(), note);
                }

                Ok(id_map.into_values().collect())
            }
            SearchQuery::Not(inner) => {
                let all_notes = self.list_notes()?;
                let exclude_results = self.execute_search(inner)?;

                // Difference
                let exclude_ids: HashSet<_> = exclude_results.iter().map(|n| &n.id).collect();
                let not_results: Vec<NoteMetadata> = all_notes
                    .into_iter()
                    .filter(|n| !exclude_ids.contains(&n.id))
                    .collect();

                Ok(not_results)
            }
        }
    }

    // ============ Statistics ============

    /// Calculate workspace statistics
    pub fn calculate_stats(&self) -> Result<WorkspaceStats> {
        let notes = self.list_notes()?;
        let notebooks = self.load_notebooks()?;

        // Count tags
        let mut tag_counts: HashMap<String, usize> = HashMap::new();
        for note in &notes {
            for tag in &note.tags {
                *tag_counts.entry(tag.clone()).or_insert(0) += 1;
            }
        }

        // Most used tags (top 10)
        let mut most_used_tags: Vec<(String, usize)> = tag_counts.into_iter().collect();
        most_used_tags.sort_by(|a, b| b.1.cmp(&a.1));
        most_used_tags.truncate(10);

        // Notes by notebook
        let mut notes_by_notebook: HashMap<String, usize> = HashMap::new();
        let mut uncategorized_count = 0;

        for note in &notes {
            if let Some(nb_id) = &note.notebook_id {
                *notes_by_notebook.entry(nb_id.clone()).or_insert(0) += 1;
            } else {
                uncategorized_count += 1;
            }
        }

        if uncategorized_count > 0 {
            notes_by_notebook.insert("Uncategorized".to_string(), uncategorized_count);
        }

        let notes_by_notebook: Vec<(String, usize)> = notes_by_notebook
            .into_iter()
            .map(|(id, count)| {
                let name = notebooks.iter()
                    .find(|n| n.id == id)
                    .map(|n| n.name.clone())
                    .unwrap_or(id);
                (name, count)
            })
            .collect();

        // Calculate storage size
        let storage_size_bytes = self.calculate_storage_size()?;

        // Find largest notebook
        let largest_notebook = notes_by_notebook
            .iter()
            .max_by_key(|(_, count)| *count)
            .map(|(name, _)| name.clone());

        // Average notes per notebook
        let average_notes_per_notebook = if notebooks.is_empty() {
            0.0
        } else {
            notes.len() as f64 / notebooks.len() as f64
        };

        Ok(WorkspaceStats {
            total_notes: notes.len(),
            total_notebooks: notebooks.len(),
            total_tags: most_used_tags.len(),
            most_used_tags,
            notes_by_notebook,
            storage_size_bytes,
            largest_notebook,
            average_notes_per_notebook,
        })
    }

    /// Calculate total storage size
    fn calculate_storage_size(&self) -> Result<u64> {
        let mut total_size = 0u64;

        for entry in walkdir::WalkDir::new(&self.notes_dir)
            .into_iter()
            .filter_map(|e| e.ok())
        {
            let path = entry.path();
            if path.is_file() {
                if let Ok(metadata) = fs::metadata(path) {
                    total_size += metadata.len();
                }
            }
        }

        Ok(total_size)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn test_storage_initialization() {
        let temp_dir = TempDir::new().unwrap();
        let storage = Storage::new(temp_dir.path().to_path_buf()).unwrap();
        assert!(storage.initialize().is_ok());
    }

    #[test]
    fn test_save_and_load_note() {
        let temp_dir = TempDir::new().unwrap();
        let mut storage = Storage::new(temp_dir.path().to_path_buf()).unwrap();

        let mut note = Note::new("Test Note".to_string(), "Test content".to_string());
        assert!(storage.save_note(&mut note).is_ok());

        let loaded = storage.load_note(&note.id).unwrap();
        assert_eq!(loaded.title, "Test Note");
        assert_eq!(loaded.content, "Test content");
    }

    #[test]
    fn test_delete_note() {
        let temp_dir = TempDir::new().unwrap();
        let mut storage = Storage::new(temp_dir.path().to_path_buf()).unwrap();

        let mut note = Note::new("Test Note".to_string(), "Test content".to_string());
        storage.save_note(&mut note).unwrap();

        assert!(storage.delete_note(&note.id).is_ok());
        assert!(storage.load_note(&note.id).is_err());
    }
}
