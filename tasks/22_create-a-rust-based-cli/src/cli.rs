use clap::{Parser, Subcommand};
use std::path::PathBuf;

/// A secure CLI password manager with AES-256-GCM encryption
#[derive(Parser, Debug)]
#[command(name = "passman")]
#[command(author = "Your Name <you@example.com>")]
#[command(version = "0.1.0")]
#[command(about = "Secure password manager with AES-256-GCM encryption", long_about = None)]
pub struct Cli {
    /// Path to the vault file (default: ~/.passman/default.vault)
    #[arg(short, long, global = true)]
    pub vault: Option<PathBuf>,

    /// Enable verbose output
    #[arg(short, long, global = true)]
    pub verbose: bool,

    #[command(subcommand)]
    pub command: Commands,
}

#[derive(Subcommand, Debug)]
pub enum Commands {
    /// Initialize a new vault
    Init {
        /// Force initialization even if vault exists
        #[arg(long)]
        force: bool,
    },

    /// Add a new credential
    Add {
        /// Title/Name of the credential
        #[arg(short, long)]
        title: Option<String>,

        /// Username/Email
        #[arg(short, long)]
        username: Option<String>,

        /// Password (if not provided, will be generated or prompted)
        #[arg(short, long)]
        password: Option<String>,

        /// URL
        #[arg(short = 'u', long)]
        url: Option<String>,

        /// Category/Tag
        #[arg(short = 'c', long)]
        category: Option<String>,

        /// Generate a random password instead of prompting
        #[arg(long)]
        generate: bool,

        /// Password length (for --generate)
        #[arg(long, default_value = "20")]
        length: usize,

        /// Use symbols in generated password
        #[arg(long, default_value = "true")]
        symbols: bool,

        /// Exclude ambiguous characters (0, O, 1, l, I)
        #[arg(long)]
        exclude_ambiguous: bool,
    },

    /// List all credentials
    List {
        /// Filter by category
        category: Option<String>,

        /// Show passwords in output
        #[arg(long)]
        show_passwords: bool,
    },

    /// Get a credential by ID or title
    Get {
        /// ID or title of the credential
        id: String,

        /// Copy password to clipboard
        #[arg(long)]
        copy: bool,

        /// Clear clipboard after N seconds (0 = never)
        #[arg(long, default_value = "30")]
        clear_after: u64,
    },

    /// Search credentials by title, username, or URL
    Search {
        /// Search query
        query: String,

        /// Show passwords in output
        #[arg(long)]
        show_passwords: bool,
    },

    /// Update an existing credential
    Update {
        /// ID or title of the credential
        id: String,

        /// New title
        #[arg(long)]
        title: Option<String>,

        /// New username
        #[arg(long)]
        username: Option<String>,

        /// New password
        #[arg(long)]
        password: Option<String>,

        /// New URL
        #[arg(short = 'u', long)]
        url: Option<String>,

        /// New category
        #[arg(short = 'c', long)]
        category: Option<String>,
    },

    /// Delete a credential
    Delete {
        /// ID or title of the credential
        id: String,

        /// Skip confirmation prompt
        #[arg(long)]
        force: bool,
    },

    /// Generate a random password
    Generate {
        /// Password length
        #[arg(short, long, default_value = "20")]
        length: usize,

        /// Include uppercase letters
        #[arg(long, default_value = "true")]
        uppercase: bool,

        /// Include lowercase letters
        #[arg(long, default_value = "true")]
        lowercase: bool,

        /// Include numbers
        #[arg(long, default_value = "true")]
        numbers: bool,

        /// Include symbols
        #[arg(long, default_value = "true")]
        symbols: bool,

        /// Exclude ambiguous characters (0, O, 1, l, I)
        #[arg(long)]
        exclude_ambiguous: bool,

        /// Show password strength
        #[arg(long)]
        strength: bool,

        /// Copy to clipboard
        #[arg(long)]
        copy: bool,

        /// Clear clipboard after N seconds
        #[arg(long, default_value = "30")]
        clear_after: u64,
    },

    /// Export credentials to unencrypted format
    Export {
        /// Export format (json, csv)
        #[arg(short, long, default_value = "json")]
        format: String,

        /// Output file (default: stdout)
        #[arg(short, long)]
        output: Option<PathBuf>,
    },

    /// List all categories
    Categories {
        /// Show credential count per category
        #[arg(long)]
        count: bool,
    },

    /// Change master password
    ChangePassword {
        /// Verify old password before changing
        #[arg(long)]
        verify: bool,
    },

    /// Show vault information
    Info {
        /// Show detailed information
        #[arg(long)]
        detailed: bool,
    },
}

impl Cli {
    /// Get the vault path, using default if not specified
    pub fn vault_path(&self) -> PathBuf {
        if let Some(ref path) = self.vault {
            path.clone()
        } else {
            // Default to ~/.passman/default.vault
            let mut home = dirs::home_dir().unwrap_or_else(|| PathBuf::from("."));
            home.push(".passman");
            home.push("default.vault");
            home
        }
    }
}
