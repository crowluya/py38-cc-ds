use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// Represents a stored credential with all its metadata
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Credential {
    pub id: String,
    pub title: String,
    pub username: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub password: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub url: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub category: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub notes: Option<String>,
    pub created_at: DateTime<Utc>,
    pub modified_at: DateTime<Utc>,
}

impl Credential {
    pub fn new(
        title: String,
        username: String,
        password: String,
    ) -> Self {
        let now = Utc::now();
        Self {
            id: Uuid::new_v4().to_string(),
            title,
            username,
            password: Some(password),
            url: None,
            category: None,
            notes: None,
            created_at: now,
            modified_at: now,
        }
    }

    pub fn with_url(mut self, url: Option<String>) -> Self {
        self.url = url;
        self
    }

    pub fn with_category(mut self, category: Option<String>) -> Self {
        self.category = category;
        self
    }

    pub fn with_notes(mut self, notes: Option<String>) -> Self {
        self.notes = notes;
        self
    }

    /// Updates the modified timestamp
    pub fn touch(&mut self) {
        self.modified_at = Utc::now();
    }
}

/// The vault containing all credentials and metadata
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Vault {
    pub version: u8,
    pub credentials: Vec<Credential>,
    pub metadata: VaultMetadata,
}

impl Vault {
    pub fn new() -> Self {
        Self {
            version: 1,
            credentials: Vec::new(),
            metadata: VaultMetadata::new(),
        }
    }

    pub fn add_credential(&mut self, credential: Credential) {
        self.credentials.push(credential);
        self.metadata.update_modified();
    }

    pub fn get_credential(&self, id: &str) -> Option<&Credential> {
        self.credentials.iter().find(|c| c.id == id)
    }

    pub fn get_credential_mut(&mut self, id: &str) -> Option<&mut Credential> {
        self.credentials.iter_mut().find(|c| c.id == id)
    }

    pub fn update_credential<F>(&mut self, id: &str, updater: F) -> Result<(), String>
    where
        F: FnOnce(&mut Credential),
    {
        if let Some(cred) = self.get_credential_mut(id) {
            updater(cred);
            cred.touch();
            self.metadata.update_modified();
            Ok(())
        } else {
            Err(format!("Credential with id {} not found", id))
        }
    }

    pub fn delete_credential(&mut self, id: &str) -> Result<Credential, String> {
        if let Some(pos) = self.credentials.iter().position(|c| c.id == id) {
            let cred = self.credentials.remove(pos);
            self.metadata.update_modified();
            Ok(cred)
        } else {
            Err(format!("Credential with id {} not found", id))
        }
    }

    pub fn list_credentials(&self, category: Option<&str>) -> Vec<&Credential> {
        match category {
            Some(cat) => self
                .credentials
                .iter()
                .filter(|c| c.category.as_deref() == Some(cat))
                .collect(),
            None => self.credentials.iter().collect(),
        }
    }

    pub fn search_credentials(&self, query: &str) -> Vec<&Credential> {
        let query_lower = query.to_lowercase();
        self.credentials
            .iter()
            .filter(|c| {
                c.title.to_lowercase().contains(&query_lower)
                    || c.username.to_lowercase().contains(&query_lower)
                    || c.url.as_ref().map_or(false, |u| u.to_lowercase().contains(&query_lower))
                    || c.category.as_ref().map_or(false, |cat| cat.to_lowercase().contains(&query_lower))
            })
            .collect()
    }

    pub fn credential_count(&self) -> usize {
        self.credentials.len()
    }

    pub fn categories(&self) -> Vec<String> {
        use std::collections::HashSet;
        let mut categories: HashSet<String> = self
            .credentials
            .iter()
            .filter_map(|c| c.category.clone())
            .collect();
        let mut sorted: Vec<String> = categories.into_iter().collect();
        sorted.sort();
        sorted
    }
}

/// Vault metadata
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct VaultMetadata {
    pub created_at: DateTime<Utc>,
    pub modified_at: DateTime<Utc>,
    pub version: u8,
}

impl VaultMetadata {
    pub fn new() -> Self {
        let now = Utc::now();
        Self {
            created_at: now,
            modified_at: now,
            version: 1,
        }
    }

    pub fn update_modified(&mut self) {
        self.modified_at = Utc::now();
    }
}

impl Default for Vault {
    fn default() -> Self {
        Self::new()
    }
}

impl Default for VaultMetadata {
    fn default() -> Self {
        Self::new()
    }
}

/// Vault file header (stored unencrypted for validation)
#[derive(Debug, Clone)]
pub struct VaultHeader {
    pub magic: [u8; 4],
    pub version: u16,
    pub salt: [u8; 32],
    pub nonce: [u8; 12],
}

impl VaultHeader {
    pub const MAGIC_BYTES: [u8; 4] = [b'P', b'W', b'M', b'N'];
    pub const CURRENT_VERSION: u16 = 1;

    pub fn new(salt: [u8; 32], nonce: [u8; 12]) -> Self {
        Self {
            magic: Self::MAGIC_BYTES,
            version: Self::CURRENT_VERSION,
            salt,
            nonce,
        }
    }

    pub fn size() -> usize {
        4 + 2 + 32 + 12 // magic + version + salt + nonce
    }

    pub fn validate(&self) -> bool {
        self.magic == Self::MAGIC_BYTES && self.version == Self::CURRENT_VERSION
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_credential_creation() {
        let cred = Credential::new("Test".to_string(), "user".to_string(), "pass".to_string());
        assert_eq!(cred.title, "Test");
        assert_eq!(cred.username, "user");
        assert_eq!(cred.password, Some("pass".to_string()));
    }

    #[test]
    fn test_vault_operations() {
        let mut vault = Vault::new();
        let cred = Credential::new("Test".to_string(), "user".to_string(), "pass".to_string());

        vault.add_credential(cred.clone());
        assert_eq!(vault.credential_count(), 1);

        let retrieved = vault.get_credential(&cred.id);
        assert!(retrieved.is_some());
        assert_eq!(retrieved.unwrap().title, "Test");

        let deleted = vault.delete_credential(&cred.id);
        assert!(deleted.is_ok());
        assert_eq!(vault.credential_count(), 0);
    }

    #[test]
    fn test_search_credentials() {
        let mut vault = Vault::new();
        vault.add_credential(
            Credential::new("GitHub".to_string(), "user1".to_string(), "pass1".to_string())
                .with_category(Some("Development".to_string())),
        );
        vault.add_credential(
            Credential::new("Gmail".to_string(), "user2".to_string(), "pass2".to_string())
                .with_category(Some("Email".to_string())),
        );

        let results = vault.search_credentials("git");
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].title, "GitHub");
    }

    #[test]
    fn test_categories() {
        let mut vault = Vault::new();
        vault.add_credential(
            Credential::new("Test1".to_string(), "user1".to_string(), "pass1".to_string())
                .with_category(Some("Dev".to_string())),
        );
        vault.add_credential(
            Credential::new("Test2".to_string(), "user2".to_string(), "pass2".to_string())
                .with_category(Some("Personal".to_string())),
        );
        vault.add_credential(
            Credential::new("Test3".to_string(), "user3".to_string(), "pass3".to_string())
                .with_category(Some("Dev".to_string())),
        );

        let categories = vault.categories();
        assert_eq!(categories.len(), 2);
        assert!(categories.contains(&"Dev".to_string()));
        assert!(categories.contains(&"Personal".to_string()));
    }
}
