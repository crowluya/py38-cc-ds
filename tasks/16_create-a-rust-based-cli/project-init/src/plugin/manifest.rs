//! Plugin manifest and metadata
//!
//! Defines the structure for plugin metadata including version, capabilities,
//! and dependencies.

use serde::{Deserialize, Serialize};
use std::collections::HashSet;
use std::path::Path;
use crate::plugin::error::{PluginError, PluginResult};

/// Current plugin ABI version
///
/// This must be incremented when breaking changes are made to the plugin API.
/// Plugins with mismatched ABI versions will not be loaded.
pub const PLUGIN_ABI_VERSION: u32 = 1;

/// Plugin manifest containing metadata and configuration
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct PluginManifest {
    /// Unique plugin identifier (e.g., "author.plugin-name")
    pub id: String,

    /// Human-readable plugin name
    pub name: String,

    /// Plugin description
    pub description: String,

    /// Plugin version (semver)
    pub version: String,

    /// Minimum required project-init version
    #[serde(default)]
    pub min_cli_version: Option<String>,

    /// Plugin author
    pub author: String,

    /// Plugin license
    pub license: String,

    /// Plugin homepage URL
    #[serde(default)]
    pub homepage: Option<String>,

    /// Plugin repository URL
    #[serde(default)]
    pub repository: Option<String>,

    /// Plugin capabilities
    #[serde(default)]
    pub capabilities: Vec<Capability>,

    /// Plugin dependencies
    #[serde(default)]
    pub dependencies: Vec<PluginDependency>,

    /// ABI version this plugin was built for
    #[serde(default = "default_abi_version")]
    pub abi_version: u32,
}

fn default_abi_version() -> u32 {
    PLUGIN_ABI_VERSION
}

/// Plugin capabilities (permissions)
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub enum Capability {
    /// Plugin can read files from the filesystem
    #[serde(rename = "fs_read")]
    FsRead,

    /// Plugin can write files to the filesystem
    #[serde(rename = "fs_write")]
    FsWrite,

    /// Plugin can make network requests
    #[serde(rename = "network")]
    Network,

    /// Plugin can execute external commands
    #[serde(rename = "execute")]
    Execute,

    /// Plugin can modify environment variables
    #[serde(rename = "env")]
    Environment,

    /// Plugin can access git operations
    #[serde(rename = "git")]
    Git,
}

impl Capability {
    /// Parse a capability from string
    pub fn from_str(s: &str) -> Option<Self> {
        match s {
            "fs_read" => Some(Capability::FsRead),
            "fs_write" => Some(Capability::FsWrite),
            "network" => Some(Capability::Network),
            "execute" => Some(Capability::Execute),
            "env" => Some(Capability::Environment),
            "git" => Some(Capability::Git),
            _ => None,
        }
    }

    /// Convert capability to string
    pub fn to_string(&self) -> String {
        match self {
            Capability::FsRead => "fs_read".to_string(),
            Capability::FsWrite => "fs_write".to_string(),
            Capability::Network => "network".to_string(),
            Capability::Execute => "execute".to_string(),
            Capability::Environment => "env".to_string(),
            Capability::Git => "git".to_string(),
        }
    }

    /// Check if this capability is considered risky
    pub fn is_risky(&self) -> bool {
        matches!(self, Capability::FsWrite | Capability::Network | Capability::Execute)
    }

    /// Get all capabilities as a set
    pub fn all() -> HashSet<Capability> {
        vec![
            Capability::FsRead,
            Capability::FsWrite,
            Capability::Network,
            Capability::Execute,
            Capability::Environment,
            Capability::Git,
        ]
        .into_iter()
        .collect()
    }
}

/// Plugin dependency specification
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct PluginDependency {
    /// Plugin ID that is required
    pub id: String,

    /// Minimum required version (semver requirement)
    #[serde(default)]
    pub version_requirement: Option<String>,

    /// Whether this dependency is optional
    #[serde(default)]
    pub optional: bool,
}

impl PluginManifest {
    /// Validate the manifest
    pub fn validate(&self) -> PluginResult<()> {
        // Check required fields
        if self.id.is_empty() {
            return Err(PluginError::InvalidManifest("Plugin ID cannot be empty".into()));
        }

        if self.name.is_empty() {
            return Err(PluginError::InvalidManifest("Plugin name cannot be empty".into()));
        }

        if self.version.is_empty() {
            return Err(PluginError::InvalidManifest("Plugin version cannot be empty".into()));
        }

        // Validate ABI version
        if self.abi_version != PLUGIN_ABI_VERSION {
            return Err(PluginError::AbiVersionMismatch(
                PLUGIN_ABI_VERSION,
                self.abi_version,
            ));
        }

        // Validate semantic version
        if semver::Version::parse(&self.version).is_err() {
            return Err(PluginError::InvalidManifest(format!(
                "Invalid semantic version: {}",
                self.version
            )));
        }

        // Validate plugin ID format (should be reverse domain notation)
        if !self.id.contains('.') {
            return Err(PluginError::InvalidManifest(
                "Plugin ID should use reverse domain notation (e.g., 'author.plugin-name')".into(),
            ));
        }

        Ok(())
    }

    /// Check if plugin has a specific capability
    pub fn has_capability(&self, capability: &Capability) -> bool {
        self.capabilities.contains(capability)
    }

    /// Get risky capabilities
    pub fn risky_capabilities(&self) -> Vec<&Capability> {
        self.capabilities
            .iter()
            .filter(|c| c.is_risky())
            .collect()
    }

    /// Check if plugin requires any permissions
    pub fn requires_permissions(&self) -> bool {
        !self.capabilities.is_empty()
    }

    /// Parse manifest from JSON string
    pub fn from_json(json: &str) -> PluginResult<Self> {
        let manifest: PluginManifest = serde_json::from_str(json)?;
        manifest.validate()?;
        Ok(manifest)
    }

    /// Parse manifest from YAML string
    pub fn from_yaml(yaml: &str) -> PluginResult<Self> {
        let manifest: PluginManifest = serde_yaml::from_str(yaml)?;
        manifest.validate()?;
        Ok(manifest)
    }

    /// Convert manifest to JSON string
    pub fn to_json(&self) -> PluginResult<String> {
        Ok(serde_json::to_string_pretty(self)?)
    }

    /// Convert manifest to YAML string
    pub fn to_yaml(&self) -> PluginResult<String> {
        Ok(serde_yaml::to_string(self)?)
    }

    /// Load manifest from a file
    pub fn load_from_file(path: &Path) -> PluginResult<Self> {
        let content = std::fs::read_to_string(path)?;

        // Try JSON first, then YAML
        if path.extension().map_or(false, |ext| ext == "json") {
            Self::from_json(&content)
        } else if path.extension().map_or(false, |ext| ext == "yaml" || ext == "yml") {
            Self::from_yaml(&content)
        } else {
            // Try to detect from content
            if content.trim_start().starts_with('{') {
                Self::from_json(&content)
            } else {
                Self::from_yaml(&content)
            }
        }
    }

    /// Save manifest to a file
    pub fn save_to_file(&self, path: &Path) -> PluginResult<()> {
        let content = if path.extension().map_or(false, |ext| ext == "json") {
            self.to_json()?
        } else {
            self.to_yaml()?
        };

        std::fs::write(path, content)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn create_test_manifest() -> PluginManifest {
        PluginManifest {
            id: "com.example.test-plugin".to_string(),
            name: "Test Plugin".to_string(),
            description: "A test plugin".to_string(),
            version: "1.0.0".to_string(),
            min_cli_version: Some("0.1.0".to_string()),
            author: "Test Author".to_string(),
            license: "MIT".to_string(),
            homepage: Some("https://example.com".to_string()),
            repository: Some("https://github.com/example/plugin".to_string()),
            capabilities: vec![Capability::FsRead, Capability::FsWrite],
            dependencies: vec![],
            abi_version: PLUGIN_ABI_VERSION,
        }
    }

    #[test]
    fn test_manifest_validation() {
        let manifest = create_test_manifest();
        assert!(manifest.validate().is_ok());
    }

    #[test]
    fn test_manifest_invalid_id() {
        let mut manifest = create_test_manifest();
        manifest.id = "invalid".to_string();
        assert!(manifest.validate().is_err());
    }

    #[test]
    fn test_manifest_abi_mismatch() {
        let mut manifest = create_test_manifest();
        manifest.abi_version = 999;
        let result = manifest.validate();
        assert!(matches!(result, Err(PluginError::AbiVersionMismatch(_, _))));
    }

    #[test]
    fn test_capability_parsing() {
        assert_eq!(Capability::from_str("fs_read"), Some(Capability::FsRead));
        assert_eq!(Capability::from_str("invalid"), None);
    }

    #[test]
    fn test_risky_capabilities() {
        let manifest = PluginManifest {
            capabilities: vec![Capability::FsRead, Capability::Network],
            ..create_test_manifest()
        };

        assert_eq!(manifest.risky_capabilities().len(), 1);
        assert!(manifest.risky_capabilities().contains(&Capability::Network));
    }

    #[test]
    fn test_manifest_serialization() {
        let manifest = create_test_manifest();
        let json = manifest.to_json().unwrap();
        let deserialized = PluginManifest::from_json(&json).unwrap();
        assert_eq!(manifest.id, deserialized.id);
        assert_eq!(manifest.version, deserialized.version);
    }
}
