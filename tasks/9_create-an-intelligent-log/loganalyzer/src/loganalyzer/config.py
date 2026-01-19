"""Configuration management for LogAnalyzer."""

import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class AnalysisConfig:
    """Configuration for anomaly detection analysis."""

    zscore_threshold: float = 3.0
    iqr_multiplier: float = 1.5
    min_error_rate: float = 0.05
    baseline_window: int = 1000
    moving_average_window: int = 50
    min_pattern_frequency: int = 5
    pattern_change_threshold: float = 2.0


@dataclass
class SeverityConfig:
    """Configuration for severity scoring."""

    critical_threshold: float = 9.0
    high_threshold: float = 7.0
    medium_threshold: float = 5.0
    low_threshold: float = 3.0
    info_threshold: float = 1.0

    @dataclass
    class Weights:
        frequency: float = 0.4
        deviation: float = 0.3
        impact: float = 0.3

    weights: Weights = field(default_factory=Weights)


@dataclass
class AlertConfig:
    """Configuration for alerting."""

    enabled: bool = True
    min_severity: float = 7.0
    channels: List[str] = field(default_factory=lambda: ["console"])

    @dataclass
    class EmailConfig:
        enabled: bool = False
        smtp_host: Optional[str] = None
        smtp_port: int = 587
        from_address: Optional[str] = None
        to_address: Optional[str] = None
        subject: str = "LogAnalyzer Alert"

    email: EmailConfig = field(default_factory=EmailConfig)

    @dataclass
    class WebhookConfig:
        enabled: bool = False
        url: Optional[str] = None

    webhook: WebhookConfig = field(default_factory=WebhookConfig)

    @dataclass
    class SuppressionConfig:
        enabled: bool = True
        window_minutes: int = 15
        max_alerts_per_window: int = 5

    suppression: SuppressionConfig = field(default_factory=SuppressionConfig)


@dataclass
class ParserConfig:
    """Configuration for log parsing."""

    auto_detect: bool = True
    date_formats: List[str] = field(default_factory=list)
    custom: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        """Set default date formats if not provided."""
        if not self.date_formats:
            self.date_formats = [
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%d %H:%M:%S",
                "%d/%b/%Y:%H:%M:%S %z",
                "%d/%b/%Y:%H:%M:%S",
                "%b %d %H:%M:%S",
                "%Y/%m/%d %H:%M:%S",
            ]


@dataclass
class ExportConfig:
    """Configuration for report exporting."""

    default_format: str = "text"

    @dataclass
    class HTMLConfig:
        theme: str = "default"
        include_charts: bool = True

    html: HTMLConfig = field(default_factory=HTMLConfig)

    @dataclass
    class JSONConfig:
        pretty: bool = True
        include_raw: bool = False

    json: JSONConfig = field(default_factory=JSONConfig)

    @dataclass
    class TextConfig:
        width: int = 100
        color: bool = True

    text: TextConfig = field(default_factory=TextConfig)


@dataclass
class PerformanceConfig:
    """Configuration for performance tuning."""

    chunk_size: int = 10000
    max_memory_mb: int = 1000
    parallel: bool = False
    workers: int = 4


@dataclass
class LoggingConfig:
    """Configuration for logging."""

    level: str = "INFO"
    file: Optional[str] = None


@dataclass
class Config:
    """Main configuration container."""

    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    severity: SeverityConfig = field(default_factory=SeverityConfig)
    alerts: AlertConfig = field(default_factory=AlertConfig)
    parsers: ParserConfig = field(default_factory=ParserConfig)
    export: ExportConfig = field(default_factory=ExportConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "Config":
        """Create Config from dictionary."""
        config = cls()

        # Analysis config
        if "analysis" in config_dict:
            analysis_dict = config_dict["analysis"]
            config.analysis = AnalysisConfig(**analysis_dict)

        # Severity config
        if "severity" in config_dict:
            severity_dict = config_dict["severity"]
            if "weights" in severity_dict:
                severity_dict["weights"] = SeverityConfig.Weights(**severity_dict["weights"])
            config.severity = SeverityConfig(**severity_dict)

        # Alert config
        if "alerts" in config_dict:
            alert_dict = config_dict["alerts"]
            if "email" in alert_dict:
                alert_dict["email"] = AlertConfig.EmailConfig(**alert_dict["email"])
            if "webhook" in alert_dict:
                alert_dict["webhook"] = AlertConfig.WebhookConfig(**alert_dict["webhook"])
            if "suppression" in alert_dict:
                alert_dict["suppression"] = AlertConfig.SuppressionConfig(**alert_dict["suppression"])
            config.alerts = AlertConfig(**alert_dict)

        # Parser config
        if "parsers" in config_dict:
            config.parsers = ParserConfig(**config_dict["parsers"])

        # Export config
        if "export" in config_dict:
            export_dict = config_dict["export"]
            if "html" in export_dict:
                export_dict["html"] = ExportConfig.HTMLConfig(**export_dict["html"])
            if "json" in export_dict:
                export_dict["json"] = ExportConfig.JSONConfig(**export_dict["json"])
            if "text" in export_dict:
                export_dict["text"] = ExportConfig.TextConfig(**export_dict["text"])
            config.export = ExportConfig(**export_dict)

        # Performance config
        if "performance" in config_dict:
            config.performance = PerformanceConfig(**config_dict["performance"])

        # Logging config
        if "logging" in config_dict:
            config.logging = LoggingConfig(**config_dict["logging"])

        return config

    @classmethod
    def from_file(cls, config_path: str) -> "Config":
        """Load configuration from YAML file."""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(path, "r") as f:
            config_dict = yaml.safe_load(f)

        return cls.from_dict(config_dict)

    @classmethod
    def load_default(cls) -> "Config":
        """Load default configuration."""
        # Get the package directory
        package_dir = Path(__file__).parent
        default_config_path = package_dir.parent.parent.parent / "config" / "default.yaml"

        if default_config_path.exists():
            return cls.from_file(str(default_config_path))
        else:
            # Return hardcoded defaults if file not found
            return cls()

    def merge_with(self, other: "Config") -> "Config":
        """Merge this config with another, preferring other's values."""
        # Simple merge - in production, you'd want deeper merging
        return other if other else self
