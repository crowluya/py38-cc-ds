//! Plugin package format and installation
//!
//! Handles plugin packaging, installation, removal, and management.

use crate::plugin::error::{PluginError, PluginResult};
use crate::plugin::manifest::PluginManifest;
use crate::plugin::registry::global_registry;
use std::fs;
use std::path::{Path, PathBuf};
use log::{debug, info, warn};
use dialoguer::{Confirm, theme::ColorfulTheme};

/// Plugin package manager
pub struct PluginPackageManager {
    /// Installation directory for plugins
    install_dir: PathBuf,
}

impl PluginPackageManager {
    /// Create a new plugin package manager
    pub fn new() -> PluginResult<Self> {
        let install_dir = Self::default_install_dir()?;

        // Ensure directory exists
        if !install_dir.exists() {
            fs::create_dir_all(&install_dir)?;
        }

        Ok(Self { install_dir })
    }

    /// Get the default plugin installation directory
    fn default_install_dir() -> PluginResult<PathBuf> {
        if let Some(home) = dirs::home_dir() {
            Ok(home.join(".project-init").join("plugins"))
        } else {
            Err(PluginError::Generic(
                "Could not determine home directory".into(),
            ))
        }
    }

    /// Install a plugin from a local file path
    pub fn install_from_file(&self, source_path: &Path) -> PluginResult<String> {
        if !source_path.exists() {
            return Err(PluginError::NotFound(source_path.display().to_string()));
        }

        info!("Installing plugin from: {}", source_path.display());

        // Load the plugin temporarily to get metadata
        let temp_loader = &mut crate::plugin::loader::PluginLoader::new();
        let plugin_id = temp_loader.load_plugin(source_path)?;

        // Get the manifest
        let plugin = temp_loader.get_plugin(&plugin_id)?;
        let manifest = {
            let guard = plugin.lock()
                .map_err(|e| PluginError::Generic(format!("Failed to lock plugin: {}", e)))?;
            guard.manifest().clone()
        };

        // Check for risky capabilities and prompt user
        if !manifest.risky_capabilities().is_empty() {
            let theme = ColorfulTheme::default();
            let should_install = Confirm::with_theme(&theme)
                .with_prompt(&format!(
                    "Plugin '{}' requires the following potentially risky capabilities:\n{}\n\nInstall anyway?",
                    manifest.name,
                    manifest.risky_capabilities()
                        .iter()
                        .map(|c| format!("  - {}", c.to_string()))
                        .collect::<Vec<_>>()
                        .join("\n")
                ))
                .default(false)
                .interact()?;

            if !should_install {
                return Err(PluginError::PermissionDenied(
                    "User declined permission for risky capabilities".into(),
                ));
            }
        }

        // Check if plugin already exists
        let dest_path = self.install_dir.join(
            source_path.file_name()
                .ok_or_else(|| PluginError::Generic("Invalid plugin file name".into()))?
        );

        if dest_path.exists() {
            return Err(PluginError::AlreadyExists(manifest.id));
        }

        // Copy the plugin file
        fs::copy(source_path, &dest_path)?;

        info!("Plugin '{}' installed successfully", manifest.name);
        Ok(manifest.id)
    }

    /// Install a plugin from a URL
    pub fn install_from_url(&self, url: &str) -> PluginResult<String> {
        info!("Downloading plugin from: {}", url);

        // Download to temporary file
        let temp_dir = tempfile::tempdir()?;
        let filename = url.split('/')
            .last()
            .unwrap_or("plugin.so");

        let temp_path = temp_dir.path().join(filename);

        // Download file
        let response = ureq::get(url)
            .timeout(std::time::Duration::from_secs(30))
            .call()
            .map_err(|e| PluginError::Generic(format!("Failed to download plugin: {}", e)))?;

        let mut file = fs::File::create(&temp_path)?;
        std::io::copy(&mut response.into_reader(), &mut file)?;

        // Install from downloaded file
        let plugin_id = self.install_from_file(&temp_path)?;

        // Clean up temp file
        let _ = fs::remove_file(&temp_path);

        Ok(plugin_id)
    }

    /// Remove an installed plugin
    pub fn remove(&self, plugin_id: &str) -> PluginResult<()> {
        let manifest = global_registry().get_manifest(plugin_id)?;

        // Find the plugin file
        let plugin_file = self.find_plugin_file(plugin_id)?;

        // Prompt for confirmation
        let theme = ColorfulTheme::default();
        let should_remove = Confirm::with_theme(&theme)
            .with_prompt(&format!(
                "Are you sure you want to remove plugin '{}'?",
                manifest.name
            ))
            .default(false)
            .interact()?;

        if !should_remove {
            return Err(PluginError::Generic("Operation cancelled by user".into()));
        }

        // Remove the plugin file
        fs::remove_file(&plugin_file)?;

        info!("Plugin '{}' removed successfully", manifest.name);
        Ok(())
    }

    /// List all installed plugins
    pub fn list_installed(&self) -> PluginResult<Vec<InstalledPluginInfo>> {
        let mut plugins = Vec::new();

        if !self.install_dir.exists() {
            return Ok(plugins);
        }

        for entry in fs::read_dir(&install_dir)? {
            let entry = entry?;
            let path = entry.path();

            if path.is_file() {
                // Try to load plugin metadata
                match self.get_plugin_info(&path) {
                    Ok(info) => plugins.push(info),
                    Err(e) => {
                        warn!("Failed to get plugin info for {:?}: {}", path, e);
                    }
                }
            }
        }

        Ok(plugins)
    }

    /// Get detailed information about an installed plugin
    pub fn get_plugin_info(&self, path: &Path) -> PluginResult<InstalledPluginInfo> {
        // Load plugin temporarily to get metadata
        let temp_loader = &mut crate::plugin::loader::PluginLoader::new();
        let plugin_id = temp_loader.load_plugin(path)?;

        let plugin = temp_loader.get_plugin(&plugin_id)?;
        let manifest = {
            let guard = plugin.lock()
                .map_err(|e| PluginError::Generic(format!("Failed to lock plugin: {}", e)))?;
            guard.manifest().clone()
        };

        Ok(InstalledPluginInfo {
            id: manifest.id.clone(),
            name: manifest.name.clone(),
            description: manifest.description.clone(),
            version: manifest.version.clone(),
            author: manifest.author.clone(),
            path: path.to_path_buf(),
        })
    }

    /// Find the plugin file for a given plugin ID
    fn find_plugin_file(&self, plugin_id: &str) -> PluginResult<PathBuf> {
        for entry in fs::read_dir(&self.install_dir)? {
            let entry = entry?;
            let path = entry.path();

            if path.is_file() {
                // Try to load and check ID
                let temp_loader = &mut crate::plugin::loader::PluginLoader::new();
                if let Ok(id) = temp_loader.load_plugin(&path) {
                    if id == plugin_id {
                        return Ok(path);
                    }
                }
            }
        }

        Err(PluginError::NotFound(plugin_id.to_string()))
    }

    /// Update a plugin from a URL
    pub fn update(&self, plugin_id: &str, url: &str) -> PluginResult<()> {
        info!("Updating plugin: {}", plugin_id);

        // Remove old version
        let plugin_file = self.find_plugin_file(plugin_id)?;
        fs::remove_file(&plugin_file)?;

        // Install new version
        self.install_from_url(url)?;

        info!("Plugin '{}' updated successfully", plugin_id);
        Ok(())
    }

    /// Verify plugin integrity
    pub fn verify(&self, plugin_id: &str) -> PluginResult<bool> {
        let plugin_file = self.find_plugin_file(plugin_id)?;

        // Try to load the plugin
        let temp_loader = &mut crate::plugin::loader::PluginLoader::new();
        let _loaded_id = temp_loader.load_plugin(&plugin_file)?;

        Ok(true)
    }
}

/// Information about an installed plugin
#[derive(Clone, Debug)]
pub struct InstalledPluginInfo {
    pub id: String,
    pub name: String,
    pub description: String,
    pub version: String,
    pub author: String,
    pub path: PathBuf,
}

impl Default for PluginPackageManager {
    fn default() -> Self {
        Self::new().unwrap()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn test_package_manager_creation() {
        let temp = TempDir::new().unwrap();
        let manager = PluginPackageManager::new();
        assert!(manager.install_dir.exists());
    }

    #[test]
    fn test_install_nonexistent() {
        let manager = PluginPackageManager::new();
        let result = manager.install_from_file(Path::new("/nonexistent/plugin.so"));
        assert!(result.is_err());
    }

    #[test]
    fn test_list_empty() {
        let manager = PluginPackageManager::new();
        let plugins = manager.list_installed().unwrap();
        assert!(plugins.is_empty());
    }
}
