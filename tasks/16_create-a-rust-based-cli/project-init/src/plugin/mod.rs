//! Plugin system for dynamic template loading
//!
//! This module provides a plugin architecture that allows users to load external
//! template modules at runtime without recompiling the main binary.

pub mod api;
pub mod loader;
pub mod registry;
pub mod manifest;
pub mod error;
pub mod package;

pub use api::{Plugin, TemplateProvider, ScaffoldingHook};
pub use loader::PluginLoader;
pub use registry::{PluginRegistry, global_registry};
pub use manifest::{PluginManifest, Capability};
pub use error::{PluginError, PluginResult};
pub use package::{PluginPackageManager, InstalledPluginInfo};
