use crate::types::DiskMetrics;
use sysinfo::{Disk, DiskExt, System, SystemExt};
use std::collections::HashMap;

pub struct DiskMonitor {
    system: System,
    previous_io: HashMap<String, (u64, u64)>,
}

impl DiskMonitor {
    pub fn new() -> Self {
        let mut system = System::new();
        system.refresh_disks_list();
        system.refresh_disks();

        Self {
            system,
            previous_io: HashMap::new(),
        }
    }

    /// Refresh disk metrics
    pub fn refresh(&mut self) {
        self.system.refresh_disks_list();
        self.system.refresh_disks();
    }

    /// Get current disk metrics for all monitored mount points
    pub fn get_metrics(&mut self, monitored_mounts: &[String]) -> Vec<DiskMetrics> {
        let disks = self.system.disks();
        let mut metrics = Vec::new();

        for disk in disks {
            let mount_point = disk.mount_point().to_string_lossy().to_string();

            // Filter if specific mounts are requested
            if !monitored_mounts.is_empty() && !monitored_mounts.contains(&mount_point) {
                continue;
            }

            let total_bytes = disk.total_space();
            let available_bytes = disk.available_space();
            let used_bytes = total_bytes.saturating_sub(available_bytes);
            let usage_percent = if total_bytes > 0 {
                (used_bytes as f32 / total_bytes as f32) * 100.0
            } else {
                0.0
            };

            let file_system = format!("{:?}", disk.file_type());

            // Calculate I/O rates
            let (read_bytes_per_sec, write_bytes_per_sec) = self.calculate_io_rates(
                &mount_point,
                disk.total_read(),
                disk.total_written(),
            );

            metrics.push(DiskMetrics {
                mount_point,
                file_system,
                total_bytes,
                used_bytes,
                available_bytes,
                usage_percent,
                read_bytes_per_sec,
                write_bytes_per_sec,
            });
        }

        metrics
    }

    /// Calculate I/O rates based on difference from previous reading
    fn calculate_io_rates(
        &mut self,
        mount_point: &str,
        total_read: u64,
        total_written: u64,
    ) -> (u64, u64) {
        let (read_rate, write_rate) = match self.previous_io.get(mount_point) {
            Some(&(prev_read, prev_written)) => {
                let read_diff = total_read.saturating_sub(prev_read);
                let write_diff = total_written.saturating_sub(prev_written);
                (read_diff, write_diff)
            }
            None => (0, 0),
        };

        // Store current values for next calculation
        self.previous_io.insert(mount_point.to_string(), (total_read, total_written));

        (read_rate, write_rate)
    }
}

impl Default for DiskMonitor {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_disk_monitor_creation() {
        let monitor = DiskMonitor::new();
        assert!(!monitor.system.disks().is_empty());
    }

    #[test]
    fn test_get_metrics() {
        let mut monitor = DiskMonitor::new();
        monitor.refresh();

        let metrics = monitor.get_metrics(&[]);
        assert!(!metrics.is_empty());

        for metric in metrics {
            assert!(metric.total_bytes > 0);
            assert!(metric.usage_percent >= 0.0 && metric.usage_percent <= 100.0);
        }
    }
}
