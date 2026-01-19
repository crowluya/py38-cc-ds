use sysinfo::{System, Disk};

/// Represents CPU usage metrics
#[derive(Debug, Clone)]
pub struct CpuMetrics {
    pub global_usage: f32,
    pub core_usage: Vec<f32>,
    pub name: String,
}

/// Represents memory metrics
#[derive(Debug, Clone)]
pub struct MemoryMetrics {
    pub total_memory: u64,
    pub used_memory: u64,
    pub available_memory: u64,
    pub total_swap: u64,
    pub used_swap: u64,
    pub usage_percent: f32,
    pub swap_usage_percent: f32,
}

/// Represents disk usage metrics for a single disk
#[derive(Debug, Clone)]
pub struct DiskMetrics {
    pub name: String,
    pub mount_point: String,
    pub total_space: u64,
    pub available_space: u64,
    pub used_space: u64,
    pub usage_percent: f32,
    pub file_system: String,
    pub file_type: String,
}

/// Aggregated system metrics
#[derive(Debug, Clone)]
pub struct Metrics {
    pub cpu: Vec<CpuMetrics>,
    pub memory: MemoryMetrics,
    pub disks: Vec<DiskMetrics>,
    pub hostname: String,
}

/// Collects all system metrics
pub fn collect_metrics() -> Metrics {
    let mut sys = System::new_all();
    sys.refresh_all();

    // Get global CPU usage
    let global_cpu_usage = sys.global_cpu_usage();

    // Collect CPU metrics
    let cpu_metrics: Vec<CpuMetrics> = sys.cpus().iter().enumerate().map(|(i, cpu)| {
        CpuMetrics {
            global_usage: global_cpu_usage,
            core_usage: vec![cpu.cpu_usage()],
            name: format!("CPU {}", i),
        }
    }).collect();

    // Collect memory metrics
    let total_memory = sys.total_memory();
    let used_memory = sys.used_memory();
    let available_memory = sys.available_memory();
    let total_swap = sys.total_swap();
    let used_swap = sys.used_swap();

    let memory_metrics = MemoryMetrics {
        total_memory,
        used_memory,
        available_memory,
        total_swap,
        used_swap,
        usage_percent: if total_memory > 0 {
            (used_memory as f32 / total_memory as f32) * 100.0
        } else {
            0.0
        },
        swap_usage_percent: if total_swap > 0 {
            (used_swap as f32 / total_swap as f32) * 100.0
        } else {
            0.0
        },
    };

    // Collect disk metrics
    let disks: Vec<Disk> = sys.disks().to_vec();
    let disk_metrics: Vec<DiskMetrics> = disks.iter().map(|disk| {
        let total_space = disk.total_space();
        let available_space = disk.available_space();
        let used_space = total_space.saturating_sub(available_space);

        let mount_point = disk.mount_point().to_string_lossy().to_string();
        let name = disk.name().to_string_lossy().to_string();
        let file_system = disk.file_system().to_string_lossy().to_string();

        DiskMetrics {
            name: if name.is_empty() { mount_point.clone() } else { name },
            mount_point: mount_point.clone(),
            total_space,
            available_space,
            used_space,
            usage_percent: if total_space > 0 {
                (used_space as f32 / total_space as f32) * 100.0
            } else {
                0.0
            },
            file_system,
            file_type: mount_point,
        }
    }).collect();

    // Get hostname
    let hostname = gethostname::gethostname()
        .to_string_lossy()
        .to_string();

    Metrics {
        cpu: cpu_metrics,
        memory: memory_metrics,
        disks: disk_metrics,
        hostname,
    }
}

/// Format bytes to human readable format
pub fn format_bytes(bytes: u64) -> String {
    const KB: u64 = 1024;
    const MB: u64 = KB * 1024;
    const GB: u64 = MB * 1024;
    const TB: u64 = GB * 1024;

    if bytes >= TB {
        format!("{:.2} TB", bytes as f64 / TB as f64)
    } else if bytes >= GB {
        format!("{:.2} GB", bytes as f64 / GB as f64)
    } else if bytes >= MB {
        format!("{:.2} MB", bytes as f64 / MB as f64)
    } else if bytes >= KB {
        format!("{:.2} KB", bytes as f64 / KB as f64)
    } else {
        format!("{} B", bytes)
    }
}
