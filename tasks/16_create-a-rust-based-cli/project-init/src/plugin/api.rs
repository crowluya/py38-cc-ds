//! Core plugin API traits
//!
//! Defines the interfaces that plugins must implement to be compatible with
//! the project-init plugin system.

use crate::templates::{Template, TemplateVariable};
use crate::plugin::manifest::PluginManifest;
use std::collections::HashMap;
use std::path::Path;

/// Main plugin trait that all plugins must implement
///
/// This trait defines the lifecycle and metadata interface for plugins.
/// Plugins are dynamically loaded libraries that can extend project-init's
/// functionality with new templates, scaffolding logic, and custom operations.
pub trait Plugin: Send + Sync {
    /// Returns the plugin's manifest containing metadata
    fn manifest(&self) -> &PluginManifest;

    /// Called when the plugin is first loaded
    ///
    /// Use this for initialization logic that should happen once,
    /// such as registering templates or setting up resources.
    fn initialize(&mut self) -> PluginResult<()> {
        Ok(())
    }

    /// Called when the plugin is about to be unloaded
    ///
    /// Use this for cleanup logic such as releasing resources or
    /// saving state.
    fn cleanup(&mut self) -> PluginResult<()> {
        Ok(())
    }

    /// Returns the template provider if this plugin provides templates
    fn as_template_provider(&self) -> Option<&dyn TemplateProvider> {
        None
    }

    /// Returns the scaffolding hook if this plugin provides custom scaffolding
    fn as_scaffolding_hook(&self) -> Option<&dyn ScaffoldingHook> {
        None
    }

    /// Executes a custom command defined by the plugin
    ///
    /// This allows plugins to add their own CLI subcommands.
    /// The command name and arguments are provided by the user.
    fn execute_command(&self, command: &str, args: &[String]) -> PluginResult<String> {
        Err(crate::plugin::error::PluginError::NotSupported)
    }
}

/// Trait for plugins that provide additional templates
///
/// Template providers can dynamically generate templates or provide
/// templates from external sources (e.g., remote repositories, databases).
pub trait TemplateProvider: Send + Sync {
    /// Returns all template names provided by this plugin
    fn template_names(&self) -> Vec<String>;

    /// Loads a template by name
    ///
    /// Returns None if the template is not provided by this plugin.
    fn load_template(&self, name: &str) -> PluginResult<Option<Template>>;

    /// Checks if a template exists in this provider
    fn has_template(&self, name: &str) -> bool {
        self.template_names().contains(&name.to_string())
    }

    /// Returns metadata for all templates without loading them fully
    fn template_metadata(&self) -> Vec<TemplateMetadata> {
        Vec::new()
    }
}

/// Metadata about a template without loading the full template
#[derive(Clone, Debug)]
pub struct TemplateMetadata {
    pub name: String,
    pub description: String,
    pub language: String,
    pub version: String,
}

/// Trait for plugins that provide custom scaffolding logic
///
/// Scaffolding hooks allow plugins to intercept and customize the
/// project creation process, enabling advanced workflows.
pub trait ScaffoldingHook: Send + Sync {
    /// Called before project creation begins
    ///
    /// Use this to validate preconditions or prepare resources.
    fn before_create(&self, project_name: &str, template_name: &str) -> PluginResult<()> {
        Ok(())
    }

    /// Called after project creation completes
    ///
    /// Use this for post-generation tasks like dependency installation,
    /// additional file generation, or project-specific setup.
    fn after_create(
        &self,
        project_path: &Path,
        project_name: &str,
        template_name: &str,
        variables: &HashMap<String, String>,
    ) -> PluginResult<()>;

    /// Called for each file being generated
    ///
    /// Return modified content to change the file, or None to use default.
    fn transform_file(
        &self,
        file_path: &Path,
        content: &str,
        variables: &HashMap<String, String>,
    ) -> PluginResult<Option<String>> {
        Ok(None)
    }

    /// Called for each directory being created
    ///
    /// Return true to create the directory, false to skip it.
    fn should_create_directory(&self, dir_path: &Path) -> PluginResult<bool> {
        Ok(true)
    }
}

/// C-compatible plugin interface for dynamic loading
///
/// This struct provides a stable ABI for loading plugins across different
/// Rust versions. All plugin libraries must export functions that conform
/// to this interface.
#[repr(C)]
pub struct PluginInterface {
    /// Opaque pointer to the plugin instance
    plugin: *mut dyn Plugin,

    /// Function to get the plugin manifest
    pub get_manifest: unsafe extern "C" fn(*mut dyn Plugin) -> *const PluginManifest,

    /// Function to initialize the plugin
    pub initialize: unsafe extern "C" fn(*mut dyn Plugin) -> PluginResult<()>,

    /// Function to cleanup the plugin
    pub cleanup: unsafe extern "C" fn(*mut dyn Plugin) -> PluginResult<()>,

    /// Function to get the template provider interface
    pub get_template_provider: unsafe extern "C" fn(*mut dyn Plugin) -> Option<*const dyn TemplateProvider>,

    /// Function to get the scaffolding hook interface
    pub get_scaffolding_hook: unsafe extern "C" fn(*mut dyn Plugin) -> Option<*const dyn ScaffoldingHook>,
}

unsafe impl Send for PluginInterface {}
unsafe impl Sync for PluginInterface {}

// Implement Clone for the interface by copying the pointer
// Note: The actual plugin is not cloned, only the interface
impl Clone for PluginInterface {
    fn clone(&self) -> Self {
        Self {
            plugin: self.plugin,
            get_manifest: self.get_manifest,
            initialize: self.initialize,
            cleanup: self.cleanup,
            get_template_provider: self.get_template_provider,
            get_scaffolding_hook: self.get_scaffolding_hook,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_template_metadata() {
        let metadata = TemplateMetadata {
            name: "test".to_string(),
            description: "Test template".to_string(),
            language: "Rust".to_string(),
            version: "1.0.0".to_string(),
        };

        assert_eq!(metadata.name, "test");
        assert_eq!(metadata.description, "Test template");
    }
}
