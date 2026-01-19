use ratatui::{
    backend::Backend,
    layout::{Alignment, Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Paragraph, Wrap},
    Frame,
};
use crate::metrics::{Metrics, format_bytes};
use crate::config::Config;
use chrono::Local;

/// Color theme definitions
pub struct Theme {
    pub cpu_color: Color,
    pub memory_color: Color,
    pub disk_color: Color,
    pub swap_color: Color,
    pub text_color: Color,
    pub border_color: Color,
    pub highlight_color: Color,
}

impl Theme {
    /// Get theme by name
    pub fn from_name(name: &str) -> Self {
        match name {
            "gruvbox" => Theme {
                cpu_color: Color::Rgb(204, 36, 29),     // red
                memory_color: Color::Rgb(213, 196, 161), // fg
                disk_color: Color::Rgb(152, 151, 26),    // green
                swap_color: Color::Rgb(215, 135, 75),    // orange
                text_color: Color::Rgb(235, 219, 178),   // bg2
                border_color: Color::Rgb(69, 133, 136),  // aqua
                highlight_color: Color::Rgb(251, 241, 199), // bg0
            },
            "monokai" => Theme {
                cpu_color: Color::Rgb(255, 85, 85),      // red
                memory_color: Color::Rgb(102, 217, 239), // cyan
                disk_color: Color::Rgb(249, 38, 114),    // magenta
                swap_color: Color::Rgb(230, 219, 116),   // yellow
                text_color: Color::Rgb(248, 248, 242),   // fg
                border_color: Color::Rgb(117, 113, 94),  // comment
                highlight_color: Color::Rgb(73, 72, 62), // bg1
            },
            "nord" => Theme {
                cpu_color: Color::Rgb(191, 97, 106),     // red
                memory_color: Color::Rgb(94, 129, 172),  // blue
                disk_color: Color::Rgb(163, 190, 140),   // green
                swap_color: Color::Rgb(208, 135, 112),   // orange
                text_color: Color::Rgb(216, 222, 233),   // fg
                border_color: Color::Rgb(59, 66, 82),    // bg3
                highlight_color: Color::Rgb(46, 52, 64), // bg2
            },
            _ => Theme::default(), // default theme
        }
    }

    /// Default theme
    pub fn default() -> Self {
        Theme {
            cpu_color: Color::Red,
            memory_color: Color::Cyan,
            disk_color: Color::Green,
            swap_color: Color::Yellow,
            text_color: Color::White,
            border_color: Color::Gray,
            highlight_color: Color::DarkGray,
        }
    }
}

/// Render the complete dashboard UI
pub fn render_ui<B: Backend>(f: &mut Frame<B>, metrics: &Metrics, config: &Config, interval: f64) {
    let theme = Theme::from_name(&config.theme);
    let size = f.area();

    // Calculate layout
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .margin(1)
        .constraints([
            Constraint::Length(3),  // Header
            Constraint::Min(0),     // Main content
            Constraint::Length(1),  // Footer
        ])
        .split(size);

    // Render header
    render_header(f, chunks[0], metrics, interval, &theme);

    // Calculate main content layout
    let mut constraints = vec![];
    if config.show_cpu {
        constraints.push(Constraint::Percentage(33));
    }
    if config.show_memory {
        constraints.push(Constraint::Percentage(33));
    }
    if config.show_disk {
        constraints.push(Constraint::Percentage(33));
    }

    if constraints.is_empty() {
        constraints.push(Constraint::Percentage(100));
    }

    let main_chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints(constraints.as_slice())
        .split(chunks[1]);

    let mut chunk_idx = 0;

    // Render CPU section
    if config.show_cpu && chunk_idx < main_chunks.len() {
        render_cpu_section(f, main_chunks[chunk_idx], metrics, &theme);
        chunk_idx += 1;
    }

    // Render Memory section
    if config.show_memory && chunk_idx < main_chunks.len() {
        render_memory_section(f, main_chunks[chunk_idx], metrics, &theme);
        chunk_idx += 1;
    }

    // Render Disk section
    if config.show_disk && chunk_idx < main_chunks.len() {
        render_disk_section(f, main_chunks[chunk_idx], metrics, &theme);
        chunk_idx += 1;
    }

    // Render footer
    render_footer(f, chunks[2], &theme);
}

/// Render the header section
fn render_header<B: Backend>(f: &mut Frame<B>, area: Rect, metrics: &Metrics, interval: f64, theme: &Theme) {
    let datetime = Local::now().format("%Y-%m-%d %H:%M:%S");
    let title = Line::from(vec![
        Span::styled(" Productivity Dashboard ", Style::default()
            .fg(Color::White)
            .add_modifier(Modifier::BOLD)),
        Span::raw(" | "),
        Span::styled(format!("Host: {} ", metrics.hostname), Style::default().fg(theme.text_color)),
        Span::raw(" | "),
        Span::styled(format!("Update: {:.1}s ", interval), Style::default().fg(theme.text_color)),
        Span::raw(" | "),
        Span::styled(datetime.to_string(), Style::default().fg(theme.text_color)),
    ]);

    let header = Paragraph::new(vec![title])
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_style(Style::default().fg(theme.border_color))
        )
        .alignment(Alignment::Center);

    f.render_widget(header, area);
}

/// Render CPU metrics section
fn render_cpu_section<B: Backend>(f: &mut Frame<B>, area: Rect, metrics: &Metrics, theme: &Theme) {
    let mut lines = vec![];

    // Global CPU usage
    if let Some(cpu) = metrics.cpu.first() {
        let usage = cpu.global_usage;
        let bar_width = 40;
        let filled = (usage as f64 / 100.0 * bar_width as f64) as usize;

        let bar: String = {
            let mut s = String::from("│");
            for i in 0..bar_width {
                if i < filled {
                    s.push('█');
                } else {
                    s.push('░');
                }
            }
            s.push('│');
            s
        };

        lines.push(Line::from(vec![
            Span::styled("Global CPU: ", Style::default().fg(theme.text_color)),
            Span::styled(format!("{:.1}%", usage), Style::default().fg(theme.cpu_color)),
        ]));

        lines.push(Line::from(vec![
            Span::styled(bar, Style::default().fg(theme.cpu_color)),
        ]));

        lines.push(Line::from(""));
    }

    // Per-core CPU usage
    lines.push(Line::from(vec![
        Span::styled("CPU Cores:", Style::default().fg(theme.text_color).add_modifier(Modifier::BOLD)),
    ]));

    for cpu in &metrics.cpu {
        let usage = cpu.core_usage.get(0).unwrap_or(&0.0);
        let bar_width = 30;
        let filled = (usage / 100.0 * bar_width as f32) as usize;

        let bar: String = {
            let mut s = String::new();
            for i in 0..bar_width {
                if i < filled {
                    s.push('█');
                } else {
                    s.push('░');
                }
            }
            s
        };

        lines.push(Line::from(vec![
            Span::styled(format!("  {} ", cpu.name), Style::default().fg(theme.text_color)),
            Span::styled(bar, Style::default().fg(theme.cpu_color)),
            Span::styled(format!(" {:.1}%", usage), Style::default().fg(theme.cpu_color)),
        ]));
    }

    let cpu_paragraph = Paragraph::new(lines)
        .block(
            Block::default()
                .title(" CPU Usage ")
                .title_style(Style::default().fg(theme.cpu_color).add_modifier(Modifier::BOLD))
                .borders(Borders::ALL)
                .border_style(Style::default().fg(theme.border_color))
        )
        .wrap(Wrap { trim: true });

    f.render_widget(cpu_paragraph, area);
}

/// Render Memory metrics section
fn render_memory_section<B: Backend>(f: &mut Frame<B>, area: Rect, metrics: &Metrics, theme: &Theme) {
    let mem = &metrics.memory;
    let mut lines = vec![];

    // Memory usage bar
    let bar_width = 40;
    let mem_filled = (mem.usage_percent / 100.0 * bar_width as f32) as usize;

    let mem_bar: String = {
        let mut s = String::from("│");
        for i in 0..bar_width {
            if i < mem_filled {
                s.push('█');
            } else {
                s.push('░');
            }
        }
        s.push('│');
        s
    };

    lines.push(Line::from(vec![
        Span::styled("Memory:", Style::default().fg(theme.text_color)),
        Span::styled(format!(" {:.1}%", mem.usage_percent), Style::default().fg(theme.memory_color)),
    ]));

    lines.push(Line::from(vec![
        Span::styled(mem_bar, Style::default().fg(theme.memory_color)),
    ]));

    lines.push(Line::from(vec![
        Span::styled(format!("  Used:      {}", format_bytes(mem.used_memory)), Style::default().fg(theme.text_color)),
    ]));

    lines.push(Line::from(vec![
        Span::styled(format!("  Available: {}", format_bytes(mem.available_memory)), Style::default().fg(theme.text_color)),
    ]));

    lines.push(Line::from(vec![
        Span::styled(format!("  Total:     {}", format_bytes(mem.total_memory)), Style::default().fg(theme.text_color)),
    ]));

    lines.push(Line::from(""));

    // Swap usage
    if mem.total_swap > 0 {
        let swap_bar_width = 40;
        let swap_filled = (mem.swap_usage_percent / 100.0 * swap_bar_width as f32) as usize;

        let swap_bar: String = {
            let mut s = String::from("│");
            for i in 0..swap_bar_width {
                if i < swap_filled {
                    s.push('█');
                } else {
                    s.push('░');
                }
            }
            s.push('│');
            s
        };

        lines.push(Line::from(vec![
            Span::styled("Swap:", Style::default().fg(theme.text_color)),
            Span::styled(format!(" {:.1}%", mem.swap_usage_percent), Style::default().fg(theme.swap_color)),
        ]));

        lines.push(Line::from(vec![
            Span::styled(swap_bar, Style::default().fg(theme.swap_color)),
        ]));

        lines.push(Line::from(vec![
            Span::styled(format!("  Used:  {}", format_bytes(mem.used_swap)), Style::default().fg(theme.text_color)),
        ]));

        lines.push(Line::from(vec![
            Span::styled(format!("  Total: {}", format_bytes(mem.total_swap)), Style::default().fg(theme.text_color)),
        ]));
    } else {
        lines.push(Line::from(vec![
            Span::styled("Swap: Not available", Style::default().fg(theme.text_color)),
        ]));
    }

    let mem_paragraph = Paragraph::new(lines)
        .block(
            Block::default()
                .title(" Memory & Swap ")
                .title_style(Style::default().fg(theme.memory_color).add_modifier(Modifier::BOLD))
                .borders(Borders::ALL)
                .border_style(Style::default().fg(theme.border_color))
        )
        .wrap(Wrap { trim: true });

    f.render_widget(mem_paragraph, area);
}

/// Render Disk metrics section
fn render_disk_section<B: Backend>(f: &mut Frame<B>, area: Rect, metrics: &Metrics, theme: &Theme) {
    let mut lines = vec![];

    if metrics.disks.is_empty() {
        lines.push(Line::from(vec![
            Span::styled("No disk information available", Style::default().fg(theme.text_color)),
        ]));
    } else {
        for disk in &metrics.disks {
            // Skip small or system partitions
            if disk.total_space < 1024 * 1024 * 100 {
                // Skip partitions smaller than 100 MB
                continue;
            }

            let bar_width = 30;
            let filled = (disk.usage_percent / 100.0 * bar_width as f32) as usize;

            let bar: String = {
                let mut s = String::new();
                for i in 0..bar_width {
                    if i < filled {
                        s.push('█');
                    } else {
                        s.push('░');
                    }
                }
                s
            };

            lines.push(Line::from(vec![
                Span::styled(format!("{}", disk.mount_point), Style::default().fg(theme.disk_color).add_modifier(Modifier::BOLD)),
                Span::styled(format!(" {:.1}%", disk.usage_percent), Style::default().fg(theme.disk_color)),
            ]));

            lines.push(Line::from(vec![
                Span::styled(bar, Style::default().fg(theme.disk_color)),
            ]));

            lines.push(Line::from(vec![
                Span::styled(
                    format!("  {} / {} ({:.1}% used)",
                        format_bytes(disk.used_space),
                        format_bytes(disk.total_space),
                        disk.usage_percent
                    ),
                    Style::default().fg(theme.text_color)
                ),
            ]));

            lines.push(Line::from(""));
        }
    }

    let disk_paragraph = Paragraph::new(lines)
        .block(
            Block::default()
                .title(" Disk Usage ")
                .title_style(Style::default().fg(theme.disk_color).add_modifier(Modifier::BOLD))
                .borders(Borders::ALL)
                .border_style(Style::default().fg(theme.border_color))
        )
        .wrap(Wrap { trim: true });

    f.render_widget(disk_paragraph, area);
}

/// Render the footer section
fn render_footer<B: Backend>(f: &mut Frame<B>, area: Rect, theme: &Theme) {
    let footer_text = Line::from(vec![
        Span::styled(" Press ", Style::default().fg(theme.text_color)),
        Span::styled("q", Style::default().fg(Color::Red).add_modifier(Modifier::BOLD)),
        Span::styled(" to quit | ", Style::default().fg(theme.text_color)),
        Span::styled("+", Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
        Span::styled("/", Style::default().fg(theme.text_color)),
        Span::styled("-", Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
        Span::styled(" to adjust refresh rate", Style::default().fg(theme.text_color)),
    ]);

    let footer = Paragraph::new(footer_text)
        .alignment(Alignment::Center);

    f.render_widget(footer, area);
}
