use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

/// Comprehensive system metrics snapshot
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SystemMetrics {
    pub timestamp: DateTime<Utc>,
    pub cpu: CpuMetrics,
    pub memory: MemoryMetrics,
    pub disk: Vec<DiskMetrics>,
    pub network: Vec<NetworkMetrics>,
}

/// CPU usage metrics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CpuMetrics {
    /// Overall CPU usage percentage (0.0 - 100.0)
    pub usage_percent: f32,
    /// Per-core CPU usage
    pub core_usage: Vec<f32>,
    /// Load averages (1min, 5min, 15min)
    pub load_average: (f64, f64, f64),
    /// CPU frequency in MHz (if available)
    pub frequency_mhz: Option<u64>,
}

/// Memory metrics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryMetrics {
    /// Total physical memory in bytes
    pub total_bytes: u64,
    /// Used physical memory in bytes
    pub used_bytes: u64,
    /// Available physical memory in bytes
    pub available_bytes: u64,
    /// Total swap in bytes
    pub swap_total_bytes: u64,
    /// Used swap in bytes
    pub swap_used_bytes: u64,
    /// Memory usage percentage (0.0 - 100.0)
    pub usage_percent: f32,
}

/// Disk metrics for a single mount point
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DiskMetrics {
    /// Mount point path (e.g., "/")
    pub mount_point: String,
    /// File system type
    pub file_system: String,
    /// Total space in bytes
    pub total_bytes: u64,
    /// Used space in bytes
    pub used_bytes: u64,
    /// Available space in bytes
    pub available_bytes: u64,
    /// Usage percentage (0.0 - 100.0)
    pub usage_percent: f32,
    /// Bytes read since last check
    pub read_bytes_per_sec: u64,
    /// Bytes written since last check
    pub write_bytes_per_sec: u64,
}

/// Network metrics for a single interface
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NetworkMetrics {
    /// Interface name (e.g., "eth0", "wlan0")
    pub interface: String,
    /// Bytes received since last check
    pub rx_bytes_per_sec: u64,
    /// Bytes transmitted since last check
    pub tx_bytes_per_sec: u64,
    /// Packets received since last check
    pub rx_packets_per_sec: u64,
    /// Packets transmitted since last check
    pub tx_packets_per_sec: u64,
    /// Receive errors
    pub rx_errors: u64,
    /// Transmit errors
    pub tx_errors: u64,
}

/// Alert configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AlertConfig {
    pub cpu: CpuAlertConfig,
    pub memory: MemoryAlertConfig,
    pub disk: DiskAlertConfig,
    pub network: NetworkAlertConfig,
    /// Cooldown period in seconds between alerts of the same type
    pub cooldown_seconds: u64,
}

/// CPU alert thresholds
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CpuAlertConfig {
    /// Enable CPU alerts
    pub enabled: bool,
    /// Threshold for overall CPU usage (0.0 - 100.0)
    pub usage_threshold_percent: f32,
    /// Threshold for load average (per CPU core)
    pub load_average_threshold: f64,
}

/// Memory alert thresholds
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryAlertConfig {
    /// Enable memory alerts
    pub enabled: bool,
    /// Threshold for memory usage (0.0 - 100.0)
    pub usage_threshold_percent: f32,
    /// Threshold for swap usage (0.0 - 100.0)
    pub swap_threshold_percent: f32,
}

/// Disk alert thresholds
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DiskAlertConfig {
    /// Enable disk alerts
    pub enabled: bool,
    /// Threshold for disk usage (0.0 - 100.0)
    pub usage_threshold_percent: f32,
}

/// Network alert thresholds
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NetworkAlertConfig {
    /// Enable network alerts
    pub enabled: bool,
    /// Threshold for error rate (errors per second)
    pub error_threshold: u64,
}

/// Alert event
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AlertEvent {
    pub timestamp: DateTime<Utc>,
    pub alert_type: AlertType,
    pub message: String,
    pub current_value: f32,
    pub threshold: f32,
}

/// Types of alerts
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum AlertType {
    HighCpuUsage,
    HighLoadAverage,
    HighMemoryUsage,
    HighSwapUsage,
    HighDiskUsage { mount_point: String },
    HighNetworkErrors { interface: String },
}

/// Application configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    /// Monitoring interval in milliseconds
    pub interval_ms: u64,
    /// Number of historical data points to keep in memory
    pub history_size: usize,
    /// Alert configuration
    pub alerts: AlertConfig,
    /// Display mode
    pub display_mode: DisplayMode,
    /// Maximum network interfaces to monitor
    pub max_network_interfaces: usize,
    /// Disk mount points to monitor (empty = all)
    pub monitored_mount_points: Vec<String>,
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            interval_ms: 1000,
            history_size: 1000,
            alerts: AlertConfig::default(),
            display_mode: DisplayMode::Normal,
            max_network_interfaces: 10,
            monitored_mount_points: Vec::new(),
        }
    }
}

impl Default for AlertConfig {
    fn default() -> Self {
        Self {
            cpu: CpuAlertConfig {
                enabled: true,
                usage_threshold_percent: 80.0,
                load_average_threshold: 2.0,
            },
            memory: MemoryAlertConfig {
                enabled: true,
                usage_threshold_percent: 85.0,
                swap_threshold_percent: 50.0,
            },
            disk: DiskAlertConfig {
                enabled: true,
                usage_threshold_percent: 90.0,
            },
            network: NetworkAlertConfig {
                enabled: true,
                error_threshold: 10,
            },
            cooldown_seconds: 60,
        }
    }
}

/// Display modes
#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub enum DisplayMode {
    /// Minimal output (one line)
    Minimal,
    /// Normal multi-line output
    Normal,
    /// Detailed with all metrics
    Detailed,
    /// JSON output
    Json,
    /// Interactive TUI
    Tui,
}

/// Monitoring state
#[derive(Debug, Clone)]
pub struct MonitoringState {
    pub config: AppConfig,
    pub metrics_history: Vec<SystemMetrics>,
    pub active_alerts: Vec<AlertEvent>,
    pub is_running: bool,
}

impl MonitoringState {
    pub fn new(config: AppConfig) -> Self {
        Self {
            config,
            metrics_history: Vec::new(),
            active_alerts: Vec::new(),
            is_running: false,
        }
    }

    pub fn add_metrics(&mut self, metrics: SystemMetrics) {
        self.metrics_history.push(metrics);

        // Keep history size bounded
        if self.metrics_history.len() > self.config.history_size {
            self.metrics_history.remove(0);
        }
    }

    pub fn get_latest_metrics(&self) -> Option<&SystemMetrics> {
        self.metrics_history.last()
    }

    pub fn add_alert(&mut self, alert: AlertEvent) {
        self.active_alerts.push(alert);

        // Keep only last 100 alerts
        if self.active_alerts.len() > 100 {
            self.active_alerts.remove(0);
        }
    }
}

/// Historical data export format
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HistoricalExport {
    pub start_time: DateTime<Utc>,
    pub end_time: DateTime<Utc>,
    pub metrics: Vec<SystemMetrics>,
    pub alerts: Vec<AlertEvent>,
}
