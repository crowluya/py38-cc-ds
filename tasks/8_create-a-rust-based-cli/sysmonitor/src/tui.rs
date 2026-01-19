use crate::types::{MonitoringState, SystemMetrics};
use crate::display::format_bytes;
use crossterm::{
    event::{self, DisableMouseCapture, EnableMouseCapture, Event, KeyCode},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use ratatui::{
    backend::{Backend, CrosstermBackend},
    layout::{Alignment, Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Span, Line},
    widgets::{Block, Borders, Paragraph, Wrap},
    Frame, Terminal,
};
use std::io;
use std::time::Duration;

/// Interactive Terminal User Interface
pub struct TuiApp {
    state: MonitoringState,
    should_quit: bool,
}

impl TuiApp {
    pub fn new(state: MonitoringState) -> Self {
        Self {
            state,
            should_quit: false,
        }
    }

    /// Run the TUI application
    pub fn run<B: Backend>(&mut self, terminal: &mut Terminal<B>) -> io::Result<()> {
        self.state.is_running = true;

        while !self.should_quit {
            terminal.draw(|f| self.draw(f))?;

            // Handle events with timeout
            if event::poll(Duration::from_millis(100))? {
                if let Event::Key(key) = event::read()? {
                    self.handle_key_event(key);
                }
            }
        }

        self.state.is_running = false;
        Ok(())
    }

    fn handle_key_event(&mut self, key: event::KeyEvent) {
        match key.code {
            KeyCode::Char('q') | KeyCode::Esc => self.should_quit = true,
            KeyCode::Char(' ') => {
                // Toggle pause/resume (not implemented yet)
            }
            _ => {}
        }
    }

    fn draw(&self, f: &mut Frame) {
        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .margin(1)
            .constraints([
                Constraint::Length(3), // Header
                Constraint::Length(10), // CPU & Memory
                Constraint::Length(12), // Disk
                Constraint::Min(8),     // Network & Alerts
                Constraint::Length(3),  // Footer
            ])
            .split(f.size());

        self.draw_header(f, chunks[0]);
        self.draw_cpu_memory(f, chunks[1]);
        self.draw_disk(f, chunks[2]);
        self.draw_network_alerts(f, chunks[3]);
        self.draw_footer(f, chunks[4]);
    }

    fn draw_header(&self, f: &mut Frame, area: Rect) {
        let title = Span::styled(
            "System Monitor",
            Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD),
        );

        let latest = self.state.get_latest_metrics();
        let time_str = latest
            .map(|m| m.timestamp.format("%Y-%m-%d %H:%M:%S").to_string())
            .unwrap_or_else(|| "No data".to_string());

        let time = Span::styled(
            time_str,
            Style::default().fg(Color::Gray),
        );

        let header = Paragraph::new(Line::from(vec![title, Span::raw("    "), time]))
            .block(Block::default().borders(Borders::ALL))
            .alignment(Alignment::Center);

        f.render_widget(header, area);
    }

    fn draw_cpu_memory(&self, f: &mut Frame, area: Rect) {
        let sections = Layout::default()
            .direction(Direction::Horizontal)
            .constraints([Constraint::Percentage(50), Constraint::Percentage(50)])
            .split(area);

        self.draw_cpu(f, sections[0]);
        self.draw_memory(f, sections[1]);
    }

    fn draw_cpu(&self, f: &mut Frame, area: Rect) {
        if let Some(metrics) = self.state.get_latest_metrics() {
            let cpu_text = vec![
                Line::from(vec![
                    Span::styled("CPU Usage", Style::default().fg(Color::Cyan)),
                ]),
                Line::from(vec![
                    Span::raw(format!("{:>6.1}%", metrics.cpu.usage_percent)),
                ]),
                Line::from(vec![
                    Span::styled(
                        format!("Load: {:.2}, {:.2}, {:.2}",
                            metrics.cpu.load_average.0,
                            metrics.cpu.load_average.1,
                            metrics.cpu.load_average.2
                        ),
                        Style::default().fg(Color::Gray),
                    ),
                ]),
            ];

            let paragraph = Paragraph::new(cpu_text)
                .block(Block::default().title("CPU").borders(Borders::ALL))
                .wrap(Wrap { trim: true });

            f.render_widget(paragraph, area);
        }
    }

    fn draw_memory(&self, f: &mut Frame, area: Rect) {
        if let Some(metrics) = self.state.get_latest_metrics() {
            let mem_text = vec![
                Line::from(vec![
                    Span::styled("Memory", Style::default().fg(Color::Cyan)),
                ]),
                Line::from(vec![
                    Span::raw(format!(
                        "{} / {} ({:.1}%)",
                        format_bytes(metrics.memory.used_bytes),
                        format_bytes(metrics.memory.total_bytes),
                        metrics.memory.usage_percent
                    )),
                ]),
                Line::from(vec![
                    Span::styled(
                        format!("Swap: {} / {}",
                            format_bytes(metrics.memory.swap_used_bytes),
                            format_bytes(metrics.memory.swap_total_bytes)
                        ),
                        Style::default().fg(Color::Gray),
                    ),
                ]),
            ];

            let paragraph = Paragraph::new(mem_text)
                .block(Block::default().title("Memory").borders(Borders::ALL))
                .wrap(Wrap { trim: true });

            f.render_widget(paragraph, area);
        }
    }

    fn draw_disk(&self, f: &mut Frame, area: Rect) {
        if let Some(metrics) = self.state.get_latest_metrics() {
            let mut disk_text = vec![];

            for disk in metrics.disk.iter().take(5) {
                let usage_color = if disk.usage_percent > 90.0 {
                    Color::Red
                } else if disk.usage_percent > 75.0 {
                    Color::Yellow
                } else {
                    Color::Green
                };

                disk_text.push(Line::from(vec![
                    Span::styled(
                        format!("{:<12}", disk.mount_point),
                        Style::default().fg(Color::Cyan),
                    ),
                    Span::raw(" "),
                    Span::styled(
                        format!("{:>5.1}%", disk.usage_percent),
                        Style::default().fg(usage_color),
                    ),
                    Span::raw(" "),
                    Span::styled(
                        format!("{} / {}",
                            format_bytes(disk.used_bytes),
                            format_bytes(disk.total_bytes)
                        ),
                        Style::default().fg(Color::Gray),
                    ),
                ]));
            }

            let paragraph = Paragraph::new(disk_text)
                .block(Block::default().title("Disk Usage").borders(Borders::ALL))
                .wrap(Wrap { trim: true });

            f.render_widget(paragraph, area);
        }
    }

    fn draw_network_alerts(&self, f: &mut Frame, area: Rect) {
        let sections = Layout::default()
            .direction(Direction::Horizontal)
            .constraints([Constraint::Percentage(50), Constraint::Percentage(50)])
            .split(area);

        self.draw_network(f, sections[0]);
        self.draw_alerts(f, sections[1]);
    }

    fn draw_network(&self, f: &mut Frame, area: Rect) {
        if let Some(metrics) = self.state.get_latest_metrics() {
            let mut net_text = vec![
                Line::from(vec![
                    Span::styled("Network Interfaces", Style::default().fg(Color::Cyan)),
                ]),
            ];

            for net in metrics.network.iter().take(5) {
                net_text.push(Line::from(vec![
                    Span::styled(
                        format!("{:<10}", net.interface),
                        Style::default().fg(Color::White),
                    ),
                    Span::raw(" ↓"),
                    Span::styled(
                        format!(" {}/s", format_bytes(net.rx_bytes_per_sec)),
                        Style::default().fg(Color::Green),
                    ),
                    Span::raw("  ↑"),
                    Span::styled(
                        format!(" {}/s", format_bytes(net.tx_bytes_per_sec)),
                        Style::default().fg(Color::Blue),
                    ),
                ]));
            }

            let paragraph = Paragraph::new(net_text)
                .block(Block::default().title("Network").borders(Borders::ALL))
                .wrap(Wrap { trim: true });

            f.render_widget(paragraph, area);
        }
    }

    fn draw_alerts(&self, f: &mut Frame, area: Rect) {
        let mut alert_text = vec![];

        if self.state.active_alerts.is_empty() {
            alert_text.push(Line::from(vec![
                Span::styled("No active alerts", Style::default().fg(Color::Green)),
            ]));
        } else {
            for alert in self.state.active_alerts.iter().rev().take(8) {
                let time = alert.timestamp.format("%H:%M:%S").to_string();
                alert_text.push(Line::from(vec![
                    Span::styled(
                        format!("[{}] ", time),
                        Style::default().fg(Color::Gray),
                    ),
                    Span::styled(
                        &alert.message,
                        Style::default().fg(Color::Red).add_modifier(Modifier::BOLD),
                    ),
                ]));
            }
        }

        let paragraph = Paragraph::new(alert_text)
            .block(Block::default().title("Recent Alerts").borders(Borders::ALL))
            .wrap(Wrap { trim: true });

        f.render_widget(paragraph, area);
    }

    fn draw_footer(&self, f: &mut Frame, area: Rect) {
        let footer_text = vec![
            Line::from(vec![
                Span::styled("Press ", Style::default().fg(Color::Gray)),
                Span::styled("q", Style::default().fg(Color::Cyan)),
                Span::styled(" to quit", Style::default().fg(Color::Gray)),
            ]),
            Line::from(vec![
                Span::styled(
                    format!("Data points: {} | History size: {}",
                        self.state.metrics_history.len(),
                        self.state.config.history_size
                    ),
                    Style::default().fg(Color::DarkGray),
                ),
            ]),
        ];

        let paragraph = Paragraph::new(footer_text)
            .block(Block::default().borders(Borders::ALL))
            .alignment(Alignment::Center);

        f.render_widget(paragraph, area);
    }
}

/// Initialize and run the TUI
pub fn run_tui(mut state: MonitoringState) -> anyhow::Result<()> {
    enable_raw_mode()?;
    let mut stdout = io::stdout();
    execute!(stdout, EnterAlternateScreen, EnableMouseCapture)?;
    let backend = CrosstermBackend::new(stdout);
    let mut terminal = Terminal::new(backend)?;

    let mut app = TuiApp::new(state.clone());
    let result = app.run(&mut terminal);

    disable_raw_mode()?;
    execute!(
        terminal.backend_mut(),
        LeaveAlternateScreen,
        DisableMouseCapture
    )?;
    terminal.show_cursor()?;

    result?;
    Ok(())
}
