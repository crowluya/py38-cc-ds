use crate::collector::MetricCollector;
use crate::error::{DashboardError, Result};
use crate::storage::MemoryMetrics;
use sysinfo::System;

/// Collector for memory metrics
pub struct MemoryCollector {
    last_metrics: Option<MemoryMetrics>,
}

impl MemoryCollector {
    /// Create a new memory collector
    pub fn new() -> Self {
        Self {
            last_metrics: None,
        }
    }

    /// Get the last collected metrics
    pub fn get_metrics(&self) -> Result<MemoryMetrics> {
        self.last_metrics
            .clone()
            .ok_or_else(|| DashboardError::SystemInfo("No memory metrics collected yet".to_string()))
    }
}

impl Default for MemoryCollector {
    fn default() -> Self {
        Self::new()
    }
}

impl MetricCollector for MemoryCollector {
    fn collect(&mut self, system: &System) -> Result<()> {
        let total = system.total_memory();
        let available = system.available_memory();
        let used = total.saturating_sub(available);
        let swap_total = system.total_swap();
        let swap_used = system.used_swap();

        let usage_percent = if total > 0 {
            (used as f32 / total as f32) * 100.0
        } else {
            0.0
        };

        self.last_metrics = Some(MemoryMetrics {
            total,
            used,
            available,
            swap_total,
            swap_used,
            usage_percent,
        });

        Ok(())
    }
}
