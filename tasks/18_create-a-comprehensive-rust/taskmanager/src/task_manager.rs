use crate::models::{Priority, Task};
use crate::storage::{Storage, StorageError, StorageResult};
use chrono::{DateTime, Duration, Utc};
use std::collections::HashMap;
use uuid::Uuid;

/// Filter options for listing tasks
#[derive(Debug, Clone, Default)]
pub struct TaskFilter {
    pub completed: Option<bool>,
    pub priorities: Option<Vec<Priority>>,
    pub tags: Option<Vec<String>>,
    pub tags_any: bool, // true = OR, false = AND
    pub search_query: Option<String>,
    pub deadline_before: Option<DateTime<Utc>>,
    pub deadline_after: Option<DateTime<Utc>>,
}

/// Sort options for listing tasks
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum TaskSort {
    /// Sort by priority (highest first)
    #[default]
    Priority,
    /// Sort by deadline (soonest first)
    Deadline,
    /// Sort by creation date (newest first)
    Created,
    /// Sort by completion date (most recently completed first)
    Completed,
    /// Sort by title (alphabetically)
    Title,
}

/// Task manager with undo/redo support
#[derive(Debug)]
pub struct TaskManager<S: Storage> {
    tasks: Vec<Task>,
    storage: S,
    undo_stack: Vec<Vec<Task>>,
    redo_stack: Vec<Vec<Task>>,
    max_undo_steps: usize,
}

impl<S: Storage> TaskManager<S> {
    /// Create a new TaskManager with the given storage
    pub fn new(storage: S) -> StorageResult<Self> {
        let tasks = storage.load_tasks()?;
        Ok(Self {
            tasks,
            storage,
            undo_stack: Vec::new(),
            redo_stack: Vec::new(),
            max_undo_steps: 50,
        })
    }

    /// Add a new task
    pub fn add_task(&mut self, mut task: Task) -> StorageResult<&Task> {
        task.validate()?;
        self.save_state_for_undo()?;
        self.tasks.push(task);
        self.persist()?;
        Ok(self.tasks.last().unwrap())
    }

    /// Get a task by ID
    pub fn get_task(&self, id: Uuid) -> Option<&Task> {
        self.tasks.iter().find(|t| t.id == id)
    }

    /// Get a mutable reference to a task by ID
    pub fn get_task_mut(&mut self, id: Uuid) -> Option<&mut Task> {
        self.tasks.iter_mut().find(|t| t.id == id)
    }

    /// Update an existing task
    pub fn update_task<F>(&mut self, id: Uuid, updater: F) -> StorageResult<()>
    where
        F: FnOnce(&mut Task),
    {
        let task = self
            .tasks
            .iter_mut()
            .find(|t| t.id == id)
            .ok_or_else(|| StorageError::NotFound(format!("Task with id {}", id)))?;

        self.save_state_for_undo()?;
        updater(task);
        task.validate()?;
        self.persist()?;
        Ok(())
    }

    /// Complete a task
    pub fn complete_task(&mut self, id: Uuid) -> StorageResult<()> {
        self.update_task(id, |task| task.complete())
    }

    /// Uncomplete a task
    pub fn uncomplete_task(&mut self, id: Uuid) -> StorageResult<()> {
        self.update_task(id, |task| task.uncomplete())
    }

    /// Delete a task
    pub fn delete_task(&mut self, id: Uuid) -> StorageResult<()> {
        self.save_state_for_undo()?;
        self.tasks.retain(|t| t.id != id);
        self.persist()?;
        Ok(())
    }

    /// Delete all completed tasks
    pub fn delete_completed(&mut self) -> StorageResult<usize> {
        self.save_state_for_undo()?;
        let before = self.tasks.len();
        self.tasks.retain(|t| !t.completed);
        let deleted = before - self.tasks.len();
        self.persist()?;
        Ok(deleted)
    }

    /// Bulk complete tasks
    pub fn complete_tasks(&mut self, ids: &[Uuid]) -> StorageResult<()> {
        self.save_state_for_undo()?;
        for id in ids {
            if let Some(task) = self.tasks.iter_mut().find(|t| t.id == *id) {
                task.complete();
            }
        }
        self.persist()?;
        Ok(())
    }

    /// Bulk delete tasks
    pub fn delete_tasks(&mut self, ids: &[Uuid]) -> StorageResult<()> {
        self.save_state_for_undo()?;
        self.tasks.retain(|t| !ids.contains(&t.id));
        self.persist()?;
        Ok(())
    }

    /// List tasks with optional filtering and sorting
    pub fn list_tasks(&self, filter: &TaskFilter, sort: TaskSort) -> Vec<&Task> {
        let mut tasks: Vec<&Task> = self
            .tasks
            .iter()
            .filter(|task| self.matches_filter(task, filter))
            .collect();

        self.sort_tasks(&mut tasks, sort);
        tasks
    }

    /// Search tasks by query string
    pub fn search_tasks(&self, query: &str) -> Vec<&Task> {
        self.tasks
            .iter()
            .filter(|task| task.matches_query(query))
            .collect()
    }

    /// Get task statistics
    pub fn get_statistics(&self) -> TaskStatistics {
        let total = self.tasks.len();
        let completed = self.tasks.iter().filter(|t| t.completed).count();
        let pending = total - completed;

        let by_priority = {
            let mut map = HashMap::new();
            for task in &self.tasks {
                *map.entry(task.priority).or_insert(0) += 1;
            }
            map
        };

        let overdue = self.tasks.iter().filter(|t| t.is_overdue()).count();
        let due_soon = self.tasks.iter().filter(|t| t.is_due_soon()).count();

        let completion_rate = if total > 0 {
            (completed as f64 / total as f64) * 100.0
        } else {
            0.0
        };

        let all_tags = {
            let mut map = HashMap::new();
            for task in &self.tasks {
                for tag in &task.tags {
                    *map.entry(tag.clone()).or_insert(0) += 1;
                }
            }
            map
        };

        TaskStatistics {
            total,
            completed,
            pending,
            by_priority,
            overdue,
            due_soon,
            completion_rate,
            all_tags,
        }
    }

    /// Undo the last operation
    pub fn undo(&mut self) -> StorageResult<bool> {
        if let Some(previous_state) = self.undo_stack.pop() {
            self.redo_stack.push(self.tasks.clone());
            self.tasks = previous_state;
            self.persist()?;
            Ok(true)
        } else {
            Ok(false)
        }
    }

    /// Redo the last undone operation
    pub fn redo(&mut self) -> StorageResult<bool> {
        if let Some(next_state) = self.redo_stack.pop() {
            self.undo_stack.push(self.tasks.clone());
            self.tasks = next_state;
            self.persist()?;
            Ok(true)
        } else {
            Ok(false)
        }
    }

    /// Clear undo/redo history
    pub fn clear_history(&mut self) {
        self.undo_stack.clear();
        self.redo_stack.clear();
    }

    /// Get all tasks
    pub fn all_tasks(&self) -> &[Task] {
        &self.tasks
    }

    /// Get storage path
    pub fn storage_path(&self) -> &std::path::Path {
        self.storage.path()
    }

    // Private helper methods

    fn matches_filter(&self, task: &Task, filter: &TaskFilter) -> bool {
        if let Some(completed) = filter.completed {
            if task.completed != completed {
                return false;
            }
        }

        if let Some(ref priorities) = filter.priorities {
            if !priorities.contains(&task.priority) {
                return false;
            }
        }

        if let Some(ref tags) = filter.tags {
            if filter.tags_any {
                if !task.has_any_tag(tags) {
                    return false;
                }
            } else {
                if !task.has_all_tags(tags) {
                    return false;
                }
            }
        }

        if let Some(ref query) = filter.search_query {
            if !task.matches_query(query) {
                return false;
            }
        }

        if let Some(before) = filter.deadline_before {
            if let Some(deadline) = task.deadline {
                if deadline > before {
                    return false;
                }
            } else {
                return false;
            }
        }

        if let Some(after) = filter.deadline_after {
            if let Some(deadline) = task.deadline {
                if deadline < after {
                    return false;
                }
            } else {
                return false;
            }
        }

        true
    }

    fn sort_tasks(&self, tasks: &mut [&Task], sort: TaskSort) {
        match sort {
            TaskSort::Priority => {
                tasks.sort_by(|a, b| {
                    b.priority
                        .cmp(&a.priority)
                        .then_with(|| a.created_at.cmp(&b.created_at))
                });
            }
            TaskSort::Deadline => {
                tasks.sort_by(|a, b| {
                    match (a.deadline, b.deadline) {
                        (Some(da), Some(db)) => da.cmp(&db),
                        (Some(_), None) => std::cmp::Ordering::Less,
                        (None, Some(_)) => std::cmp::Ordering::Greater,
                        (None, None) => a.created_at.cmp(&b.created_at),
                    }
                });
            }
            TaskSort::Created => {
                tasks.sort_by(|a, b| b.created_at.cmp(&a.created_at));
            }
            TaskSort::Completed => {
                tasks.sort_by(|a, b| {
                    match (a.completed_at, b.completed_at) {
                        (Some(da), Some(db)) => db.cmp(&da),
                        (Some(_), None) => std::cmp::Ordering::Less,
                        (None, Some(_)) => std::cmp::Ordering::Greater,
                        (None, None) => b.created_at.cmp(&a.created_at),
                    }
                });
            }
            TaskSort::Title => {
                tasks.sort_by(|a, b| a.title.to_lowercase().cmp(&b.title.to_lowercase()));
            }
        }
    }

    fn save_state_for_undo(&mut self) -> StorageResult<()> {
        self.undo_stack.push(self.tasks.clone());
        if self.undo_stack.len() > self.max_undo_steps {
            self.undo_stack.remove(0);
        }
        self.redo_stack.clear(); // Clear redo stack on new operation
        Ok(())
    }

    fn persist(&self) -> StorageResult<()> {
        self.storage.save_tasks(&self.tasks)
    }
}

/// Task statistics
#[derive(Debug)]
pub struct TaskStatistics {
    pub total: usize,
    pub completed: usize,
    pub pending: usize,
    pub by_priority: HashMap<Priority, usize>,
    pub overdue: usize,
    pub due_soon: usize,
    pub completion_rate: f64,
    pub all_tags: HashMap<String, usize>,
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::storage::JsonStorage;
    use tempfile::TempDir;

    fn create_test_manager() -> TaskManager<JsonStorage> {
        let temp_dir = TempDir::new().unwrap();
        let file_path = temp_dir.path().join("tasks.json");
        let storage = JsonStorage::new(file_path);
        TaskManager::new(storage).unwrap()
    }

    #[test]
    fn test_add_task() {
        let mut manager = create_test_manager();
        let task = Task::new("Test task".to_string());
        manager.add_task(task).unwrap();
        assert_eq!(manager.all_tasks().len(), 1);
    }

    #[test]
    fn test_complete_task() {
        let mut manager = create_test_manager();
        let task = Task::new("Test task".to_string());
        let added = manager.add_task(task).unwrap();
        manager.complete_task(added.id).unwrap();
        assert!(manager.get_task(added.id).unwrap().completed);
    }

    #[test]
    fn test_delete_task() {
        let mut manager = create_test_manager();
        let task = Task::new("Test task".to_string());
        let added = manager.add_task(task).unwrap();
        manager.delete_task(added.id).unwrap();
        assert_eq!(manager.all_tasks().len(), 0);
    }

    #[test]
    fn test_filter_by_priority() {
        let mut manager = create_test_manager();
        manager
            .add_task(Task::new("Low").to_string())
            .with_priority(Priority::Low)
            .clone()
        );
        manager
            .add_task(Task::new("High").to_string())
            .with_priority(Priority::High)
            .clone()
        );

        let filter = TaskFilter {
            priorities: Some(vec![Priority::High]),
            ..Default::default()
        };
        let results = manager.list_tasks(&filter, TaskSort::Priority);
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].title, "High");
    }

    #[test]
    fn test_statistics() {
        let mut manager = create_test_manager();
        manager.add_task(Task::new("Task 1".to_string())).unwrap();
        manager.add_task(Task::new("Task 2".to_string())).unwrap();
        manager.complete_task(manager.all_tasks()[0].id).unwrap();

        let stats = manager.get_statistics();
        assert_eq!(stats.total, 2);
        assert_eq!(stats.completed, 1);
        assert_eq!(stats.pending, 1);
    }
}
