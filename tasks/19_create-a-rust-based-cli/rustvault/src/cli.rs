//! CLI argument parsing and command structure
//!
//! This module defines the command-line interface using clap.

use clap::{Parser, Subcommand};
use std::path::PathBuf;

/// RustVault - A secure CLI password manager
#[derive(Parser, Debug)]
#[command(name = "rustvault")]
#[command(author = "RustVault Contributors")]
#[command(version = "0.1.0")]
#[command(about = "A secure CLI password manager with encryption, hierarchical vaults, and TOTP support", long_about = None)]
pub struct Cli {
    /// Path to the vault file (default: ~/.config/rustvault/vault.rustvault)
    #[arg(short, long, global = true)]
    pub vault_path: Option<PathBuf>,

    /// Enable verbose output
    #[arg(short, long, global = true)]
    pub verbose: bool,

    #[command(subcommand)]
    pub command: Commands,
}

/// Available commands
#[derive(Subcommand, Debug)]
pub enum Commands {
    /// Initialize a new vault
    Init,

    /// Unlock the vault (interactive session)
    Unlock,

    /// Lock the vault
    Lock,

    /// Manage entries
    #[command(subcommand)]
    Entry(EntryCommands),

    /// Manage folders
    #[command(subcommand)]
    Folder(FolderCommands),

    /// Generate a password or passphrase
    #[command(subcommand)]
    Generate(GenerateCommands),

    /// Display TOTP code for an entry
    Totp {
        /// Entry ID or title
        #[arg(value_name = "ENTRY")]
        entry: String,

        /// Folder path (default: root)
        #[arg(short, long, default_value = "")]
        folder: String,
    },

    /// Search for entries
    Search {
        /// Search query
        #[arg(value_name = "QUERY")]
        query: String,

        /// Show full entry details
        #[arg(short, long)]
        full: bool,
    },

    /// Export vault data
    Export {
        /// Output file path
        #[arg(value_name = "PATH")]
        path: PathBuf,

        /// Export as plaintext JSON (default: encrypted)
        #[arg(short, long)]
        plaintext: bool,
    },

    /// Import vault data
    Import {
        /// Input file path
        #[arg(value_name = "PATH")]
        path: PathBuf,
    },

    /// Show vault status
    Status,
}

/// Entry management commands
#[derive(Subcommand, Debug)]
pub enum EntryCommands {
    /// Add a new entry
    Add {
        /// Entry title
        #[arg(short, long)]
        title: Option<String>,

        /// Username
        #[arg(short, long)]
        username: Option<String>,

        /// Password (will prompt if not provided)
        #[arg(short, long)]
        password: Option<String>,

        /// URL
        #[arg(short, long)]
        url: Option<String>,

        /// Notes
        #[arg(short, long)]
        notes: Option<String>,

        /// Comma-separated tags
        #[arg(short, long)]
        tags: Option<String>,

        /// Folder path (default: root)
        #[arg(short, long, default_value = "")]
        folder: String,

        /// Generate password instead of prompting
        #[arg(long)]
        generate_password: bool,

        /// Password length for generated password
        #[arg(long, default_value = "16")]
        password_length: usize,
    },

    /// List entries in a folder
    List {
        /// Folder path (default: root)
        #[arg(short, long, default_value = "")]
        folder: String,

        /// Show passwords in list
        #[arg(long)]
        show_passwords: bool,
    },

    /// Show entry details
    Show {
        /// Entry ID or title
        #[arg(value_name = "ENTRY")]
        entry: String,

        /// Folder path (default: root)
        #[arg(short, long, default_value = "")]
        folder: String,

        /// Show password
        #[arg(long)]
        show_password: bool,

        /// Copy password to clipboard
        #[arg(long)]
        copy_password: bool,

        /// Copy TOTP code to clipboard
        #[arg(long)]
        copy_totp: bool,
    },

    /// Edit an existing entry
    Edit {
        /// Entry ID or title
        #[arg(value_name = "ENTRY")]
        entry: String,

        /// Folder path (default: root)
        #[arg(short, long, default_value = "")]
        folder: String,
    },

    /// Delete an entry
    Delete {
        /// Entry ID or title
        #[arg(value_name = "ENTRY")]
        entry: String,

        /// Folder path (default: root)
        #[arg(short, long, default_value = "")]
        folder: String,

        /// Skip confirmation prompt
        #[arg(long)]
        force: bool,
    },
}

/// Folder management commands
#[derive(Subcommand, Debug)]
pub enum FolderCommands {
    /// Create a new folder
    Add {
        /// Folder name
        #[arg(value_name = "NAME")]
        name: String,

        /// Parent folder path (default: root)
        #[arg(short, long, default_value = "")]
        parent: String,
    },

    /// List all folders
    List,

    /// Rename a folder
    Rename {
        /// Current folder path
        #[arg(value_name = "CURRENT")]
        current: String,

        /// New folder path
        #[arg(value_name = "NEW")]
        new_path: String,
    },

    /// Delete a folder
    Delete {
        /// Folder path
        #[arg(value_name = "PATH")]
        path: String,

        /// Skip confirmation prompt
        #[arg(long)]
        force: bool,

        /// Delete folder and all contents recursively
        #[arg(long)]
        recursive: bool,
    },
}

/// Password generation commands
#[derive(Subcommand, Debug)]
pub enum GenerateCommands {
    /// Generate a password
    Password {
        /// Password length
        #[arg(short, long, default_value = "16")]
        length: usize,

        /// Include uppercase letters
        #[arg(long, default_value = "true")]
        uppercase: bool,

        /// Include lowercase letters
        #[arg(long, default_value = "true")]
        lowercase: bool,

        /// Include digits
        #[arg(long, default_value = "true")]
        digits: bool,

        /// Include symbols
        #[arg(long, default_value = "true")]
        symbols: bool,

        /// Exclude ambiguous characters (0/O, 1/l/I)
        #[arg(long)]
        exclude_ambiguous: bool,

        /// Exclude similar characters (i, l, 1, L, o, 0, O)
        #[arg(long)]
        exclude_similar: bool,

        /// Copy to clipboard
        #[arg(long)]
        copy: bool,

        /// Show strength estimate
        #[arg(long)]
        show_strength: bool,
    },

    /// Generate a passphrase
    Passphrase {
        /// Number of words
        #[arg(short, long, default_value = "5")]
        words: usize,

        /// Word separator
        #[arg(short, long, default_value = "-")]
        separator: String,

        /// Capitalize each word
        #[arg(long)]
        capitalize: bool,

        /// Include a number
        #[arg(long)]
        include_number: bool,

        /// Copy to clipboard
        #[arg(long)]
        copy: bool,

        /// Show strength estimate
        #[arg(long)]
        show_strength: bool,
    },
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cli_parsing() {
        let cli = Cli::try_parse_from(["rustvault", "init"]);
        assert!(cli.is_ok());
        if let Ok(Cli { command, .. }) = cli {
            assert!(matches!(command, Commands::Init));
        }
    }

    #[test]
    fn test_entry_add_command() {
        let cli = Cli::try_parse_from([
            "rustvault",
            "entry",
            "add",
            "--title", "Test Entry",
            "--username", "user@example.com",
        ]);
        assert!(cli.is_ok());
    }

    #[test]
    fn test_generate_password_command() {
        let cli = Cli::try_parse_from([
            "rustvault",
            "generate",
            "password",
            "--length", "24",
            "--exclude-ambiguous",
        ]);
        assert!(cli.is_ok());
    }

    #[test]
    fn test_search_command() {
        let cli = Cli::try_parse_from(["rustvault", "search", "github"]);
        assert!(cli.is_ok());
    }
}
