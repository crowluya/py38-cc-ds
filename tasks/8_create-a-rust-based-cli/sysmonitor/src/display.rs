use crate::types::{DisplayMode, SystemMetrics};
use std::io::{self, Write};

/// Display metrics in different formats
pub struct MetricsDisplay;

impl MetricsDisplay {
    /// Display metrics based on the configured mode
    pub fn display(metrics: &SystemMetrics, mode: DisplayMode) {
        match mode {
            DisplayMode::Minimal => Self::display_minimal(metrics),
            DisplayMode::Normal => Self::display_normal(metrics),
            DisplayMode::Detailed => Self::display_detailed(metrics),
            DisplayMode::Json => Self::display_json(metrics),
            DisplayMode::Tui => {
                // TUI mode is handled separately
                eprintln!("TUI mode requires interactive terminal");
            }
        }
    }

    /// Minimal one-line output
    fn display_minimal(metrics: &SystemMetrics) {
        let time = metrics.timestamp.format("%H:%M:%S");
        println!(
            "[{}] CPU: {:>5.1}% | Mem: {:>5.1}% | Disk: {:>3} mount(s)",
            time,
            metrics.cpu.usage_percent,
            metrics.memory.usage_percent,
            metrics.disk.len()
        );
    }

    /// Normal multi-line output
    fn display_normal(metrics: &SystemMetrics) {
        let time = metrics.timestamp.format("%Y-%m-%d %H:%M:%S");

        println!("\n══════════════════════════════════════════════════════");
        println!("System Metrics - {}", time);
        println!("═══════════════════════════════════════════════════════");

        // CPU
        println!("\n📊 CPU");
        println!("  Usage:     {:>6.1}%", metrics.cpu.usage_percent);
        println!(
            "  Load Avg:  {:.2}, {:.2}, {:.2}",
            metrics.cpu.load_average.0, metrics.cpu.load_average.1, metrics.cpu.load_average.2
        );

        // Memory
        println!("\n💾 Memory");
        println!(
            "  RAM:       {:>9} / {} ({:.1}%)",
            format_bytes(metrics.memory.used_bytes),
            format_bytes(metrics.memory.total_bytes),
            metrics.memory.usage_percent
        );

        if metrics.memory.swap_total_bytes > 0 {
            let swap_percent = (metrics.memory.swap_used_bytes as f32
                / metrics.memory.swap_total_bytes as f32)
                * 100.0;
            println!(
                "  Swap:      {:>9} / {} ({:.1}%)",
                format_bytes(metrics.memory.swap_used_bytes),
                format_bytes(metrics.memory.swap_total_bytes),
                swap_percent
            );
        }

        // Disk
        println!("\n💿 Disk");
        for disk in &metrics.disk {
            println!(
                "  {:<10}: {:>9} / {} ({:.1}%)",
                disk.mount_point,
                format_bytes(disk.used_bytes),
                format_bytes(disk.total_bytes),
                disk.usage_percent
            );
        }

        // Network
        if !metrics.network.is_empty() {
            println!("\n🌐 Network");
            for net in metrics.network.iter().take(5) {
                println!(
                    "  {:<10}: ↓ {}/s  ↑ {}/s",
                    net.interface,
                    format_bytes(net.rx_bytes_per_sec),
                    format_bytes(net.tx_bytes_per_sec)
                );
            }
        }

        print!("{}", "\x1b[2K"); // Clear to end of line
        io::stdout().flush().ok();
    }

    /// Detailed output with all information
    fn display_detailed(metrics: &SystemMetrics) {
        Self::display_normal(metrics);

        // Additional details
        println!("\n🔍 Detailed Information");

        // CPU cores
        println!("\n  CPU Cores:");
        for (i, usage) in metrics.cpu.core_usage.iter().enumerate() {
            print!("    Core {}: {:>5.1}%", i, usage);
            if (i + 1) % 4 == 0 {
                println!();
            }
        }
        if metrics.cpu.core_usage.len() % 4 != 0 {
            println!();
        }

        // Disk I/O
        println!("\n  Disk I/O:");
        for disk in &metrics.disk {
            println!(
                "    {}: ↓ {}  ↑ {}",
                disk.mount_point,
                format_bytes(disk.read_bytes_per_sec),
                format_bytes(disk.write_bytes_per_sec)
            );
        }
    }

    /// JSON output
    fn display_json(metrics: &SystemMetrics) {
        match serde_json::to_string_pretty(metrics) {
            Ok(json) => println!("{}", json),
            Err(e) => eprintln!("Error serializing to JSON: {}", e),
        }
    }
}

/// Format bytes to human-readable size
fn format_bytes(bytes: u64) -> String {
    const units: &[&str] = &["B", "KB", "MB", "GB", "TB", "PB"];

    if bytes == 0 {
        return "0 B".to_string();
    }

    let mut size = bytes as f64;
    let mut unit_index = 0;

    while size >= 1024.0 && unit_index < units.len() - 1 {
        size /= 1024.0;
        unit_index += 1;
    }

    format!("{:.1} {}", size, units[unit_index])
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_format_bytes() {
        assert_eq!(format_bytes(0), "0 B");
        assert_eq!(format_bytes(1024), "1.0 KB");
        assert_eq!(format_bytes(1024 * 1024), "1.0 MB");
        assert_eq!(format_bytes(1536), "1.5 KB");
    }
}
