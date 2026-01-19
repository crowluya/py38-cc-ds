mod cli;
mod clipboard;
mod config;
mod crypto;
mod error;
mod storage;
mod validation;
mod vault;

use crate::cli::VaultUI;
use crate::config::{Config, ConfigManager};
use crate::storage::VaultStorage;
use crate::validation::{analyze_password, validate_password_requirements, PasswordStrength};
use crate::vault::Vault;
use anyhow::Result;
use rpassword::read_password;
use std::io::{self, Write};
use std::path::Path;

const VERSION: &str = env!("CARGO_PKG_VERSION");

fn main() -> Result<()> {
    let args: Vec<String> = std::env::args().collect();

    if args.len() < 2 {
        print_usage();
        return Ok(());
    }

    let command = args[1].as_str();

    match command {
        "init" => init_vault(),
        "unlock" | "open" => unlock_vault(),
        "version" | "--version" | "-v" => show_version(),
        "help" | "--help" | "-h" => print_usage(),
        _ => {
            eprintln!("Unknown command: {}", command);
            print_usage();
            std::process::exit(1);
        }
    }
}

fn init_vault() -> Result<()> {
    println!("=== VaultKeeper v{} Setup ===", VERSION);
    println!();

    let storage = VaultStorage::in_config_dir()?;

    if storage.vault_exists() {
        println!("❌ A vault already exists at: {:?}", storage.vault_path());
        println!("   Use 'vaultkeeper unlock' to open it.");
        return Ok(());
    }

    println!("Creating a new encrypted vault...");
    println!();

    // Get master password
    let password = read_password_with_prompt("Enter master password: ")?;
    let confirm = read_password_with_prompt("Confirm master password: ")?;

    if password != confirm {
        println!("❌ Passwords do not match!");
        return Ok(());
    }

    // Validate password strength
    let analysis = analyze_password(&password, &[]);

    if let Err(errors) = validate_password_requirements(&password) {
        println!("⚠️  Password does not meet requirements:");
        for error in errors {
            println!("   - {}", error);
        }
        println!();
        println!("Recommendations:");
        for suggestion in &analysis.suggestions {
            println!("   - {}", suggestion);
        }
        println!();
        println!("Continue anyway? (y/N): ");
        let mut input = String::new();
        io::stdin().read_line(&mut input)?;
        if !input.trim().to_lowercase().starts_with('y') {
            println!("Setup cancelled.");
            return Ok(());
        }
    } else {
        match analysis.strength {
            PasswordStrength::Weak => {
                println!("⚠️  Weak password detected. Consider using a stronger password.");
            }
            PasswordStrength::Fair => {
                println!("ℹ️  Fair password strength.");
            }
            PasswordStrength::Good | PasswordStrength::Strong => {
                println!("✓ Good password strength!");
            }
        }
    }

    // Create vault
    let vault = Vault::new();
    storage.create_vault(&vault, &password)?;

    println!();
    println!("✓ Vault created successfully at: {:?}", storage.vault_path());
    println!("  Use 'vaultkeeper unlock' to start managing passwords.");
    println!();
    println!("🔐 Remember your master password! It cannot be recovered.");

    Ok(())
}

fn unlock_vault() -> Result<()> {
    let storage = VaultStorage::in_config_dir()?;

    if !storage.vault_exists() {
        println!("❌ No vault found at: {:?}", storage.vault_path());
        println!("   Use 'vaultkeeper init' to create a new vault.");
        return Ok(());
    }

    println!("=== VaultKeeper v{} ===", VERSION);
    println!();

    // Get master password
    let password = read_password_with_prompt("Enter master password: ")?;

    // Load vault
    let vault = storage.load_vault(&password);

    if vault.is_err() {
        println!("❌ Incorrect master password!");
        return Ok(());
    }

    let mut vault = vault.unwrap();

    println!("✓ Vault unlocked!");
    println!("  Loading entries...\n");

    // Load config
    let config_manager = ConfigManager::in_config_dir()?;
    let config = config_manager.config().clone();

    // Start UI
    let mut ui = VaultUI::new(config)?;

    let updated_vault = ui.run(vault);

    // Save vault on exit
    if let Ok(updated_vault) = updated_vault {
        storage.save_vault(&updated_vault, &password)?;
        println!("\n✓ Vault saved successfully.");
    }

    Ok(())
}

fn show_version() {
    println!("VaultKeeper v{}", VERSION);
    println!("A secure, interactive CLI password manager with AES-256 encryption");
}

fn print_usage() {
    println!("VaultKeeper v{} - Secure Password Manager", VERSION);
    println!();
    println!("USAGE:");
    println!("  vaultkeeper <COMMAND>");
    println!();
    println!("COMMANDS:");
    println!("  init          Create a new encrypted vault");
    println!("  unlock        Open and manage the vault");
    println!("  open          Alias for 'unlock'");
    println!("  version       Show version information");
    println!("  help          Show this help message");
    println!();
    println!("EXAMPLES:");
    println!("  $ vaultkeeper init");
    println!("  $ vaultkeeper unlock");
    println!();
    println!("Once unlocked, use the following keybindings:");
    println!("  ↑/↓           Navigate entries");
    println!("  / or s        Search entries");
    println!("  Enter         View entry details");
    println!("  a             Add new entry");
    println!("  e             Edit entry");
    println!("  d             Delete entry");
    println!("  c             Copy password to clipboard");
    println!("  q             Quit and save");
    println!();
    println!("For more information, visit: https://github.com/vaultkeeper/vaultkeeper");
}

fn read_password_with_prompt(prompt: &str) -> Result<String> {
    print!("{}", prompt);
    io::stdout().flush()?;
    let password = read_password()?;
    Ok(password)
}
