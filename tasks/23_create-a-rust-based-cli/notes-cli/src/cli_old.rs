use crate::error::Result;
use crate::storage::Storage;
use crate::types::{Note, WorkspaceStats};
use clap::{Parser, Subcommand};
use colored::Colorize;
use std::io::{self, Write};

/// A CLI note-taking tool with markdown support, search, and tags
#[derive(Parser)]
#[command(name = "notes")]
#[command(about = "A CLI note-taking tool with markdown support", long_about = None)]
#[command(version = "0.1.0")]
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

/// Main CLI handler
pub struct CliApp {
    storage: Storage,
}

impl CliApp {
    pub fn new(storage: Storage) -> Self {
        Self { storage }
    }

    pub fn run(&self) -> Result<()> {
        let cli = Cli::parse();

        match cli.command {
            Commands::Create { title, tags, notebook, parent } => {
                self.create_note(title, tags, notebook, parent)
            }
            Commands::List { tag, limit, notebook } => self.list_notes(tag, limit, notebook),
            Commands::View { id } => self.view_note(&id),
            Commands::Edit { id } => self.edit_note(&id),
            Commands::Delete { id, force } => self.delete_note(&id, force),
            Commands::Search { query } => self.search_notes(&query),
            Commands::Tag { tag_command } => self.handle_tag_command(tag_command),
            Commands::Notebook { notebook_command } => self.handle_notebook_command(notebook_command),
            Commands::Parent { parent_command } => self.handle_parent_command(parent_command),
            Commands::Stats { json } => self.show_stats(json),
            Commands::Tree { id, depth } => self.show_tree(id, depth),
            Commands::Init => self.init(),
        }
    }

    fn create_note(&self, title: String, tags: Option<String>, notebook: Option<String>, parent: Option<String>) -> Result<()> {
        println!("{}", "Creating new note...".green().bold());

        // Get initial content from user or use empty
        print!("Enter note content (press Enter when done):\n> ");
        io::stdout().flush()?;

        let mut content = String::new();
        io::stdin().read_line(&mut content)?;
        content = content.trim().to_string();

        // Create note
        let mut note = Note::new(title.clone(), content);

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
            // Validate notebook exists
            if let Ok(_) = self.storage.get_notebook(&notebook_id) {
                note.set_notebook(notebook_id);
            } else {
                println!("{}", format!("Warning: Notebook '{}' not found", notebook_id).yellow());
            }
        }

        // Set parent if provided
        if let Some(parent_id) = parent {
            if let Ok(_) = self.storage.load_note(&parent_id) {
                note.set_parent(parent_id);
            } else {
                println!("{}", format!("Warning: Parent note '{}' not found", parent_id).yellow());
            }
        }

        // Save note
        let mut storage = self.storage.clone();
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
        if let Some(nb_id) = &note.notebook_id {
            println!("Notebook: {}", nb_id.cyan());
        }
        if let Some(parent_id) = &note.parent_id {
            println!("Parent: {}", parent_id.cyan());
        }

        Ok(())
    }

    fn list_notes(&self, tag_filter: Option<String>, limit: usize, notebook_filter: Option<String>) -> Result<()> {
        let notes = if let Some(notebook_id) = notebook_filter {
            self.storage.get_notes_in_notebook(&notebook_id)?
        } else if let Some(tag) = tag_filter {
            self.storage.get_notes_by_tag(&tag)?
        } else {
            self.storage.list_notes()?
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
        let note = self.storage.load_note_with_inheritance(id)?;

        println!("\n{}", note.title.white().bold());
        println!("{}", "─".repeat(80).dimmed());
        println!();

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
        let mut note = self.storage.load_note(id)?;

        println!("Editing note: {}", note.title.cyan());
        println!("Current content:\n{}", note.content);
        println!("\n{}", "─".repeat(80).dimmed());

        // Get new content
        print!("\nEnter new content (press Enter when done):\n> ");
        io::stdout().flush()?;

        let mut new_content = String::new();
        io::stdin().read_line(&mut new_content)?;
        new_content = new_content.trim().to_string();

        if !new_content.is_empty() {
            note.update_content(new_content);

            let mut storage = self.storage.clone();
            storage.save_note(&mut note)?;

            println!("{}", "Note updated successfully!".green().bold());
        } else {
            println!("{}", "No changes made.".yellow());
        }

        Ok(())
    }

    fn delete_note(&self, id: &str, force: bool) -> Result<()> {
        // Load note to show info
        let note = self.storage.load_note(id)?;

        if !force {
            println!("Are you sure you want to delete note: {}?", note.title.red());
            print!("This action cannot be undone. Continue? [y/N]: ");
            io::stdout().flush()?;

            let mut confirmation = String::new();
            io::stdin().read_line(&mut confirmation)?;

            if !confirmation.trim().to_lowercase().starts_with('y') {
                println!("{}", "Deletion cancelled.".yellow());
                return Ok(());
            }
        }

        self.storage.delete_note(id)?;
        println!("{}", "Note deleted successfully!".green().bold());

        Ok(())
    }

    fn search_notes(&self, query: &str) -> Result<()> {
        // Try to parse as boolean query first
        let parsed_query = self.storage.parse_search_query(query)?;

        // Execute the search
        let results = self.storage.execute_search(&parsed_query)?;

        if results.is_empty() {
            println!(
                "{}",
                format!("No notes found matching '{}'.", query).yellow()
            );
            return Ok(());
        }

        println!(
            "{}\n",
            format!("Found {} note(s) matching '{}':", results.len(), query)
                .green()
                .bold()
        );

        for (idx, metadata) in results.iter().enumerate() {
            println!(
                "{}. {}",
                (idx + 1).to_string().cyan(),
                metadata.title.white().bold()
            );
            println!("   ID: {}", metadata.id.dimmed());
            println!(
                "   Tags: {} | Created: {}",
                if metadata.tags.is_empty() {
                    "None".to_string()
                } else {
                    metadata.tags.join(", ")
                },
                metadata.created_at.format("%Y-%m-%d")
            );
            println!();
        }

        Ok(())
    }

    fn handle_tag_command(&self, command: TagCommands) -> Result<()> {
        match command {
            TagCommands::Add { id, tag } => {
                let mut note = self.storage.load_note(&id)?;
                note.add_tag(tag.clone());

                let mut storage = self.storage.clone();
                storage.save_note(&mut note)?;

                println!(
                    "{}",
                    format!("Tag '{}' added to note successfully!", tag).green()
                );
            }

            TagCommands::Remove { id, tag } => {
                let mut note = self.storage.load_note(&id)?;

                if note.remove_tag(&tag) {
                    let mut storage = self.storage.clone();
                    storage.save_note(&mut note)?;

                    println!(
                        "{}",
                        format!("Tag '{}' removed from note successfully!", tag).green()
                    );
                } else {
                    println!(
                        "{}",
                        format!("Note does not have tag '{}'.", tag).yellow()
                    );
                }
            }

            TagCommands::List => {
                let notes = self.storage.list_notes()?;

                let mut all_tags: std::collections::HashMap<String, usize> = std::collections::HashMap::new();

                for note in &notes {
                    for tag in &note.tags {
                        *all_tags.entry(tag.clone()).or_insert(0) += 1;
                    }
                }

                if all_tags.is_empty() {
                    println!("{}", "No tags found.".yellow());
                    return Ok(());
                }

                println!("{}", "All tags:".green().bold());
                let mut tags: Vec<_> = all_tags.into_iter().collect();
                tags.sort_by(|a, b| a.0.cmp(&b.0));

                for (tag, count) in tags {
                    println!("  {} ({} notes)", tag.cyan(), count.to_string().yellow());
                }
            }
        }

        Ok(())
    }

    fn init(&self) -> Result<()> {
        println!("{}", "Initializing notes directory...".cyan());
        self.storage.initialize()?;
        println!(
            "{}",
            format!("Notes directory initialized at: {:?}", self.storage.notes_dir)
                .green()
        );
        Ok(())
    }

    fn handle_notebook_command(&self, command: NotebookCommands) -> Result<()> {
        match command {
            NotebookCommands::Create { name, description } => {
                let notebook = self.storage.create_notebook(name.clone(), description.unwrap_or_default())?;
                println!(
                    "{}",
                    format!("Notebook '{}' created successfully!", name).green()
                );
                println!("ID: {}", notebook.id.cyan());
            }

            NotebookCommands::List => {
                let notebooks = self.storage.load_notebooks()?;

                if notebooks.is_empty() {
                    println!("{}", "No notebooks found.".yellow());
                    return Ok(());
                }

                println!("{}", "Notebooks:".green().bold());
                for (idx, notebook) in notebooks.iter().enumerate() {
                    println!(
                        "{}. {} - {}",
                        (idx + 1).to_string().cyan(),
                        notebook.name.white().bold(),
                        notebook.id.dimmed()
                    );
                    if !notebook.description.is_empty() {
                        println!("   Description: {}", notebook.description.dimmed());
                    }
                    println!("   Created: {}", notebook.created_at.format("%Y-%m-%d").dimmed());
                    println!();
                }
            }

            NotebookCommands::Show { id } => {
                let notebook = self.storage.get_notebook(&id)?;
                let notes = self.storage.get_notes_in_notebook(&id)?;

                println!("\n{}", notebook.name.white().bold());
                println!("{}", "─".repeat(80).dimmed());
                println!("ID: {}", notebook.id.cyan());
                if !notebook.description.is_empty() {
                    println!("Description: {}", notebook.description);
                }
                println!("Created: {}", notebook.created_at.format("%Y-%m-%d %H:%M"));
                println!();
                println!("Notes: {}", notes.len().to_string().yellow());
                for note in &notes {
                    println!("  • {} ({})", note.title.white(), note.id.dimmed());
                }
            }

            NotebookCommands::Delete { id, force } => {
                let notebook = self.storage.get_notebook(&id)?;

                if !force {
                    println!(
                        "Are you sure you want to delete notebook: {}?",
                        notebook.name.red()
                    );
                    print!("This will not delete the notes themselves. Continue? [y/N]: ");
                    io::stdout().flush()?;

                    let mut confirmation = String::new();
                    io::stdin().read_line(&mut confirmation)?;

                    if !confirmation.trim().to_lowercase().starts_with('y') {
                        println!("{}", "Deletion cancelled.".yellow());
                        return Ok(());
                    }
                }

                self.storage.delete_notebook(&id)?;
                println!("{}", "Notebook deleted successfully!".green().bold());
            }

            NotebookCommands::Rename { id, new_name } => {
                let mut notebooks = self.storage.load_notebooks()?;
                let notebook = notebooks.iter_mut().find(|n| n.id == id)
                    .ok_or_else(|| NotesError::NoteNotFound(format!("Notebook {}", id)))?;

                notebook.name = new_name.clone();
                notebook.updated_at = chrono::Utc::now();

                self.storage.save_notebooks(&notebooks)?;
                println!(
                    "{}",
                    format!("Notebook renamed to '{}' successfully!", new_name).green()
                );
            }
        }

        Ok(())
    }

    fn handle_parent_command(&self, command: ParentCommands) -> Result<()> {
        match command {
            ParentCommands::Set { child_id, parent_id } => {
                let mut storage = self.storage.clone();
                storage.set_note_parent(&child_id, &parent_id)?;

                println!(
                    "{}",
                    format!("Note '{}' is now a child of '{}'", child_id, parent_id).green()
                );
            }

            ParentCommands::Remove { child_id } => {
                let mut storage = self.storage.clone();
                storage.remove_note_parent(&child_id)?;

                println!(
                    "{}",
                    format!("Parent removed from note '{}'", child_id).green()
                );
            }
        }

        Ok(())
    }

    fn show_stats(&self, json_output: bool) -> Result<()> {
        let stats = self.storage.calculate_stats()?;

        if json_output {
            println!("{}", serde_json::to_string_pretty(&stats)?);
            return Ok(());
        }

        println!("\n{}", "Workspace Statistics".white().bold());
        println!("{}", "═".repeat(80).cyan());
        println!();

        println!("{}", "Overview".cyan().bold());
        println!("  Total Notes: {}", stats.total_notes.to_string().yellow().bold());
        println!("  Total Notebooks: {}", stats.total_notebooks.to_string().yellow().bold());
        println!("  Total Tags: {}", stats.total_tags.to_string().yellow().bold());
        println!();

        if !stats.most_used_tags.is_empty() {
            println!("{}", "Most Used Tags".cyan().bold());
            for (tag, count) in &stats.most_used_tags {
                println!("  {} ({} notes)", tag.cyan(), count.to_string().yellow());
            }
            println!();
        }

        if !stats.notes_by_notebook.is_empty() {
            println!("{}", "Notes by Notebook".cyan().bold());
            for (notebook, count) in &stats.notes_by_notebook {
                println!("  {} ({} notes)", notebook.cyan(), count.to_string().yellow());
            }
            println!();
        }

        println!("{}", "Storage".cyan().bold());
        println!("  Total Size: {} bytes", format_size(stats.storage_size_bytes).yellow());
        if let Some(largest) = &stats.largest_notebook {
            println!("  Largest Notebook: {}", largest.cyan());
        }
        println!("  Average Notes per Notebook: {:.1}", stats.average_notes_per_notebook);

        println!();

        Ok(())
    }

    fn show_tree(&self, root_id: Option<String>, max_depth: usize) -> Result<()> {
        if let Some(id) = root_id {
            // Show tree for specific note
            self.print_subtree(&id, 0, max_depth)?;
        } else {
            // Show all trees (notes without parents)
            let all_notes = self.storage.list_notes()?;
            let root_notes: Vec<_> = all_notes
                .iter()
                .filter(|n| n.parent_id.is_none())
                .collect();

            if root_notes.is_empty() {
                println!("{}", "No notes found.".yellow());
                return Ok(());
            }

            println!("{}", "Note Hierarchy".white().bold());
            println!("{}", "═".repeat(80).cyan());
            println!();

            for (idx, note) in root_notes.iter().enumerate() {
                self.print_note_node(&note.id, 0, max_depth)?;
                if idx < root_notes.len() - 1 {
                    println!();
                }
            }
        }

        println!();
        Ok(())
    }

    fn print_subtree(&self, note_id: &str, depth: usize, max_depth: usize) -> Result<()> {
        if depth > max_depth {
            return Ok(());
        }

        let note = self.storage.load_note(note_id)?;
        let indent = "  ".repeat(depth);
        let prefix = if depth == 0 { "├─ " } else { "└─ " };

        println!("{}{}{} ({})", indent, prefix, note.title.white().bold(), note.id.dimmed());

        if !note.children.is_empty() {
            for child_id in &note.children {
                self.print_subtree(child_id, depth + 1, max_depth)?;
            }
        }

        Ok(())
    }

    fn print_note_node(&self, note_id: &str, depth: usize, max_depth: usize) -> Result<()> {
        if depth > max_depth {
            return Ok(());
        }

        let note = self.storage.load_note(note_id)?;
        let indent = "  ".repeat(depth);
        let connector = if depth == 0 { "├─" } else { "└─" };
        let tags_str = if note.tags.is_empty() {
            String::new()
        } else {
            format!("[{}]", note.tags.join(","))
        };

        println!("{}{} {} {}", indent, connector.cyan(), note.title.white().bold(), tags_str.yellow());

        for child_id in &note.children {
            self.print_note_node(child_id, depth + 1, max_depth)?;
        }

        Ok(())
    }
}

/// Format byte size for human readability
fn format_size(bytes: u64) -> String {
    const KB: u64 = 1024;
    const MB: u64 = KB * 1024;
    const GB: u64 = MB * 1024;

    if bytes >= GB {
        format!("{:.2} GB", bytes as f64 / GB as f64)
    } else if bytes >= MB {
        format!("{:.2} MB", bytes as f64 / MB as f64)
    } else if bytes >= KB {
        format!("{:.2} KB", bytes as f64 / KB as f64)
    } else {
        format!("{} bytes", bytes)
    }
}
