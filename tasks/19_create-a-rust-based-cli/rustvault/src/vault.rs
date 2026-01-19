//! Vault data structures and hierarchical organization
//!
//! This module defines the core data models for the password manager vault,
//! including support for folders, entries, and metadata.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Version of the vault format for migration support
const VAULT_VERSION: u32 = 1;

/// Main vault structure containing all data
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Vault {
    pub version: u32,
    pub folders: HashMap<String, Folder>,
    pub metadata: VaultMetadata,
}

impl Vault {
    /// Creates a new empty vault
    pub fn new() -> Self {
        Self {
            version: VAULT_VERSION,
            folders: {
                let mut map = HashMap::new();
                // Create root folder
                map.insert(
                    "".to_string(),
                    Folder {
                        name: String::new(),
                        entries: HashMap::new(),
                        subfolders: vec![],
                        created_at: Utc::now(),
                        updated_at: Utc::now(),
                    },
                );
                map
            },
            metadata: VaultMetadata::default(),
        }
    }

    /// Gets a folder by path (e.g., "" for root, "work/projects")
    pub fn get_folder(&self, path: &str) -> Option<&Folder> {
        self.folders.get(path)
    }

    /// Gets a mutable reference to a folder by path
    pub fn get_folder_mut(&mut self, path: &str) -> Option<&mut Folder> {
        self.folders.get_mut(path)
    }

    /// Creates a new folder at the specified path
    pub fn create_folder(&mut self, path: &str, name: &str) -> Result<()> {
        if self.folders.contains_key(path) {
            return Err(anyhow::anyhow!("Folder already exists: {}", path));
        }

        let folder = Folder {
            name: name.to_string(),
            entries: HashMap::new(),
            subfolders: vec![],
            created_at: Utc::now(),
            updated_at: Utc::now(),
        };

        self.folders.insert(path.to_string(), folder);

        // Update parent folder's subfolders list
        if let Some(parent_path) = parent_path(path) {
            if let Some(parent) = self.get_folder_mut(&parent_path) {
                if !parent.subfolders.contains(&path.to_string()) {
                    parent.subfolders.push(path.to_string());
                }
            }
        }

        self.metadata.updated_at = Utc::now();
        Ok(())
    }

    /// Adds an entry to a folder
    pub fn add_entry(&mut self, folder_path: &str, entry: Entry) -> Result<()> {
        let folder = self
            .get_folder_mut(folder_path)
            .ok_or_else(|| anyhow::anyhow!("Folder not found: {}", folder_path))?;

        let id = entry.id.clone();
        folder.entries.insert(id, entry);
        folder.updated_at = Utc::now();
        self.metadata.updated_at = Utc::now();
        self.metadata.entry_count += 1;

        Ok(())
    }

    /// Gets an entry by folder path and entry ID
    pub fn get_entry(&self, folder_path: &str, entry_id: &str) -> Option<&Entry> {
        self.get_folder(folder_path)?.entries.get(entry_id)
    }

    /// Gets a mutable reference to an entry
    pub fn get_entry_mut(&mut self, folder_path: &str, entry_id: &str) -> Option<&mut Entry> {
        let folder = self.get_folder_mut(folder_path)?;
        folder.updated_at = Utc::now();
        self.metadata.updated_at = Utc::now();
        folder.entries.get_mut(entry_id)
    }

    /// Deletes an entry
    pub fn delete_entry(&mut self, folder_path: &str, entry_id: &str) -> Result<()> {
        let folder = self
            .get_folder_mut(folder_path)
            .ok_or_else(|| anyhow::anyhow!("Folder not found: {}", folder_path))?;

        folder
            .entries
            .remove(entry_id)
            .ok_or_else(|| anyhow::anyhow!("Entry not found: {}", entry_id))?;

        folder.updated_at = Utc::now();
        self.metadata.updated_at = Utc::now();
        self.metadata.entry_count -= 1;

        Ok(())
    }

    /// Searches for entries matching a query
    pub fn search(&self, query: &str) -> Vec<SearchResult> {
        let query_lower = query.to_lowercase();
        let mut results = Vec::new();

        for (folder_path, folder) in &self.folders {
            for entry in folder.entries.values() {
                if entry.matches_query(&query_lower) {
                    results.push(SearchResult {
                        entry: entry.clone(),
                        folder_path: folder_path.clone(),
                    });
                }
            }
        }

        // Sort by relevance (title matches first, then username)
        results.sort_by(|a, b| {
            let a_title = a.entry.title.to_lowercase().starts_with(&query_lower);
            let b_title = b.entry.title.to_lowercase().starts_with(&query_lower);
            b_title.cmp(&a_title)
        });

        results
    }

    /// Lists all entries in a folder
    pub fn list_entries(&self, folder_path: &str) -> Vec<&Entry> {
        self.get_folder(folder_path)
            .map(|folder| folder.entries.values().collect())
            .unwrap_or_default()
    }

    /// Lists all folders
    pub fn list_folders(&self) -> Vec<String> {
        let mut folders: Vec<String> = self.folders.keys().cloned().collect();
        folders.sort();
        folders
    }
}

impl Default for Vault {
    fn default() -> Self {
        Self::new()
    }
}

/// Folder containing entries
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Folder {
    pub name: String,
    pub entries: HashMap<String, Entry>,
    pub subfolders: Vec<String>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// Password entry with all fields
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Entry {
    pub id: String,
    pub title: String,
    pub username: String,
    pub password: String,
    pub url: Option<String>,
    pub notes: Option<String>,
    pub tags: Vec<String>,
    pub totp_secret: Option<String>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    pub custom_fields: HashMap<String, String>,
}

impl Entry {
    /// Creates a new entry
    pub fn new(title: String, username: String, password: String) -> Self {
        let id = generate_id();
        Self {
            id,
            title,
            username,
            password,
            url: None,
            notes: None,
            tags: Vec::new(),
            totp_secret: None,
            created_at: Utc::now(),
            updated_at: Utc::now(),
            custom_fields: HashMap::new(),
        }
    }

    /// Checks if the entry matches a search query
    fn matches_query(&self, query: &str) -> bool {
        self.title.to_lowercase().contains(query)
            || self.username.to_lowercase().contains(query)
            || self.url.as_ref().map_or(false, |u| u.to_lowercase().contains(query))
            || self.tags.iter().any(|t| t.to_lowercase().contains(query))
            || self.notes.as_ref().map_or(false, |n| n.to_lowercase().contains(query))
    }

    /// Updates the entry and sets updated_at timestamp
    pub fn touch(&mut self) {
        self.updated_at = Utc::now();
    }
}

/// Search result including folder context
#[derive(Debug, Clone)]
pub struct SearchResult {
    pub entry: Entry,
    pub folder_path: String,
}

/// Vault metadata
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VaultMetadata {
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    pub entry_count: usize,
    pub version: u32,
}

impl Default for VaultMetadata {
    fn default() -> Self {
        Self {
            created_at: Utc::now(),
            updated_at: Utc::now(),
            entry_count: 0,
            version: VAULT_VERSION,
        }
    }
}

/// Generates a unique ID for entries
fn generate_id() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let timestamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    format!("{:x}", timestamp)
}

/// Gets the parent path from a folder path
fn parent_path(path: &str) -> Option<String> {
    if path.is_empty() {
        return None;
    }

    if let Some(last_slash) = path.rfind('/') {
        Some(path[..last_slash].to_string())
    } else {
        Some("".to_string())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_vault_creation() {
        let vault = Vault::new();
        assert_eq!(vault.version, VAULT_VERSION);
        assert!(vault.folders.contains_key(""));
        assert_eq!(vault.metadata.entry_count, 0);
    }

    #[test]
    fn test_folder_creation() {
        let mut vault = Vault::new();
        vault.create_folder("personal", "Personal").unwrap();
        assert!(vault.folders.contains_key("personal"));
    }

    #[test]
    fn test_entry_operations() {
        let mut vault = Vault::new();
        let entry = Entry::new("Test".to_string(), "user".to_string(), "pass".to_string());

        vault.add_entry("", entry).unwrap();
        assert_eq!(vault.metadata.entry_count, 1);

        let entries = vault.list_entries("");
        assert_eq!(entries.len(), 1);

        let retrieved = vault.get_entry("", &entries[0].id).unwrap();
        assert_eq!(retrieved.title, "Test");
    }

    #[test]
    fn test_search() {
        let mut vault = Vault::new();
        let entry1 = Entry::new("GitHub".to_string(), "user1".to_string(), "pass1".to_string());
        let entry2 = Entry::new("GitLab".to_string(), "user2".to_string(), "pass2".to_string());

        vault.add_entry("", entry1).unwrap();
        vault.add_entry("", entry2).unwrap();

        let results = vault.search("git");
        assert_eq!(results.len(), 2);
    }

    #[test]
    fn test_entry_deletion() {
        let mut vault = Vault::new();
        let entry = Entry::new("Test".to_string(), "user".to_string(), "pass".to_string());

        vault.add_entry("", entry.clone()).unwrap();
        vault.delete_entry("", &entry.id).unwrap();
        assert_eq!(vault.metadata.entry_count, 0);
    }
}
