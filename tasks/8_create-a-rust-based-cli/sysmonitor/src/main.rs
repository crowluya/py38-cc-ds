mod alerts;
mod cli;
mod collector;
mod config;
mod display;
mod export;
mod monitor;
mod tui;
mod types;

use crate::alerts::AlertManager;
use crate::cli::{Args, ExportFormat, RuntimeConfig};
use crate::collector::MetricsCollector;
use crate::display::MetricsDisplay;
use crate::export::MetricsExporter;
use crate::tui::run_tui;
use crate::types::{AppConfig, DisplayMode, MonitoringState};
use anyhow::Result;
use std::sync::{Arc, Mutex};
use std::time::Duration;
use tokio::time;

#[tokio::main]
async fn main() -> Result<()> {
    let args = Args::parse();

    match args.load_configuration()? {
        RuntimeConfig::GenerateConfig(path) => {
            println!("Generated default configuration at: {}", path.display());
            println!("Edit this file to customize monitoring settings.");
            return Ok(());
        }
        RuntimeConfig::Run(config) => run_monitoring(args, config).await,
    }
}

async fn run_monitoring(args: Args, config: AppConfig) -> Result<()> {
    // Create monitoring state
    let state = Arc::new(Mutex::new(MonitoringState::new(config.clone())));

    // Handle TUI mode specially
    if config.display_mode == DisplayMode::Tui {
        return run_tui_mode(state, args.duration).await;
    }

    // Create components
    let mut collector = MetricsCollector::new(config.clone());
    let mut alert_manager = AlertManager::new(config.alerts.clone());

    // Determine run duration
    let duration_seconds = args.parse_duration()?;

    println!("System Monitor started");
    println!("Press Ctrl+C to stop\n");

    let start_time = std::time::Instant::now();
    let mut interval = time::interval(Duration::from_millis(config.interval_ms));

    loop {
        interval.tick().await;

        // Check if duration limit reached
        if let Some(duration) = duration_seconds {
            if start_time.elapsed().as_secs() >= duration {
                break;
            }
        }

        // Collect metrics
        let metrics = collector.collect();

        // Check for alerts
        let alerts = alert_manager.check_metrics(&metrics);

        // Update state
        let mut state_guard = state.lock().unwrap();
        state_guard.add_metrics(metrics.clone());
        for alert in alerts {
            eprintln!("⚠️  ALERT: {}", alert.message);
            state_guard.add_alert(alert);
        }
        drop(state_guard);

        // Display metrics
        MetricsDisplay::display(&metrics, config.display_mode);
    }

    // Handle export if requested
    if let Some(export_path) = args.export {
        let state_guard = state.lock().unwrap();
        let format = args.get_export_format();
        MetricsExporter::export(&state_guard.metrics_history, &state_guard.active_alerts, &export_path, format)?;
        println!("\nExported data to: {}", export_path.display());
    }

    Ok(())
}

async fn run_tui_mode(state: Arc<Mutex<MonitoringState>>, duration: Option<String>) -> Result<()> {
    let config = {
        let state_guard = state.lock().unwrap();
        state_guard.config.clone()
    };

    let duration_seconds = if let Some(dur) = duration {
        let args = Args {
            duration: Some(dur),
            ..Default::default()
        };
        args.parse_duration()?
    } else {
        None
    };

    // Spawn background task for collecting metrics
    let state_clone = state.clone();
    let interval = Duration::from_millis(config.interval_ms);
    let start_time = std::time::Instant::now();

    tokio::spawn(async move {
        let mut collector = MetricsCollector::new(config.clone());
        let mut alert_manager = AlertManager::new(config.alerts.clone());

        loop {
            // Check duration
            if let Some(duration) = duration_seconds {
                if start_time.elapsed().as_secs() >= duration {
                    break;
                }
            }

            // Collect metrics
            let metrics = collector.collect();

            // Check alerts
            let alerts = alert_manager.check_metrics(&metrics);

            // Update state
            let mut state_guard = state_clone.lock().unwrap();
            state_guard.add_metrics(metrics);

            for alert in alerts {
                state_guard.add_alert(alert);
            }
            drop(state_guard);

            tokio::time::sleep(interval).await;
        }
    });

    // Run TUI
    run_tui(Arc::try_unwrap(state).unwrap().into_inner()?)?;

    Ok(())
}

// Implement Default for Args for use in TUI mode
impl Default for Args {
    fn default() -> Self {
        Self {
            interval: None,
            mode: None,
            config: None,
            generate_config: None,
            history: None,
            export: None,
            export_format: None,
            no_alerts: false,
            verbose: false,
            duration: None,
            mounts: None,
        }
    }
}
