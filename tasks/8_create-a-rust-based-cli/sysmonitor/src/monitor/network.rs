use crate::types::NetworkMetrics;
use sysinfo::{NetworkExt, Networks, System, SystemExt};
use std::collections::HashMap;

pub struct NetworkMonitor {
    system: System,
    previous_stats: HashMap<String, (u64, u64, u64, u64)>,
}

impl NetworkMonitor {
    pub fn new() -> Self {
        let system = System::new();
        Self {
            system,
            previous_stats: HashMap::new(),
        }
    }

    /// Refresh network metrics
    pub fn refresh(&mut self) {
        self.system.refresh_networks();
    }

    /// Get current network metrics for all interfaces
    pub fn get_metrics(&mut self, max_interfaces: usize) -> Vec<NetworkMetrics> {
        let networks = self.system.networks();
        let mut metrics = Vec::new();

        for (interface_name, data) in networks.iter().take(max_interfaces) {
            let (rx_bytes_per_sec, tx_bytes_per_sec, rx_packets_per_sec, tx_packets_per_sec) =
                self.calculate_rates(
                    interface_name,
                    data.total_received(),
                    data.total_transmitted(),
                    data.total_packets_received(),
                    data.total_packets_transmitted(),
                );

            metrics.push(NetworkMetrics {
                interface: interface_name.clone(),
                rx_bytes_per_sec,
                tx_bytes_per_sec,
                rx_packets_per_sec,
                tx_packets_per_sec,
                rx_errors: data.errors_on_received(),
                tx_errors: data.errors_on_transmitted(),
            });
        }

        metrics
    }

    /// Calculate network rates based on difference from previous reading
    fn calculate_rates(
        &mut self,
        interface: &str,
        total_rx: u64,
        total_tx: u64,
        total_rx_packets: u64,
        total_tx_packets: u64,
    ) -> (u64, u64, u64, u64) {
        let (rx_rate, tx_rate, rx_packets_rate, tx_packets_rate) =
            match self.previous_stats.get(interface) {
                Some(&(prev_rx, prev_tx, prev_rx_packets, prev_tx_packets)) => {
                    let rx_diff = total_rx.saturating_sub(prev_rx);
                    let tx_diff = total_tx.saturating_sub(prev_tx);
                    let rx_packets_diff = total_rx_packets.saturating_sub(prev_rx_packets);
                    let tx_packets_diff = total_tx_packets.saturating_sub(prev_tx_packets);
                    (rx_diff, tx_diff, rx_packets_diff, tx_packets_diff)
                }
                None => (0, 0, 0, 0),
            };

        // Store current values for next calculation
        self.previous_stats.insert(
            interface.to_string(),
            (total_rx, total_tx, total_rx_packets, total_tx_packets),
        );

        (rx_rate, tx_rate, rx_packets_rate, tx_packets_rate)
    }
}

impl Default for NetworkMonitor {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_network_monitor_creation() {
        let monitor = NetworkMonitor::new();
        // Network interfaces might be empty in some environments
        let networks = monitor.system.networks();
        // Just verify it doesn't panic
        let _ = monitor.get_metrics(10);
    }

    #[test]
    fn test_get_metrics() {
        let mut monitor = NetworkMonitor::new();
        monitor.refresh();

        let metrics = monitor.get_metrics(10);
        // Verify structure is correct even if no interfaces
        for metric in metrics {
            assert!(!metric.interface.is_empty());
        }
    }
}
