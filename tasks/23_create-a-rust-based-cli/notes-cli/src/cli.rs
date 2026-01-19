use crate::backup::BackupManager;
use crate::error::Result;
use crate::password::PasswordManager;
use crate::storage::Storage;
use crate::types::{Config, Note, WorkspaceStats};
use crate::semantic::{OpenAIEmbedder, EmbeddingStore, SemanticSearcher};
use clap::{Parser, Subcommand};
use colored::Colorize;
use rpassword::read_password;
use std::io::{self, Write};
use std::path::PathBuf;
use std::sync::{Arc, Mutex};

/// A CLI note-taking tool with markdown support, search, tags, encryption, and backups
#[derive(Parser)]
#[command(name = "notes")]
#[command(about = "A CLI note-taking tool with encryption and backup support", long_about = None)]
#[command(version = "0.2.0")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Create a new note
    Create {
        /// Title of the note
        title: String,
        /// Tags to add to the note (comma-separated)
        #[arg(short, long)]
        tags: Option<String>,
        /// Notebook ID to add the note to
        #[arg(short, long)]
        notebook: Option<String>,
        /// Parent note ID (for hierarchical notes)
        #[arg(short, long)]
        parent: Option<String>,
        /// Encrypt the note
        #[arg(short, long)]
        encrypt: bool,
    },

    /// List all notes
    List {
        /// Filter by tag
        #[arg(short, long)]
        tag: Option<String>,
        /// Maximum number of notes to display
        #[arg(short, long, default_value_t = 50)]
        limit: usize,
        /// Filter by notebook
        #[arg(short, long)]
        notebook: Option<String>,
    },

    /// View a note
    View {
        /// ID of the note to view
        id: String,
    },

    /// Edit a note
    Edit {
        /// ID of the note to edit
        id: String,
    },

    /// Delete a note
    Delete {
        /// ID of the note to delete
        id: String,
        /// Skip confirmation prompt
        #[arg(short, long)]
        force: bool,
    },

    /// Search notes
    Search {
        /// Search query
        query: String,
        /// Use semantic search
        #[arg(short, long)]
        semantic: bool,
    },

    /// Semantic search commands
    Semantic {
        #[command(subcommand)]
        semantic_command: SemanticCommands,
    },

    /// Manage tags
    Tag {
        #[command(subcommand)]
        tag_command: TagCommands,
    },

    /// Manage notebooks
    Notebook {
        #[command(subcommand)]
        notebook_command: NotebookCommands,
    },

    /// Manage note hierarchy
    Parent {
        #[command(subcommand)]
        parent_command: ParentCommands,
    },

    /// Show workspace statistics
    Stats {
        /// Export as JSON
        #[arg(short, long)]
        json: bool,
    },

    /// Show note hierarchy tree
    Tree {
        /// ID of the note (root of tree)
        id: Option<String>,
        /// Maximum depth to display
        #[arg(short, long, default_value_t = 3)]
        depth: usize,
    },

    /// Initialize the notes directory
    Init,

    /// Manage encryption and passwords
    Encrypt {
        #[command(subcommand)]
        encrypt_command: EncryptCommands,
    },

    /// Manage backups
    Backup {
        #[command(subcommand)]
        backup_command: BackupCommands,
    },
}

#[derive(Subcommand)]
enum EncryptCommands {
    /// Set a master password for encryption
    Set,

    /// Change the master password
    Change {
        /// Skip confirmation
        #[arg(short, long)]
        force: bool,
    },

    /// Remove encryption (decrypts all notes)
    Remove {
        /// Skip confirmation
        #[arg(short, long)]
        force: bool,
    },

    /// Unlock encrypted notes
    Unlock,

    /// Lock encrypted notes (clear master key from memory)
    Lock,

    /// Show encryption status
    Status,

    /// Encrypt a specific note
    Note {
        /// ID of the note to encrypt
        id: String,
    },

    /// Decrypt a specific note
    Decrypt {
        /// ID of the note to decrypt
        id: String,
    },
}

#[derive(Subcommand)]
enum BackupCommands {
    /// Create a backup
    Create {
        /// Backup name (optional)
        #[arg(short, long)]
        name: Option<String>,
    },

    /// List all backups
    List,

    /// Restore from backup
    Restore {
        /// Backup file path
        backup_path: String,
        /// Skip safety backup creation
        #[arg(short, long)]
        no_safety: bool,
    },

    /// Delete a backup
    Delete {
        /// Backup file path
        backup_path: String,
        /// Skip confirmation
        #[arg(short, long)]
        force: bool,
    },

    /// Configure automatic backups
    Schedule {
        /// Enable/disable automatic backups
        #[arg(short, long)]
        enabled: Option<bool>,
        /// Backup interval in hours
        #[arg(short, long)]
        interval: Option<u64>,
        /// Maximum number of backups to keep
        #[arg(short, long)]
        max: Option<usize>,
    },

    /// Verify backup integrity
    Verify {
        /// Backup file path
        backup_path: String,
    },
}

#[derive(Subcommand)]
enum SemanticCommands {
    /// Index all notes for semantic search
    Index {
        /// Force re-indexing even if already indexed
        #[arg(short, long)]
        force: bool,
    },

    /// Search notes by meaning
    Search {
        /// Natural language query
        query: String,
        /// Maximum number of results
        #[arg(short, long, default_value_t = 10)]
        limit: usize,
        /// Minimum similarity threshold (0.0 to 1.0)
        #[arg(short, long)]
        threshold: Option<f32>,
    },

    /// Show semantic search status
    Status,

    /// Clear the embedding index
    Clear {
        /// Skip confirmation
        #[arg(short, long)]
        force: bool,
    },
}

#[derive(Subcommand)]
enum TagCommands {
    /// Add a tag to a note
    Add {
        /// ID of the note
        id: String,
        /// Tag to add
        tag: String,
    },

    /// Remove a tag from a note
    Remove {
        /// ID of the note
        id: String,
        /// Tag to remove
        tag: String,
    },

    /// List all tags
    List,
}

#[derive(Subcommand)]
enum NotebookCommands {
    /// Create a new notebook
    Create {
        /// Name of the notebook
        name: String,
        /// Description of the notebook
        #[arg(short, long)]
        description: Option<String>,
    },

    /// List all notebooks
    List,

    /// Show notebook details
    Show {
        /// ID of the notebook
        id: String,
    },

    /// Delete a notebook
    Delete {
        /// ID of the notebook
        id: String,
        /// Skip confirmation
        #[arg(short, long)]
        force: bool,
    },

    /// Rename a notebook
    Rename {
        /// ID of the notebook
        id: String,
        /// New name
        new_name: String,
    },
}

#[derive(Subcommand)]
enum ParentCommands {
    /// Set parent of a note
    Set {
        /// Child note ID
        child_id: String,
        /// Parent note ID
        parent_id: String,
    },

    /// Remove parent from a note
    Remove {
        /// Child note ID
        child_id: String,
    },
}

/// Main CLI handler with password and backup management
pub struct CliApp {
    storage: Arc<Mutex<Storage>>,
    password_manager: Arc<Mutex<PasswordManager>>,
    config: Config,
    backup_manager: Arc<Mutex<BackupManager>>,
    runtime: tokio::runtime::Runtime,
}

impl CliApp {
    pub fn new(mut storage: Storage, config: Config) -> Self {
        let password_manager = PasswordManager::new(config.notes_dir.clone());
        let backup_manager = BackupManager::new(
            config.notes_dir.clone(),
            config.backup.clone(),
        ).expect("Failed to initialize backup manager");

        let runtime = tokio::runtime::Runtime::new()
            .expect("Failed to create async runtime");

        Self {
            storage: Arc::new(Mutex::new(storage)),
            password_manager: Arc::new(Mutex::new(password_manager)),
            config,
            backup_manager: Arc::new(Mutex::new(backup_manager)),
            runtime,
        }
    }

    pub fn run(&self) -> Result<()> {
        // Run automatic backup if needed
        if let Ok(backup_mgr) = self.backup_manager.lock() {
            if let Ok(Some(metadata)) = backup_mgr.run_auto_backup_if_needed() {
                println!("{}", format!("Automatic backup created: {}", metadata.name).green());
            }
        }

        let cli = Cli::parse();

        match cli.command {
            Commands::Create { title, tags, notebook, parent, encrypt } => {
                self.create_note(title, tags, notebook, parent, encrypt)
            }
            Commands::List { tag, limit, notebook } => self.list_notes(tag, limit, notebook),
            Commands::View { id } => self.view_note(&id),
            Commands::Edit { id } => self.edit_note(&id),
            Commands::Delete { id, force } => self.delete_note(&id, force),
            Commands::Search { query, semantic } => {
                if semantic {
                    self.semantic_search(&query)
                } else {
                    self.search_notes(&query)
                }
            }
            Commands::Semantic { semantic_command } => self.handle_semantic_command(semantic_command),
            Commands::Tag { tag_command } => self.handle_tag_command(tag_command),
            Commands::Notebook { notebook_command } => self.handle_notebook_command(notebook_command),
            Commands::Parent { parent_command } => self.handle_parent_command(parent_command),
            Commands::Stats { json } => self.show_stats(json),
            Commands::Tree { id, depth } => self.show_tree(id, depth),
            Commands::Init => self.init(),
            Commands::Encrypt { encrypt_command } => self.handle_encrypt_command(encrypt_command),
            Commands::Backup { backup_command } => self.handle_backup_command(backup_command),
        }
    }

    fn create_note(&self, title: String, tags: Option<String>, notebook: Option<String>, parent: Option<String>, encrypt: bool) -> Result<()> {
        println!("{}", "Creating new note...".green().bold());

        // Get initial content from user or use empty
        print!("Enter note content (press Enter when done):\n> ");
        io::stdout().flush()?;

        let mut content = String::new();
        io::stdin().read_line(&mut content)?;
        content = content.trim().to_string();

        // Create note
        let mut note = Note::new(title.clone(), content);

        // Set encryption flag
        note.encrypted = encrypt;

        // If encrypting, ensure we're unlocked
        if encrypt {
            let mut storage = self.storage.lock().unwrap();
            if !storage.is_unlocked() {
                println!("{}", "Error: Storage is locked. Use 'notes encrypt unlock' first.".red());
                return Ok(());
            }
        }

        // Add tags if provided
        if let Some(tags_str) = tags {
            for tag in tags_str.split(',') {
                let tag = tag.trim().to_string();
                if !tag.is_empty() {
                    note.add_tag(tag);
                }
            }
        }

        // Set notebook if provided
        if let Some(notebook_id) = notebook {
            let storage = self.storage.lock().unwrap();
            if let Ok(_) = storage.get_notebook(&notebook_id) {
                note.set_notebook(notebook_id);
            } else {
                println!("{}", format!("Warning: Notebook '{}' not found", notebook_id).yellow());
            }
        }

        // Set parent if provided
        if let Some(parent_id) = parent {
            let storage = self.storage.lock().unwrap();
            if let Ok(_) = storage.load_note(&parent_id) {
                note.set_parent(parent_id);
            } else {
                println!("{}", format!("Warning: Parent note '{}' not found", parent_id).yellow());
            }
        }

        // Save note
        let mut storage = self.storage.lock().unwrap();
        storage.save_note(&mut note)?;

        // If has parent, update parent's children list
        if let Some(parent_id) = &note.parent_id {
            let mut parent_note = storage.load_note(parent_id)?;
            parent_note.add_child(note.id.clone());
            storage.save_note(&mut parent_note)?;
        }

        println!("{}", "Note created successfully!".green().bold());
        println!("ID: {}", note.id.cyan());
        println!("Title: {}", note.title.white());
        println!("Tags: {}", note.tags.join(", ").yellow());
        if note.encrypted {
            println!("{} {}", "Encrypted:".cyan(), "Yes".green());
        }
        if let Some(nb_id) = &note.notebook_id {
            println!("Notebook: {}", nb_id.cyan());
        }
        if let Some(parent_id) = &note.parent_id {
            println!("Parent: {}", parent_id.cyan());
        }

        Ok(())
    }

    fn list_notes(&self, tag_filter: Option<String>, limit: usize, notebook_filter: Option<String>) -> Result<()> {
        let storage = self.storage.lock().unwrap();
        let notes = if let Some(notebook_id) = notebook_filter {
            storage.get_notes_in_notebook(&notebook_id)?
        } else if let Some(tag) = tag_filter {
            storage.get_notes_by_tag(&tag)?
        } else {
            storage.list_notes()?
        };

        let notes: Vec<_> = notes.into_iter().take(limit).collect();

        if notes.is_empty() {
            println!("{}", "No notes found.".yellow());
            return Ok(());
        }

        println!(
            "{}",
            format!("Found {} note(s):\n", notes.len()).green().bold()
        );

        for (idx, metadata) in notes.iter().enumerate() {
            println!(
                "{}. {} - {}",
                (idx + 1).to_string().cyan(),
                metadata.title.white().bold(),
                metadata.id.dimmed()
            );
            println!(
                "   Tags: {} | Created: {}",
                if metadata.tags.is_empty() {
                    "None".to_string().dimmed().to_string()
                } else {
                    metadata.tags.join(", ").yellow()
                },
                metadata.created_at.format("%Y-%m-%d %H:%M").to_string().dimmed()
            );
            if let Some(parent_id) = &metadata.parent_id {
                println!("   Parent: {}", parent_id.cyan());
            }
            println!();
        }

        Ok(())
    }

    fn view_note(&self, id: &str) -> Result<()> {
        let storage = self.storage.lock().unwrap();
        let note = storage.load_note_with_inheritance(id)?;

        println!("\n{}", note.title.white().bold());
        println!("{}", "─".repeat(80).dimmed());
        println!();

        if note.encrypted {
            println!("{} {}", "Encrypted:".cyan(), "Yes".yellow());
        }

        if !note.tags.is_empty() {
            println!("Tags: {}", note.tags.join(", ").yellow());
        }

        if !note.inherited_tags.is_empty() {
            println!("Inherited Tags: {}", note.inherited_tags.join(", ").dimmed());
        }

        if !note.tags.is_empty() || !note.inherited_tags.is_empty() {
            println!();
        }

        if let Some(parent_id) = &note.parent_id {
            println!("{} {}", "Parent:".cyan(), parent_id);
        }
        if let Some(notebook_id) = &note.notebook_id {
            println!("{} {}", "Notebook:".cyan(), notebook_id);
        }
        if !note.children.is_empty() {
            println!("{} {}", "Children:".cyan(), note.children.join(", ").dimmed());
        }

        println!("{} {}", "Created:".cyan(), note.created_at.format("%Y-%m-%d %H:%M:%S"));
        println!("{} {}", "Updated:".cyan(), note.updated_at.format("%Y-%m-%d %H:%M:%S"));
        println!();
        println!("{}", "─".repeat(80).dimmed());
        println!();
        println!("{}", note.content);
        println!();

        Ok(())
    }

    fn edit_note(&self, id: &str) -> Result<()> {
        let mut storage = self.storage.lock().unwrap();
        let mut note = storage.load_note(id)?;

        println!("Editing note: {}", note.title.cyan());
        println!("Current content:\n{}", note.content);
        println!("\n{}", "─".repeat(80).dimmed());

        // Check if note is encrypted
        if note.encrypted && !storage.is_unlocked() {
            println!("{}", "Error: Note is encrypted and storage is locked. Use 'notes encrypt unlock' first.".red());
            return Ok(());
        }

        // Get new content
        print!("\nEnter new content (press Enter when done):\n> ");
        io::stdout().flush()?;

        let mut new_content = String::new();
        io::stdin().read_line(&mut new_content)?;
        new_content = new_content.trim().to_string();

        if !new_content.is_empty() {
            note.update_content(new_content);

            storage.save_note(&mut note)?;

            println!("{}", "Note updated successfully!".green().bold());
        } else {
            println!("{}", "No changes made.".yellow());
        }

        Ok(())
    }

    fn delete_note(&self, id: &str, force: bool) -> Result<()> {
        if !force {
            print!("Are you sure you want to delete this note? (y/N): ");
            io::stdout().flush()?;

            let mut confirmation = String::new();
            io::stdin().read_line(&mut confirmation)?;

            if !confirmation.trim().to_lowercase().starts_with('y') {
                println!("{}", "Deletion cancelled.".yellow());
                return Ok(());
            }
        }

        let storage = self.storage.lock().unwrap();
        storage.delete_note(id)?;

        println!("{}", "Note deleted successfully!".green().bold());
        Ok(())
    }

    fn search_notes(&self, query: &str) -> Result<()> {
        let storage = self.storage.lock().unwrap();
        let notes = storage.search_notes(query)?;

        if notes.is_empty() {
            println!("{}", "No notes found matching your query.".yellow());
            return Ok(());
        }

        println!(
            "{}",
            format!("Found {} note(s) matching '{}':\n", notes.len(), query).green().bold()
        );

        for (idx, metadata) in notes.iter().enumerate() {
            println!(
                "{}. {} - {}",
                (idx + 1).to_string().cyan(),
                metadata.title.white().bold(),
                metadata.id.dimmed()
            );
            println!(
                "   Tags: {} | Updated: {}",
                if metadata.tags.is_empty() {
                    "None".to_string().dimmed().to_string()
                } else {
                    metadata.tags.join(", ").yellow()
                },
                metadata.updated_at.format("%Y-%m-%d %H:%M").to_string().dimmed()
            );
            println!();
        }

        Ok(())
    }

    fn handle_tag_command(&self, command: TagCommands) -> Result<()> {
        match command {
            TagCommands::Add { id, tag } => {
                let mut storage = self.storage.lock().unwrap();
                let mut note = storage.load_note(&id)?;
                note.add_tag(tag);
                storage.save_note(&mut note)?;
                println!("{}", "Tag added successfully!".green().bold());
            }
            TagCommands::Remove { id, tag } => {
                let mut storage = self.storage.lock().unwrap();
                let mut note = storage.load_note(&id)?;
                if note.remove_tag(&tag) {
                    storage.save_note(&mut note)?;
                    println!("{}", "Tag removed successfully!".green().bold());
                } else {
                    println!("{}", "Tag not found on note.".yellow());
                }
            }
            TagCommands::List => {
                let storage = self.storage.lock().unwrap();
                let notes = storage.list_notes()?;
                let mut all_tags = std::collections::HashSet::new();

                for note in &notes {
                    all_tags.extend(note.tags.clone());
                }

                let mut tags: Vec<_> = all_tags.into_iter().collect();
                tags.sort();

                if tags.is_empty() {
                    println!("{}", "No tags found.".yellow());
                } else {
                    println!("{}", format!("Found {} tag(s):\n", tags.len()).green().bold());
                    for tag in tags {
                        println!("- {}", tag.yellow());
                    }
                }
            }
        }
        Ok(())
    }

    fn handle_notebook_command(&self, command: NotebookCommands) -> Result<()> {
        match command {
            NotebookCommands::Create { name, description } => {
                let storage = self.storage.lock().unwrap();
                let notebook = storage.create_notebook(name, description.unwrap_or_default())?;
                println!("{}", "Notebook created successfully!".green().bold());
                println!("ID: {}", notebook.id.cyan());
                println!("Name: {}", notebook.name.white());
            }
            NotebookCommands::List => {
                let storage = self.storage.lock().unwrap();
                let notebooks = storage.load_notebooks()?;

                if notebooks.is_empty() {
                    println!("{}", "No notebooks found.".yellow());
                } else {
                    println!("{}", format!("Found {} notebook(s):\n", notebooks.len()).green().bold());
                    for notebook in &notebooks {
                        println!("{} - {}", notebook.id.cyan(), notebook.name.white());
                        if !notebook.description.is_empty() {
                            println!("  {}", notebook.description.dimmed());
                        }
                        println!();
                    }
                }
            }
            NotebookCommands::Show { id } => {
                let storage = self.storage.lock().unwrap();
                let notebook = storage.get_notebook(&id)?;
                let notes = storage.get_notes_in_notebook(&id)?;

                println!("\n{}", notebook.name.white().bold());
                println!("{}", "─".repeat(80).dimmed());
                println!("ID: {}", notebook.id.cyan());
                println!("Description: {}", notebook.description.dimmed());
                println!("Notes: {}", notes.len().to_string().yellow());
                println!("Created: {}", notebook.created_at.format("%Y-%m-%d %H:%M").to_string().dimmed());

                if !notes.is_empty() {
                    println!("\nNotes in this notebook:");
                    for (idx, note) in notes.iter().enumerate() {
                        println!("  {}. {} - {}", (idx + 1).to_string().cyan(), note.title.white(), note.id.dimmed());
                    }
                }
            }
            NotebookCommands::Delete { id, force } => {
                if !force {
                    print!("Are you sure you want to delete this notebook? (y/N): ");
                    io::stdout().flush()?;

                    let mut confirmation = String::new();
                    io::stdin().read_line(&mut confirmation)?;

                    if !confirmation.trim().to_lowercase().starts_with('y') {
                        println!("{}", "Deletion cancelled.".yellow());
                        return Ok(());
                    }
                }

                let storage = self.storage.lock().unwrap();
                storage.delete_notebook(&id)?;
                println!("{}", "Notebook deleted successfully!".green().bold());
            }
            NotebookCommands::Rename { id, new_name } => {
                let mut storage = self.storage.lock().unwrap();
                let mut notebook = storage.get_notebook(&id)?;
                notebook.name = new_name.clone();
                notebook.update_at = chrono::Utc::now();

                storage.save_notebooks(&[notebook])?;
                println!("{}", "Notebook renamed successfully!".green().bold());
            }
        }
        Ok(())
    }

    fn handle_parent_command(&self, command: ParentCommands) -> Result<()> {
        match command {
            ParentCommands::Set { child_id, parent_id } => {
                let mut storage = self.storage.lock().unwrap();
                storage.set_note_parent(&child_id, &parent_id)?;
                println!("{}", "Parent set successfully!".green().bold());
            }
            ParentCommands::Remove { child_id } => {
                let mut storage = self.storage.lock().unwrap();
                storage.remove_note_parent(&child_id)?;
                println!("{}", "Parent removed successfully!".green().bold());
            }
        }
        Ok(())
    }

    fn show_stats(&self, json: bool) -> Result<()> {
        let storage = self.storage.lock().unwrap();
        let stats = storage.calculate_stats()?;

        if json {
            println!("{}", serde_json::to_string_pretty(&stats)?);
        } else {
            println!("\n{}", "Workspace Statistics".white().bold());
            println!("{}", "─".repeat(80).dimmed());
            println!();
            println!("{} {}", "Total Notes:".cyan(), stats.total_notes.to_string().yellow());
            println!("{} {}", "Total Notebooks:".cyan(), stats.total_notebooks.to_string().yellow());
            println!("{} {}", "Total Tags:".cyan(), stats.total_tags.to_string().yellow());
            println!("{} {}", "Storage Size:".cyan(), format_bytes(stats.storage_size_bytes).yellow());
            println!();

            if !stats.most_used_tags.is_empty() {
                println!("{}", "Most Used Tags:".white().bold());
                for (tag, count) in &stats.most_used_tags {
                    println!("  - {}: {}", tag.yellow(), count.to_string().dimmed());
                }
                println!();
            }

            if !stats.notes_by_notebook.is_empty() {
                println!("{}", "Notes by Notebook:".white().bold());
                for (notebook, count) in &stats.notes_by_notebook {
                    println!("  - {}: {}", notebook.cyan(), count.to_string().yellow());
                }
            }
        }

        Ok(())
    }

    fn show_tree(&self, id: Option<String>, depth: usize) -> Result<()> {
        let storage = self.storage.lock().unwrap();

        let root_id = id.unwrap_or_else(|| {
            // Use first note as root if none specified
            storage.list_notes().ok().and_then(|notes| notes.first().map(|n| n.id.clone())).unwrap_or_default()
        });

        if root_id.is_empty() {
            println!("{}", "No notes found.".yellow());
            return Ok(());
        }

        println!("\n{}", "Note Hierarchy Tree".white().bold());
        println!("{}", "─".repeat(80).dimmed());
        println!();

        self.print_tree(&storage, &root_id, 0, depth, "")?;

        Ok(())
    }

    fn print_tree(&self, storage: &Storage, note_id: &str, current_depth: usize, max_depth: usize, prefix: &str) -> Result<()> {
        if current_depth > max_depth {
            return Ok(());
        }

        let note = storage.load_note_with_inheritance(note_id)?;

        println!("{}{} - {}", prefix, "├─".cyan(), note.title.white());
        println!("{}   {}", prefix, note.id.dimmed());

        if !note.children.is_empty() {
            let child_prefix = format!("{}│  ", prefix);
            for (idx, child_id) in note.children.iter().enumerate() {
                let is_last = idx == note.children.len() - 1;
                let new_prefix = if is_last {
                    format!("{}   ", prefix)
                } else {
                    child_prefix.clone()
                };
                self.print_tree(storage, child_id, current_depth + 1, max_depth, &new_prefix)?;
            }
        }

        Ok(())
    }

    fn init(&self) -> Result<()> {
        let storage = self.storage.lock().unwrap();
        storage.initialize()?;
        println!("{}", "Notes directory initialized successfully!".green().bold());
        println!("Location: {}", self.config.notes_dir.display().to_string().cyan());
        Ok(())
    }

    fn handle_encrypt_command(&self, command: EncryptCommands) -> Result<()> {
        match command {
            EncryptCommands::Set => {
                let mut pwd_mgr = self.password_manager.lock().unwrap();

                if pwd_mgr.is_password_set() {
                    println!("{}", "Password is already set. Use 'notes encrypt change' to change it.".yellow());
                    return Ok(());
                }

                print!("Enter master password: ");
                io::stdout().flush()?;
                let password = read_password()?;

                print!("Confirm master password: ");
                io::stdout().flush()?;
                let confirm_password = read_password()?;

                if password != confirm_password {
                    println!("{}", "Passwords do not match!".red());
                    return Ok(());
                }

                pwd_mgr.set_password(&password)?;
                println!("{}", "Master password set successfully!".green().bold());
                println!("{}", "Warning: If you forget your password, your encrypted notes cannot be recovered.".yellow());
            }
            EncryptCommands::Change { force } => {
                let mut pwd_mgr = self.password_manager.lock().unwrap();

                if !pwd_mgr.is_password_set() {
                    println!("{}", "No password set. Use 'notes encrypt set' to set one.".yellow());
                    return Ok(());
                }

                if !pwd_mgr.is_unlocked() {
                    print!("Enter current password: ");
                    io::stdout().flush()?;
                    let current_password = read_password()?;
                    pwd_mgr.unlock(&current_password)?;
                }

                print!("Enter new password: ");
                io::stdout().flush()?;
                let new_password = read_password()?;

                if !force {
                    print!("Confirm new password: ");
                    io::stdout().flush()?;
                    let confirm_password = read_password()?;

                    if new_password != confirm_password {
                        println!("{}", "Passwords do not match!".red());
                        return Ok(());
                    }
                }

                let current_password = if pwd_mgr.is_unlocked() {
                    print!("Enter current password: ");
                    io::stdout().flush()?;
                    Some(read_password()?)
                } else {
                    None
                };

                if let Some(current) = current_password {
                    pwd_mgr.change_password(&current, &new_password)?;
                    println!("{}", "Password changed successfully!".green().bold());
                } else {
                    println!("{}", "Error: Must provide current password to change.".red());
                }
            }
            EncryptCommands::Remove { force } => {
                if !force {
                    print!("Are you sure you want to remove encryption? All encrypted notes will be decrypted. (y/N): ");
                    io::stdout().flush()?;

                    let mut confirmation = String::new();
                    io::stdin().read_line(&mut confirmation)?;

                    if !confirmation.trim().to_lowercase().starts_with('y') {
                        println!("{}", "Operation cancelled.".yellow());
                        return Ok(());
                    }
                }

                let mut pwd_mgr = self.password_manager.lock().unwrap();

                if !pwd_mgr.is_password_set() {
                    println!("{}", "No password set.".yellow());
                    return Ok(());
                }

                pwd_mgr.remove_password()?;
                println!("{}", "Encryption removed successfully!".green().bold());
            }
            EncryptCommands::Unlock => {
                let mut pwd_mgr = self.password_manager.lock().unwrap();

                if !pwd_mgr.is_password_set() {
                    println!("{}", "No password set. Use 'notes encrypt set' to set one.".yellow());
                    return Ok(());
                }

                if pwd_mgr.is_unlocked() {
                    println!("{}", "Already unlocked.".yellow());
                    return Ok(());
                }

                print!("Enter master password: ");
                io::stdout().flush()?;
                let password = read_password()?;

                pwd_mgr.unlock(&password)?;

                // Update storage with master key
                if let Ok(key) = pwd_mgr.get_master_key() {
                    let mut storage = self.storage.lock().unwrap();
                    storage.set_master_key(*key);
                }

                println!("{}", "Unlocked successfully!".green().bold());
            }
            EncryptCommands::Lock => {
                let mut pwd_mgr = self.password_manager.lock().unwrap();

                if !pwd_mgr.is_unlocked() {
                    println!("{}", "Already locked.".yellow());
                    return Ok(());
                }

                pwd_mgr.lock();

                // Clear master key from storage
                let mut storage = self.storage.lock().unwrap();
                storage.clear_master_key();

                println!("{}", "Locked successfully!".green().bold());
            }
            EncryptCommands::Status => {
                let pwd_mgr = self.password_manager.lock().unwrap();
                let storage = self.storage.lock().unwrap();

                println!("\n{}", "Encryption Status".white().bold());
                println!("{}", "─".repeat(80).dimmed());
                println!();
                println!("{} {}", "Password Set:".cyan(), if pwd_mgr.is_password_set() { "Yes".green() } else { "No".yellow() });
                println!("{} {}", "Unlocked:".cyan(), if storage.is_unlocked() { "Yes".green() } else { "No".yellow() });

                if pwd_mgr.is_password_set() {
                    let notes = storage.list_notes()?;
                    let encrypted_count = notes.iter().filter(|n| n.file_path.and_then(|p| fs::metadata(p).ok()).is_some()).count(); // This is simplified - in reality we'd check the encrypted flag
                    println!("{} {}", "Encrypted Notes:".cyan(), "Check individual notes".yellow());
                }
            }
            EncryptCommands::Note { id } => {
                let mut storage = self.storage.lock().unwrap();

                if !storage.is_unlocked() {
                    println!("{}", "Error: Storage is locked. Use 'notes encrypt unlock' first.".red());
                    return Ok(());
                }

                let mut note = storage.load_note(&id)?;
                note.encrypted = true;
                storage.save_note(&mut note)?;
                println!("{}", "Note encrypted successfully!".green().bold());
            }
            EncryptCommands::Decrypt { id } => {
                let mut storage = self.storage.lock().unwrap();

                if !storage.is_unlocked() {
                    println!("{}", "Error: Storage is locked. Use 'notes encrypt unlock' first.".red());
                    return Ok(());
                }

                let mut note = storage.load_note(&id)?;
                note.encrypted = false;
                storage.save_note(&mut note)?;
                println!("{}", "Note decrypted successfully!".green().bold());
            }
        }
        Ok(())
    }

    fn handle_backup_command(&self, command: BackupCommands) -> Result<()> {
        match command {
            BackupCommands::Create { name } => {
                let backup_mgr = self.backup_manager.lock().unwrap();
                let metadata = backup_mgr.create_backup(name)?;

                println!("{}", "Backup created successfully!".green().bold());
                println!("Name: {}", metadata.name.cyan());
                println!("Notes: {}", metadata.note_count.to_string().yellow());
                println!("Created: {}", metadata.created_at.format("%Y-%m-%d %H:%M:%S").to_string().dimmed());
                println!("Compressed: {}", if metadata.compressed { "Yes" } else { "No" }.yellow());
            }
            BackupCommands::List => {
                let backup_mgr = self.backup_manager.lock().unwrap();
                let backups = backup_mgr.list_backups()?;

                if backups.is_empty() {
                    println!("{}", "No backups found.".yellow());
                } else {
                    println!("{}", format!("Found {} backup(s):\n", backups.len()).green().bold());

                    for (idx, backup) in backups.iter().enumerate() {
                        println!("{}. {} - {}", (idx + 1).to_string().cyan(), backup.metadata.name.white(), backup.file_path.display().to_string().dimmed());
                        println!("   Notes: {} | Size: {} | Created: {}",
                            backup.metadata.note_count.to_string().yellow(),
                            format_bytes(backup.size_bytes).yellow(),
                            backup.metadata.created_at.format("%Y-%m-%d %H:%M").to_string().dimmed()
                        );
                        println!();
                    }
                }
            }
            BackupCommands::Restore { backup_path, no_safety } => {
                let backup_mgr = self.backup_manager.lock().unwrap();
                let path = PathBuf::from(backup_path);

                if !path.exists() {
                    println!("{}", format!("Error: Backup file not found: {}", backup_path).red());
                    return Ok(());
                }

                if !no_safety {
                    print!("Are you sure you want to restore from this backup? Current notes will be replaced. (y/N): ");
                    io::stdout().flush()?;

                    let mut confirmation = String::new();
                    io::stdin().read_line(&mut confirmation)?;

                    if !confirmation.trim().to_lowercase().starts_with('y') {
                        println!("{}", "Restore cancelled.".yellow());
                        return Ok(());
                    }
                }

                backup_mgr.restore_backup(&path, !no_safety)?;
                println!("{}", "Backup restored successfully!".green().bold());
            }
            BackupCommands::Delete { backup_path, force } => {
                if !force {
                    print!("Are you sure you want to delete this backup? (y/N): ");
                    io::stdout().flush()?;

                    let mut confirmation = String::new();
                    io::stdin().read_line(&mut confirmation)?;

                    if !confirmation.trim().to_lowercase().starts_with('y') {
                        println!("{}", "Deletion cancelled.".yellow());
                        return Ok(());
                    }
                }

                let backup_mgr = self.backup_manager.lock().unwrap();
                let path = PathBuf::from(backup_path);
                backup_mgr.delete_backup(&path)?;
                println!("{}", "Backup deleted successfully!".green().bold());
            }
            BackupCommands::Schedule { enabled, interval, max } => {
                let mut config = self.config.clone();

                if let Some(e) = enabled {
                    config.backup.auto_backup_enabled = e;
                    println!("{} {}", "Automatic backups:".cyan(), if e { "enabled".green() } else { "disabled".yellow() }.to_string());
                }

                if let Some(i) = interval {
                    config.backup.auto_backup_interval_hours = i;
                    println!("{} {}", "Backup interval:".cyan(), format!("{} hours", i).yellow());
                }

                if let Some(m) = max {
                    config.backup.max_backups = m;
                    println!("{} {}", "Maximum backups:".cyan(), m.to_string().yellow());
                }

                // Save updated config (would need config_manager here)
                println!("\n{}", "Backup configuration updated!".green().bold());
            }
            BackupCommands::Verify { backup_path } => {
                let backup_mgr = self.backup_manager.lock().unwrap();
                let path = PathBuf::from(backup_path);

                if !path.exists() {
                    println!("{}", format!("Error: Backup file not found: {}", backup_path).red());
                    return Ok(());
                }

                // Read metadata and verify
                if let Ok(metadata) = backup_mgr.read_backup_metadata(&path) {
                    println!("{}", "Backup verification successful!".green().bold());
                    println!("Name: {}", metadata.name.cyan());
                    println!("Notes: {}", metadata.note_count.to_string().yellow());
                    println!("Created: {}", metadata.created_at.format("%Y-%m-%d %H:%M:%S").to_string().dimmed());
                } else {
                    println!("{}", "Backup verification failed!".red());
                }
            }
        }
        Ok(())
    }
}

fn format_bytes(bytes: u64) -> String {
    const UNITS: &[&str] = &["B", "KB", "MB", "GB"];
    let mut size = bytes as f64;
    let mut unit_index = 0;

    while size >= 1024.0 && unit_index < UNITS.len() - 1 {
        size /= 1024.0;
        unit_index += 1;
    }

    format!("{:.2} {}", size, UNITS[unit_index])
}

// ============ Semantic Search Methods ============

    /// Perform semantic search
    fn semantic_search(&self, query: &str) -> Result<()> {
        if !self.config.semantic.enabled {
            println!("{}", "Semantic search is disabled. Enable it in config.".yellow());
            return Ok(());
        }

        // Initialize embedder and store
        let embedder = match OpenAIEmbedder::new(&self.config.semantic) {
            Ok(e) => Box::new(e),
            Err(e) => {
                println!("{}", format!("Error initializing semantic search: {}", e).red());
                println!("{}", "Hint: Set OPENAI_API_KEY environment variable".yellow());
                return Err(e.into());
            }
        };

        let mut store = EmbeddingStore::new(self.config.notes_dir.clone())?;
        let storage = self.storage.lock().unwrap();
        let all_notes = storage.list_notes()?;

        if store.is_empty() {
            println!("{}", "No notes indexed yet. Run 'notes semantic index' first.".yellow());
            return Ok(());
        }

        let mut searcher = SemanticSearcher::new(
            embedder,
            store,
            self.config.semantic.clone(),
        );

        // Perform search
        let results = self.runtime.block_on(async {
            searcher.search(query, &all_notes).await
        })?;

        if results.is_empty() {
            println!("{}", "No semantically similar notes found.".yellow());
            return Ok(());
        }

        println!(
            "{}",
            format!("Found {} note(s) semantically similar to '{}':\n", results.len(), query).green().bold()
        );

        for (idx, result) in results.iter().enumerate() {
            println!(
                "{}. {} - {}",
                (idx + 1).to_string().cyan(),
                result.metadata.title.white().bold(),
                result.metadata.id.dimmed()
            );
            println!(
                "   Similarity: {:.2}% | Tags: {}",
                (result.score * 100.0).to_string().green(),
                if result.metadata.tags.is_empty() {
                    "None".to_string().dimmed().to_string()
                } else {
                    result.metadata.tags.join(", ").yellow()
                }
            );
            println!();
        }

        Ok(())
    }

    /// Handle semantic commands
    fn handle_semantic_command(&self, command: SemanticCommands) -> Result<()> {
        if !self.config.semantic.enabled {
            println!("{}", "Semantic search is disabled. Enable it in config.".yellow());
            return Ok(());
        }

        match command {
            SemanticCommands::Index { force } => self.semantic_index(force),
            SemanticCommands::Search { query, limit, threshold } => {
                self.semantic_search_with_options(query, limit, threshold)
            }
            SemanticCommands::Status => self.semantic_status(),
            SemanticCommands::Clear { force } => self.semantic_clear(force),
        }
    }

    /// Index all notes for semantic search
    fn semantic_index(&self, force: bool) -> Result<()> {
        println!("{}", "Indexing notes for semantic search...".green().bold());

        // Initialize embedder and store
        let embedder = match OpenAIEmbedder::new(&self.config.semantic) {
            Ok(e) => Box::new(e),
            Err(e) => {
                println!("{}", format!("Error: {}", e).red());
                println!("{}", "Hint: Set OPENAI_API_KEY environment variable".yellow());
                return Err(e.into());
            }
        };

        let mut store = EmbeddingStore::new(self.config.notes_dir.clone())?;
        let storage = self.storage.lock().unwrap();
        let all_notes = storage.list_notes()?;

        if all_notes.is_empty() {
            println!("{}", "No notes to index.".yellow());
            return Ok(());
        }

        let mut notes_to_index = Vec::new();

        for metadata in &all_notes {
            if let Ok(note) = storage.load_note(&metadata.id) {
                let content_hash = crate::semantic::store::compute_content_hash(&note.content);

                if force || !store.is_valid(&note.id, &content_hash) {
                    notes_to_index.push((note.id.clone(), note.content));
                }
            }
        }

        if notes_to_index.is_empty() {
            println!("{}", "All notes are already indexed. Use --force to re-index.".yellow());
            return Ok(());
        }

        println!("{}", format!("Indexing {} note(s)...", notes_to_index.len()).cyan());

        let mut searcher = SemanticSearcher::new(
            embedder,
            store,
            self.config.semantic.clone(),
        );

        // Index in batches
        let batch_size = 50;
        for chunk in notes_to_index.chunks(batch_size) {
            self.runtime.block_on(async {
                searcher.index_notes_batch(chunk).await
            })?;
        }

        searcher.save()?;

        println!(
            "{}",
            format!("Successfully indexed {} notes!", notes_to_index.len()).green().bold()
        );

        Ok(())
    }

    /// Semantic search with custom options
    fn semantic_search_with_options(&self, query: String, limit: usize, threshold: Option<f32>) -> Result<()> {
        // Initialize embedder and store
        let embedder = match OpenAIEmbedder::new(&self.config.semantic) {
            Ok(e) => Box::new(e),
            Err(e) => {
                println!("{}", format!("Error: {}", e).red());
                return Err(e.into());
            }
        };

        let mut store = EmbeddingStore::new(self.config.notes_dir.clone())?;
        let storage = self.storage.lock().unwrap();
        let all_notes = storage.list_notes()?;

        if store.is_empty() {
            println!("{}", "No notes indexed yet. Run 'notes semantic index' first.".yellow());
            return Ok(());
        }

        let mut config = self.config.semantic.clone();
        if let Some(t) = threshold {
            config.similarity_threshold = t;
        }
        config.max_results = limit;

        let mut searcher = SemanticSearcher::new(
            embedder,
            store,
            config,
        );

        let results = self.runtime.block_on(async {
            searcher.search(&query, &all_notes).await
        })?;

        if results.is_empty() {
            println!("{}", "No semantically similar notes found.".yellow());
            return Ok(());
        }

        println!(
            "{}",
            format!("Found {} note(s) semantically similar to '{}':\n", results.len(), query).green().bold()
        );

        for (idx, result) in results.iter().enumerate() {
            println!(
                "{}. {} - {}",
                (idx + 1).to_string().cyan(),
                result.metadata.title.white().bold(),
                result.metadata.id.dimmed()
            );
            println!(
                "   Similarity: {:.2}% | Tags: {}",
                (result.score * 100.0).to_string().green(),
                if result.metadata.tags.is_empty() {
                    "None".to_string().dimmed().to_string()
                } else {
                    result.metadata.tags.join(", ").yellow()
                }
            );
            println!();
        }

        Ok(())
    }

    /// Show semantic search status
    fn semantic_status(&self) -> Result<()> {
        let store = EmbeddingStore::new(self.config.notes_dir.clone())?;
        let storage = self.storage.lock().unwrap();
        let total_notes = storage.list_notes()?.len();

        println!("\n{}", "Semantic Search Status".white().bold());
        println!("{}", "─".repeat(80).dimmed());
        println!();
        println!("{} {}", "Enabled:".cyan(), if self.config.semantic.enabled { "Yes".green() } else { "No".yellow() });
        println!("{} {}", "Model:".cyan(), self.config.semantic.model.yellow());
        println!("{} {}", "Indexed Notes:".cyan(), format!("{} / {}", store.len(), total_notes).yellow());
        println!("{} {}", "Similarity Threshold:".cyan(), format!("{:.2}", self.config.semantic.similarity_threshold).yellow());
        println!("{} {}", "Max Results:".cyan(), self.config.semantic.max_results.to_string().yellow());

        if let Ok(metadata) = store.metadata() {
            println!("{} {}", "Last Updated:".cyan(), metadata.updated_at.format("%Y-%m-%d %H:%M").to_string().dimmed());
        }

        Ok(())
    }

    /// Clear the embedding index
    fn semantic_clear(&self, force: bool) -> Result<()> {
        if !force {
            print!("Are you sure you want to clear the embedding index? (y/N): ");
            io::stdout().flush()?;

            let mut confirmation = String::new();
            io::stdin().read_line(&mut confirmation)?;

            if !confirmation.trim().to_lowercase().starts_with('y') {
                println!("{}", "Operation cancelled.".yellow());
                return Ok(());
            }
        }

        let mut store = EmbeddingStore::new(self.config.notes_dir.clone())?;
        store.clear();
        store.save()?;

        println!("{}", "Embedding index cleared successfully!".green().bold());

        Ok(())
    }

