use crate::monitor::{CpuMonitor, DiskMonitor, MemoryMonitor, NetworkMonitor};
use crate::types::{AppConfig, SystemMetrics};
use chrono::Utc;

/// Unified metrics collector that orchestrates all monitoring modules
pub struct MetricsCollector {
    cpu_monitor: CpuMonitor,
    memory_monitor: MemoryMonitor,
    disk_monitor: DiskMonitor,
    network_monitor: NetworkMonitor,
    config: AppConfig,
}

impl MetricsCollector {
    pub fn new(config: AppConfig) -> Self {
        Self {
            cpu_monitor: CpuMonitor::new(),
            memory_monitor: MemoryMonitor::new(),
            disk_monitor: DiskMonitor::new(),
            network_monitor: NetworkMonitor::new(),
            config,
        }
    }

    /// Collect all system metrics in a single call
    pub fn collect(&mut self) -> SystemMetrics {
        // Refresh all monitors
        self.cpu_monitor.refresh();
        self.memory_monitor.refresh();
        self.disk_monitor.refresh();
        self.network_monitor.refresh();

        // Collect metrics
        let cpu = self.cpu_monitor.get_metrics();
        let memory = self.memory_monitor.get_metrics();
        let disk = self.disk_monitor.get_metrics(&self.config.monitored_mount_points);
        let network = self.network_monitor.get_metrics(self.config.max_network_interfaces);

        SystemMetrics {
            timestamp: Utc::now(),
            cpu,
            memory,
            disk,
            network,
        }
    }

    /// Update configuration
    pub fn update_config(&mut self, config: AppConfig) {
        self.config = config;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_collector_creation() {
        let config = AppConfig::default();
        let collector = MetricsCollector::new(config);
        // Just verify it doesn't panic
    }

    #[test]
    fn test_collect_metrics() {
        let config = AppConfig::default();
        let mut collector = MetricsCollector::new(config);

        let metrics = collector.collect();

        assert!(metrics.cpu.usage_percent >= 0.0 && metrics.cpu.usage_percent <= 100.0);
        assert!(metrics.memory.total_bytes > 0);
        assert!(!metrics.disk.is_empty());
    }
}
