mod cli;
mod config;
mod error;
mod storage;
mod types;
mod crypto;
mod password;
mod backup;
mod semantic;

use crate::cli::CliApp;
use crate::config::ConfigManager;
use crate::error::Result;
use crate::storage::Storage;
use std::path::PathBuf;

fn main() -> Result<()> {
    // Load or create configuration
    let config_manager = ConfigManager::new()?;
    let config = config_manager.load_or_create()?;

    // Initialize storage with configured directory
    let storage = Storage::new(config.notes_dir)?;

    // Create and run CLI app
    let app = CliApp::new(storage);
    app.run()
}
