use crate::collector::MetricCollector;
use crate::error::Result;
use crate::storage::DiskMetrics;
use sysinfo::System;

/// Collector for disk metrics
pub struct DiskCollector {
    last_metrics: Vec<DiskMetrics>,
}

impl DiskCollector {
    /// Create a new disk collector
    pub fn new() -> Self {
        Self {
            last_metrics: Vec::new(),
        }
    }

    /// Get the last collected metrics
    pub fn get_metrics(&self) -> Result<Vec<DiskMetrics>> {
        if self.last_metrics.is_empty() {
            return Ok(Vec::new());
        }
        Ok(self.last_metrics.clone())
    }
}

impl Default for DiskCollector {
    fn default() -> Self {
        Self::new()
    }
}

impl MetricCollector for DiskCollector {
    fn collect(&mut self, system: &System) -> Result<()> {
        let disks = system.disks();

        let metrics: Vec<DiskMetrics> = disks
            .iter()
            .map(|disk| {
                let total = disk.total_space();
                let available = disk.available_space();
                let used = total.saturating_sub(available);

                let usage_percent = if total > 0 {
                    (used as f32 / total as f32) * 100.0
                } else {
                    0.0
                };

                DiskMetrics {
                    mount_point: disk.mount_point().to_string_lossy().to_string(),
                    file_system: disk.file_system().to_string_lossy().to_string(),
                    total,
                    used,
                    available,
                    usage_percent,
                }
            })
            .collect();

        self.last_metrics = metrics;
        Ok(())
    }
}
