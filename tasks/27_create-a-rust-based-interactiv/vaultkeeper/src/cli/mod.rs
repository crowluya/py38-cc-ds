use crate::clipboard::ClipboardManager;
use crate::config::Config;
use crate::vault::{Vault, VaultEntry};
use crate::validation::{analyze_password, PasswordStrength};
use anyhow::Result;
use crossterm::{
    event::{self, DisableMouseCapture, EnableMouseCapture, Event, KeyCode, KeyEvent},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use ratatui::{
    backend::CrosstermBackend,
    layout::{Alignment, Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Span, Text},
    widgets::{Block, BorderType, Borders, List, ListItem, Paragraph, Wrap},
    Frame, Terminal,
};
use std::io;
use std::sync::{Arc, Mutex};

mod app;
pub use app::{App, AppState, InputMode};

/// Terminal UI for VaultKeeper
pub struct VaultUI {
    terminal: Terminal<CrosstermBackend<io::Stdout>>,
    app: Arc<Mutex<App>>,
}

impl VaultUI {
    /// Creates a new VaultUI instance
    pub fn new(config: Config) -> Result<Self> {
        // Setup terminal
        enable_raw_mode()?;
        let mut stdout = io::stdout();
        execute!(stdout, EnterAlternateScreen, EnableMouseCapture)?;
        let backend = CrosstermBackend::new(stdout);
        let terminal = Terminal::new(backend)?;

        let app = Arc::new(Mutex::new(App::new(config)));

        Ok(Self { terminal, app })
    }

    /// Runs the main UI loop
    pub fn run(&mut self, mut vault: Vault) -> Result<Vault> {
        {
            let mut app = self.app.lock().unwrap();
            app.set_vault(vault);
        }

        let res = self.run_inner();

        // Restore terminal
        disable_raw_mode()?;
        execute!(
            self.terminal.backend_mut(),
            LeaveAlternateScreen,
            DisableMouseCapture
        )?;

        // Return vault (possibly modified)
        let app = self.app.lock().unwrap();
        vault = app.get_vault().clone();

        res?;
        Ok(vault)
    }

    fn run_inner(&mut self) -> Result<()> {
        loop {
            // Draw UI
            self.terminal.draw(|f| {
                let app = self.app.lock().unwrap();
                Self::draw(f, &app);
            })?;

            // Handle events
            if event::poll(std::time::Duration::from_millis(100))? {
                if let Event::Key(key) = event::read()? {
                    let mut app = self.app.lock().unwrap();
                    if app.handle_key_event(key) {
                        return Ok(());
                    }
                }
            }
        }
    }

    fn draw(f: &mut Frame, app: &App) {
        let size = f.size();

        // Main layout
        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .margin(1)
            .constraints(
                [
                    Constraint::Length(3),  // Header
                    Constraint::Length(3),  // Search bar
                    Constraint::Min(0),     // Entry list
                    Constraint::Length(3),  // Footer
                ]
                .as_ref(),
            )
            .split(size);

        // Draw header
        Self::draw_header(f, chunks[0], app);

        // Draw search bar
        Self::draw_search(f, chunks[1], app);

        // Draw entry list
        Self::draw_entry_list(f, chunks[2], app);

        // Draw footer
        Self::draw_footer(f, chunks[3], app);

        // Draw entry details modal if viewing
        if app.state == AppState::ViewingEntry {
            Self::draw_entry_modal(f, app, size);
        }

        // Draw add/edit entry modal if editing
        if app.state == AppState::AddingEntry || app.state == AppState::EditingEntry {
            Self::draw_entry_form(f, app, size);
        }
    }

    fn draw_header(f: &mut Frame, area: Rect, app: &App) {
        let title = Span::styled(
            " VaultKeeper - Password Manager ",
            Style::default()
                .fg(Color::Cyan)
                .add_modifier(Modifier::BOLD),
        );

        let header = Paragraph::new(title)
            .block(
                Block::default()
                    .borders(Borders::ALL)
                    .border_type(BorderType::Rounded),
            )
            .alignment(Alignment::Center);

        f.render_widget(header, area);
    }

    fn draw_search(f: &mut Frame, area: Rect, app: &App) {
        let search_text = if app.input_mode == InputMode::Search {
            Span::raw(format!("Search: {}_ ", app.search_query))
        } else {
            Span::raw(format!("Search: {}", app.search_query))
        };

        let search_paragraph = Paragraph::new(search_text)
            .block(
                Block::default()
                    .borders(Borders::ALL)
                    .border_style(if app.input_mode == InputMode::Search {
                        Style::default().fg(Color::Yellow)
                    } else {
                        Style::default()
                    })
                    .title(" Filter "),
            )
            .wrap(Wrap { trim: false });

        f.render_widget(search_paragraph, area);
    }

    fn draw_entry_list(f: &mut Frame, area: Rect, app: &App) {
        let entries: Vec<ListItem> = app
            .filtered_entries()
            .iter()
            .enumerate()
            .map(|(i, entry)| {
                let style = if i == app.selected_index {
                    Style::default()
                        .fg(Color::Yellow)
                        .add_modifier(Modifier::BOLD)
                } else {
                    Style::default()
                };

                let content = format!("{} - {}", entry.title, entry.username);
                ListItem::new(Span::styled(content, style))
            })
            .collect();

        let list = List::new(entries)
            .block(
                Block::default()
                    .borders(Borders::ALL)
                    .title(format!(" Entries ({}) ", app.filtered_entries().len())),
            )
            .highlight_style(
                Style::default()
                    .bg(Color::DarkGray)
                    .add_modifier(Modifier::BOLD),
            );

        f.render_widget(list, area);
    }

    fn draw_footer(f: &mut Frame, area: Rect, app: &App) {
        let help_text = vec![
            Span::raw(" "),
            Span::styled(
                "↑↓",
                Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD),
            ),
            Span::raw(" Navigate "),
            Span::styled(
                "Enter",
                Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD),
            ),
            Span::raw(" View "),
            Span::styled(
                "a",
                Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD),
            ),
            Span::raw(" Add "),
            Span::styled(
                "d",
                Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD),
            ),
            Span::raw(" Delete "),
            Span::styled(
                "q",
                Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD),
            ),
            Span::raw(" Quit "),
            Span::raw(" "),
        ];

        let footer = Paragraph::new(Text::from(help_text))
            .block(
                Block::default()
                    .borders(Borders::ALL)
                    .border_type(BorderType::Rounded),
            )
            .alignment(Alignment::Center);

        f.render_widget(footer, area);
    }

    fn draw_entry_modal(f: &mut Frame, app: &App, size: Rect) {
        let popup_area = Rect {
            x: size.width / 4,
            y: size.height / 4,
            width: size.width / 2,
            height: size.height / 2,
        };

        f.render_widget(
            Block::default()
                .borders(Borders::ALL)
                .border_type(BorderType::Double)
                .style(Style::default().bg(Color::Black)),
            popup_area,
        );

        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .margin(1)
            .constraints([Constraint::Percentage(50), Constraint::Percentage(50)].as_ref())
            .split(popup_area);

        if let Some(entry) = app.selected_entry() {
            let details = vec![
                Span::styled("Title:\n", Style::default().fg(Color::Cyan)),
                Span::raw(&entry.title),
                Span::raw("\n\n"),
                Span::styled("Username:\n", Style::default().fg(Color::Cyan)),
                Span::raw(&entry.username),
                Span::raw("\n\n"),
                Span::styled("Password:\n", Style::default().fg(Color::Cyan)),
                Span::raw("********"),
            ];

            let details_para = Paragraph::new(Text::from(details))
                .wrap(Wrap { trim: true });

            f.render_widget(details_para, chunks[0]);

            let actions = vec![
                Span::styled("Actions:\n", Style::default().fg(Color::Cyan)),
                Span::styled(
                    "[c] Copy Password  ",
                    Style::default().fg(Color::Green),
                ),
                Span::raw("\n"),
                Span::styled("[e] Edit Entry  ", Style::default().fg(Color::Yellow)),
                Span::raw("\n"),
                Span::styled("[ESC] Back", Style::default().fg(Color::Gray)),
            ];

            let actions_para = Paragraph::new(Text::from(actions))
                .wrap(Wrap { trim: true });

            f.render_widget(actions_para, chunks[1]);
        }
    }

    fn draw_entry_form(f: &mut Frame, app: &App, size: Rect) {
        let popup_area = Rect {
            x: size.width / 4,
            y: size.height / 6,
            width: size.width / 2,
            height: size.height * 2 / 3,
        };

        f.render_widget(
            Block::default()
                .borders(Borders::ALL)
                .border_type(BorderType::Double)
                .style(Style::default().bg(Color::Black)),
            popup_area,
        );

        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .margin(1)
            .constraints(
                [
                    Constraint::Length(3),
                    Constraint::Length(3),
                    Constraint::Length(3),
                    Constraint::Length(3),
                    Constraint::Length(3),
                    Constraint::Min(0),
                ]
                .as_ref(),
            )
            .split(popup_area);

        let fields = ["Title", "Username", "Password", "URL", "Notes"];
        let input_values = [
            &app.form_title,
            &app.form_username,
            &app.form_password,
            &app.form_url,
            &app.form_notes,
        ];

        for (i, (field, value)) in fields.iter().zip(input_values.iter()).enumerate() {
            let is_active = app.form_field == i;

            let label = if is_active {
                Span::styled(
                    format!("{}: ", field),
                    Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD),
                )
            } else {
                Span::raw(format!("{}: ", field))
            };

            let value_str = if *field == "Password" && !value.is_empty() {
                "********".to_string()
            } else {
                value.clone()
            };

            let input = Paragraph::new(vec![label, Span::raw(&value_str)])
                .block(
                    Block::default()
                        .borders(Borders::ALL)
                        .border_style(if is_active {
                            Style::default().fg(Color::Yellow)
                        } else {
                            Style::default()
                        }),
                )
                .wrap(Wrap { trim: false });

            f.render_widget(input, chunks[i]);
        }
    }
}
