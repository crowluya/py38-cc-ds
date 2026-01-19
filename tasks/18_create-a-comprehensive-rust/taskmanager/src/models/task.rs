use super::priority::Priority;
use chrono::{DateTime, NaiveDateTime, Utc};
use serde::{Deserialize, Serialize};
use std::fmt;
use uuid::Uuid;

/// Represents a task with all its properties
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Task {
    /// Unique identifier for the task
    pub id: Uuid,

    /// Title of the task
    pub title: String,

    /// Detailed description of the task
    pub description: Option<String>,

    /// Priority level of the task
    pub priority: Priority,

    /// Optional deadline for the task
    pub deadline: Option<DateTime<Utc>>,

    /// Tags associated with the task
    pub tags: Vec<String>,

    /// Whether the task is completed
    pub completed: bool,

    /// When the task was created
    pub created_at: DateTime<Utc>,

    /// When the task was completed (if applicable)
    pub completed_at: Option<DateTime<Utc>>,

    /// When the task was last modified
    pub updated_at: DateTime<Utc>,
}

impl Task {
    /// Create a new task
    pub fn new(title: String) -> Self {
        let now = Utc::now();
        Self {
            id: Uuid::new_v4(),
            title,
            description: None,
            priority: Priority::default(),
            deadline: None,
            tags: Vec::new(),
            completed: false,
            created_at: now,
            completed_at: None,
            updated_at: now,
        }
    }

    /// Set the description of the task
    pub fn with_description(mut self, description: Option<String>) -> Self {
        self.description = description;
        self.updated_at = Utc::now();
        self
    }

    /// Set the priority of the task
    pub fn with_priority(mut self, priority: Priority) -> Self {
        self.priority = priority;
        self.updated_at = Utc::now();
        self
    }

    /// Set the deadline of the task
    pub fn with_deadline(mut self, deadline: Option<DateTime<Utc>>) -> Self {
        self.deadline = deadline;
        self.updated_at = Utc::now();
        self
    }

    /// Set the tags of the task
    pub fn with_tags(mut self, tags: Vec<String>) -> Self {
        self.tags = tags;
        self.updated_at = Utc::now();
        self
    }

    /// Mark the task as completed
    pub fn complete(&mut self) {
        self.completed = true;
        self.completed_at = Some(Utc::now());
        self.updated_at = Utc::now();
    }

    /// Mark the task as incomplete
    pub fn uncomplete(&mut self) {
        self.completed = false;
        self.completed_at = None;
        self.updated_at = Utc::now();
    }

    /// Check if the task is overdue
    pub fn is_overdue(&self) -> bool {
        if self.completed {
            return false;
        }
        match self.deadline {
            Some(deadline) => deadline < Utc::now(),
            None => false,
        }
    }

    /// Check if the task is due soon (within 24 hours)
    pub fn is_due_soon(&self) -> bool {
        if self.completed || self.deadline.is_none() {
            return false;
        }
        let deadline = self.deadline.unwrap();
        let now = Utc::now();
        let hours_until_deadline = (deadline - now).num_hours();
        hours_until_deadline >= 0 && hours_until_deadline <= 24
    }

    /// Get a short ID string (first 8 characters of UUID)
    pub fn short_id(&self) -> String {
        format!("{}", self.id)[..8].to_string()
    }

    /// Validate the task data
    pub fn validate(&self) -> Result<(), String> {
        if self.title.trim().is_empty() {
            return Err("Task title cannot be empty".to_string());
        }
        if self.title.len() > 200 {
            return Err("Task title too long (max 200 characters)".to_string());
        }
        if let Some(ref description) = self.description {
            if description.len() > 5000 {
                return Err("Task description too long (max 5000 characters)".to_string());
            }
        }
        for tag in &self.tags {
            if tag.trim().is_empty() {
                return Err("Task tags cannot be empty".to_string());
            }
            if tag.len() > 50 {
                return Err(format!("Tag '{}' too long (max 50 characters)", tag));
            }
            if tag.contains(',') || tag.contains(' ') {
                return Err(format!(
                    "Tag '{}' cannot contain commas or spaces",
                    tag
                ));
            }
        }
        Ok(())
    }

    /// Check if task matches a search query
    pub fn matches_query(&self, query: &str) -> bool {
        let query_lower = query.to_lowercase();
        self.title.to_lowercase().contains(&query_lower)
            || self
                .description
                .as_ref()
                .map(|d| d.to_lowercase().contains(&query_lower))
                .unwrap_or(false)
            || self.tags.iter().any(|t| t.to_lowercase() == query_lower)
    }

    /// Check if task has any of the specified tags
    pub fn has_any_tag(&self, tags: &[String]) -> bool {
        tags.iter().any(|tag| self.tags.contains(tag))
    }

    /// Check if task has all of the specified tags
    pub fn has_all_tags(&self, tags: &[String]) -> bool {
        tags.iter().all(|tag| self.tags.contains(tag))
    }
}

impl fmt::Display for Task {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "[{}] {} {}",
            self.short_id(),
            self.priority.emoji(),
            self.title
        )
    }
}

impl PartialEq for Task {
    fn eq(&self, other: &Self) -> bool {
        self.id == other.id
    }
}

impl Eq for Task {}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_task_creation() {
        let task = Task::new("Test task".to_string());
        assert_eq!(task.title, "Test task");
        assert_eq!(task.priority, Priority::Medium);
        assert!(!task.completed);
        assert!(task.deadline.is_none());
        assert!(task.tags.is_empty());
    }

    #[test]
    fn test_task_builder() {
        let task = Task::new("Test task".to_string())
            .with_description(Some("Description".to_string()))
            .with_priority(Priority::High)
            .with_tags(vec!["work".to_string(), "urgent".to_string()]);

        assert_eq!(task.description, Some("Description".to_string()));
        assert_eq!(task.priority, Priority::High);
        assert_eq!(task.tags, vec!["work".to_string(), "urgent".to_string()]);
    }

    #[test]
    fn test_task_completion() {
        let mut task = Task::new("Test task".to_string());
        assert!(!task.completed);
        assert!(task.completed_at.is_none());

        task.complete();
        assert!(task.completed);
        assert!(task.completed_at.is_some());

        task.uncomplete();
        assert!(!task.completed);
        assert!(task.completed_at.is_none());
    }

    #[test]
    fn test_task_validation() {
        let mut task = Task::new("Valid task".to_string());
        assert!(task.validate().is_ok());

        task.title = "".to_string();
        assert!(task.validate().is_err());

        task.title = "a".repeat(201);
        assert!(task.validate().is_err());
    }

    #[test]
    fn test_tag_validation() {
        let mut task = Task::new("Test".to_string());
        task.tags = vec!["valid".to_string()];
        assert!(task.validate().is_ok());

        task.tags = vec!["".to_string()];
        assert!(task.validate().is_err());

        task.tags = vec!["has space".to_string()];
        assert!(task.validate().is_err());

        task.tags = vec!["has,comma".to_string()];
        assert!(task.validate().is_err());
    }

    #[test]
    fn test_short_id() {
        let task = Task::new("Test".to_string());
        assert_eq!(task.short_id().len(), 8);
    }

    #[test]
    fn test_matches_query() {
        let task = Task::new("Important meeting".to_string())
            .with_description("Discuss project plans".to_string())
            .with_tags(vec!["work".to_string()]);

        assert!(task.matches_query("meeting"));
        assert!(task.matches_query("plans"));
        assert!(task.matches_query("work"));
        assert!(!task.matches_query("personal"));
    }

    #[test]
    fn test_has_tags() {
        let task = Task::new("Test".to_string())
            .with_tags(vec!["work".to_string(), "urgent".to_string()]);

        assert!(task.has_any_tag(&["work".to_string()]));
        assert!(task.has_any_tag(&["personal".to_string(), "work".to_string()]));
        assert!(!task.has_any_tag(&["personal".to_string()]));

        assert!(task.has_all_tags(&["work".to_string()]));
        assert!(task.has_all_tags(&["work".to_string(), "urgent".to_string()]));
        assert!(!task.has_all_tags(&["work".to_string(), "personal".to_string()]));
    }

    #[test]
    fn test_is_overdue() {
        let mut task = Task::new("Test".to_string());

        // No deadline means not overdue
        assert!(!task.is_overdue());

        // Past deadline means overdue
        task.deadline = Some(Utc::now() - chrono::Duration::hours(1));
        assert!(task.is_overdue());

        // Future deadline means not overdue
        task.deadline = Some(Utc::now() + chrono::Duration::hours(1));
        assert!(!task.is_overdue());

        // Completed tasks are never overdue
        task.deadline = Some(Utc::now() - chrono::Duration::hours(1));
        task.complete();
        assert!(!task.is_overdue());
    }
}
