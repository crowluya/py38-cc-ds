use crate::collector::MetricCollector;
use crate::error::{DashboardError, Result};
use crate::storage::CpuMetrics;
use sysinfo::System;

/// Collector for CPU metrics
pub struct CpuCollector {
    last_metrics: Option<CpuMetrics>,
}

impl CpuCollector {
    /// Create a new CPU collector
    pub fn new() -> Self {
        Self {
            last_metrics: None,
        }
    }

    /// Get the last collected metrics
    pub fn get_metrics(&self) -> Result<CpuMetrics> {
        self.last_metrics
            .clone()
            .ok_or_else(|| DashboardError::SystemInfo("No CPU metrics collected yet".to_string()))
    }
}

impl Default for CpuCollector {
    fn default() -> Self {
        Self::new()
    }
}

impl MetricCollector for CpuCollector {
    fn collect(&mut self, system: &System) -> Result<()> {
        let cpus = system.cpus();

        if cpus.is_empty() {
            return Err(DashboardError::SystemInfo("No CPUs found".to_string()));
        }

        // Calculate overall usage as average of all cores
        let total_usage: f32 = cpus.iter().map(|cpu| cpu.cpu_usage()).sum();
        let overall_usage = total_usage / cpus.len() as f32;

        // Collect per-core usage
        let per_core_usage: Vec<f32> = cpus.iter().map(|cpu| cpu.cpu_usage()).collect();

        self.last_metrics = Some(CpuMetrics {
            overall_usage,
            per_core_usage,
        });

        Ok(())
    }
}
