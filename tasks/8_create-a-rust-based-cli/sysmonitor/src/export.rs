use crate::types::{HistoricalExport, SystemMetrics};
use anyhow::{Context, Result};
use std::fs::File;
use std::io::BufWriter;
use std::path::Path;

/// Export metrics to various formats
pub struct MetricsExporter;

impl MetricsExporter {
    /// Export metrics to CSV format
    pub fn export_csv(
        metrics: &[SystemMetrics],
        alerts: &[crate::types::AlertEvent],
        path: &Path,
    ) -> Result<()> {
        let file = File::create(path).context("Failed to create CSV file")?;
        let mut writer = csv::Writer::from_writer(BufWriter::new(file));

        // Write header
        writer.write_field("timestamp")?;
        writer.write_field("cpu_usage_percent")?;
        writer.write_field("load_avg_1min")?;
        writer.write_field("memory_total_bytes")?;
        writer.write_field("memory_used_bytes")?;
        writer.write_field("memory_usage_percent")?;
        writer.write_field("swap_used_bytes")?;
        writer.write_field("disk_mount_point")?;
        writer.write_field("disk_usage_percent")?;
        writer.write_field("network_interface")?;
        writer.write_field("network_rx_bytes_per_sec")?;
        writer.write_field("network_tx_bytes_per_sec")?;
        writer.write_record(&[] as [&str; 0])?;

        // Write metrics
        for metric in metrics {
            for disk in &metric.disk {
                for net in &metric.network {
                    writer.write_field(&metric.timestamp.to_rfc3339())?;
                    writer.write_field(format!("{:.2}", metric.cpu.usage_percent))?;
                    writer.write_field(format!("{:.2}", metric.cpu.load_average.0))?;
                    writer.write_field(metric.memory.total_bytes.to_string())?;
                    writer.write_field(metric.memory.used_bytes.to_string())?;
                    writer.write_field(format!("{:.2}", metric.memory.usage_percent))?;
                    writer.write_field(metric.memory.swap_used_bytes.to_string())?;
                    writer.write_field(&disk.mount_point)?;
                    writer.write_field(format!("{:.2}", disk.usage_percent))?;
                    writer.write_field(&net.interface)?;
                    writer.write_field(net.rx_bytes_per_sec.to_string())?;
                    writer.write_field(net.tx_bytes_per_sec.to_string())?;
                    writer.write_record(&[] as [&str; 0])?;
                }
            }
        }

        writer.flush().context("Failed to flush CSV writer")?;
        log::info!("Exported {} metrics to CSV: {}", metrics.len(), path.display());
        Ok(())
    }

    /// Export metrics to JSON format
    pub fn export_json(
        metrics: &[SystemMetrics],
        alerts: &[crate::types::AlertEvent],
        path: &Path,
    ) -> Result<()> {
        let export = HistoricalExport {
            start_time: metrics.first().map(|m| m.timestamp).unwrap_or_else(|| {
                chrono::Utc::now()
            }),
            end_time: metrics.last().map(|m| m.timestamp).unwrap_or_else(|| {
                chrono::Utc::now()
            }),
            metrics: metrics.to_vec(),
            alerts: alerts.to_vec(),
        };

        let file = File::create(path).context("Failed to create JSON file")?;
        let writer = BufWriter::new(file);
        serde_json::to_writer_pretty(writer, &export)
            .context("Failed to write JSON export")?;

        log::info!("Exported {} metrics to JSON: {}", metrics.len(), path.display());
        Ok(())
    }

    /// Export metrics to the specified format
    pub fn export(
        metrics: &[SystemMetrics],
        alerts: &[crate::types::AlertEvent],
        path: &Path,
        format: crate::cli::ExportFormat,
    ) -> Result<()> {
        match format {
            crate::cli::ExportFormat::Csv => Self::export_csv(metrics, alerts, path),
            crate::cli::ExportFormat::Json => Self::export_json(metrics, alerts, path),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::*;

    #[test]
    fn test_export_json() {
        let metrics = vec![SystemMetrics {
            timestamp: chrono::Utc::now(),
            cpu: CpuMetrics {
                usage_percent: 50.0,
                core_usage: vec![50.0],
                load_average: (1.0, 1.0, 1.0),
                frequency_mhz: Some(3000),
            },
            memory: MemoryMetrics {
                total_bytes: 16000000000000,
                used_bytes: 8000000000000,
                available_bytes: 8000000000000,
                swap_total_bytes: 2000000000000,
                swap_used_bytes: 0,
                usage_percent: 50.0,
            },
            disk: vec![],
            network: vec![],
        }];

        let temp_path = std::env::temp_dir().join("test_export.json");
        let result = MetricsExporter::export_json(&metrics, &[], &temp_path);

        assert!(result.is_ok());
        assert!(temp_path.exists());

        // Clean up
        std::fs::remove_file(&temp_path).ok();
    }
}
