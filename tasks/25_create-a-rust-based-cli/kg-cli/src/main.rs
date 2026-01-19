mod types;
mod linking;
mod storage;
mod search;
mod export;

use anyhow::Result;
use clap::{Parser, Subcommand};
use colored::*;
use std::path::PathBuf;
use storage::Storage;
use types::Note;

#[derive(Parser)]
#[command(name = "kg")]
#[command(about = "A personal knowledge graph management tool", long_about = None)]
#[command(version = "0.1.0")]
struct Cli {
    #[command(subcommand)]
    command: Commands,

    /// Custom notes directory path
    #[arg(short, long, global = true)]
    dir: Option<PathBuf>,
}

#[derive(Subcommand)]
enum Commands {
    /// Create a new note
    New {
        /// Note title
        title: String,

        /// Note content (optional, will open editor if not provided)
        #[arg(short, long)]
        content: Option<String>,

        /// Tags for the note (comma-separated)
        #[arg(short, long)]
        tags: Option<String>,
    },

    /// Show a note's content
    Show {
        /// Note ID or title
        id: String,

        /// Show backlinks
        #[arg(short, long)]
        backlinks: bool,

        /// Show forward links
        #[arg(short, long)]
        links: bool,
    },

    /// List all notes
    List {
        /// Show detailed information
        #[arg(short, long)]
        detailed: bool,
    },

    /// Edit an existing note
    Edit {
        /// Note ID or title
        id: String,

        /// New content (will open editor if not provided)
        #[arg(short, long)]
        content: Option<String>,
    },

    /// Delete a note
    Delete {
        /// Note ID or title
        id: String,

        /// Skip confirmation prompt
        #[arg(short, long)]
        force: bool,
    },

    /// Search notes
    Search {
        /// Search query
        query: String,

        /// Use fuzzy search
        #[arg(short, long)]
        fuzzy: bool,

        /// Maximum number of results
        #[arg(short, long, default_value = "10")]
        limit: usize,
    },

    /// Show backlinks for a note
    Backlinks {
        /// Note ID or title
        id: String,
    },

    /// Export knowledge graph
    Export {
        /// Output format (dot or json)
        #[arg(short, long, default_value = "dot")]
        format: String,

        /// Output file path
        #[arg(short, long)]
        output: PathBuf,
    },

    /// Show graph statistics
    Stats {
        /// Show most connected notes
        #[arg(short, long)]
        top: Option<usize>,
    },

    /// Initialize the knowledge graph
    Init,
}

fn main() -> Result<()> {
    let cli = Cli::parse();

    // Handle init command first (doesn't need storage)
    if let Commands::Init = cli.command {
        let storage = Storage::new(cli.dir)?;
        storage.initialize()?;
        println!(
            "{}",
            "Knowledge graph initialized successfully!".green()
        );
        println!("Notes directory: {:?}", storage.notes_dir);
        return Ok(());
    }

    // Initialize storage
    let storage = Storage::new(cli.dir)?;
    if !storage.notes_dir.exists() {
        println!(
            "{}",
            "Knowledge graph not initialized. Run 'kg init' first.".red()
        );
        return Ok(());
    }

    // Execute command
    match cli.command {
        Commands::New { title, content, tags } => {
            cmd_new(&storage, title, content, tags)?;
        }
        Commands::Show { id, backlinks, links } => {
            cmd_show(&storage, id, backlinks, links)?;
        }
        Commands::List { detailed } => {
            cmd_list(&storage, detailed)?;
        }
        Commands::Edit { id, content } => {
            cmd_edit(&storage, id, content)?;
        }
        Commands::Delete { id, force } => {
            cmd_delete(&storage, id, force)?;
        }
        Commands::Search { query, fuzzy, limit } => {
            cmd_search(&storage, &query, fuzzy, limit)?;
        }
        Commands::Backlinks { id } => {
            cmd_backlinks(&storage, id)?;
        }
        Commands::Export { format, output } => {
            cmd_export(&storage, &format, &output)?;
        }
        Commands::Stats { top } => {
            cmd_stats(&storage, top)?;
        }
        Commands::Init => {
            // Already handled above
        }
    }

    Ok(())
}

fn cmd_new(storage: &Storage, title: String, content: Option<String>, tags: Option<String>) -> Result<()> {
    let note_content = content.unwrap_or_else(|| {
        println!("Enter note content (press Ctrl+D when done):");
        let mut input = String::new();
        std::io::stdin().read_line(&mut input).ok();
        input
    });

    let mut note = Note::new(title.clone(), note_content);

    if let Some(tags_str) = tags {
        for tag in tags_str.split(',') {
            note.add_tag(tag.trim().to_string());
        }
    }

    storage.save_note(&note)?;
    println!("{} {}", "Created note:".green(), title);
    println!("  ID: {}", note.id);

    Ok(())
}

fn cmd_show(storage: &Storage, id: String, show_backlinks: bool, show_links: bool) -> Result<()> {
    let graph = storage.load_all()?;
    let note_id = find_note_id(&graph, &id)?;

    let note = graph.get_note(&note_id).ok_or_else(|| {
        anyhow::anyhow!("Note '{}' not found", id)
    })?;

    println!("\n{}", note.title.bold().cyan());
    println!("{}\n", "=".repeat(note.title.len()));
    println!("{}", note.content);

    if !note.tags.is_empty() {
        println!("\n{}", "Tags:".yellow());
        println!("  {}", note.tags.join(", "));
    }

    if show_links {
        let forward = graph.get_forward_links(&note_id);
        if !forward.is_empty() {
            println!("\n{}", "Links to:".yellow());
            for link_id in &forward {
                if let Some(linked_note) = graph.get_note(link_id) {
                    println!("  → {} ({})", linked_note.title, link_id);
                }
            }
        }
    }

    if show_backlinks {
        let backward = graph.get_backward_links(&note_id);
        if !backward.is_empty() {
            println!("\n{}", "Backlinked from:".yellow());
            for link_id in &backward {
                if let Some(linked_note) = graph.get_note(link_id) {
                    println!("  ← {} ({})", linked_note.title, link_id);
                }
            }
        }
    }

    Ok(())
}

fn cmd_list(storage: &Storage, detailed: bool) -> Result<()> {
    let graph = storage.load_all()?;
    let note_ids = graph.note_ids();

    if note_ids.is_empty() {
        println!("{}", "No notes found.".yellow());
        return Ok(());
    }

    println!("\n{}", format!("Total notes: {}", note_ids.len()).cyan());
    println!("{}", "=".repeat(40));

    for (idx, note_id) in note_ids.iter().enumerate() {
        if let Some(note) = graph.get_note(note_id) {
            println!("\n{}. {}", idx + 1, note.title.bold());
            println!("   ID: {}", note_id);

            if detailed {
                let forward = graph.get_forward_links(note_id);
                let backward = graph.get_backward_links(note_id);
                println!("   Links: {} forward, {} backward", forward.len(), backward.len());

                if !note.tags.is_empty() {
                    println!("   Tags: {}", note.tags.join(", "));
                }

                println!("   Modified: {}", note.modified_at.format("%Y-%m-%d"));
            }
        }
    }

    println!();
    Ok(())
}

fn cmd_edit(storage: &Storage, id: String, content: Option<String>) -> Result<()> {
    let graph = storage.load_all()?;
    let note_id = find_note_id(&graph, &id)?;

    let mut note = graph.get_note(&note_id)
        .ok_or_else(|| anyhow::anyhow!("Note '{}' not found", id))?
        .clone();

    let new_content = content.unwrap_or_else(|| {
        println!("Editing note: {}", note.title);
        println!("Current content:\n{}\n", note.content);
        println!("Enter new content (press Ctrl+D when done):");
        let mut input = String::new();
        std::io::stdin().read_line(&mut input).ok();
        input
    });

    note.update_content(new_content);
    storage.save_note(&note)?;
    println!("{} {}", "Updated note:".green(), note.title);

    Ok(())
}

fn cmd_delete(storage: &Storage, id: String, force: bool) -> Result<()> {
    let graph = storage.load_all()?;
    let note_id = find_note_id(&graph, &id)?;

    let note = graph.get_note(&note_id)
        .ok_or_else(|| anyhow::anyhow!("Note '{}' not found", id))?;

    if !force {
        println!("Are you sure you want to delete '{}'? (y/N)", note.title);
        let mut confirm = String::new();
        std::io::stdin().read_line(&mut confirm)?;
        if !confirm.trim().to_lowercase().starts_with('y') {
            println!("{}", "Deletion cancelled.".yellow());
            return Ok(());
        }
    }

    storage.delete_note(&note_id)?;
    println!("{} {}", "Deleted note:".red(), note.title);

    Ok(())
}

fn cmd_search(storage: &Storage, query: &str, fuzzy: bool, limit: usize) -> Result<()> {
    let graph = storage.load_all()?;

    let results = if fuzzy {
        search::fuzzy_search(&graph, query)
    } else {
        search::search_notes(&graph, query)
    };

    let results: Vec<_> = results.into_iter().take(limit).collect();

    if results.is_empty() {
        println!("{} No results found for '{}'", "⚠".yellow(), query);
        return Ok(());
    }

    println!("\n{} {} results for '{}':\n", "🔍".cyan(), results.len(), query);

    for (idx, result) in results.iter().enumerate() {
        println!("{}. {} ({})", idx + 1, result.title.bold(), result.note_id);
        println!("   Score: {:.2}", result.score);

        if !result.matched_lines.is_empty() {
            println!("   Matches:");
            for line in &result.matched_lines {
                println!("     • {}", line);
            }
        }
        println!();
    }

    Ok(())
}

fn cmd_backlinks(storage: &Storage, id: String) -> Result<()> {
    let graph = storage.load_all()?;
    let note_id = find_note_id(&graph, &id)?;

    let note = graph.get_note(&note_id)
        .ok_or_else(|| anyhow::anyhow!("Note '{}' not found", id))?;

    let backlinks = graph.get_backward_links(&note_id);

    if backlinks.is_empty() {
        println!("{} No backlinks found for '{}'", "ℹ".blue(), note.title);
        return Ok(());
    }

    println!("\n{} backlinks for '{}':\n", backlinks.len(), note.title.bold());

    for (idx, link_id) in backlinks.iter().enumerate() {
        if let Some(linking_note) = graph.get_note(link_id) {
            println!("{}. {}", idx + 1, linking_note.title.bold());
            println!("   ID: {}", link_id);

            // Show context
            if let Some(pos) = linking_note.content.find(&format!("[[{}]]", note.id)) {
                let start = pos.saturating_sub(30);
                let end = (pos + 50).min(linking_note.content.len());
                let context = linking_note.content[start..end].trim();
                println!("   Context: \"...{}...\"", context);
            }
            println!();
        }
    }

    Ok(())
}

fn cmd_export(storage: &Storage, format: &str, output: &PathBuf) -> Result<()> {
    let graph = storage.load_all()?;

    let export_format = match format.to_lowercase().as_str() {
        "dot" => storage::ExportFormat::Dot,
        "json" => storage::ExportFormat::Json,
        _ => return Err(anyhow::anyhow!("Invalid format. Use 'dot' or 'json'")),
    };

    storage.export_graph(&graph, export_format, output)?;
    println!("{} Exported knowledge graph to {:?}", "✓".green(), output);

    Ok(())
}

fn cmd_stats(storage: &Storage, top_n: Option<usize>) -> Result<()> {
    let graph = storage.load_all()?;
    let stats = graph.statistics();

    println!("\n{}", "Knowledge Graph Statistics".bold().cyan());
    println!("{}", "=".repeat(40));
    println!("📝 Total notes: {}", stats.note_count);
    println!("🔗 Total links: {}", stats.link_count);
    println!("👻 Orphaned notes: {}", stats.orphaned_count);

    if !stats.most_connected.is_empty() {
        let top = top_n.unwrap_or(5);
        println!("\n{} Most connected notes:", "🌟".yellow());
        for (idx, (id, count)) in stats.most_connected.iter().take(top).enumerate() {
            if let Some(note) = graph.get_note(id) {
                println!("{}. {} - {} connections", idx + 1, note.title, count);
            }
        }
    }

    println!();
    Ok(())
}

/// Find a note ID from a partial match or title
fn find_note_id(graph: &types::KnowledgeGraph, query: &str) -> Result<String> {
    // Try exact match first
    if graph.get_note(query).is_some() {
        return Ok(query.to_string());
    }

    // Try case-insensitive title match
    let query_lower = query.to_lowercase();
    for note_id in graph.note_ids() {
        if let Some(note) = graph.get_note(&note_id) {
            if note.title.to_lowercase() == query_lower {
                return Ok(note_id);
            }
        }
    }

    // Try partial match
    for note_id in graph.note_ids() {
        if let Some(note) = graph.get_note(&note_id) {
            if note.title.to_lowercase().contains(&query_lower) {
                return Ok(note_id);
            }
        }
    }

    Err(anyhow::anyhow!("Note '{}' not found", query))
}
