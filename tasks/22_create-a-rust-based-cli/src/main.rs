mod clipboard;
mod cli;
mod crypto;
mod error;
mod models;
mod password;
mod storage;

use crate::clipboard::{copy_to_clipboard, clear_clipboard};
use crate::cli::{Cli, Commands};
use crate::error::{PasswordManagerError, Result};
use crate::models::Credential;
use crate::password::{calculate_entropy, estimate_strength, generate_password, PasswordOptions, PasswordStrength};
use crate::storage::{create_vault, save_vault, unlock_vault, vault_exists};
use colored::*;
use rpassword::prompt_password;
use std::io::{self, Write};
use std::path::PathBuf;
use std::time::Duration;

fn main() {
    let cli = Cli::parse();

    if let Err(e) = run(cli) {
        eprintln!("{}: {}", "Error".red().bold(), e);
        std::process::exit(1);
    }
}

fn run(cli: Cli) -> Result<()> {
    match cli.command {
        Commands::Init { force } => {
            handle_init(&cli.vault_path(), force)?;
        }
        Commands::Add {
            title,
            username,
            password,
            url,
            category,
            generate,
            length,
            symbols,
            exclude_ambiguous,
        } => {
            handle_add(
                &cli.vault_path(),
                title,
                username,
                password,
                url,
                category,
                generate,
                length,
                symbols,
                exclude_ambiguous,
            )?;
        }
        Commands::List {
            category,
            show_passwords,
        } => {
            handle_list(&cli.vault_path(), category.as_deref(), show_passwords)?;
        }
        Commands::Get { id, copy, clear_after } => {
            handle_get(&cli.vault_path(), &id, copy, clear_after)?;
        }
        Commands::Search {
            query,
            show_passwords,
        } => {
            handle_search(&cli.vault_path(), &query, show_passwords)?;
        }
        Commands::Update {
            id,
            title,
            username,
            password,
            url,
            category,
        } => {
            handle_update(
                &cli.vault_path(),
                &id,
                title,
                username,
                password,
                url,
                category,
            )?;
        }
        Commands::Delete { id, force } => {
            handle_delete(&cli.vault_path(), &id, force)?;
        }
        Commands::Generate {
            length,
            uppercase,
            lowercase,
            numbers,
            symbols,
            exclude_ambiguous,
            strength,
            copy,
            clear_after,
        } => {
            handle_generate(
                length,
                uppercase,
                lowercase,
                numbers,
                symbols,
                exclude_ambiguous,
                strength,
                copy,
                clear_after,
            )?;
        }
        Commands::Export { format, output } => {
            handle_export(&cli.vault_path(), &format, output)?;
        }
        Commands::Categories { count } => {
            handle_categories(&cli.vault_path(), count)?;
        }
        Commands::ChangePassword { verify } => {
            handle_change_password(&cli.vault_path(), verify)?;
        }
        Commands::Info { detailed } => {
            handle_info(&cli.vault_path(), detailed)?;
        }
    }

    Ok(())
}

fn get_master_password(confirm: bool) -> Result<String> {
    let password = prompt_password("Enter master password: ")?;
    if confirm {
        let confirm_password = prompt_password("Confirm master password: ")?;
        if password != confirm_password {
            return Err(PasswordManagerError::InvalidInput(
                "Passwords do not match".to_string(),
            ));
        }
    }
    Ok(password)
}

fn handle_init(vault_path: &PathBuf, force: bool) -> Result<()> {
    if vault_exists(vault_path) && !force {
        return Err(PasswordManagerError::InvalidInput(format!(
            "Vault already exists at {}. Use --force to overwrite.",
            vault_path.display()
        )));
    }

    println!("{}: {}", "Initializing vault".green().bold(), vault_path.display());
    let password = get_master_password(true)?;

    // Validate password strength
    let entropy = calculate_entropy(&password);
    if entropy < 60.0 {
        println!(
            "{}: Master password is weak ({} bits). Consider using a stronger password.",
            "Warning".yellow(),
            entropy as u32
        );
        print!("Continue anyway? [y/N]: ");
        io::stdout().flush()?;
        let mut response = String::new();
        io::stdin().read_line(&mut response)?;
        if !response.trim().to_lowercase().starts_with('y') {
            return Err(PasswordManagerError::Cancelled);
        }
    }

    create_vault(vault_path, &password)?;
    println!("{}", "Vault created successfully!".green());

    // Clear password from memory
    crypto::secure_wipe_string(&mut password.into_bytes().into_iter().collect::<String>());

    Ok(())
}

fn handle_add(
    vault_path: &PathBuf,
    title: Option<String>,
    username: Option<String>,
    password: Option<String>,
    url: Option<String>,
    category: Option<String>,
    generate: bool,
    length: usize,
    symbols: bool,
    exclude_ambiguous: bool,
) -> Result<()> {
    let master_password = get_master_password(false)?;
    let mut vault = unlock_vault(vault_path, &master_password)?;

    let title = title.unwrap_or_else(|| prompt("Title: ")?);
    let username = username.unwrap_or_else(|| prompt("Username/Email: ")?);

    let password = if generate {
        let options = PasswordOptions {
            length,
            use_uppercase: true,
            use_lowercase: true,
            use_numbers: true,
            use_symbols: symbols,
            exclude_ambiguous,
        };
        generate_password(options)?
    } else {
        password.unwrap_or_else(|| prompt_password("Password: ")?)
    };

    let url = url.or_else(|| prompt_opt("URL: ")?);
    let category = category.or_else(|| prompt_opt("Category: ")?);
    let notes = prompt_opt("Notes: ")?;

    let mut credential = Credential::new(title, username, password);
    credential.url = url;
    credential.category = category;
    credential.notes = notes;

    vault.add_credential(credential);
    save_vault(vault_path, &vault, &master_password)?;

    println!("{}", "Credential added successfully!".green());
    println!("ID: {}", vault.credentials.last().unwrap().id);

    Ok(())
}

fn handle_list(vault_path: &PathBuf, category: Option<&str>, show_passwords: bool) -> Result<()> {
    let master_password = get_master_password(false)?;
    let vault = unlock_vault(vault_path, &master_password)?;

    let credentials = vault.list_credentials(category);

    if credentials.is_empty() {
        println!("No credentials found.");
        return Ok(());
    }

    println!();
    println!("{:<10} {:<30} {:<25} {}", "ID", "Title", "Username", "Category");
    println!("{}", "-".repeat(80));

    for cred in credentials {
        let id_short = &cred.id[..8.min(cred.id.len())];
        let title = if cred.title.len() > 28 {
            format!("{}...", &cred.title[..25])
        } else {
            cred.title.clone()
        };
        let username = if cred.username.len() > 23 {
            format!("{}...", &cred.username[..20])
        } else {
            cred.username.clone()
        };
        let category = cred.category.as_deref().unwrap_or("");

        println!("{:<10} {:<30} {:<25} {}", id_short, title, username, category);

        if show_passwords {
            if let Some(ref pwd) = cred.password {
                println!("  Password: {}", pwd);
            }
        }
    }

    println!();
    println!("Total: {} credential(s)", credentials.len());

    Ok(())
}

fn handle_get(vault_path: &PathBuf, id: &str, copy: bool, clear_after: u64) -> Result<()> {
    let master_password = get_master_password(false)?;
    let vault = unlock_vault(vault_path, &master_password)?;

    // Try to find by ID or title
    let credential = vault.get_credential(id).or_else(|| {
        vault
            .credentials
            .iter()
            .find(|c| c.title.to_lowercase() == id.to_lowercase())
    });

    let credential = credential.ok_or_else(|| {
        PasswordManagerError::CredentialNotFound(format!("No credential found matching '{}'", id))
    })?;

    println!();
    println!("Title: {}", credential.title);
    println!("Username: {}", credential.username);
    println!("URL: {}", credential.url.as_deref().unwrap_or("N/A"));
    println!("Category: {}", credential.category.as_deref().unwrap_or("N/A"));
    println!("Notes: {}", credential.notes.as_deref().unwrap_or("N/A"));
    println!("Created: {}", credential.created_at.format("%Y-%m-%d %H:%M:%S UTC"));
    println!("Modified: {}", credential.modified_at.format("%Y-%m-%d %H:%M:%S UTC"));

    if let Some(ref password) = credential.password {
        if copy {
            let duration = if clear_after == 0 {
                None
            } else {
                Some(Duration::from_secs(clear_after))
            };
            copy_to_clipboard(password, duration)?;
            println!(
                "{}",
                "Password copied to clipboard".green().bold()
            );
            if let Some(d) = duration {
                println!("Clipboard will be cleared in {} seconds", d.as_secs());
            }
        } else {
            println!("Password: {}", password);
        }
    }

    Ok(())
}

fn handle_search(vault_path: &PathBuf, query: &str, show_passwords: bool) -> Result<()> {
    let master_password = get_master_password(false)?;
    let vault = unlock_vault(vault_path, &master_password)?;

    let credentials = vault.search_credentials(query);

    if credentials.is_empty() {
        println!("No credentials found matching '{}'.", query);
        return Ok(());
    }

    println!();
    println!("Found {} credential(s) matching '{}':", credentials.len(), query);
    println!("{:<10} {:<30} {:<25} {}", "ID", "Title", "Username", "Category");
    println!("{}", "-".repeat(80));

    for cred in credentials {
        let id_short = &cred.id[..8.min(cred.id.len())];
        println!(
            "{:<10} {:<30} {:<25} {}",
            id_short,
            cred.title,
            cred.username,
            cred.category.as_deref().unwrap_or("")
        );

        if show_passwords {
            if let Some(ref pwd) = cred.password {
                println!("  Password: {}", pwd);
            }
        }
    }

    Ok(())
}

fn handle_update(
    vault_path: &PathBuf,
    id: &str,
    title: Option<String>,
    username: Option<String>,
    password: Option<String>,
    url: Option<String>,
    category: Option<String>,
) -> Result<()> {
    let master_password = get_master_password(false)?;
    let mut vault = unlock_vault(vault_path, &master_password)?;

    // Find credential
    let credential = vault.get_credential(id).or_else(|| {
        vault
            .credentials
            .iter()
            .find(|c| c.title.to_lowercase() == id.to_lowercase())
    });

    let cred_id = credential
        .ok_or_else(|| {
            PasswordManagerError::CredentialNotFound(format!("No credential found matching '{}'", id))
        })?
        .id
        .clone();

    // Update fields
    if let Some(title) = title {
        vault.update_credential(&cred_id, |c| c.title = title)?;
    }
    if let Some(username) = username {
        vault.update_credential(&cred_id, |c| c.username = username)?;
    }
    if let Some(password) = password {
        vault.update_credential(&cred_id, |c| c.password = Some(password))?;
    }
    if let Some(url) = url {
        vault.update_credential(&cred_id, |c| c.url = Some(url))?;
    }
    if let Some(category) = category {
        vault.update_credential(&cred_id, |c| c.category = Some(category))?;
    }

    save_vault(vault_path, &vault, &master_password)?;
    println!("{}", "Credential updated successfully!".green());

    Ok(())
}

fn handle_delete(vault_path: &PathBuf, id: &str, force: bool) -> Result<()> {
    let master_password = get_master_password(false)?;
    let mut vault = unlock_vault(vault_path, &master_password)?;

    // Find credential
    let credential = vault.get_credential(id).or_else(|| {
        vault
            .credentials
            .iter()
            .find(|c| c.title.to_lowercase() == id.to_lowercase())
    });

    let cred_id = credential
        .ok_or_else(|| {
            PasswordManagerError::CredentialNotFound(format!("No credential found matching '{}'", id))
        })?
        .id
        .clone();
    let cred_title = credential.unwrap().title.clone();

    if !force {
        print!(
            "Are you sure you want to delete '{}'? [y/N]: ",
            cred_title
        );
        io::stdout().flush()?;
        let mut response = String::new();
        io::stdin().read_line(&mut response)?;
        if !response.trim().to_lowercase().starts_with('y') {
            println!("Cancelled.");
            return Ok(());
        }
    }

    vault.delete_credential(&cred_id)?;
    save_vault(vault_path, &vault, &master_password)?;
    println!("{}", "Credential deleted successfully!".green());

    Ok(())
}

fn handle_generate(
    length: usize,
    uppercase: bool,
    lowercase: bool,
    numbers: bool,
    symbols: bool,
    exclude_ambiguous: bool,
    show_strength: bool,
    copy: bool,
    clear_after: u64,
) -> Result<()> {
    let options = PasswordOptions {
        length,
        use_uppercase: uppercase,
        use_lowercase: lowercase,
        use_numbers,
        use_symbols,
        exclude_ambiguous,
    };

    let password = generate_password(options)?;

    println!("Generated password: {}", password);

    if show_strength {
        let strength = estimate_strength(&password);
        let entropy = calculate_entropy(&password);
        println!(
            "Strength: {} ({} bits)",
            strength.as_str().color(strength.color()).bold(),
            entropy as u32
        );
    }

    if copy {
        let duration = if clear_after == 0 {
            None
        } else {
            Some(Duration::from_secs(clear_after))
        };
        copy_to_clipboard(&password, duration)?;
        println!("{}", "Copied to clipboard!".green());
        if let Some(d) = duration {
            println!("Clipboard will be cleared in {} seconds", d.as_secs());
        }
    }

    Ok(())
}

fn handle_export(vault_path: &PathBuf, format: &str, output: Option<PathBuf>) -> Result<()> {
    let master_password = get_master_password(false)?;
    let vault = unlock_vault(vault_path, &master_password)?;

    let data = match format {
        "json" => serde_json::to_string_pretty(&vault.credentials)?,
        "csv" => {
            let mut csv = String::from("Title,Username,Password,URL,Category,Notes\n");
            for cred in &vault.credentials {
                csv.push_str(&format!(
                    "{},{},{},{},{},{}\n",
                    escape_csv(&cred.title),
                    escape_csv(&cred.username),
                    escape_csv(&cred.password.as_deref().unwrap_or("")),
                    escape_csv(&cred.url.as_deref().unwrap_or("")),
                    escape_csv(&cred.category.as_deref().unwrap_or("")),
                    escape_csv(&cred.notes.as_deref().unwrap_or(""))
                ));
            }
            csv
        }
        _ => {
            return Err(PasswordManagerError::InvalidInput(format!(
                "Unsupported export format: {}",
                format
            )))
        }
    };

    match output {
        Some(path) => {
            std::fs::write(&path, data)?;
            println!(
                "{}: Exported {} credentials to {}",
                "Success".green().bold(),
                vault.credentials.len(),
                path.display()
            );
        }
        None => {
            println!("\n{}", data);
        }
    }

    Ok(())
}

fn escape_csv(s: &str) -> String {
    if s.contains(',') || s.contains('"') || s.contains('\n') {
        format!("\"{}\"", s.replace("\"", "\"\""))
    } else {
        s.to_string()
    }
}

fn handle_categories(vault_path: &PathBuf, show_count: bool) -> Result<()> {
    let master_password = get_master_password(false)?;
    let vault = unlock_vault(vault_path, &master_password)?;

    let categories = vault.categories();

    if categories.is_empty() {
        println!("No categories found.");
        return Ok(());
    }

    println!("Categories:");
    for category in &categories {
        if show_count {
            let count = vault.list_credentials(Some(category)).len();
            println!("  {} ({})", category, count);
        } else {
            println!("  {}", category);
        }
    }

    Ok(())
}

fn handle_change_password(vault_path: &PathBuf, verify: bool) -> Result<()> {
    println!("Change master password");
    println!();

    let old_password = prompt_password("Current master password: ")?;

    // Verify old password if requested
    if verify {
        unlock_vault(vault_path, &old_password)?;
    }

    let new_password = get_master_password(true)?;

    // Unlock with old password
    let vault = unlock_vault(vault_path, &old_password)?;

    // Re-save with new password
    save_vault(vault_path, &vault, &new_password)?;

    println!("{}", "Master password changed successfully!".green());

    Ok(())
}

fn handle_info(vault_path: &PathBuf, detailed: bool) -> Result<()> {
    let master_password = get_master_password(false)?;
    let vault = unlock_vault(vault_path, &master_password)?;

    println!("Vault Information");
    println!();
    println!("Location: {}", vault_path.display());
    println!("Version: {}", vault.version);
    println!("Total credentials: {}", vault.credential_count());
    println!("Created: {}", vault.metadata.created_at.format("%Y-%m-%d %H:%M:%S UTC"));
    println!(
        "Last modified: {}",
        vault.metadata.modified_at.format("%Y-%m-%d %H:%M:%S UTC")
    );

    if detailed {
        println!();
        println!("Categories:");
        for category in vault.categories() {
            let count = vault.list_credentials(Some(&category)).len();
            println!("  {} ({})", category, count);
        }
    }

    Ok(())
}

fn prompt(prompt_text: &str) -> Result<String> {
    print!("{}", prompt_text);
    io::stdout().flush()?;

    let mut input = String::new();
    io::stdin().read_line(&mut input)?;
    Ok(input.trim().to_string())
}

fn prompt_opt(prompt_text: &str) -> Result<Option<String>> {
    print!("{}", prompt_text);
    io::stdout().flush()?;

    let mut input = String::new();
    io::stdin().read_line(&mut input)?;
    let trimmed = input.trim().to_string();
    Ok(if trimmed.is_empty() { None } else { Some(trimmed) })
}
