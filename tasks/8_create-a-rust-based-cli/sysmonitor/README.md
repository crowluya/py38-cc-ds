# System Monitor (sysmonitor)

A comprehensive CLI tool for real-time system resource monitoring with customizable alerts and data export capabilities. Built with Rust for performance and reliability.

## Features

- **Real-time Monitoring**: Track CPU, memory, disk, and network usage with configurable intervals
- **Multiple Display Modes**: Minimal, normal, detailed, JSON, and interactive TUI
- **Customizable Alerts**: Set thresholds for CPU, memory, disk, and network usage with cooldown periods
- **Data Export**: Export historical metrics to CSV or JSON formats
- **Low Overhead**: Designed for minimal CPU and memory usage
- **Cross-platform**: Supports Linux, macOS, and Windows

## Installation

### From Source

```bash
# Clone the repository
git clone <repository-url>
cd sysmonitor

# Build the project
cargo build --release

# The binary will be available at target/release/sysmonitor
```

### Installing System-wide

```bash
cargo install --path .
```

## Quick Start

```bash
# Start monitoring with default settings (normal mode, 1 second interval)
sysmonitor

# Minimal one-line output
sysmonitor -m minimal

# Interactive terminal UI
sysmonitor -m tui

# JSON output for integration with other tools
sysmonitor -m json

# Monitor for 30 seconds and export to CSV
sysmonitor -d 30s --export metrics.csv --export-format csv

# Monitor specific disk mounts only
sysmonitor --mounts / /home
```

## Usage

### Command-Line Options

```
System resource monitoring tool

Usage: sysmonitor [OPTIONS]

Options:
  -i, --interval <MS>           Monitoring interval in milliseconds [default: 1000]
  -m, --mode <MODE>             Display mode: minimal, normal, detailed, json, tui [default: normal]
  -c, --config <FILE>           Configuration file path
      --generate-config [FILE]  Generate default configuration file
      --history <N>             Number of historical data points to keep [default: 1000]
      --export <FILE>           Export historical data to file
      --export-format <FORMAT>  Export format: csv, json [default: json]
      --no-alerts               Disable all alerts
  -v, --verbose                 Verbose output (debug logging)
  -d, --duration <DURATION>     Run for specified duration (e.g., 10s, 5m, 1h)
      --mounts <MOUNTS>         Monitor specific disk mount points only
  -h, --help                    Print help
  -V, --version                 Print version
```

### Display Modes

#### Minimal Mode
Single-line output showing key metrics:
```
[14:32:15] CPU:  25.3% | Mem:  62.8% | Disk:   3 mount(s)
```

#### Normal Mode (default)
Multi-line formatted output with color-coded metrics:
```
══════════════════════════════════════════════════════
System Metrics - 2024-01-19 14:32:15
═══════════════════════════════════════════════════════

📊 CPU
  Usage:      25.3%
  Load Avg:  1.23, 1.45, 1.67

💾 Memory
  RAM:        8.2 GB / 16.0 GB (51.2%)
  Swap:       0.0 B / 4.0 GB (0.0%)

💿 Disk
  /          : 120.5 GB / 500.0 GB (24.1%)
  /home      : 450.2 GB / 1.0 TB (43.9%)

🌐 Network
  eth0      : ↓ 1.2 MB/s  ↑ 512 KB/s
  wlan0     : ↓ 0 B/s  ↑ 0 B/s
```

#### Detailed Mode
Includes per-core CPU usage and disk I/O rates:
```
... (normal mode output) ...

🔍 Detailed Information

  CPU Cores:
    Core 0:  23.1%  Core 1:  27.5%  Core 2:  22.8%  Core 3:  28.1%

  Disk I/O:
    /: ↓ 2.3 MB/s  ↑ 1.1 MB/s
    /home: ↓ 5.6 MB/s  ↑ 2.3 MB/s
```

#### TUI Mode
Interactive terminal UI with real-time updates:
- Press `q` or `Esc` to quit
- Color-coded usage indicators (green → yellow → red)
- Shows all metrics in a single dashboard
- Displays recent alerts

## Configuration

### Configuration File Format

The tool supports YAML configuration files for advanced customization. Generate a default configuration:

```bash
sysmonitor --generate-config
```

Default configuration file locations:
- Current directory: `./sysmonitor.yaml`
- User config: `~/.config/sysmonitor/sysmonitor.yaml`
- System-wide: `/etc/sysmonitor.yaml`

### Configuration Options

```yaml
# Monitoring interval in milliseconds
interval_ms: 1000

# Number of historical data points to keep in memory
history_size: 1000

# Display mode: minimal, normal, detailed, json, tui
display_mode: normal

# Maximum number of network interfaces to monitor
max_network_interfaces: 10

# Specific disk mount points to monitor (empty = all)
monitored_mount_points: []

# Alert configuration
alerts:
  cpu:
    enabled: true
    usage_threshold_percent: 80.0
    load_average_threshold: 2.0

  memory:
    enabled: true
    usage_threshold_percent: 85.0
    swap_threshold_percent: 50.0

  disk:
    enabled: true
    usage_threshold_percent: 90.0

  network:
    enabled: true
    error_threshold: 10

  # Cooldown period in seconds between alerts of the same type
  cooldown_seconds: 60
```

## Alerting

The system monitors your resources and triggers alerts when thresholds are exceeded:

### Alert Types

1. **High CPU Usage**: Triggered when CPU usage exceeds threshold
2. **High Load Average**: Triggered when load average exceeds threshold
3. **High Memory Usage**: Triggered when RAM usage exceeds threshold
4. **High Swap Usage**: Triggered when swap usage exceeds threshold
5. **High Disk Usage**: Triggered when disk usage exceeds threshold
6. **High Network Errors**: Triggered when network error rate exceeds threshold

### Alert Cooldown

Alerts have a configurable cooldown period to prevent spam. By default, the same alert type won't trigger more than once per 60 seconds.

### Disabling Alerts

```bash
# Disable all alerts
sysmonitor --no-alerts

# Or disable specific alerts in config file
alerts:
  cpu:
    enabled: false
```

## Data Export

### CSV Export

```bash
sysmonitor -d 5m --export system_metrics.csv --export-format csv
```

CSV format includes:
- Timestamp
- CPU usage percentage
- Load averages
- Memory usage (total, used, percentage)
- Swap usage
- Disk usage per mount point
- Network statistics per interface

### JSON Export

```bash
sysmonitor -d 5m --export system_metrics.json --export-format json
```

JSON format includes:
- All metrics data
- Alert history
- Time range information
- Machine-readable format for integration

## Examples

### Monitor for 10 minutes and export

```bash
sysmonitor -d 10m --export monitoring_session.json
```

### Real-time monitoring with custom interval

```bash
sysmonitor -i 500 -m minimal
```

### Monitor specific mounts with detailed output

```bash
sysmonitor --mounts / /var -m detailed
```

### Continuous monitoring with alerts

```bash
# Run in background with alerts enabled
sysmonitor -m normal &

# Save PID for later
echo $! > sysmonitor.pid

# Stop later
kill $(cat sysmonitor.pid)
```

## Performance

The tool is designed for minimal overhead:

- **CPU Usage**: < 1% during normal operation
- **Memory Usage**: ~50-100 MB with default history size
- **Update Rate**: Configurable, default 1 second

## Platform Support

### Linux
Full support for all features including load averages.

### macOS
Full support (some system calls may differ).

### Windows
Full support (load averages not available, shows 0).

## Troubleshooting

### Permission Issues

Some metrics may require elevated privileges:

```bash
sudo sysmonitor
```

### Terminal Issues with TUI

If TUI mode doesn't work:
- Ensure your terminal supports alternate screen mode
- Try increasing terminal size (minimum 80x24)
- Fall back to normal mode: `sysmonitor -m normal`

### High CPU Usage

If the tool uses more CPU than expected:
- Increase the monitoring interval: `sysmonitor -i 2000`
- Reduce history size: `sysmonitor --history 500`
- Use minimal mode: `sysmonitor -m minimal`

## Development

### Building

```bash
cargo build
```

### Running Tests

```bash
cargo test
```

### Building with All Features

```bash
cargo build --release --all-features
```

## License

MIT License - see LICENSE file for details

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## Author

System Monitor Development Team

## Version

0.1.0 - Initial release
