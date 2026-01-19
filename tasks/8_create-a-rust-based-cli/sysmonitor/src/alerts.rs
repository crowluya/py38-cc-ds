use crate::types::{AlertConfig, AlertEvent, AlertType, SystemMetrics};
use chrono::Utc;
use std::collections::HashMap;

/// Alert manager that checks metrics against thresholds
pub struct AlertManager {
    config: AlertConfig,
    last_alert_times: HashMap<String, chrono::DateTime<chrono::Utc>>,
}

impl AlertManager {
    pub fn new(config: AlertConfig) -> Self {
        Self {
            config,
            last_alert_times: HashMap::new(),
        }
    }

    /// Check metrics against all alert thresholds
    pub fn check_metrics(&mut self, metrics: &SystemMetrics) -> Vec<AlertEvent> {
        let mut alerts = Vec::new();

        // Check CPU alerts
        if self.config.cpu.enabled {
            if let Some(alert) = self.check_cpu(metrics) {
                alerts.push(alert);
            }
        }

        // Check memory alerts
        if self.config.memory.enabled {
            if let Some(alert) = self.check_memory(metrics) {
                alerts.push(alert);
            }
        }

        // Check disk alerts
        if self.config.disk.enabled {
            alerts.extend(self.check_disk(metrics));
        }

        // Check network alerts
        if self.config.network.enabled {
            alerts.extend(self.check_network(metrics));
        }

        alerts
    }

    fn check_cpu(&mut self, metrics: &SystemMetrics) -> Option<AlertEvent> {
        // Check CPU usage
        if metrics.cpu.usage_percent > self.config.cpu.usage_threshold_percent {
            let key = format!("cpu_usage");
            if self.should_alert(&key) {
                return Some(AlertEvent {
                    timestamp: Utc::now(),
                    alert_type: AlertType::HighCpuUsage,
                    message: format!(
                        "High CPU usage: {:.1}% (threshold: {:.1}%)",
                        metrics.cpu.usage_percent, self.config.cpu.usage_threshold_percent
                    ),
                    current_value: metrics.cpu.usage_percent,
                    threshold: self.config.cpu.usage_threshold_percent,
                });
            }
        }

        // Check load average
        let load_avg = metrics.cpu.load_average.0;
        if load_avg > self.config.cpu.load_average_threshold {
            let key = format!("cpu_load");
            if self.should_alert(&key) {
                return Some(AlertEvent {
                    timestamp: Utc::now(),
                    alert_type: AlertType::HighLoadAverage,
                    message: format!(
                        "High load average: {:.2} (threshold: {:.2})",
                        load_avg, self.config.cpu.load_average_threshold
                    ),
                    current_value: load_avg as f32,
                    threshold: self.config.cpu.load_average_threshold as f32,
                });
            }
        }

        None
    }

    fn check_memory(&mut self, metrics: &SystemMetrics) -> Option<AlertEvent> {
        // Check memory usage
        if metrics.memory.usage_percent > self.config.memory.usage_threshold_percent {
            let key = format!("memory_usage");
            if self.should_alert(&key) {
                return Some(AlertEvent {
                    timestamp: Utc::now(),
                    alert_type: AlertType::HighMemoryUsage,
                    message: format!(
                        "High memory usage: {:.1}% (threshold: {:.1}%)",
                        metrics.memory.usage_percent, self.config.memory.usage_threshold_percent
                    ),
                    current_value: metrics.memory.usage_percent,
                    threshold: self.config.memory.usage_threshold_percent,
                });
            }
        }

        // Check swap usage
        if metrics.memory.swap_total_bytes > 0 {
            let swap_percent = (metrics.memory.swap_used_bytes as f32
                / metrics.memory.swap_total_bytes as f32)
                * 100.0;

            if swap_percent > self.config.memory.swap_threshold_percent {
                let key = format!("swap_usage");
                if self.should_alert(&key) {
                    return Some(AlertEvent {
                        timestamp: Utc::now(),
                        alert_type: AlertType::HighSwapUsage,
                        message: format!(
                            "High swap usage: {:.1}% (threshold: {:.1}%)",
                            swap_percent, self.config.memory.swap_threshold_percent
                        ),
                        current_value: swap_percent,
                        threshold: self.config.memory.swap_threshold_percent,
                    });
                }
            }
        }

        None
    }

    fn check_disk(&mut self, metrics: &SystemMetrics) -> Vec<AlertEvent> {
        let mut alerts = Vec::new();

        for disk in &metrics.disk {
            if disk.usage_percent > self.config.disk.usage_threshold_percent {
                let key = format!("disk_usage_{}", disk.mount_point);
                if self.should_alert(&key) {
                    alerts.push(AlertEvent {
                        timestamp: Utc::now(),
                        alert_type: AlertType::HighDiskUsage {
                            mount_point: disk.mount_point.clone(),
                        },
                        message: format!(
                            "High disk usage on {}: {:.1}% (threshold: {:.1}%)",
                            disk.mount_point, disk.usage_percent, self.config.disk.usage_threshold_percent
                        ),
                        current_value: disk.usage_percent,
                        threshold: self.config.disk.usage_threshold_percent,
                    });
                }
            }
        }

        alerts
    }

    fn check_network(&mut self, metrics: &SystemMetrics) -> Vec<AlertEvent> {
        let mut alerts = Vec::new();

        for net in &metrics.network {
            let total_errors = net.rx_errors + net.tx_errors;

            if total_errors > self.config.network.error_threshold {
                let key = format!("network_errors_{}", net.interface);
                if self.should_alert(&key) {
                    alerts.push(AlertEvent {
                        timestamp: Utc::now(),
                        alert_type: AlertType::HighNetworkErrors {
                            interface: net.interface.clone(),
                        },
                        message: format!(
                            "High network errors on {}: {} (threshold: {})",
                            net.interface, total_errors, self.config.network.error_threshold
                        ),
                        current_value: total_errors as f32,
                        threshold: self.config.network.error_threshold as f32,
                    });
                }
            }
        }

        alerts
    }

    /// Check if enough time has passed since the last alert of this type
    fn should_alert(&mut self, key: &str) -> bool {
        let now = Utc::now();
        let cooldown = chrono::Duration::seconds(self.config.cooldown_seconds as i64);

        if let Some(&last_time) = self.last_alert_times.get(key) {
            if now.signed_duration_since(last_time) < cooldown {
                return false;
            }
        }

        self.last_alert_times.insert(key.to_string(), now);
        true
    }

    /// Update alert configuration
    pub fn update_config(&mut self, config: AlertConfig) {
        self.config = config;
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::*;

    #[test]
    fn test_alert_cooldown() {
        let config = AlertConfig {
            cooldown_seconds: 1,
            ..Default::default()
        };
        let mut manager = AlertManager::new(config);

        // Create high CPU metrics
        let mut metrics = SystemMetrics {
            timestamp: Utc::now(),
            cpu: CpuMetrics {
                usage_percent: 95.0,
                core_usage: vec![95.0],
                load_average: (5.0, 4.0, 3.0),
                frequency_mhz: Some(3000),
            },
            memory: MemoryMetrics::default(),
            disk: vec![],
            network: vec![],
        };

        // First alert should trigger
        let alerts1 = manager.check_metrics(&metrics);
        assert_eq!(alerts1.len(), 2); // CPU usage and load average

        // Immediate second call should not trigger (cooldown)
        let alerts2 = manager.check_metrics(&metrics);
        assert_eq!(alerts2.len(), 0);
    }
}
