use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::path::PathBuf;

/// Represents a single note in the knowledge graph
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct Note {
    /// Unique identifier (filename without extension)
    pub id: String,
    /// Title of the note
    pub title: String,
    /// Content of the note (markdown format)
    pub content: String,
    /// When the note was created
    pub created_at: DateTime<Utc>,
    /// When the note was last modified
    pub modified_at: DateTime<Utc>,
    /// Tags associated with the note
    pub tags: Vec<String>,
}

impl Note {
    /// Create a new note with the given title and content
    pub fn new(title: String, content: String) -> Self {
        let now = Utc::now();
        let id = Self::sanitize_title(&title);
        Note {
            id,
            title,
            content,
            created_at: now,
            modified_at: now,
            tags: Vec::new(),
        }
    }

    /// Sanitize title to create a valid filename/ID
    fn sanitize_title(title: &str) -> String {
        title
            .to_lowercase()
            .chars()
            .map(|c| {
                if c.is_alphanumeric() || c == '-' || c == '_' {
                    c
                } else if c.is_whitespace() {
                    '-'
                } else {
                    '_'
                }
            })
            .collect::<String>()
            .trim_matches('-')
            .to_string()
    }

    /// Update the content of the note
    pub fn update_content(&mut self, content: String) {
        self.content = content;
        self.modified_at = Utc::now();
    }

    /// Add a tag to the note
    pub fn add_tag(&mut self, tag: String) {
        if !self.tags.contains(&tag) {
            self.tags.push(tag);
        }
    }
}

/// Represents a link from one note to another
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub struct Link {
    /// The note that contains the link
    pub from: String,
    /// The note being linked to
    pub to: String,
    /// The context/text around the link
    pub context: Option<String>,
}

impl Link {
    pub fn new(from: String, to: String, context: Option<String>) -> Self {
        Link { from, to, context }
    }
}

/// The knowledge graph containing all notes and their relationships
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KnowledgeGraph {
    /// All notes indexed by ID
    pub notes: HashMap<String, Note>,
    /// Forward links: note -> notes it links to
    pub forward_links: HashMap<String, Vec<String>>,
    /// Backward links: note -> notes that link to it
    pub backward_links: HashMap<String, Vec<String>>,
}

impl Default for KnowledgeGraph {
    fn default() -> Self {
        Self::new()
    }
}

impl KnowledgeGraph {
    /// Create a new empty knowledge graph
    pub fn new() -> Self {
        KnowledgeGraph {
            notes: HashMap::new(),
            forward_links: HashMap::new(),
            backward_links: HashMap::new(),
        }
    }

    /// Add a note to the graph
    pub fn add_note(&mut self, note: Note) {
        let id = note.id.clone();
        self.notes.insert(id.clone(), note);
        // Initialize empty link vectors for the new note
        self.forward_links.entry(id.clone()).or_insert_with(Vec::new);
        self.backward_links.entry(id).or_insert_with(Vec::new);
    }

    /// Remove a note from the graph
    pub fn remove_note(&mut self, id: &str) -> Option<Note> {
        let note = self.notes.remove(id)?;
        // Remove all links to and from this note
        self.forward_links.remove(id);
        self.backward_links.remove(id);

        // Clean up links from other notes
        for links in self.forward_links.values_mut() {
            links.retain(|target| target != id);
        }
        for links in self.backward_links.values_mut() {
            links.retain(|source| source != id);
        }

        Some(note)
    }

    /// Get a note by ID
    pub fn get_note(&self, id: &str) -> Option<&Note> {
        self.notes.get(id)
    }

    /// Get all note IDs
    pub fn note_ids(&self) -> Vec<String> {
        self.notes.keys().cloned().collect()
    }

    /// Get forward links for a note
    pub fn get_forward_links(&self, id: &str) -> Vec<String> {
        self.forward_links.get(id).cloned().unwrap_or_default()
    }

    /// Get backward links for a note
    pub fn get_backward_links(&self, id: &str) -> Vec<String> {
        self.backward_links.get(id).cloned().unwrap_or_default()
    }

    /// Add a forward link
    pub fn add_forward_link(&mut self, from: String, to: String) {
        self.forward_links
            .entry(from.clone())
            .or_insert_with(Vec::new)
            .push(to.clone());
        self.backward_links
            .entry(to)
            .or_insert_with(Vec::new)
            .push(from);
    }

    /// Rebuild all links from note contents
    pub fn rebuild_links(&mut self) {
        // Clear existing links
        self.forward_links.clear();
        self.backward_links.clear();

        // Initialize empty vectors for all notes
        for id in self.notes.keys() {
            self.forward_links.insert(id.clone(), Vec::new());
            self.backward_links.insert(id.clone(), Vec::new());
        }

        // Extract links from each note
        for (id, note) in &self.notes {
            let linked_ids = crate::linking::extract_links(&note.content);
            for linked_id in linked_ids {
                // Only add links to existing notes
                if self.notes.contains_key(&linked_id) {
                    self.add_forward_link(id.clone(), linked_id);
                }
            }
        }
    }

    /// Get graph statistics
    pub fn statistics(&self) -> GraphStatistics {
        let total_links: usize = self.forward_links.values().map(|v| v.len()).sum();
        let orphaned_notes: Vec<String> = self
            .notes
            .iter()
            .filter(|(id, _)| {
                self.forward_links.get(*id).map_or(true, |v| v.is_empty())
                    && self.backward_links.get(*id).map_or(true, |v| v.is_empty())
            })
            .map(|(id, _)| id.clone())
            .collect();

        GraphStatistics {
            note_count: self.notes.len(),
            link_count: total_links,
            orphaned_count: orphaned_notes.len(),
            most_connected: self.find_most_connected(),
        }
    }

    /// Find the most connected notes
    fn find_most_connected(&self) -> Vec<(String, usize)> {
        let mut connections: Vec<(String, usize)> = self
            .notes
            .keys()
            .map(|id| {
                let forward = self.forward_links.get(id).map_or(0, |v| v.len());
                let backward = self.backward_links.get(id).map_or(0, |v| v.len());
                (id.clone(), forward + backward)
            })
            .collect();

        connections.sort_by(|a, b| b.1.cmp(&a.1));
        connections.into_iter().take(10).collect()
    }
}

/// Statistics about the knowledge graph
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GraphStatistics {
    pub note_count: usize,
    pub link_count: usize,
    pub orphaned_count: usize,
    pub most_connected: Vec<(String, usize)>,
}

/// Search result with relevance score
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchResult {
    pub note_id: String,
    pub title: String,
    pub score: f64,
    pub matched_lines: Vec<String>,
}

impl SearchResult {
    pub fn new(note_id: String, title: String, score: f64, matched_lines: Vec<String>) -> Self {
        SearchResult {
            note_id,
            title,
            score,
            matched_lines,
        }
    }
}
