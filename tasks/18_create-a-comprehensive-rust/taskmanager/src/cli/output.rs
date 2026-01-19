use crate::models::Priority;
use crate::models::Task;
use crate::task_manager::TaskSort;
use chrono::{DateTime, Utc};
use colored::Colorize;
use tabled::{
    settings::{
        object::Rows,
        style::{Border, HorizontalLine},
        Alignment, Modify,
    },
    Table, Tabled,
};

/// Format a task list as a table
pub fn format_task_table(tasks: &[&Task], simple: bool) -> String {
    if tasks.is_empty() {
        return "No tasks found.".dimmed().to_string();
    }

    if simple {
        format_simple_list(tasks)
    } else {
        format_table(tasks)
    }
}

/// Format tasks as a simple list
fn format_simple_list(tasks: &[&Task]) -> String {
    tasks
        .iter()
        .map(|task| format_task_simple(task))
        .collect::<Vec<_>>()
        .join("\n")
}

/// Format a single task in simple format
fn format_task_simple(task: &Task) -> String {
    let status = if task.completed {
        "✓".green()
    } else {
        "○".bright_black()
    };

    let priority = format!("{} {}", task.priority.emoji(), task.priority.short_name())
        .color(get_priority_color(task.priority));

    let deadline_str = match task.deadline {
        Some(deadline) => {
            let date_str = deadline.format("%Y-%m-%d").to_string();
            if task.is_overdue() {
                format!(" {}", date_str.red().bold())
            } else if task.is_due_soon() {
                format!(" {}", date_str.yellow().bold())
            } else {
                format!(" {}", date_str.bright_black())
            }
        }
        None => String::new(),
    };

    let tags_str = if task.tags.is_empty() {
        String::new()
    } else {
        format!(
            " {}",
            task.tags
                .iter()
                .map(|t| format!("#{}", t.cyan()))
                .collect::<Vec<_>>()
                .join(" ")
        )
    };

    format!(
        "{} {} {}{}{} {}",
        status,
        priority,
        task.title.bold(),
        deadline_str,
        tags_str,
        format_id(task)
    )
}

/// Format tasks as a detailed table
fn format_table(tasks: &[&Task]) -> String {
    let rows: Vec<TaskRow> = tasks.iter().map(|t| TaskRow::from_task(*t)).collect();

    Table::new(rows)
        .with(Modify::new(Rows::new(1..)).with(Alignment::left()))
        .with(
            Border::new()
                .set_top(HorizontalLine::new('─', '┬', '╌', '┌'))
                .set_bottom(HorizontalLine::new('─', '┴', '╌', '└'))
                .set_vertical('│')
                .set_horizontal('─')
                .set_left_corner('│')
                .set_right_corner('│')
                .set_left_intersection('├')
                .set_right_intersection('┤')
                .set_top_left_corner('╭')
                .set_top_right_corner('╮')
                .set_bottom_left_corner('╰')
                .set_bottom_right_corner('╯'),
        )
        .to_string()
}

/// Get color for priority
fn get_priority_color(priority: Priority) -> colored::Color {
    match priority {
        Priority::Low => colored::Color::Blue,
        Priority::Medium => colored::Color::Yellow,
        Priority::High => colored::Color::Magenta,
        Priority::Critical => colored::Color::Red,
    }
}

/// Format task ID
fn format_id(task: &Task) -> String {
    format!("[{}]", task.short_id()).dimmed().to_string()
}

/// Table row for task display
#[derive(Tabled)]
struct TaskRow {
    #[tabled(rename = "ID")]
    id: String,
    #[tabled(rename = "Status")]
    status: String,
    #[tabled(rename = "Priority")]
    priority: String,
    #[tabled(rename = "Title")]
    title: String,
    #[tabled(rename = "Deadline")]
    deadline: String,
    #[tabled(rename = "Tags")]
    tags: String,
}

impl TaskRow {
    fn from_task(task: &Task) -> Self {
        let status = if task.completed {
            "✓".to_string()
        } else {
            "○".to_string()
        };

        let priority = format!("{} {}", task.priority.emoji(), task.priority.short_name());

        let deadline = match task.deadline {
            Some(d) => {
                if task.is_overdue() {
                    format!("{} (overdue)", d.format("%Y-%m-%d"))
                } else if task.is_due_soon() {
                    format!("{} (soon)", d.format("%Y-%m-%d"))
                } else {
                    d.format("%Y-%m-%d").to_string()
                }
            }
            None => "-".to_string(),
        };

        let tags = if task.tags.is_empty() {
            "-".to_string()
        } else {
            task.tags
                .iter()
                .map(|t| format!("#{}", t))
                .collect::<Vec<_>>()
                .join(" ")
        };

        Self {
            id: task.short_id(),
            status,
            priority,
            title: task.title.clone(),
            deadline,
            tags,
        }
    }
}

/// Parse sort option from string
pub fn parse_sort_option(sort_str: &str) -> Result<TaskSort, String> {
    match sort_str.to_lowercase().as_str() {
        "priority" => Ok(TaskSort::Priority),
        "deadline" => Ok(TaskSort::Deadline),
        "created" => Ok(TaskSort::Created),
        "completed" => Ok(TaskSort::Completed),
        "title" => Ok(TaskSort::Title),
        _ => Err(format!(
            "Invalid sort option: '{}'. Valid options are: priority, deadline, created, completed, title",
            sort_str
        )),
    }
}

/// Parse date string to DateTime
pub fn parse_date(date_str: &str) -> Result<DateTime<Utc>, String> {
    // Try different formats
    let formats = [
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d %H:%M",
        "%Y/%m/%d",
    ];

    for format in &formats {
        if let Ok(naive) = chrono::NaiveDateTime::parse_from_str(date_str, format) {
            return Ok(DateTime::from_naive_utc_and_offset(naive, Utc));
        }

        if let Ok(naive_date) = chrono::NaiveDate::parse_from_str(date_str, format) {
            let naive = naive_date.and_hms_opt(23, 59, 59).unwrap();
            return Ok(DateTime::from_naive_utc_and_offset(naive, Utc));
        }
    }

    Err(format!(
        "Invalid date format: '{}'. Expected format: YYYY-MM-DD or YYYY-MM-DD HH:MM",
        date_str
    ))
}

/// Format statistics for display
pub fn format_statistics(stats: &crate::task_manager::TaskStatistics) -> String {
    let mut output = String::new();

    output.push_str(&format!(
        "{}\n",
        "═══════════════════════════════════════".dimmed()
    ));
    output.push_str(&format!(
        "{}\n",
        "           TASK STATISTICS           ".bold()
    ));
    output.push_str(&format!(
        "{}\n\n",
        "═══════════════════════════════════════".dimmed()
    ));

    output.push_str(&format!(
        "  Total Tasks:     {}\n",
        stats.total.to_string().bold()
    ));
    output.push_str(&format!(
        "  Completed:       {}\n",
        stats.completed.to_string().green()
    ));
    output.push_str(&format!(
        "  Pending:         {}\n",
        stats.pending.to_string().yellow()
    ));
    output.push_str(&format!(
        "  Overdue:         {}\n",
        stats.overdue.to_string().red().bold()
    ));
    output.push_str(&format!(
        "  Due Soon:        {}\n",
        stats.due_soon.to_string().yellow().bold()
    ));
    output.push_str(&format!(
        "  Completion Rate: {:.1}%\n",
        stats.completion_rate
    ));

    if !stats.by_priority.is_empty() {
        output.push_str("\n");
        output.push_str(&format!("{}\n", "By Priority:".bold()));
        for (priority, count) in stats.by_priority.iter() {
            output.push_str(&format!(
                "  {} {}: {}\n",
                priority.emoji(),
                priority,
                count.to_string().color(get_priority_color(*priority))
            ));
        }
    }

    if !stats.all_tags.is_empty() {
        output.push_str("\n");
        output.push_str(&format!("{}\n", "Tags:".bold()));
        let mut sorted_tags: Vec<_> = stats.all_tags.iter().collect();
        sorted_tags.sort_by(|a, b| b.1.cmp(a.1)); // Sort by count descending
        for (tag, count) in sorted_tags.iter().take(10) {
            output.push_str(&format!("  #{}: {}\n", tag.cyan(), count));
        }
    }

    output
}
