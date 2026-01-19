use anyhow::{Context, Result};
use rustate::history::{FileHistory, History};
use std::path::PathBuf;
use crate::config;

/// Maximum number of history entries to keep
const MAX_HISTORY_SIZE: usize = 1000;

/// Get the path to the history file
pub fn get_history_path() -> Result<PathBuf> {
    let config_dir = config::get_config_dir()
        .context("Failed to get config directory")?;
    Ok(config_dir.join("history"))
}

/// Create a new history instance with the history file
pub fn create_history() -> Result<FileHistory> {
    let history_path = get_history_path()?;

    // Create parent directories if they don't exist
    if let Some(parent) = history_path.parent() {
        std::fs::create_dir_all(parent)
            .context("Failed to create history directory")?;
    }

    let mut history = FileHistory::new();
    history.set_max_len(MAX_HISTORY_SIZE);

    // Try to load existing history
    if history_path.exists() {
        history.load(&history_path)
            .context("Failed to load history file")?;
    }

    Ok(history)
}

/// Save history to disk
pub fn save_history(history: &mut FileHistory) -> Result<()> {
    let history_path = get_history_path()?;
    history.save(&history_path)
        .context("Failed to save history file")?;
    Ok(())
}

/// Clear all history
pub fn clear_history() -> Result<()> {
    let history_path = get_history_path()?;
    if history_path.exists() {
        std::fs::remove_file(&history_path)
            .context("Failed to remove history file")?;
    }
    Ok(())
}

/// Search history for commands matching a pattern
pub fn search_history(pattern: &str) -> Result<Vec<String>> {
    let history_path = get_history_path()?;

    if !history_path.exists() {
        return Ok(Vec::new());
    }

    let content = std::fs::read_to_string(&history_path)
        .context("Failed to read history file")?;

    let pattern_lower = pattern.to_lowercase();
    let matches: Vec<String> = content
        .lines()
        .filter(|line| line.to_lowercase().contains(&pattern_lower))
        .map(|line| line.to_string())
        .collect();

    Ok(matches)
}

/// Get most frequently used commands
pub fn get_frequent_commands(limit: usize) -> Result<Vec<(String, usize)>> {
    let history_path = get_history_path()?;

    if !history_path.exists() {
        return Ok(Vec::new());
    }

    let content = std::fs::read_to_string(&history_path)
        .context("Failed to read history file")?;

    let mut command_counts: std::collections::HashMap<String, usize> = std::collections::HashMap::new();

    for line in content.lines() {
        // Extract the base command (first word)
        if let Some(command) = line.split_whitespace().next() {
            *command_counts.entry(command.to_string()).or_insert(0) += 1;
        }
    }

    let mut counts: Vec<(String, usize)> = command_counts.into_iter().collect();
    counts.sort_by(|a, b| b.1.cmp(&a.1));

    Ok(counts.into_iter().take(limit).collect())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_get_history_path() {
        let path = get_history_path();
        assert!(path.is_ok());
    }
}
