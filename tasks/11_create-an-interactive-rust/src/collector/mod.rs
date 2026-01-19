pub mod cpu;
pub mod disk;
pub mod memory;
pub mod network;

use crate::error::Result;
use crate::storage::SystemSnapshot;
use sysinfo::System;

pub use cpu::CpuCollector;
pub use disk::DiskCollector;
pub use memory::MemoryCollector;
pub use network::NetworkCollector;

/// Trait for collecting system metrics
pub trait MetricCollector {
    /// Collect the current state of the metric
    fn collect(&mut self, system: &System) -> Result<()>;
}

/// Main collector that aggregates all system metrics
pub struct SystemCollector {
    system: System,
    cpu_collector: CpuCollector,
    memory_collector: MemoryCollector,
    disk_collector: DiskCollector,
    network_collector: NetworkCollector,
    last_snapshot: Option<SystemSnapshot>,
}

impl SystemCollector {
    /// Create a new system collector
    pub fn new() -> Self {
        Self {
            system: System::new_all(),
            cpu_collector: CpuCollector::new(),
            memory_collector: MemoryCollector::new(),
            disk_collector: DiskCollector::new(),
            network_collector: NetworkCollector::new(),
            last_snapshot: None,
        }
    }

    /// Collect all system metrics and return a snapshot
    pub fn collect_snapshot(&mut self) -> Result<SystemSnapshot> {
        // Refresh all system information
        self.system.refresh_all();
        self.system.refresh_cpu_usage();
        self.system.refresh_memory();
        self.system.refresh_disks_list();
        self.system.refresh_disks();
        self.system.refresh_networks_list();
        self.system.refresh_networks();

        // Collect all metrics
        self.cpu_collector.collect(&self.system)?;
        self.memory_collector.collect(&self.system)?;
        self.disk_collector.collect(&self.system)?;
        self.network_collector.collect(&self.system)?;

        // Create snapshot
        let snapshot = SystemSnapshot::new(
            self.cpu_collector.get_metrics()?,
            self.memory_collector.get_metrics()?,
            self.disk_collector.get_metrics()?,
            self.network_collector.get_metrics()?,
        );

        self.last_snapshot = Some(snapshot.clone());
        Ok(snapshot)
    }

    /// Get the last collected snapshot
    pub fn last_snapshot(&self) -> Option<&SystemSnapshot> {
        self.last_snapshot.as_ref()
    }
}

impl Default for SystemCollector {
    fn default() -> Self {
        Self::new()
    }
}
