//! Dynamic plugin loading infrastructure
//!
//! Handles loading external plugin libraries using libloading, providing
//! a safe interface to dynamically loaded code.

use crate::plugin::api::{Plugin, PluginInterface};
use crate::plugin::error::{PluginError, PluginResult};
use crate::plugin::manifest::PluginManifest;
use libloading::{Library, Symbol};
use std::path::Path;
use std::sync::{Arc, Mutex};
use log::{debug, info, warn};

/// Plugin loader responsible for dynamically loading plugin libraries
pub struct PluginLoader {
    /// Loaded libraries (kept to prevent premature unloading)
    libraries: Vec<Library>,

    /// Loaded plugins with their interfaces
    plugins: Vec<LoadedPlugin>,
}

/// A loaded plugin with its interface and library reference
struct LoadedPlugin {
    /// Plugin interface for calling plugin methods
    interface: PluginInterface,

    /// Mutable plugin instance
    plugin: Arc<Mutex<dyn Plugin>>,

    /// Whether the plugin has been initialized
    initialized: bool,
}

impl PluginLoader {
    /// Create a new plugin loader
    pub fn new() -> Self {
        Self {
            libraries: Vec::new(),
            plugins: Vec::new(),
        }
    }

    /// Load a plugin from a library file
    ///
    /// This loads the dynamic library and extracts the plugin interface.
    /// The plugin is validated but not initialized - you must call
    /// `initialize_plugin()` separately.
    pub fn load_plugin(&mut self, path: &Path) -> PluginResult<String> {
        debug!("Loading plugin from: {}", path.display());

        // Check if file exists
        if !path.exists() {
            return Err(PluginError::load_error(
                path.display().to_string(),
                "File not found",
            ));
        }

        // Load the library
        let library = unsafe {
            Library::new(path)
                .map_err(|e| PluginError::load_error(path.display().to_string(), e.to_string()))?
        };

        // Get the plugin creation function
        // Expected symbol: _plugin_create
        let create: Symbol<unsafe extern "C" fn() -> *mut dyn Plugin> = unsafe {
            library.get(b"_plugin_create")
                .map_err(|_| PluginError::symbol_not_found("_plugin_create"))?
        };

        // Get the plugin ABI version
        // Expected symbol: _plugin_abi_version
        let abi_version: Symbol<unsafe extern "C" fn() -> u32> = unsafe {
            library.get(b"_plugin_abi_version")
                .unwrap_or_else(|_| {
                    // Default to version 0 if symbol not found (old plugin)
                    Symbol::from_raw(library.into_raw().as_ptr() as *const _, b"_plugin_abi_version\0".as_ptr() as *mut _)
                })
        };

        // Check ABI version
        let version = unsafe { abi_version() };
        if version != crate::plugin::manifest::PLUGIN_ABI_VERSION {
            return Err(PluginError::AbiVersionMismatch(
                crate::plugin::manifest::PLUGIN_ABI_VERSION,
                version,
            ));
        }

        // Create the plugin instance
        let plugin_ptr = unsafe { create() };
        if plugin_ptr.is_null() {
            return Err(PluginError::InitializationFailed(
                "Plugin creation returned null pointer".into(),
            ));
        }

        // Convert to a safe reference
        let plugin: Box<dyn Plugin> = unsafe { Box::from_raw(plugin_ptr) };
        let plugin = Arc::new(Mutex::new(plugin));

        // Get the manifest to validate the plugin
        let manifest = {
            let plugin_guard = plugin.lock()
                .map_err(|e| PluginError::Generic(format!("Failed to lock plugin: {}", e)))?;
            plugin_guard.manifest().clone()
        };

        // Validate manifest
        manifest.validate()?;

        // Create the plugin interface
        let plugin_ptr_for_interface = Arc::as_ptr(&plugin) as *mut dyn Plugin;

        let interface = PluginInterface {
            plugin: plugin_ptr_for_interface,
            get_manifest: unsafe { std::mem::transmute(library.get(b"_plugin_get_manifest")?) },
            initialize: unsafe { std::mem::transmute(library.get(b"_plugin_initialize")?) },
            cleanup: unsafe { std::mem::transmute(library.get(b"_plugin_cleanup")?) },
            get_template_provider: unsafe {
                std::mem::transmute(library.get(b"_plugin_get_template_provider").ok())
            },
            get_scaffolding_hook: unsafe {
                std::mem::transmute(library.get(b"_plugin_get_scaffolding_hook").ok())
            },
        };

        // Store the library to prevent it from being unloaded
        self.libraries.push(library);

        // Store the loaded plugin
        let plugin_id = manifest.id.clone();
        self.plugins.push(LoadedPlugin {
            interface,
            plugin,
            initialized: false,
        });

        info!("Successfully loaded plugin: {}", plugin_id);
        Ok(plugin_id)
    }

    /// Initialize a loaded plugin
    ///
    /// This calls the plugin's initialization hook. Should be called
    /// after `load_plugin()`.
    pub fn initialize_plugin(&mut self, plugin_id: &str) -> PluginResult<()> {
        let plugin = self.plugins.iter_mut()
            .find(|p| {
                let manifest = p.plugin.lock().unwrap().manifest();
                manifest.id == plugin_id
            })
            .ok_or_else(|| PluginError::NotFound(plugin_id.to_string()))?;

        if plugin.initialized {
            warn!("Plugin '{}' already initialized", plugin_id);
            return Ok(());
        }

        debug!("Initializing plugin: {}", plugin_id);

        // Call the plugin's initialize method
        {
            let mut plugin_guard = plugin.plugin.lock()
                .map_err(|e| PluginError::Generic(format!("Failed to lock plugin: {}", e)))?;
            plugin_guard.initialize()?;
        }

        plugin.initialized = true;
        info!("Plugin '{}' initialized successfully", plugin_id);
        Ok(())
    }

    /// Unload all plugins
    ///
    /// Calls cleanup on all plugins and releases resources.
    pub fn unload_all(&mut self) -> PluginResult<()> {
        debug!("Unloading all plugins");

        for plugin in &mut self.plugins {
            if plugin.initialized {
                // Call cleanup
                if let Err(e) = {
                    let mut plugin_guard = plugin.plugin.lock()
                        .map_err(|e| PluginError::Generic(format!("Failed to lock plugin: {}", e)))?;
                    plugin_guard.cleanup()
                } {
                    warn!("Plugin cleanup failed: {}", e);
                }
            }
        }

        // Clear plugins and libraries
        // Libraries will be dropped here, unloading them
        self.plugins.clear();
        self.libraries.clear();

        debug!("All plugins unloaded");
        Ok(())
    }

    /// Get a plugin by ID
    pub fn get_plugin(&self, plugin_id: &str) -> PluginResult<Arc<Mutex<dyn Plugin>>> {
        self.plugins.iter()
            .find(|p| {
                let manifest = p.plugin.lock().unwrap().manifest();
                manifest.id == plugin_id
            })
            .map(|p| p.plugin.clone())
            .ok_or_else(|| PluginError::NotFound(plugin_id.to_string()))
    }

    /// Get all loaded plugin IDs
    pub fn plugin_ids(&self) -> Vec<String> {
        self.plugins.iter()
            .map(|p| {
                let manifest = p.plugin.lock().unwrap().manifest();
                manifest.id.clone()
            })
            .collect()
    }

    /// Get manifests of all loaded plugins
    pub fn manifests(&self) -> Vec<PluginManifest> {
        self.plugins.iter()
            .map(|p| {
                let manifest = p.plugin.lock().unwrap().manifest();
                manifest.clone()
            })
            .collect()
    }

    /// Check if a plugin is loaded
    pub fn is_loaded(&self, plugin_id: &str) -> bool {
        self.plugins.iter()
            .any(|p| {
                let manifest = p.plugin.lock().unwrap().manifest();
                manifest.id == plugin_id
            })
    }

    /// Get the number of loaded plugins
    pub fn count(&self) -> usize {
        self.plugins.len()
    }
}

impl Default for PluginLoader {
    fn default() -> Self {
        Self::new()
    }
}

// Safety: The plugin interface is Send and Sync
unsafe impl Send for PluginLoader {}
unsafe impl Sync for PluginLoader {}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::TempDir;

    #[test]
    fn test_plugin_loader_creation() {
        let loader = PluginLoader::new();
        assert_eq!(loader.count(), 0);
        assert!(loader.plugin_ids().is_empty());
    }

    #[test]
    fn test_plugin_loader_default() {
        let loader = PluginLoader::default();
        assert_eq!(loader.count(), 0);
    }

    #[test]
    fn test_load_nonexistent_plugin() {
        let mut loader = PluginLoader::new();
        let result = loader.load_plugin(Path::new("/nonexistent/plugin.so"));
        assert!(result.is_err());
    }

    #[test]
    fn test_unload_all_empty() {
        let mut loader = PluginLoader::new();
        assert!(loader.unload_all().is_ok());
    }

    #[test]
    fn test_get_nonexistent_plugin() {
        let loader = PluginLoader::new();
        let result = loader.get_plugin("nonexistent");
        assert!(result.is_err());
    }
}
