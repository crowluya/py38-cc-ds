mod config;
mod metrics;
mod ui;

use clap::Parser;
use config::Args;
use crossterm::{
    event::{self, DisableMouseCapture, EnableMouseCapture, Event, KeyCode},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use metrics::collect_metrics;
use ratatui::{
    backend::{Backend, CrosstermBackend},
    Terminal,
};
use std::io;
use std::time::{Duration, Instant};
use tokio::time::sleep;

/// Application state
struct AppState {
    running: bool,
    update_interval: Duration,
    last_update: Instant,
    min_interval: Duration,
    max_interval: Duration,
}

impl AppState {
    fn new(config: &config::Config) -> Self {
        AppState {
            running: true,
            update_interval: config.update_interval,
            last_update: Instant::now(),
            min_interval: config.min_interval,
            max_interval: config.max_interval,
        }
    }

    /// Adjust update interval
    fn adjust_interval(&mut self, delta_ms: i64) {
        let current_ms = self.update_interval.as_millis() as i64;
        let new_ms = (current_ms + delta_ms).max(0);
        let new_interval = Duration::from_millis(new_ms as u64);

        self.update_interval = new_interval.clamp(self.min_interval, self.max_interval);
    }

    /// Check if it's time to update
    fn should_update(&self) -> bool {
        self.last_update.elapsed() >= self.update_interval
    }

    /// Mark as updated
    fn mark_updated(&mut self) {
        self.last_update = Instant::now();
    }
}

/// Main application entry point
#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Parse CLI arguments
    let args = Args::parse();

    // Validate arguments
    if let Err(e) = args.validate() {
        eprintln!("Error: {}", e);
        std::process::exit(1);
    }

    // Convert to config
    let config = config::Config::from(args.clone());

    // Setup terminal
    enable_raw_mode()?;
    let mut stdout = io::stdout();
    execute!(stdout, EnterAlternateScreen, EnableMouseCapture)?;
    let backend = CrosstermBackend::new(stdout);
    let mut terminal = Terminal::new(backend)?;

    // Initialize application state
    let mut state = AppState::new(&config);

    // Initial metrics collection
    let mut metrics = collect_metrics();

    // Main application loop
    let result = run_application(
        &mut terminal,
        &mut metrics,
        &mut state,
        &config,
    ).await;

    // Restore terminal
    disable_raw_mode()?;
    execute!(
        terminal.backend_mut(),
        LeaveAlternateScreen,
        DisableMouseCapture
    )?;
    terminal.show_cursor()?;

    // Propagate any errors
    if let Err(e) = result {
        eprintln!("Application error: {}", e);
        std::process::exit(1);
    }

    Ok(())
}

/// Run the main application loop
async fn run_application<B: Backend>(
    terminal: &mut Terminal<B>,
    metrics: &mut metrics::Metrics,
    state: &mut AppState,
    config: &config::Config,
) -> Result<(), Box<dyn std::error::Error>> {
    // Event loop tick rate
    let tick_rate = Duration::from_millis(100);

    loop {
        // Render UI
        terminal.draw(|f| {
            ui::render_ui(
                f,
                metrics,
                config,
                state.update_interval.as_secs_f64(),
            );
        })?;

        // Handle events
        if event::poll(tick_rate)? {
            if let Event::Key(key) = event::read()? {
                match key.code {
                    KeyCode::Char('q') | KeyCode::Char('Q') => {
                        state.running = false;
                    }
                    KeyCode::Char('+') | KeyCode::Char('=') => {
                        state.adjust_interval(Duration::from_millis(100));
                    }
                    KeyCode::Char('-') | KeyCode::Char('_') => {
                        state.adjust_interval(Duration::from_millis(-100));
                    }
                    KeyCode::Char(']') => {
                        state.adjust_interval(Duration::from_secs(1));
                    }
                    KeyCode::Char('[') => {
                        state.adjust_interval(Duration::from_secs(-1));
                    }
                    _ => {}
                }
            }
        }

        // Check if we should exit
        if !state.running {
            break;
        }

        // Update metrics if it's time
        if state.should_update() {
            *metrics = collect_metrics();
            state.mark_updated();
        }

        // Sleep a bit to prevent busy-waiting
        sleep(Duration::from_millis(50)).await;
    }

    Ok(())
}
