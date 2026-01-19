mod cli;
mod config;
mod templates;
mod scaffolding;
mod git;
mod error;
mod interactive;
mod wizard;
mod variables;
mod history;
mod session;
mod plugin;

use anyhow::Result;
use clap::Parser;
use cli::{Commands, HistoryCommand, ProjectInit};
use log::{info, warn};

fn main() -> Result<()> {
    // Initialize logger
    env_logger::init();

    let cli = ProjectInit::parse();

    match cli.command {
        Commands::Init { interactive } => {
            info!("Initializing project-init configuration");
            config::init_config(interactive)?;
        }
        Commands::New {
            template,
            name,
            path,
            git,
            variables,
            interactive,
        } => {
            info!("Creating new project from template '{}'", template);

            if interactive {
                // Interactive mode for collecting variables
                interactive::create_project_interactive(&template, &name, path, git, &variables)?;
            } else {
                scaffolding::create_project(&template, &name, path.as_deref(), git, &variables)?;
            }
        }
        Commands::Template { command } => {
            templates::handle_template_command(command)?;
        }
        Commands::List => {
            templates::list_templates()?;
        }
        Commands::Config { key, value } => {
            config::handle_config(key, value)?;
        }
        Commands::Interactive => {
            info!("Entering interactive mode");
            interactive::run_interactive_mode()?;
        }
        Commands::Wizard { resume } => {
            info!("Running template creation wizard");
            wizard::run_template_wizard(resume)?;
        }
        Commands::History { command } => {
            handle_history_command(command)?;
        }
    }

    Ok(())
}

/// Handle history-related commands
fn handle_history_command(command: Option<HistoryCommand>) -> Result<()> {
    match command {
        Some(HistoryCommand::Clear) => {
            history::clear_history()?;
            println!("History cleared.");
        }
        Some(HistoryCommand::Search { pattern }) => {
            let matches = history::search_history(&pattern)?;
            println!("Matching commands:");
            for entry in matches {
                println!("  {}", entry);
            }
        }
        Some(HistoryCommand::Frequent { count }) => {
            let frequent = history::get_frequent_commands(count)?;
            println!("Most frequent commands:");
            for (cmd, count) in frequent {
                println!("  {} - {} times", cmd, count);
            }
        }
        Some(HistoryCommand::List) => {
            let history_path = history::get_history_path()?;
            if history_path.exists() {
                let content = std::fs::read_to_string(&history_path)?;
                println!("Command history:");
                for (i, line) in content.lines().enumerate() {
                    println!("  {}  {}", i + 1, line);
                }
            } else {
                println!("No history found.");
            }
        }
        None => {
            // Show recent history by default
            let history_path = history::get_history_path()?;
            if history_path.exists() {
                let content = std::fs::read_to_string(&history_path)?;
                let lines: Vec<&str> = content.lines().collect();
                let recent = lines.iter().rev().take(20).collect::<Vec<_>>();
                println!("Recent commands:");
                for (i, line) in recent.iter().enumerate() {
                    println!("  {}  {}", i + 1, line);
                }
            } else {
                println!("No history found.");
            }
        }
    }
    Ok(())
}
