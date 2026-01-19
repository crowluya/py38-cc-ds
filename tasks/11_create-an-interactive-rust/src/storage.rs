use crate::error::{DashboardError, Result};
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::VecDeque;

/// CPU metrics at a point in time
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CpuMetrics {
    /// Overall CPU usage percentage (0.0 - 100.0)
    pub overall_usage: f32,
    /// Per-core usage percentages
    pub per_core_usage: Vec<f32>,
}

/// Memory metrics at a point in time
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryMetrics {
    /// Total RAM in bytes
    pub total: u64,
    /// Used RAM in bytes
    pub used: u64,
    /// Available RAM in bytes
    pub available: u64,
    /// Total swap in bytes
    pub swap_total: u64,
    /// Used swap in bytes
    pub swap_used: u64,
    /// Usage percentage (0.0 - 100.0)
    pub usage_percent: f32,
}

/// Disk metrics for a single mount point
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DiskMetrics {
    /// Mount point path
    pub mount_point: String,
    /// File system type
    pub file_system: String,
    /// Total space in bytes
    pub total: u64,
    /// Used space in bytes
    pub used: u64,
    /// Available space in bytes
    pub available: u64,
    /// Usage percentage (0.0 - 100.0)
    pub usage_percent: f32,
}

/// Network metrics for a single interface
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NetworkMetrics {
    /// Interface name
    pub interface: String,
    /// Bytes received
    pub bytes_received: u64,
    /// Bytes transmitted
    pub bytes_transmitted: u64,
    /// Packets received
    pub packets_received: u64,
    /// Packets transmitted
    pub packets_transmitted: u64,
    /// Errors on receive
    pub errors_received: u64,
    /// Errors on transmit
    pub errors_transmitted: u64,
}

/// Complete system snapshot at a point in time
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SystemSnapshot {
    /// Timestamp of the snapshot
    pub timestamp: DateTime<Utc>,
    /// CPU metrics
    pub cpu: CpuMetrics,
    /// Memory metrics
    pub memory: MemoryMetrics,
    /// Disk metrics for all mount points
    pub disks: Vec<DiskMetrics>,
    /// Network metrics for all interfaces
    pub networks: Vec<NetworkMetrics>,
}

impl SystemSnapshot {
    /// Create a new system snapshot with the current timestamp
    pub fn new(
        cpu: CpuMetrics,
        memory: MemoryMetrics,
        disks: Vec<DiskMetrics>,
        networks: Vec<NetworkMetrics>,
    ) -> Self {
        Self {
            timestamp: Utc::now(),
            cpu,
            memory,
            disks,
            networks,
        }
    }
}

/// Alert severity levels
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq, PartialOrd, Ord)]
pub enum AlertLevel {
    /// Informational alert
    Info,
    /// Warning threshold exceeded
    Warning,
    /// Critical threshold exceeded
    Critical,
}

/// Alert configuration for a specific metric
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AlertThreshold {
    /// Warning threshold value (0.0 - 100.0)
    pub warning: f32,
    /// Critical threshold value (0.0 - 100.0)
    pub critical: f32,
}

impl AlertThreshold {
    /// Create a new alert threshold
    pub fn new(warning: f32, critical: f32) -> Self {
        Self { warning, critical }
    }

    /// Check a value against thresholds and return alert level if exceeded
    pub fn check(&self, value: f32) -> Option<AlertLevel> {
        if value >= self.critical {
            Some(AlertLevel::Critical)
        } else if value >= self.warning {
            Some(AlertLevel::Warning)
        } else {
            None
        }
    }
}

impl Default for AlertThreshold {
    fn default() -> Self {
        Self {
            warning: 70.0,
            critical: 90.0,
        }
    }
}

/// Alert configuration for all metrics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AlertConfig {
    /// CPU alert thresholds
    pub cpu: AlertThreshold,
    /// Memory alert thresholds
    pub memory: AlertThreshold,
    /// Disk alert thresholds
    pub disk: AlertThreshold,
    /// Enable audio alerts
    pub audio_enabled: bool,
}

impl Default for AlertConfig {
    fn default() -> Self {
        Self {
            cpu: AlertThreshold::default(),
            memory: AlertThreshold::default(),
            disk: AlertThreshold::default(),
            audio_enabled: false,
        }
    }
}

/// Circular buffer for storing historical snapshots
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MetricHistory {
    /// Maximum number of snapshots to store
    max_size: usize,
    /// Historical snapshots (oldest at front, newest at back)
    history: VecDeque<SystemSnapshot>,
}

impl MetricHistory {
    /// Create a new metric history with a maximum size
    pub fn new(max_size: usize) -> Self {
        Self {
            max_size,
            history: VecDeque::with_capacity(max_size),
        }
    }

    /// Add a new snapshot to the history
    pub fn push(&mut self, snapshot: SystemSnapshot) {
        if self.history.len() == self.max_size {
            self.history.pop_front();
        }
        self.history.push_back(snapshot);
    }

    /// Get the most recent snapshot
    pub fn latest(&self) -> Option<&SystemSnapshot> {
        self.history.back()
    }

    /// Get all snapshots in the history
    pub fn all(&self) -> &VecDeque<SystemSnapshot> {
        &self.history
    }

    /// Get the N most recent snapshots
    pub fn latest_n(&self, n: usize) -> Vec<&SystemSnapshot> {
        self.history.iter().rev().take(n).collect()
    }

    /// Clear all history
    pub fn clear(&mut self) {
        self.history.clear();
    }

    /// Get the number of snapshots stored
    pub fn len(&self) -> usize {
        self.history.len()
    }

    /// Check if the history is empty
    pub fn is_empty(&self) -> bool {
        self.history.is_empty()
    }

    /// Get snapshots within a time range
    pub fn time_range(&self, start: DateTime<Utc>, end: DateTime<Utc>) -> Vec<&SystemSnapshot> {
        self.history
            .iter()
            .filter(|s| s.timestamp >= start && s.timestamp <= end)
            .collect()
    }
}

impl Default for MetricHistory {
    fn default() -> Self {
        Self::new(3600) // Default: 1 hour of 1-second snapshots
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_alert_threshold() {
        let threshold = AlertThreshold::new(70.0, 90.0);

        assert!(threshold.check(50.0).is_none());
        assert_eq!(threshold.check(75.0), Some(AlertLevel::Warning));
        assert_eq!(threshold.check(95.0), Some(AlertLevel::Critical));
    }

    #[test]
    fn test_metric_history() {
        let mut history = MetricHistory::new(3);

        let snapshot1 = SystemSnapshot::new(
            CpuMetrics {
                overall_usage: 10.0,
                per_core_usage: vec![10.0],
            },
            MemoryMetrics {
                total: 1000,
                used: 500,
                available: 500,
                swap_total: 0,
                swap_used: 0,
                usage_percent: 50.0,
            },
            vec![],
            vec![],
        );

        history.push(snapshot1.clone());
        assert_eq!(history.len(), 1);

        // Fill to capacity
        for i in 0..=3 {
            let mut snapshot = snapshot1.clone();
            snapshot.cpu.overall_usage = i as f32;
            history.push(snapshot);
        }

        // Should only keep 3 most recent
        assert_eq!(history.len(), 3);
    }
}
