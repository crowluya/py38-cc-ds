mod cli;
mod models;
mod storage;
mod task_manager;

use anyhow::Result;
use clap::Parser;
use colored::Colorize;

use cli::{execute_command, Cli};

fn main() -> Result<()> {
    let cli = Cli::parse();

    if let Err(e) = execute_command(cli.command) {
        eprintln!("{} {}", "Error:".red().bold(), e);
        std::process::exit(1);
    }

    Ok(())
}
