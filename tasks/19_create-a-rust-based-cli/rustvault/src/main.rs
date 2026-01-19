//! RustVault - A secure CLI password manager
//!
//! Main application entry point and command handlers.

use anyhow::{Context, Result};
use clap::Parser;
use inquire::{Confirm, Password, PasswordDisplayMode, Text};
use rustvault::{
    cli::{Cli, Commands, EntryCommands, FolderCommands, GenerateCommands},
    copy_to_clipboard, generate_passphrase, generate_password, generate_totp_default,
    estimate_strength, PassphrasePolicy, PasswordPolicy, VaultEntry, VaultSession, VaultStorage,
};
use std::path::PathBuf;
use std::thread;
use std::time::Duration;

fn main() -> Result<()> {
    let cli = Cli::parse();

    // Initialize logger if verbose
    if cli.verbose {
        env_logger::Builder::from_default_env()
            .filter_level(log::LevelFilter::Debug)
            .init();
    }

    // Determine vault path
    let vault_path = cli.vault_path.unwrap_or_else(|| {
        VaultStorage::default_vault_path().expect("Could not determine vault path")
    });

    // Execute command
    match cli.command {
        Commands::Init => cmd_init(&vault_path),
        Commands::Unlock => cmd_unlock(&vault_path),
        Commands::Lock => cmd_lock(),
        Commands::Entry(entry_cmd) => cmd_entry(&vault_path, entry_cmd),
        Commands::Folder(folder_cmd) => cmd_folder(&vault_path, folder_cmd),
        Commands::Generate(gen_cmd) => cmd_generate(gen_cmd),
        Commands::Totp { entry, folder } => cmd_totp(&vault_path, entry, folder),
        Commands::Search { query, full } => cmd_search(&vault_path, query, full),
        Commands::Export { path, plaintext } => cmd_export(&vault_path, path, plaintext),
        Commands::Import { path } => cmd_import(&vault_path, path),
        Commands::Status => cmd_status(&vault_path),
    }
}

/// Initialize a new vault
fn cmd_init(vault_path: &PathBuf) -> Result<()> {
    println!("Initializing new vault at: {}", vault_path.display());

    if VaultStorage::new(vault_path.clone()).vault_exists() {
        println!("❌ Vault already exists at this location.");
        println!("If you want to create a new vault, please delete or backup the existing one first.");
        return Ok(());
    }

    // Prompt for master password
    let password = Password::new("Master password:")
        .with_display_toggle_enabled()
        .with_display_mode(PasswordDisplayMode::Hidden)
        .prompt()?;

    let confirm = Password::new("Confirm master password:")
        .with_display_toggle_enabled()
        .with_display_mode(PasswordDisplayMode::Hidden)
        .prompt()?;

    if password != confirm {
        println!("❌ Passwords do not match!");
        return Ok(());
    }

    if password.len() < 8 {
        println!("❌ Master password must be at least 8 characters long.");
        return Ok(());
    }

    // Create the vault
    let storage = VaultStorage::new(vault_path.clone());
    storage.create_vault(&password)?;

    println!("✅ Vault created successfully!");
    println!("⚠️  Remember your master password - it cannot be recovered!");

    Ok(())
}

/// Unlock the vault
fn cmd_unlock(vault_path: &PathBuf) -> Result<()> {
    let storage = VaultStorage::new(vault_path.clone());

    if !storage.vault_exists() {
        println!("❌ Vault not found. Use 'rustvault init' to create a new vault.");
        return Ok(());
    }

    println!("🔐 Unlocking vault...");

    let password = Password::new("Master password:")
        .with_display_toggle_enabled()
        .with_display_mode(PasswordDisplayMode::Hidden)
        .prompt()?;

    let session = VaultSession::new(storage, 5);

    match session.unlock(&password) {
        Ok(()) => {
            println!("✅ Vault unlocked!");
            println!("Your vault is now available for operations.");
            println!("The vault will auto-lock after 5 minutes of inactivity.");
            Ok(())
        }
        Err(e) => {
            println!("❌ Failed to unlock vault: {}", e);
            Err(e)
        }
    }
}

/// Lock the vault
fn cmd_lock() -> Result<()> {
    // This would need session state management
    println!("🔒 Vault locked.");
    Ok(())
}

/// Entry commands
fn cmd_entry(vault_path: &PathBuf, cmd: EntryCommands) -> Result<()> {
    let storage = VaultStorage::new(vault_path.clone());

    match cmd {
        EntryCommands::Add {
            title,
            username,
            password,
            url,
            notes,
            tags,
            folder,
            generate_password,
            password_length,
        } => {
            let session = unlock_session(&storage)?;

            // Prompt for missing fields
            let title = title.unwrap_or_else(|| {
                Text::new("Entry title:").prompt().unwrap_or_default()
            });

            let username = username.unwrap_or_else(|| {
                Text::new("Username:").prompt().unwrap_or_default()
            });

            let password = if generate_password {
                let policy = PasswordPolicy::new(password_length);
                generate_password(&policy).unwrap()
            } else {
                password.unwrap_or_else(|| {
                    Password::new("Password:")
                        .with_display_toggle_enabled()
                        .prompt()
                        .unwrap_or_default()
                })
            };

            let url = url.unwrap_or_else(|| {
                Text::new("URL (optional):")
                    .prompt()
                    .unwrap_or_default()
            });

            let notes = notes.unwrap_or_else(|| {
                Text::new("Notes (optional):")
                    .prompt()
                    .unwrap_or_default()
            });

            let tags: Vec<String> = tags
                .unwrap_or_default()
                .split(',')
                .map(|s| s.trim().to_string())
                .filter(|s| !s.is_empty())
                .collect();

            let entry = VaultEntry::new(title.clone(), username, password);
            let entry = VaultEntry {
                url: if url.is_empty() { None } else { Some(url) },
                notes: if notes.is_empty() { None } else { Some(notes) },
                tags,
                ..entry
            };

            session.with_vault_mut(|vault| {
                vault.add_entry(&folder, entry)?;
                Ok(())
            })?;

            println!("✅ Entry '{}' added successfully!", title);
            Ok(())
        }

        EntryCommands::List { folder, show_passwords } => {
            let session = unlock_session(&storage)?;

            let entries = session.with_vault(|vault| {
                Ok(vault.list_entries(&folder))
            })?;

            if entries.is_empty() {
                println!("📭 No entries found in folder '{}'", folder);
            } else {
                println!("📋 Entries in folder '{}':", folder);
                println!();
                for entry in entries {
                    println!("  📌 {}", entry.title);
                    println!("     👤 {}", entry.username);
                    if let Some(url) = &entry.url {
                        println!("     🔗 {}", url);
                    }
                    if show_passwords {
                        println!("     🔑 {}", entry.password);
                    }
                    if !entry.tags.is_empty() {
                        println!("     🏷️  {}", entry.tags.join(", "));
                    }
                    println!();
                }
            }

            Ok(())
        }

        EntryCommands::Show {
            entry,
            folder,
            show_password,
            copy_password,
            copy_totp,
        } => {
            let session = unlock_session(&storage)?;

            let entry = session.with_vault(|vault| {
                let entries = vault.list_entries(&folder);
                entries
                    .into_iter()
                    .find(|e| e.id == entry || e.title == entry)
                    .ok_or_else(|| anyhow::anyhow!("Entry not found"))
            })?;

            println!("📌 {}", entry.title);
            println!("👤 Username: {}", entry.username);

            if let Some(url) = &entry.url {
                println!("🔗 URL: {}", url);
            }

            if let Some(notes) = &entry.notes {
                println!("📝 Notes: {}", notes);
            }

            if !entry.tags.is_empty() {
                println!("🏷️  Tags: {}", entry.tags.join(", "));
            }

            if let Some(totp_secret) = &entry.totp_secret {
                let totp = generate_totp_default(totp_secret)?;
                println!("🔐 TOTP: {} (expires in {}s)", totp.code, totp.remaining_seconds);

                if copy_totp {
                    copy_to_clipboard(&totp.code)?;
                    println!("✅ TOTP code copied to clipboard!");
                }
            }

            if show_password {
                println!("🔑 Password: {}", entry.password);
            }

            if copy_password {
                copy_to_clipboard(&entry.password)?;
                println!("✅ Password copied to clipboard!");

                // Clear clipboard after 30 seconds
                let password = entry.password.clone();
                thread::spawn(move || {
                    thread::sleep(Duration::from_secs(30));
                    let _ = copy_to_clipboard(&"");
                    println!("🔒 Clipboard cleared");
                });
            }

            Ok(())
        }

        EntryCommands::Delete { entry, folder, force } => {
            let session = unlock_session(&storage)?;

            if !force {
                let confirm = Confirm::new("Are you sure you want to delete this entry?")
                    .with_default(false)
                    .prompt()?;

                if !confirm {
                    println!("❌ Deletion cancelled.");
                    return Ok(());
                }
            }

            session.with_vault_mut(|vault| {
                // Find entry by title or ID
                let entries = vault.list_entries(&folder);
                let entry_id = entries
                    .into_iter()
                    .find(|e| e.id == entry || e.title == entry)
                    .map(|e| e.id)
                    .ok_or_else(|| anyhow::anyhow!("Entry not found"))?;

                vault.delete_entry(&folder, &entry_id)
            })?;

            println!("✅ Entry deleted successfully!");
            Ok(())
        }

        EntryCommands::Edit { entry, folder } => {
            println!("⚠️  Edit functionality is not yet implemented.");
            println!("💡 For now, delete and recreate the entry.");
            Ok(())
        }
    }
}

/// Folder commands
fn cmd_folder(vault_path: &PathBuf, cmd: FolderCommands) -> Result<()> {
    let storage = VaultStorage::new(vault_path.clone());
    let session = unlock_session(&storage)?;

    match cmd {
        FolderCommands::Add { name, parent } => {
            let path = if parent.is_empty() {
                name.clone()
            } else {
                format!("{}/{}", parent, name)
            };

            session.with_vault_mut(|vault| {
                vault.create_folder(&path, &name)
            })?;

            println!("✅ Folder '{}' created successfully!", path);
            Ok(())
        }

        FolderCommands::List => {
            let folders = session.with_vault(|vault| {
                Ok(vault.list_folders())
            })?;

            println!("📁 Folders:");
            for folder in folders {
                println!("  📂 {}", if folder.is_empty() { "[root]" } else { &folder });
            }
            Ok(())
        }

        FolderCommands::Rename { current, new_path } => {
            println!("⚠️  Folder rename is not yet implemented.");
            Ok(())
        }

        FolderCommands::Delete { path, force, recursive } => {
            if !force {
                let confirm = Confirm::new(&format!("Delete folder '{}' and all contents?", path))
                    .with_default(false)
                    .prompt()?;

                if !confirm {
                    println!("❌ Deletion cancelled.");
                    return Ok(());
                }
            }

            println!("⚠️  Folder delete is not yet implemented.");
            Ok(())
        }
    }
}

/// Password generation commands
fn cmd_generate(cmd: GenerateCommands) -> Result<()> {
    match cmd {
        GenerateCommands::Password {
            length,
            uppercase,
            lowercase,
            digits,
            symbols,
            exclude_ambiguous,
            exclude_similar,
            copy,
            show_strength,
        } => {
            let mut policy = PasswordPolicy::new(length);
            policy.uppercase = uppercase;
            policy.lowercase = lowercase;
            policy.digits = digits;
            policy.symbols = symbols;
            policy.exclude_ambiguous = exclude_ambiguous;
            policy.exclude_similar = exclude_similar;

            let password = generate_password(&policy)?;

            println!("🔑 Generated Password:");
            println!("{}", password);

            if show_strength {
                let strength = estimate_strength(&password);
                println!("Strength: {}", strength.description());
            }

            if copy {
                copy_to_clipboard(&password)?;
                println!("✅ Password copied to clipboard!");
            }

            Ok(())
        }

        GenerateCommands::Passphrase {
            words,
            separator,
            capitalize,
            include_number,
            copy,
            show_strength,
        } => {
            let policy = PassphrasePolicy {
                word_count: words,
                separator,
                capitalize,
                include_number,
            };

            let passphrase = generate_passphrase(&policy)?;

            println!("🔑 Generated Passphrase:");
            println!("{}", passphrase);

            if show_strength {
                let strength = estimate_strength(&passphrase);
                println!("Strength: {}", strength.description());
            }

            if copy {
                copy_to_clipboard(&passphrase)?;
                println!("✅ Passphrase copied to clipboard!");
            }

            Ok(())
        }
    }
}

/// TOTP command
fn cmd_totp(vault_path: &PathBuf, entry: String, folder: String) -> Result<()> {
    let storage = VaultStorage::new(vault_path.clone());
    let session = unlock_session(&storage)?;

    let entry_data = session.with_vault(|vault| {
        let entries = vault.list_entries(&folder);
        entries
            .into_iter()
            .find(|e| e.id == entry || e.title == entry)
            .ok_or_else(|| anyhow::anyhow!("Entry not found"))
    })?;

    let totp_secret = entry_data.totp_secret.as_ref()
        .ok_or_else(|| anyhow::anyhow!("This entry does not have a TOTP secret configured"))?;

    let totp = generate_totp_default(totp_secret)?;

    println!("🔐 TOTP Code:");
    println!("{}", totp.code);
    println!("Expires in: {}s", totp.remaining_seconds);

    Ok(())
}

/// Search command
fn cmd_search(vault_path: &PathBuf, query: String, full: bool) -> Result<()> {
    let storage = VaultStorage::new(vault_path.clone());
    let session = unlock_session(&storage)?;

    let results = session.with_vault(|vault| {
        Ok(vault.search(&query))
    })?;

    if results.is_empty() {
        println!("🔍 No results found for '{}'", query);
    } else {
        println!("🔍 Search results for '{}':", query);
        println!();
        for result in results {
            println!("📌 {}", result.entry.title);
            println!("   👤 {}", result.entry.username);
            if let Some(url) = &result.entry.url {
                println!("   🔗 {}", url);
            }
            println!("   📂 {}", if result.folder_path.is_empty() { "[root]" } else { &result.folder_path });

            if full {
                if !result.entry.tags.is_empty() {
                    println!("   🏷️  {}", result.entry.tags.join(", "));
                }
                if let Some(notes) = &result.entry.notes {
                    println!("   📝 {}", notes);
                }
            }
            println!();
        }
    }

    Ok(())
}

/// Export command
fn cmd_export(vault_path: &PathBuf, path: PathBuf, plaintext: bool) -> Result<()> {
    let storage = VaultStorage::new(vault_path.clone());

    if plaintext {
        let password = Password::new("Master password:")
            .with_display_toggle_enabled()
            .with_display_mode(PasswordDisplayMode::Hidden)
            .prompt()?;

        storage.export_decrypted(&password, &path)?;
        println!("✅ Vault exported to: {}", path.display());
        println!("⚠️  WARNING: The export is unencrypted plaintext!");
    } else {
        println!("⚠️  Encrypted export is not yet implemented.");
        println!("💡 Use --plaintext flag for unencrypted export.");
    }

    Ok(())
}

/// Import command
fn cmd_import(vault_path: &PathBuf, path: PathBuf) -> Result<()> {
    let storage = VaultStorage::new(vault_path.clone());

    let password = Password::new("Master password:")
        .with_display_toggle_enabled()
        .with_display_mode(PasswordDisplayMode::Hidden)
        .prompt()?;

    storage.import_decrypted(&path, &password)?;
    println!("✅ Vault imported from: {}", path.display());

    Ok(())
}

/// Status command
fn cmd_status(vault_path: &PathBuf) -> Result<()> {
    let storage = VaultStorage::new(vault_path.clone());

    if !storage.vault_exists() {
        println!("❌ Vault not found at: {}", vault_path.display());
        println!("💡 Use 'rustvault init' to create a new vault.");
        return Ok(());
    }

    println!("📊 Vault Status:");
    println!("   Location: {}", vault_path.display());
    println!("   Status: Initialized");

    // Try to get vault info (will fail if wrong password, but we can show basic info)
    let _ = (|| -> Result<()> {
        let password = Password::new("Master password:")
            .with_display_toggle_enabled()
            .with_display_mode(PasswordDisplayMode::Hidden)
            .prompt()?;

        let vault = storage.load_vault(&password)?;
        println!("   Entries: {}", vault.metadata.entry_count);
        println!("   Folders: {}", vault.folders.len());
        println!("   Version: {}", vault.version);
        println!("   Last updated: {}", vault.metadata.updated_at.format("%Y-%m-%d %H:%M:%S UTC"));

        Ok(())
    })();

    Ok(())
}

/// Helper function to unlock the vault session
fn unlock_session(storage: &VaultStorage) -> Result<VaultSession> {
    println!("🔐 Unlocking vault...");

    let password = Password::new("Master password:")
        .with_display_toggle_enabled()
        .with_display_mode(PasswordDisplayMode::Hidden)
        .prompt()?;

    let session = VaultSession::new(storage.clone(), 5);
    session.unlock(&password)?;

    Ok(session)
}

// Temporary alias for Entry (to fix compilation)
type VaultEntry = rustvault::Entry;
