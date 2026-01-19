use clap::{Parser, Subcommand};
use crate::templates::TemplateCommand;
use std::collections::HashMap;
use std::path::PathBuf;

#[derive(Parser)]
#[command(name = "project-init")]
#[command(about = "A CLI productivity tool for managing project templates with customizable scaffolding", long_about = None)]
#[command(version = "0.1.0")]
#[command(author = "Your Name <your.email@example.com>")]
pub struct ProjectInit {
    #[command(subcommand)]
    pub command: Commands,
}

#[derive(Subcommand)]
pub enum Commands {
    /// Initialize project-init configuration
    Init {
        /// Use interactive mode for configuration
        #[arg(short, long, default_value_t = false)]
        interactive: bool,
    },

    /// Create a new project from a template
    New {
        /// Template name to use
        #[arg(short, long)]
        template: String,

        /// Project name
        #[arg(short, long)]
        name: String,

        /// Custom path for the project (default: project name)
        #[arg(short, long)]
        path: Option<String>,

        /// Initialize Git repository
        #[arg(short, long, default_value_t = true)]
        git: bool,

        /// Template variables (key=value format, can be used multiple times)
        #[arg(short, long, value_parser = parse_key_value)]
        variables: Vec<(String, String)>,

        /// Interactive mode for collecting variables
        #[arg(long, default_value_t = false)]
        interactive: bool,
    },

    /// Manage templates
    Template {
        #[command(subcommand)]
        command: TemplateCommand,
    },

    /// List all available templates
    List,

    /// Manage configuration
    Config {
        /// Configuration key to get/set
        key: Option<String>,

        /// Value to set (use with --key)
        value: Option<String>,
    },

    /// Enter interactive mode
    Interactive,

    /// Run the template creation wizard
    Wizard {
        /// Resume a previous wizard session
        #[arg(short, long)]
        resume: Option<String>,
    },

    /// Manage command history
    History {
        /// Subcommand: clear, search, or list
        #[arg(subcommand)]
        command: Option<HistoryCommand>,
    },
}

fn parse_key_value(s: &str) -> Result<(String, String), String> {
    let parts: Vec<&str> = s.splitn(2, '=').collect();
    if parts.len() != 2 {
        return Err(format!("Invalid key-value pair: '{}'. Expected format: key=value", s));
    }
    Ok((parts[0].to_string(), parts[1].to_string()))
}

impl From<Vec<(String, String)>> for HashMap<String, String> {
    fn from(vec: Vec<(String, String)>) -> Self {
        vec.into_iter().collect()
    }
}

/// History management commands
#[derive(Debug, clap::Subcommand)]
pub enum HistoryCommand {
    /// Clear command history
    Clear,
    /// Search command history
    Search {
        /// Search pattern
        pattern: String,
    },
    /// Show frequent commands
    Frequent {
        /// Number of commands to show (default: 10)
        #[arg(short, long, default_value_t = 10)]
        count: usize,
    },
    /// List all history
    List,
}

/// Plugin management commands
#[derive(Debug, clap::Subcommand)]
pub enum PluginCommand {
    /// List all installed plugins
    List,

    /// Install a plugin from a file or URL
    Install {
        /// Source path or URL of the plugin
        source: String,

        /// Force installation without confirmation
        #[arg(short, long, default_value_t = false)]
        force: bool,
    },

    /// Remove an installed plugin
    Remove {
        /// Plugin ID to remove
        id: String,
    },

    /// Show detailed information about a plugin
    Info {
        /// Plugin ID
        id: String,
    },

    /// Update a plugin
    Update {
        /// Plugin ID to update
        id: String,

        /// URL to download updated plugin from
        url: String,
    },

    /// Reload all plugins from disk
    Reload,

    /// Verify plugin integrity
    Verify {
        /// Plugin ID to verify
        id: String,
    },
}
