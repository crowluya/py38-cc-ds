use clap::Parser;

/// CLI arguments for the productivity dashboard
#[derive(Parser, Debug, Clone)]
#[command(name = "productivity-dashboard")]
#[command(author = "Your Name <your.email@example.com>")]
#[command(version = "0.1.0")]
#[command(about = "A CLI productivity dashboard for real-time system monitoring", long_about = None)]
pub struct Args {
    /// Update interval in seconds (default: 1.0)
    #[arg(short, long, default_value = "1.0")]
    pub interval: f64,

    /// Color theme to use (default, gruvbox, monokai, nord)
    #[arg(short, long, default_value = "default")]
    pub theme: String,

    /// Show only specific metrics (cpu, memory, disk, all)
    #[arg(short, long, default_value = "all")]
    pub show: String,

    /// Minimum update interval in seconds
    #[arg(short, long, default_value = "0.1")]
    pub min_interval: f64,

    /// Maximum update interval in seconds
    #[arg(short, long, default_value = "10.0")]
    pub max_interval: f64,
}

impl Args {
    /// Validate the interval settings
    pub fn validate(&self) -> Result<(), String> {
        if self.interval < self.min_interval {
            return Err(format!(
                "Interval {} is less than minimum {}",
                self.interval, self.min_interval
            ));
        }
        if self.interval > self.max_interval {
            return Err(format!(
                "Interval {} is greater than maximum {}",
                self.interval, self.max_interval
            ));
        }
        Ok(())
    }
}

/// Application configuration
#[derive(Debug, Clone)]
pub struct Config {
    pub update_interval: std::time::Duration,
    pub theme: String,
    pub show_cpu: bool,
    pub show_memory: bool,
    pub show_disk: bool,
    pub min_interval: std::time::Duration,
    pub max_interval: std::time::Duration,
}

impl From<Args> for Config {
    fn from(args: Args) -> Self {
        let show_cpu = args.show == "all" || args.show == "cpu";
        let show_memory = args.show == "all" || args.show == "memory";
        let show_disk = args.show == "all" || args.show == "disk";

        Config {
            update_interval: std::time::Duration::from_secs_f64(args.interval),
            theme: args.theme,
            show_cpu,
            show_memory,
            show_disk,
            min_interval: std::time::Duration::from_secs_f64(args.min_interval),
            max_interval: std::time::Duration::from_secs_f64(args.max_interval),
        }
    }
}

impl Config {
    /// Create default configuration
    pub fn default() -> Self {
        Config {
            update_interval: std::time::Duration::from_secs(1),
            theme: String::from("default"),
            show_cpu: true,
            show_memory: true,
            show_disk: true,
            min_interval: std::time::Duration::from_secs_f64(0.1),
            max_interval: std::time::Duration::from_secs(10),
        }
    }
}
