use crate::types::{CpuMetrics, SystemMetrics};
use sysinfo::{System, SystemExt};
use std::time::Duration;

pub struct CpuMonitor {
    system: System,
}

impl CpuMonitor {
    pub fn new() -> Self {
        let mut system = System::new();
        system.refresh_cpu();
        Self { system }
    }

    /// Refresh CPU metrics
    pub fn refresh(&mut self) {
        self.system.refresh_cpu();
        self.system.refresh_cpu_usage();
    }

    /// Get current CPU metrics
    pub fn get_metrics(&self) -> CpuMetrics {
        let processors = self.system.cpus();
        let total_cores = processors.len() as f32;

        // Calculate overall CPU usage
        let total_usage: f32 = processors.iter().map(|p| p.cpu_usage()).sum();
        let usage_percent = total_usage / total_cores;

        // Per-core usage
        let core_usage: Vec<f32> = processors.iter().map(|p| p.cpu_usage()).collect();

        // Load average (if available on platform)
        let load_average = self.get_load_average();

        // CPU frequency (if available)
        let frequency_mhz = processors.first().and_then(|p| Some(p.frequency()));

        CpuMetrics {
            usage_percent,
            core_usage,
            load_average,
            frequency_mhz,
        }
    }

    #[cfg(target_os = "linux")]
    fn get_load_average(&self) -> (f64, f64, f64) {
        use sysinfo::SystemExt;
        let load_avg = self.system.load_average();
        (load_avg.one, load_avg.five, load_avg.fifteen)
    }

    #[cfg(not(target_os = "linux"))]
    fn get_load_average(&self) -> (f64, f64, f64) {
        // Load average is not available on non-Linux platforms
        (0.0, 0.0, 0.0)
    }
}

impl Default for CpuMonitor {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cpu_monitor_creation() {
        let monitor = CpuMonitor::new();
        assert!(monitor.system.cpus().len() > 0);
    }

    #[test]
    fn test_get_metrics() {
        let mut monitor = CpuMonitor::new();
        monitor.refresh();

        let metrics = monitor.get_metrics();
        assert!(metrics.usage_percent >= 0.0 && metrics.usage_percent <= 100.0);
        assert!(!metrics.core_usage.is_empty());
    }
}
