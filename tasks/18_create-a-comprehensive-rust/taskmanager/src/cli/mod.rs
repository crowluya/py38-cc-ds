pub mod commands;
pub mod output;

pub use commands::*;
pub use output::format_task_table;

use clap::{Parser, Subcommand};
use colored::Colorize;

/// A comprehensive CLI task manager with priority queues, deadlines, and tags
#[derive(Parser, Debug)]
#[command(name = "taskmanager")]
#[command(author = "Task Manager Team")]
#[command(version = "0.1.0")]
#[command(about = "Manage your tasks efficiently with priorities, deadlines, and tags", long_about = None)]
pub struct Cli {
    #[command(subcommand)]
    pub command: Commands,
}

/// Available CLI commands
#[derive(Subcommand, Debug)]
pub enum Commands {
    /// Add a new task
    Add {
        /// Task title
        #[arg(short, long)]
        title: String,

        /// Task description
        #[arg(short, long)]
        description: Option<String>,

        /// Task priority (low, medium, high, critical)
        #[arg(short, long, default_value = "medium")]
        priority: String,

        /// Task deadline (format: YYYY-MM-DD or YYYY-MM-DD HH:MM)
        #[arg(short, long)]
        deadline: Option<String>,

        /// Task tags (comma-separated)
        #[arg(short, long, value_delimiter = ',')]
        tags: Vec<String>,

        /// Interactive mode
        #[arg(short, long)]
        interactive: bool,
    },

    /// List tasks with optional filtering
    List {
        /// Show only completed tasks
        #[arg(short, long)]
        completed: bool,

        /// Show only pending tasks
        #[arg(short, long)]
        pending: bool,

        /// Filter by priority (can be specified multiple times)
        #[arg(short, long, value_delimiter = ',')]
        priority: Vec<String>,

        /// Filter by tags (comma-separated, requires all tags by default)
        #[arg(short, long, value_delimiter = ',')]
        tags: Vec<String>,

        /// Match any tag instead of all tags
        #[arg(long)]
        tags_any: bool,

        /// Search in title and description
        #[arg(short, long)]
        search: Option<String>,

        /// Sort by (priority, deadline, created, completed, title)
        #[arg(short, long, default_value = "priority")]
        sort: String,

        /// Show tasks as a simple list (no table)
        #[arg(short, long)]
        simple: bool,
    },

    /// Complete a task
    Complete {
        /// Task ID (short or full UUID)
        #[arg(required = true)]
        id: String,

        /// Complete multiple tasks
        #[arg(short, long, value_delimiter = ',')]
        additional: Vec<String>,
    },

    /// Uncomplete a task (mark as not done)
    Uncomplete {
        /// Task ID (short or full UUID)
        #[arg(required = true)]
        id: String,
    },

    /// Delete a task
    Delete {
        /// Task ID (short or full UUID)
        #[arg(required = true)]
        id: String,

        /// Delete multiple tasks
        #[arg(short, long, value_delimiter = ',')]
        additional: Vec<String>,

        /// Delete all completed tasks
        #[arg(long)]
        completed: bool,
    },

    /// Edit an existing task
    Edit {
        /// Task ID (short or full UUID)
        #[arg(required = true)]
        id: String,

        /// New title
        #[arg(short, long)]
        title: Option<String>,

        /// New description
        #[arg(short, long)]
        description: Option<String>,

        /// New priority
        #[arg(short, long)]
        priority: Option<String>,

        /// New deadline (format: YYYY-MM-DD or YYYY-MM-DD HH:MM)
        #[arg(short, long)]
        deadline: Option<String>,

        /// Add tags (comma-separated)
        #[arg(long, value_delimiter = ',')]
        add_tags: Vec<String>,

        /// Remove tags (comma-separated)
        #[arg(long, value_delimiter = ',')]
        remove_tags: Vec<String>,

        /// Interactive mode
        #[arg(short, long)]
        interactive: bool,
    },

    /// Show task statistics
    Stats {
        /// Show tag statistics
        #[arg(short, long)]
        tags: bool,

        /// Show priority statistics
        #[arg(short, long)]
        priority: bool,
    },

    /// Search tasks
    Search {
        /// Search query
        #[arg(required = true)]
        query: String,

        /// Sort by (priority, deadline, created, completed, title)
        #[arg(short, long, default_value = "priority")]
        sort: String,
    },

    /// Undo the last operation
    Undo,

    /// Redo the last undone operation
    Redo,

    /// Backup and restore operations
    Backup {
        /// Create a backup
        #[arg(short, long)]
        create: bool,

        /// List available backups
        #[arg(short, long)]
        list: bool,

        /// Restore from a backup file
        #[arg(short, long)]
        restore: Option<String>,
    },
}
