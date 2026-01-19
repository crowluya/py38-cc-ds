use anyhow::{Context, Result};
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;
use crate::config;

/// Session state for wizard and interactive operations
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Session {
    pub id: String,
    pub session_type: SessionType,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    pub data: SessionData,
}

/// Type of session
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum SessionType {
    Wizard,
    Interactive,
    TemplateCreation,
}

/// Session data container
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SessionData {
    pub current_step: String,
    pub completed_steps: Vec<String>,
    pub variables: HashMap<String, String>,
    pub template_data: Option<TemplateDraft>,
    pub metadata: HashMap<String, String>,
}

/// Draft template data for wizard sessions
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TemplateDraft {
    pub name: String,
    pub description: String,
    pub language: String,
    pub version: String,
    pub variables: Vec<crate::variables::EnhancedVariable>,
    pub files: Vec<String>,
    pub directories: Vec<String>,
}

impl Session {
    /// Create a new session
    pub fn new(session_type: SessionType) -> Self {
        let id = uuid::Uuid::new_v4().to_string();
        let now = Utc::now();

        Session {
            id,
            session_type,
            created_at: now,
            updated_at: now,
            data: SessionData {
                current_step: "start".to_string(),
                completed_steps: Vec::new(),
                variables: HashMap::new(),
                template_data: None,
                metadata: HashMap::new(),
            },
        }
    }

    /// Update the current step
    pub fn set_current_step(&mut self, step: &str) {
        // Move current step to completed if not already there
        if !self.data.completed_steps.contains(&self.data.current_step) {
            self.data.completed_steps.push(self.data.current_step.clone());
        }
        self.data.current_step = step.to_string();
        self.updated_at = Utc::now();
    }

    /// Set a variable value
    pub fn set_variable(&mut self, key: &str, value: &str) {
        self.data.variables.insert(key.to_string(), value.to_string());
        self.updated_at = Utc::now();
    }

    /// Get a variable value
    pub fn get_variable(&self, key: &str) -> Option<&String> {
        self.data.variables.get(key)
    }

    /// Set metadata
    pub fn set_metadata(&mut self, key: &str, value: &str) {
        self.data.metadata.insert(key.to_string(), value.to_string());
        self.updated_at = Utc::now();
    }
}

/// Get the sessions directory path
pub fn get_sessions_dir() -> Result<PathBuf> {
    let config_dir = config::get_config_dir()
        .context("Failed to get config directory")?;
    let sessions_dir = config_dir.join("sessions");

    // Create directory if it doesn't exist
    fs::create_dir_all(&sessions_dir)
        .context("Failed to create sessions directory")?;

    Ok(sessions_dir)
}

/// Save a session to disk
pub fn save_session(session: &Session) -> Result<()> {
    let sessions_dir = get_sessions_dir()?;
    let session_path = sessions_dir.join(format!("{}.json", session.id));

    let json = serde_json::to_string_pretty(session)
        .context("Failed to serialize session")?;

    fs::write(&session_path, json)
        .context("Failed to write session file")?;

    Ok(())
}

/// Load a session from disk
pub fn load_session(session_id: &str) -> Result<Session> {
    let sessions_dir = get_sessions_dir()?;
    let session_path = sessions_dir.join(format!("{}.json", session_id));

    if !session_path.exists() {
        anyhow::bail!("Session '{}' not found", session_id);
    }

    let content = fs::read_to_string(&session_path)
        .context("Failed to read session file")?;

    let session: Session = serde_json::from_str(&content)
        .context("Failed to deserialize session")?;

    Ok(session)
}

/// List all sessions
pub fn list_sessions() -> Result<Vec<Session>> {
    let sessions_dir = get_sessions_dir()?;
    let mut sessions = Vec::new();

    for entry in fs::read_dir(sessions_dir)? {
        let entry = entry?;
        let path = entry.path();

        if path.extension().and_then(|s| s.to_str()) == Some("json") {
            if let Ok(session) = load_session(
                path.file_stem()
                    .and_then(|s| s.to_str())
                    .unwrap_or("")
            ) {
                sessions.push(session);
            }
        }
    }

    // Sort by updated_at, most recent first
    sessions.sort_by(|a, b| b.updated_at.cmp(&a.updated_at));

    Ok(sessions)
}

/// Delete a session
pub fn delete_session(session_id: &str) -> Result<()> {
    let sessions_dir = get_sessions_dir()?;
    let session_path = sessions_dir.join(format!("{}.json", session_id));

    if session_path.exists() {
        fs::remove_file(&session_path)
            .context("Failed to remove session file")?;
    }

    Ok(())
}

/// Clean up old sessions (older than 7 days)
pub fn cleanup_old_sessions() -> Result<usize> {
    let sessions = list_sessions()?;
    let now = Utc::now();
    let max_age = chrono::Duration::days(7);
    let mut cleaned = 0;

    for session in sessions {
        if now - session.updated_at > max_age {
            delete_session(&session.id)?;
            cleaned += 1;
        }
    }

    Ok(cleaned)
}

/// Resume a wizard session
pub fn resume_session(session_id: &str) -> Result<Session> {
    let session = load_session(session_id)?;

    // Validate session type
    if session.session_type != SessionType::Wizard {
        anyhow::bail!("Session '{}' is not a wizard session", session_id);
    }

    Ok(session)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_session_creation() {
        let session = Session::new(SessionType::Wizard);
        assert_eq!(session.data.current_step, "start");
        assert!(session.data.completed_steps.is_empty());
    }

    #[test]
    fn test_session_variables() {
        let mut session = Session::new(SessionType::Wizard);
        session.set_variable("test", "value");
        assert_eq!(session.get_variable("test"), Some(&"value".to_string()));
    }

    #[test]
    fn test_session_steps() {
        let mut session = Session::new(SessionType::Wizard);
        session.set_current_step("step1");
        assert_eq!(session.data.current_step, "step1");
        assert!(session.data.completed_steps.contains(&"start".to_string()));
    }
}
