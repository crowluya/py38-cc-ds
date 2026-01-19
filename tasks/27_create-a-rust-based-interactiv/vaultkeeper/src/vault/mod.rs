use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};
use uuid::Uuid;
use zeroize::{Zeroize, ZeroizeOnDrop};

/// Represents a single password vault entry
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct VaultEntry {
    pub id: String,
    pub title: String,
    pub username: String,
    #[serde(skip_serializing)]
    pub password: SecretString,
    pub url: Option<String>,
    pub notes: Option<String>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    pub tags: Vec<String>,
}

/// Secure string wrapper that zeroizes on drop
#[derive(Clone, Serialize, Deserialize)]
#[serde(from = "String", into = "String")]
pub struct SecretString {
    inner: String,
}

impl SecretString {
    pub fn new(s: String) -> Self {
        Self { inner: s }
    }

    pub fn as_str(&self) -> &str {
        &self.inner
    }

    pub fn into_string(self) -> String {
        self.inner
    }
}

impl From<String> for SecretString {
    fn from(s: String) -> Self {
        Self::new(s)
    }
}

impl From<SecretString> for String {
    fn from(s: SecretString) -> String {
        s.inner
    }
}

impl Drop for SecretString {
    fn drop(&mut self) {
        self.inner.zeroize();
    }
}

impl ZeroizeOnDrop for SecretString {}

impl VaultEntry {
    pub fn new(title: String, username: String, password: String) -> Self {
        let now = Utc::now();
        Self {
            id: Uuid::new_v4().to_string(),
            title,
            username,
            password: SecretString::new(password),
            url: None,
            notes: None,
            created_at: now,
            updated_at: now,
            tags: Vec::new(),
        }
    }

    pub fn with_url(mut self, url: String) -> Self {
        self.url = Some(url);
        self.updated_at = Utc::now();
        self
    }

    pub fn with_notes(mut self, notes: String) -> Self {
        self.notes = Some(notes);
        self.updated_at = Utc::now();
        self
    }

    pub fn with_tags(mut self, tags: Vec<String>) -> Self {
        self.tags = tags;
        self.updated_at = Utc::now();
        self
    }

    pub fn update_password(&mut self, new_password: String) {
        self.password = SecretString::new(new_password);
        self.updated_at = Utc::now();
    }
}

/// Represents the entire password vault
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Vault {
    pub version: u32,
    pub entries: Vec<VaultEntry>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    pub metadata: VaultMetadata,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VaultMetadata {
    pub master_password_hint: Option<String>,
    pub iteration_count: u32,
    pub memory_limit: u32,
}

impl Default for Vault {
    fn default() -> Self {
        let now = Utc::now();
        Self {
            version: 1,
            entries: Vec::new(),
            created_at: now,
            updated_at: now,
            metadata: VaultMetadata {
                master_password_hint: None,
                iteration_count: 100_000,
                memory_limit: 64 * 1024, // 64 MB
            },
        }
    }
}

impl Vault {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn add_entry(&mut self, entry: VaultEntry) {
        self.entries.push(entry);
        self.updated_at = Utc::now();
    }

    pub fn remove_entry(&mut self, id: &str) -> Option<VaultEntry> {
        if let Some(pos) = self.entries.iter().position(|e| e.id == id) {
            self.updated_at = Utc::now();
            Some(self.entries.remove(pos))
        } else {
            None
        }
    }

    pub fn get_entry(&self, id: &str) -> Option<&VaultEntry> {
        self.entries.iter().find(|e| e.id == id)
    }

    pub fn update_entry<F>(&mut self, id: &str, updater: F) -> bool
    where
        F: FnOnce(&mut VaultEntry),
    {
        if let Some(entry) = self.entries.iter_mut().find(|e| e.id == id) {
            updater(entry);
            entry.updated_at = Utc::now();
            self.updated_at = Utc::now();
            true
        } else {
            false
        }
    }

    pub fn search_entries(&self, query: &str) -> Vec<&VaultEntry> {
        let query_lower = query.to_lowercase();
        self.entries
            .iter()
            .filter(|entry| {
                entry.title.to_lowercase().contains(&query_lower)
                    || entry.username.to_lowercase().contains(&query_lower)
                    || entry.url.as_ref().map_or(false, |url| {
                        url.to_lowercase().contains(&query_lower)
                    })
                    || entry.tags.iter().any(|tag| tag.to_lowercase().contains(&query_lower))
            })
            .collect()
    }

    pub fn entry_count(&self) -> usize {
        self.entries.len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_vault_entry_creation() {
        let entry = VaultEntry::new("Test".to_string(), "user".to_string(), "pass".to_string());
        assert_eq!(entry.title, "Test");
        assert_eq!(entry.username, "user");
        assert_eq!(entry.password.as_str(), "pass");
    }

    #[test]
    fn test_vault_add_remove() {
        let mut vault = Vault::new();
        let entry = VaultEntry::new("Test".to_string(), "user".to_string(), "pass".to_string());
        let id = entry.id.clone();

        vault.add_entry(entry);
        assert_eq!(vault.entry_count(), 1);

        let removed = vault.remove_entry(&id);
        assert!(removed.is_some());
        assert_eq!(vault.entry_count(), 0);
    }

    #[test]
    fn test_vault_search() {
        let mut vault = Vault::new();
        vault.add_entry(VaultEntry::new(
            "GitHub".to_string(),
            "user1".to_string(),
            "pass1".to_string(),
        ));
        vault.add_entry(VaultEntry::new(
            "GitLab".to_string(),
            "user2".to_string(),
            "pass2".to_string(),
        ));

        let results = vault.search_entries("git");
        assert_eq!(results.len(), 2);

        let results = vault.search_entries("github");
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].title, "GitHub");
    }

    #[test]
    fn test_secret_string_zeroize() {
        // This test just ensures SecretString compiles and works
        let secret = SecretString::new("password".to_string());
        assert_eq!(secret.as_str(), "password");
        // When dropped, it should zeroize
    }
}
