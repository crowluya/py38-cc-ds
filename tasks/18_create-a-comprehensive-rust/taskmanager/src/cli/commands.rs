use super::output::{format_date, format_statistics, format_task_table, parse_date, parse_sort_option};
use super::Commands;
use crate::models::{Priority, Task};
use crate::storage::JsonStorage;
use crate::task_manager::{TaskFilter, TaskManager, TaskSort};
use anyhow::Result;
use chrono::Utc;
use colored::Colorize;
use dialoguer::{theme::ColorfulTheme, Input, MultiSelect, Select};
use inquire::{Confirm, Text};
use std::fs;
use std::path::PathBuf;
use uuid::Uuid;

/// Execute the CLI command
pub fn execute_command(command: Commands) -> Result<()> {
    let storage = JsonStorage::default_location()?;
    let mut manager = TaskManager::new(storage)?;

    match command {
        Commands::Add {
            title,
            description,
            priority,
            deadline,
            tags,
            interactive,
        } => {
            if interactive {
                cmd_add_interactive(&mut manager)?;
            } else {
                cmd_add(&mut manager, title, description, priority, deadline, tags)?;
            }
        }
        Commands::List {
            completed,
            pending,
            priority,
            tags,
            tags_any,
            search,
            sort,
            simple,
        } => {
            cmd_list(
                &manager,
                completed,
                pending,
                priority,
                tags,
                tags_any,
                search,
                sort,
                simple,
            )?;
        }
        Commands::Complete { id, additional } => {
            cmd_complete(&mut manager, id, additional)?;
        }
        Commands::Uncomplete { id } => {
            cmd_uncomplete(&mut manager, id)?;
        }
        Commands::Delete {
            id,
            additional,
            completed,
        } => {
            cmd_delete(&mut manager, id, additional, completed)?;
        }
        Commands::Edit {
            id,
            title,
            description,
            priority,
            deadline,
            add_tags,
            remove_tags,
            interactive,
        } => {
            if interactive {
                cmd_edit_interactive(&mut manager, id)?;
            } else {
                cmd_edit(
                    &mut manager,
                    id,
                    title,
                    description,
                    priority,
                    deadline,
                    add_tags,
                    remove_tags,
                )?;
            }
        }
        Commands::Stats { tags, priority } => {
            cmd_stats(&manager, tags, priority)?;
        }
        Commands::Search { query, sort } => {
            cmd_search(&manager, &query, sort)?;
        }
        Commands::Undo => {
            cmd_undo(&mut manager)?;
        }
        Commands::Redo => {
            cmd_redo(&mut manager)?;
        }
        Commands::Backup { create, list, restore } => {
            cmd_backup(&mut manager, create, list, restore)?;
        }
    }

    Ok(())
}

/// Add a new task
fn cmd_add(
    manager: &mut TaskManager<TaskManager<JsonStorage>>,
    title: String,
    description: Option<String>,
    priority: String,
    deadline: Option<String>,
    tags: Vec<String>,
) -> Result<()> {
    let priority = Priority::from_str(&priority)?;

    let deadline = match deadline {
        Some(d) => Some(parse_date(&d)?),
        None => None,
    };

    let mut task = Task::new(title)
        .with_description(description)
        .with_priority(priority)
        .with_deadline(deadline)
        .with_tags(tags);

    task.validate()?;

    let added = manager.add_task(task)?;
    println!(
        "{} {}",
        "✓ Task added:".green().bold(),
        added
    );

    // Check for deadline warnings
    if let Some(task) = manager.get_task(added.id) {
        show_deadline_warning(task);
    }

    Ok(())
}

/// Add task interactively
fn cmd_add_interactive(manager: &mut TaskManager<TaskManager<JsonStorage>>) -> Result<()> {
    println!("{}", "Add a new task".bold());
    println!("{}", "═".repeat(40).dimmed());

    let title = Text::new("Task title:")
        .with_placeholder("Enter task title")
        .prompt()?;

    let description = Text::new("Description (optional):")
        .with_placeholder("Enter task description")
        .allow_empty(true)
        .prompt()?;

    let description = if description.trim().is_empty() {
        None
    } else {
        Some(description)
    };

    let priorities = vec!["Low", "Medium", "High", "Critical"];
    let default_idx = 1; // Medium
    let priority_str = Select::new("Select priority:", priorities)
        .default(default_idx)
        .prompt()?;

    let priority = Priority::from_str(priority_str)?;

    let deadline_str = Text::new("Deadline (optional, format: YYYY-MM-DD):")
        .with_placeholder("e.g., 2024-12-31")
        .allow_empty(true)
        .prompt()?;

    let deadline = if deadline_str.trim().is_empty() {
        None
    } else {
        Some(parse_date(&deadline_str)?)
    };

    let tags_str = Text::new("Tags (optional, comma-separated):")
        .with_placeholder("e.g., work,urgent")
        .allow_empty(true)
        .prompt()?;

    let tags = if tags_str.trim().is_empty() {
        Vec::new()
    } else {
        tags_str
            .split(',')
            .map(|t| t.trim().to_string())
            .filter(|t| !t.is_empty())
            .collect()
    };

    let mut task = Task::new(title)
        .with_description(description)
        .with_priority(priority)
        .with_deadline(deadline)
        .with_tags(tags);

    task.validate()?;

    let added = manager.add_task(task)?;
    println!("\n{} {}", "✓ Task added:".green().bold(), added);

    if let Some(task) = manager.get_task(added.id) {
        show_deadline_warning(task);
    }

    Ok(())
}

/// List tasks
fn cmd_list(
    manager: &TaskManager<TaskManager<JsonStorage>>,
    completed: bool,
    pending: bool,
    priority_strs: Vec<String>,
    tags: Vec<String>,
    tags_any: bool,
    search: Option<String>,
    sort_str: String,
    simple: bool,
) -> Result<()> {
    let mut filter = TaskFilter::default();

    // Set completion filter
    if completed {
        filter.completed = Some(true);
    } else if pending {
        filter.completed = Some(false);
    }

    // Parse priorities
    if !priority_strs.is_empty() {
        let priorities: Result<Vec<_>, _> = priority_strs
            .iter()
            .map(|p| Priority::from_str(p))
            .collect();
        filter.priorities = Some(priorities?);
    }

    // Set tags
    if !tags.is_empty() {
        filter.tags = Some(tags);
        filter.tags_any = tags_any;
    }

    // Set search query
    if let Some(query) = search {
        filter.search_query = Some(query);
    }

    let sort = parse_sort_option(&sort_str)?;

    let tasks = manager.list_tasks(&filter, sort);

    println!("{}", format_task_table(&tasks, simple));

    // Show warnings for overdue tasks
    if !completed {
        for task in tasks.iter() {
            show_deadline_warning(task);
        }
    }

    Ok(())
}

/// Complete a task
fn cmd_complete(
    manager: &mut TaskManager<TaskManager<JsonStorage>>,
    id: String,
    additional: Vec<String>,
) -> Result<()> {
    let mut ids = vec![id];
    ids.extend(additional);

    for id_str in ids {
        let id = parse_task_id(manager, &id_str)?;

        match manager.get_task(id) {
            Some(task) => {
                if task.completed {
                    println!(
                        "{} {} is already completed",
                        "◉".yellow(),
                        format_task_name(task)
                    );
                } else {
                    manager.complete_task(id)?;
                    println!(
                        "{} {}",
                        "✓ Completed:".green().bold(),
                        format_task_name(task)
                    );
                }
            }
            None => {
                println!(
                    "{} Task with ID {} not found",
                    "✗".red(),
                    id_str.dimmed()
                );
                return Err(anyhow::anyhow!("Task not found"));
            }
        }
    }

    Ok(())
}

/// Uncomplete a task
fn cmd_uncomplete(
    manager: &mut TaskManager<TaskManager<JsonStorage>>,
    id: String,
) -> Result<()> {
    let id = parse_task_id(manager, &id)?;

    match manager.get_task(id) {
        Some(task) => {
            if !task.completed {
                println!(
                    "{} {} is not completed",
                    "◉".yellow(),
                    format_task_name(task)
                );
            } else {
                manager.uncomplete_task(id)?;
                println!(
                    "{} {}",
                    "○ Marked as incomplete:".bright_black(),
                    format_task_name(task)
                );
            }
        }
        None => {
            println!(
                "{} Task with ID {} not found",
                "✗".red(),
                id.dimmed()
            );
            return Err(anyhow::anyhow!("Task not found"));
        }
    }

    Ok(())
}

/// Delete a task
fn cmd_delete(
    manager: &mut TaskManager<TaskManager<JsonStorage>>,
    id: String,
    additional: Vec<String>,
    delete_completed: bool,
) -> Result<()> {
    if delete_completed {
        let count = manager.delete_completed()?;
        if count > 0 {
            println!("{} Deleted {} completed task(s)", "✓".green(), count);
        } else {
            println!("{}", "No completed tasks to delete".dimmed());
        }
        return Ok(());
    }

    let mut ids = vec![id];
    ids.extend(additional);

    for id_str in ids {
        let id = parse_task_id(manager, &id_str)?;

        match manager.get_task(id) {
            Some(task) => {
                let confirmed = Confirm::new(&format!(
                    "Delete task '{}'?",
                    task.title
                ))
                .with_default(false)
                .prompt()?;

                if confirmed {
                    manager.delete_task(id)?;
                    println!("{} Deleted: {}", "✓".green(), format_task_name(task));
                } else {
                    println!("{}", "Cancelled".dimmed());
                }
            }
            None => {
                println!(
                    "{} Task with ID {} not found",
                    "✗".red(),
                    id_str.dimmed()
                );
                return Err(anyhow::anyhow!("Task not found"));
            }
        }
    }

    Ok(())
}

/// Edit a task
fn cmd_edit(
    manager: &mut TaskManager<TaskManager<JsonStorage>>,
    id: String,
    title: Option<String>,
    description: Option<String>,
    priority: Option<String>,
    deadline: Option<String>,
    add_tags: Vec<String>,
    remove_tags: Vec<String>,
) -> Result<()> {
    let id = parse_task_id(manager, &id)?;

    manager.update_task(id, |task| {
        if let Some(new_title) = title {
            task.title = new_title;
        }

        if let Some(new_description) = description {
            task.description = if new_description.is_empty() {
                None
            } else {
                Some(new_description)
            };
        }

        if let Some(priority_str) = priority {
            if let Ok(p) = Priority::from_str(&priority_str) {
                task.priority = p;
            }
        }

        if let Some(deadline_str) = deadline {
            if deadline_str.is_empty() {
                task.deadline = None;
            } else if let Ok(d) = parse_date(&deadline_str) {
                task.deadline = Some(d);
            }
        }

        for tag in add_tags {
            if !task.tags.contains(&tag) {
                task.tags.push(tag);
            }
        }

        for tag in remove_tags {
            task.tags.retain(|t| t != &tag);
        }
    })?;

    let task = manager.get_task(id).unwrap();
    println!("{} {}", "✓ Updated:".green(), format_task_name(task));

    Ok(())
}

/// Edit task interactively
fn cmd_edit_interactive(manager: &mut TaskManager<TaskManager<JsonStorage>>, id: String) -> Result<()> {
    let id = parse_task_id(manager, &id)?;

    let task = match manager.get_task(id) {
        Some(t) => t.clone(),
        None => {
            println!("{} Task not found", "✗".red());
            return Err(anyhow::anyhow!("Task not found"));
        }
    };

    println!("{}", "Edit task".bold());
    println!("{}", "═".repeat(40).dimmed());
    println!("Current: {}\n", format_task_name(&task));

    let new_title = Text::new("New title (leave empty to keep current):")
        .with_default(&task.title)
        .prompt()?;

    let new_description = Text::new("New description (leave empty to keep current):")
        .with_default(task.description.as_deref().unwrap_or(""))
        .allow_empty(true)
        .prompt()?;

    manager.update_task(id, |t| {
        t.title = new_title;
        t.description = if new_description.trim().is_empty() {
            None
        } else {
            Some(new_description)
        };
    })?;

    println!("{} {}", "✓ Updated:".green(), format_task_name(&task));

    Ok(())
}

/// Show statistics
fn cmd_stats(
    manager: &TaskManager<TaskManager<JsonStorage>>,
    show_tags: bool,
    show_priority: bool,
) -> Result<()> {
    let stats = manager.get_statistics();

    if show_tags {
        // Show only tag stats
        println!("{}", "Tag Statistics".bold());
        println!("{}", "═".repeat(40).dimmed());
        if stats.all_tags.is_empty() {
            println!("{}", "No tags found".dimmed());
        } else {
            let mut sorted: Vec<_> = stats.all_tags.iter().collect();
            sorted.sort_by(|a, b| b.1.cmp(a.1));
            for (tag, count) in sorted {
                println!("  #{}: {}", tag.cyan(), count);
            }
        }
    } else if show_priority {
        // Show only priority stats
        println!("{}", "Priority Statistics".bold());
        println!("{}", "═".repeat(40).dimmed());
        for (priority, count) in stats.by_priority.iter() {
            println!("  {} {}: {}", priority.emoji(), priority, count);
        }
    } else {
        // Show full stats
        println!("{}", format_statistics(&stats));
    }

    Ok(())
}

/// Search tasks
fn cmd_search(
    manager: &TaskManager<TaskManager<JsonStorage>>,
    query: &str,
    sort_str: String,
) -> Result<()> {
    let sort = parse_sort_option(&sort_str)?;
    let tasks = manager.search_tasks(query);

    // Sort results
    let mut tasks_vec: Vec<_> = tasks.into_iter().collect();
    match sort {
        TaskSort::Priority => {
            tasks_vec.sort_by(|a, b| {
                b.priority
                    .cmp(&a.priority)
                    .then_with(|| a.created_at.cmp(&b.created_at))
            });
        }
        TaskSort::Title => {
            tasks_vec.sort_by(|a, b| a.title.to_lowercase().cmp(&b.title.to_lowercase()));
        }
        _ => {} // Default order
    }

    println!("{} {}\n", "Search results for:".bold(), query.cyan());
    println!("{}", format_task_table(&tasks_vec, false));

    Ok(())
}

/// Undo last operation
fn cmd_undo(manager: &mut TaskManager<TaskManager<JsonStorage>>) -> Result<()> {
    if manager.undo()? {
        println!("{}", "✓ Undo successful".green());
    } else {
        println!("{}", "Nothing to undo".dimmed());
    }
    Ok(())
}

/// Redo last undone operation
fn cmd_redo(manager: &mut TaskManager<TaskManager<JsonStorage>>) -> Result<()> {
    if manager.redo()? {
        println!("{}", "✓ Redo successful".green());
    } else {
        println!("{}", "Nothing to redo".dimmed());
    }
    Ok(())
}

/// Backup operations
fn cmd_backup(
    manager: &mut TaskManager<TaskManager<JsonStorage>>,
    create: bool,
    list: bool,
    restore: Option<String>,
) -> Result<()> {
    let storage = JsonStorage::default_location()?;

    if create {
        let backup_path = storage.create_backup()?;
        println!("{} Backup created: {}", "✓".green(), backup_path.display());
    } else if list {
        let backup_dir = storage.path().parent().unwrap();
        let backups: Vec<_> = fs::read_dir(backup_dir)?
            .filter_map(|entry| entry.ok())
            .filter(|entry| {
                entry
                    .file_name()
                    .to_string_lossy()
                    .starts_with("tasks.json.bak.")
            })
            .collect();

        if backups.is_empty() {
            println!("{}", "No backups found".dimmed());
        } else {
            println!("{}", "Available backups:".bold());
            for backup in backups {
                println!("  {}", backup.file_name().to_string_lossy());
            }
        }
    } else if let Some(restore_path) = restore {
        let path = PathBuf::from(restore_path);
        let tasks = storage.import_backup(&path)?;
        // Create backup before restoring
        let _ = storage.create_backup();

        for task in tasks {
            manager.add_task(task)?;
        }

        println!("{} Restored from backup", "✓".green());
    } else {
        println!("{}", "Use --create, --list, or --restore <file>".dimmed());
    }

    Ok(())
}

// Helper functions

/// Parse task ID from short or full UUID
fn parse_task_id(
    manager: &TaskManager<TaskManager<JsonStorage>>,
    id_str: &str,
) -> Result<Uuid> {
    // Try as full UUID first
    if let Ok(id) = Uuid::parse_str(id_str) {
        return Ok(id);
    }

    // Try as short ID (first 8 characters)
    let tasks = manager.all_tasks();
    let matches: Vec<_> = tasks
        .iter()
        .filter(|t| t.short_id() == id_str)
        .collect();

    if matches.len() == 1 {
        Ok(matches[0].id)
    } else if matches.is_empty() {
        Err(anyhow::anyhow!("No task found with ID {}", id_str))
    } else {
        Err(anyhow::anyhow!(
            "Multiple tasks match ID {}, use full UUID",
            id_str
        ))
    }
}

/// Format task name for display
fn format_task_name(task: &Task) -> String {
    format!(
        "{} {} {}",
        task.priority.emoji(),
        task.title.bold(),
        format!("[{}]", task.short_id()).dimmed()
    )
}

/// Show deadline warning if applicable
fn show_deadline_warning(task: &Task) {
    if task.completed {
        return;
    }

    if task.is_overdue() {
        println!(
            "   ⚠ {} is {}",
            task.title,
            "OVERDUE".red().bold()
        );
    } else if task.is_due_soon() {
        if let Some(deadline) = task.deadline {
            let hours_left = (deadline - Utc::now()).num_hours();
            println!(
                "   ⏰ {} is due in {} hour(s)",
                task.title,
                hours_left.to_string().yellow()
            );
        }
    }
}
