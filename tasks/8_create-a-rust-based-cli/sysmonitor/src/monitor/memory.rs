use crate::types::MemoryMetrics;
use sysinfo::{System, SystemExt};

pub struct MemoryMonitor {
    system: System,
}

impl MemoryMonitor {
    pub fn new() -> Self {
        let system = System::new();
        Self { system }
    }

    /// Refresh memory metrics
    pub fn refresh(&mut self) {
        self.system.refresh_memory();
    }

    /// Get current memory metrics
    pub fn get_metrics(&self) -> MemoryMetrics {
        let total_bytes = self.system.total_memory();
        let available_bytes = self.system.available_memory();
        let used_bytes = total_bytes.saturating_sub(available_bytes);
        let usage_percent = if total_bytes > 0 {
            (used_bytes as f32 / total_bytes as f32) * 100.0
        } else {
            0.0
        };

        let swap_total_bytes = self.system.total_swap();
        let swap_used_bytes = self.system.used_swap();

        MemoryMetrics {
            total_bytes,
            used_bytes,
            available_bytes,
            swap_total_bytes,
            swap_used_bytes,
            usage_percent,
        }
    }
}

impl Default for MemoryMonitor {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_memory_monitor_creation() {
        let monitor = MemoryMonitor::new();
        assert!(monitor.system.total_memory() > 0);
    }

    #[test]
    fn test_get_metrics() {
        let mut monitor = MemoryMonitor::new();
        monitor.refresh();

        let metrics = monitor.get_metrics();
        assert!(metrics.total_bytes > 0);
        assert!(metrics.usage_percent >= 0.0 && metrics.usage_percent <= 100.0);
    }
}
