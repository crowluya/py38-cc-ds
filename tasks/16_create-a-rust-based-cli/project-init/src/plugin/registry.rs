//! Plugin registry and discovery system
//!
//! Manages plugin discovery, loading, and provides a centralized interface
//! for accessing loaded plugins.

use crate::plugin::api::{Plugin, TemplateProvider};
use crate::plugin::error::{PluginError, PluginResult};
use crate::plugin::loader::PluginLoader;
use crate::plugin::manifest::PluginManifest;
use crate::templates::Template;
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex, RwLock};
use log::{debug, info, warn};

use crate::plugin::api::ScaffoldingHook;
use std::sync::Mutex as StdMutex;

/// Global plugin registry
///
/// This singleton manages all loaded plugins and provides discovery
/// and access to plugin functionality.
pub struct PluginRegistry {
    /// Plugin loader for dynamic loading
    loader: Mutex<PluginLoader>,

    /// Plugin directories to scan for plugins
    plugin_dirs: RwLock<Vec<PathBuf>>,

    /// Cache of plugin manifests by ID
    manifests: RwLock<HashMap<String, PluginManifest>>,

    /// Template provider index (template name -> plugin ID)
    template_index: RwLock<HashMap<String, String>>,
}

impl PluginRegistry {
    /// Create a new plugin registry
    pub fn new() -> Self {
        let registry = Self {
            loader: Mutex::new(PluginLoader::new()),
            plugin_dirs: RwLock::new(Vec::new()),
            manifests: RwLock::new(HashMap::new()),
            template_index: RwLock::new(HashMap::new()),
        };

        // Initialize default plugin directories
        registry.init_default_dirs();

        registry
    }

    /// Initialize default plugin directories
    fn init_default_dirs(&self) {
        let mut dirs = self.plugin_dirs.write().unwrap();

        // User-local plugin directory
        if let Some(home) = dirs::home_dir() {
            let user_plugins = home.join(".project-init").join("plugins");
            dirs.push(user_plugins);
        }

        // System-wide plugin directory (Unix)
        #[cfg(unix)]
        {
            dirs.push(PathBuf::from("/usr/local/lib/project-init/plugins"));
        }

        // System-wide plugin directory (Windows)
        #[cfg(windows)]
        {
            if let Some(app_data) = std::env::var_os("LOCALAPPDATA") {
                let system_plugins = PathBuf::from(app_data).join("project-init").join("plugins");
                dirs.push(system_plugins);
            }
        }
    }

    /// Add a plugin directory to scan
    pub fn add_plugin_dir(&self, path: PathBuf) -> PluginResult<()> {
        if !path.exists() {
            fs::create_dir_all(&path)?;
        }

        let mut dirs = self.plugin_dirs.write().unwrap();
        if !dirs.contains(&path) {
            dirs.push(path);
            info!("Added plugin directory: {}", path.display());
        }

        Ok(())
    }

    /// Discover and load all plugins from registered directories
    pub fn discover_and_load(&self) -> PluginResult<usize> {
        let mut loaded_count = 0;
        let dirs = self.plugin_dirs.read().unwrap();

        for dir in dirs.iter() {
            match self.discover_in_directory(dir) {
                Ok(count) => loaded_count += count,
                Err(e) => {
                    warn!("Failed to discover plugins in {}: {}", dir.display(), e);
                }
            }
        }

        info!("Discovered and loaded {} plugins", loaded_count);
        Ok(loaded_count)
    }

    /// Discover and load plugins from a specific directory
    fn discover_in_directory(&self, dir: &Path) -> PluginResult<usize> {
        if !dir.exists() {
            return Ok(0);
        }

        debug!("Scanning directory for plugins: {}", dir.display());

        let mut loaded_count = 0;
        let extensions = self.get_library_extensions();

        for entry in fs::read_dir(dir)? {
            let entry = entry?;
            let path = entry.path();

            // Skip directories
            if path.is_dir() {
                continue;
            }

            // Check if file has a valid library extension
            let extension = path.extension().and_then(|e| e.to_str());
            if extension.map_or(false, |e| extensions.contains(&e.to_string())) {
                match self.load_plugin_from_path(&path) {
                    Ok(plugin_id) => {
                        info!("Loaded plugin: {}", plugin_id);
                        loaded_count += 1;
                    }
                    Err(e) => {
                        warn!("Failed to load plugin from {}: {}", path.display(), e);
                    }
                }
            }
        }

        Ok(loaded_count)
    }

    /// Get platform-specific library extensions
    fn get_library_extensions(&self) -> Vec<String> {
        let mut extensions = Vec::new();

        #[cfg(target_os = "linux")]
        {
            extensions.push("so".to_string());
        }

        #[cfg(target_os = "macos")]
        {
            extensions.push("dylib".to_string());
            extensions.push("so".to_string());
        }

        #[cfg(target_os = "windows")]
        {
            extensions.push("dll".to_string());
        }

        extensions
    }

    /// Load a plugin from a specific file path
    pub fn load_plugin_from_path(&self, path: &Path) -> PluginResult<String> {
        let mut loader = self.loader.lock().unwrap();
        let plugin_id = loader.load_plugin(path)?;

        // Initialize the plugin
        loader.initialize_plugin(&plugin_id)?;

        // Index the plugin
        self.index_plugin(&plugin_id)?;

        Ok(plugin_id)
    }

    /// Index a plugin's templates and capabilities
    fn index_plugin(&self, plugin_id: &str) -> PluginResult<()> {
        let plugin = self.get_plugin(plugin_id)?;

        // Store manifest
        {
            let plugin_guard = plugin.lock()
                .map_err(|e| PluginError::Generic(format!("Failed to lock plugin: {}", e)))?;
            let manifest = plugin_guard.manifest().clone();

            let mut manifests = self.manifests.write().unwrap();
            manifests.insert(manifest.id.clone(), manifest);
        }

        // Index templates
        let plugin = self.get_plugin(plugin_id)?;
        if let Some(provider) = {
            let plugin_guard = plugin.lock()
                .map_err(|e| PluginError::Generic(format!("Failed to lock plugin: {}", e)))?;
            plugin_guard.as_template_provider().map(|p| p as *const dyn TemplateProvider)
        } {
            // Note: We're storing raw pointers here for simplicity
            // In production, you'd want a safer approach
            let plugin_guard = plugin.lock()
                .map_err(|e| PluginError::Generic(format!("Failed to lock plugin: {}", e)))?;

            if let Some(provider) = plugin_guard.as_template_provider() {
                let mut index = self.template_index.write().unwrap();
                for template_name in provider.template_names() {
                    index.insert(template_name, plugin_id.to_string());
                }
            }
        }

        Ok(())
    }

    /// Get a plugin by ID
    pub fn get_plugin(&self, plugin_id: &str) -> PluginResult<Arc<StdMutex<dyn Plugin>>> {
        let loader = self.loader.lock().unwrap();
        loader.get_plugin(plugin_id)
    }

    /// Get all loaded plugin IDs
    pub fn plugin_ids(&self) -> Vec<String> {
        let loader = self.loader.lock().unwrap();
        loader.plugin_ids()
    }

    /// Get all plugin manifests
    pub fn manifests(&self) -> Vec<PluginManifest> {
        let manifests = self.manifests.read().unwrap();
        manifests.values().cloned().collect()
    }

    /// Get manifest for a specific plugin
    pub fn get_manifest(&self, plugin_id: &str) -> PluginResult<PluginManifest> {
        let manifests = self.manifests.read().unwrap();
        manifests.get(plugin_id)
            .cloned()
            .ok_or_else(|| PluginError::NotFound(plugin_id.to_string()))
    }

    /// Check if a plugin is loaded
    pub fn is_loaded(&self, plugin_id: &str) -> bool {
        let loader = self.loader.lock().unwrap();
        loader.is_loaded(plugin_id)
    }

    /// Find which plugin provides a template
    pub fn find_template_provider(&self, template_name: &str) -> PluginResult<Option<String>> {
        let index = self.template_index.read().unwrap();
        Ok(index.get(template_name).cloned())
    }

    /// Load a template from any plugin
    pub fn load_template(&self, template_name: &str) -> PluginResult<Template> {
        let plugin_id = self.find_template_provider(template_name)?
            .ok_or_else(|| PluginError::TemplateNotFound(
                template_name.to_string(),
                "no provider".to_string(),
            ))?;

        let plugin = self.get_plugin(&plugin_id)?;
        let plugin_guard = plugin.lock()
            .map_err(|e| PluginError::Generic(format!("Failed to lock plugin: {}", e)))?;

        let provider = plugin_guard.as_template_provider()
            .ok_or_else(|| PluginError::TemplateNotFound(
                template_name.to_string(),
                plugin_id.clone(),
            ))?;

        provider.load_template(template_name)?
            .ok_or_else(|| PluginError::TemplateNotFound(
                template_name.to_string(),
                plugin_id,
            ))
    }

    /// Get all templates from all plugins
    pub fn all_templates(&self) -> PluginResult<Vec<String>> {
        let index = self.template_index.read().unwrap();
        Ok(index.keys().cloned().collect())
    }

    /// Get the number of loaded plugins
    pub fn count(&self) -> usize {
        let loader = self.loader.lock().unwrap();
        loader.count()
    }

    /// Unload all plugins
    pub fn unload_all(&self) -> PluginResult<()> {
        let mut loader = self.loader.lock().unwrap();
        loader.unload_all()?;

        // Clear indexes
        self.manifests.write().unwrap().clear();
        self.template_index.write().unwrap().clear();

        Ok(())
    }
}

impl Default for PluginRegistry {
    fn default() -> Self {
        Self::new()
    }
}

// Global registry instance
static GLOBAL_REGISTRY: once_cell::sync::Lazy<PluginRegistry> =
    once_cell::sync::Lazy::new(PluginRegistry::new);

/// Get the global plugin registry
pub fn global_registry() -> &'static PluginRegistry {
    &GLOBAL_REGISTRY
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn test_registry_creation() {
        let registry = PluginRegistry::new();
        assert_eq!(registry.count(), 0);
    }

    #[test]
    fn test_add_plugin_dir() {
        let registry = PluginRegistry::new();
        let temp = TempDir::new().unwrap();
        let dir = temp.path().join("plugins");

        assert!(registry.add_plugin_dir(dir.clone()).is_ok());
        assert!(dir.exists());
    }

    #[test]
    fn test_get_nonexistent_plugin() {
        let registry = PluginRegistry::new();
        let result = registry.get_plugin("nonexistent");
        assert!(result.is_err());
    }

    #[test]
    fn test_find_template_provider_empty() {
        let registry = PluginRegistry::new();
        let result = registry.find_template_provider("test");
        assert!(result.is_ok());
        assert!(result.unwrap().is_none());
    }

    #[test]
    fn test_default_registry() {
        let registry = global_registry();
        assert_eq!(registry.count(), 0);
    }
}
