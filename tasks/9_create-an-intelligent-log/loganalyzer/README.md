# LogAnalyzer

Intelligent log analysis CLI tool that parses application logs, detects anomalies using statistical analysis and pattern recognition, generates actionable insights with severity scoring, and exports summary reports in multiple formats.

## Features

- **Multi-Format Log Parsing**: Supports Apache, Nginx, JSON, and custom log formats
- **Statistical Anomaly Detection**: Z-score, IQR, moving average analysis
- **Pattern Recognition**: Detects unusual patterns, spikes, and correlations
- **Severity Scoring**: Intelligent 0-10 scoring with contextual awareness
- **Multiple Export Formats**: JSON, HTML, plain text, CSV, Markdown
- **Advanced Filtering**: Time range, log levels, patterns, regex support
- **Alert System**: Configurable thresholds with multiple notification channels
- **Performance**: Efficient streaming for large log files (10k+ lines/second)

## Installation

```bash
# Clone repository
git clone https://github.com/yourusername/loganalyzer.git
cd loganalyzer

# Install in development mode
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"
```

## Quick Start

```bash
# Analyze a log file
loganalyzer analyze /path/to/app.log

# Export to HTML report
loganalyzer analyze /path/to/app.log --output report.html --format html

# Filter by time range and severity
loganalyzer analyze app.log --after "2024-01-01" --before "2024-01-31" --min-severity 7

# Use custom configuration
loganalyzer analyze app.log --config custom-config.yaml
```

## Usage

### Basic Analysis

```bash
loganalyzer analyze <logfile> [options]
```

### Options

- `--format, -f`: Output format (json, html, text, csv, markdown)
- `--output, -o`: Output file path
- `--config, -c`: Configuration file path
- `--after`: Start time filter (ISO 8601 or common format)
- `--before`: End time filter
- `--level, -l`: Minimum log level (DEBUG, INFO, WARN, ERROR)
- `--min-severity`: Minimum anomaly severity (0-10)
- `--verbose, -v`: Verbose output
- `--quiet, -q`: Suppress warnings

### Configuration

Create a `config.yaml` file:

```yaml
analysis:
  zscore_threshold: 3.0
  iqr_multiplier: 1.5
  min_error_rate: 0.05

severity:
  critical_threshold: 9
  high_threshold: 7
  medium_threshold: 5
  low_threshold: 3

alerts:
  enabled: true
  min_severity: 7
  channels:
    - console
    - email  # Optional
```

## Log Formats

### Apache Common Log Format
```
127.0.0.1 - - [10/Oct/2023:13:55:36 +0000] "GET /api/users HTTP/1.1" 200 2326
```

### Nginx Combined Format
```
127.0.0.1 - - [10/Oct/2023:13:55:36 +0000] "GET /api/status HTTP/1.1" 200 1234 "http://example.com" "Mozilla/5.0"
```

### JSON Format
```json
{"timestamp": "2023-10-10T13:55:36Z", "level": "ERROR", "message": "Database connection failed", "service": "api"}
```

### Custom Format
Configure regex patterns in config file:

```yaml
parsers:
  custom:
    pattern: '^(?P<timestamp>\S+) \[(?P<level>\w+)\] (?P<message>.*)$'
    timestamp_format: "%Y-%m-%d %H:%M:%S"
```

## Examples

See the `examples/` directory for sample log files and use cases.

## Development

```bash
# Run tests
pytest

# Format code
black src/
isort src/

# Type checking
mypy src/

# Run with debug output
loganalyzer analyze app.log --verbose
```

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions welcome! Please read CONTRIBUTING.md for guidelines.
