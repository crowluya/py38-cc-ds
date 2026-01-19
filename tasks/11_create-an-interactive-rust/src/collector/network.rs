use crate::collector::MetricCollector;
use crate::error::Result;
use crate::storage::NetworkMetrics;
use sysinfo::System;

/// Collector for network metrics
pub struct NetworkCollector {
    last_metrics: Vec<NetworkMetrics>,
    previous_metrics: Option<Vec<NetworkMetrics>>,
}

impl NetworkCollector {
    /// Create a new network collector
    pub fn new() -> Self {
        Self {
            last_metrics: Vec::new(),
            previous_metrics: None,
        }
    }

    /// Get the last collected metrics
    pub fn get_metrics(&self) -> Result<Vec<NetworkMetrics>> {
        if self.last_metrics.is_empty() {
            return Ok(Vec::new());
        }
        Ok(self.last_metrics.clone())
    }

    /// Calculate bandwidth (bytes per second) based on previous measurements
    pub fn get_bandwidth(&self) -> Vec<(String, u64, u64)> {
        if let Some(prev) = &self.previous_metrics {
            self.last_metrics
                .iter()
                .filter_map(|current| {
                    prev.iter()
                        .find(|p| p.interface == current.interface)
                        .map(|previous| {
                            let rx_per_sec = current
                                .bytes_received
                                .saturating_sub(previous.bytes_received);
                            let tx_per_sec = current
                                .bytes_transmitted
                                .saturating_sub(previous.bytes_transmitted);
                            (current.interface.clone(), rx_per_sec, tx_per_sec)
                        })
                })
                .collect()
        } else {
            Vec::new()
        }
    }
}

impl Default for NetworkCollector {
    fn default() -> Self {
        Self::new()
    }
}

impl MetricCollector for NetworkCollector {
    fn collect(&mut self, system: &System) -> Result<()> {
        // Store current as previous before collecting new data
        if !self.last_metrics.is_empty() {
            self.previous_metrics = Some(self.last_metrics.clone());
        }

        let networks = system.networks();

        let metrics: Vec<NetworkMetrics> = networks
            .iter()
            .map(|(name, data)| {
                let data = data.clone();
                NetworkMetrics {
                    interface: name.clone(),
                    bytes_received: data.total_received(),
                    bytes_transmitted: data.total_transmitted(),
                    packets_received: data.total_packets_received(),
                    packets_transmitted: data.total_packets_transmitted(),
                    errors_received: data.total_errors_on_received(),
                    errors_transmitted: data.total_errors_on_transmitted(),
                }
            })
            .collect();

        self.last_metrics = metrics;
        Ok(())
    }
}
