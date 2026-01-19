use clap::{Parser, ValueEnum};
use std::path::PathBuf;

#[derive(Parser, Debug)]
#[command(name = "data-viz")]
#[command(about = "A CLI data visualization tool for JSON/CSV files", long_about = None)]
pub struct Args {
    /// Input file path (JSON or CSV)
    #[arg(short, long, value_name = "FILE")]
    pub input: PathBuf,

    /// Output file path (HTML)
    #[arg(short, long, value_name = "FILE", default_value = "chart.html")]
    pub output: PathBuf,

    /// Chart type to generate
    #[arg(short, long, value_name = "TYPE", default_value = "bar")]
    pub chart_type: ChartTypeArg,

    /// Chart title
    #[arg(short, long, value_name = "TITLE", default_value = "Data Visualization")]
    pub title: String,

    /// Color theme
    #[arg(short, long, value_name = "THEME", default_value = "default")]
    pub theme: String,

    /// Primary color (hex format, e.g., #3498db)
    #[arg(long, value_name = "COLOR")]
    pub color: Option<String>,

    /// Show legend
    #[arg(long, default_value = "true")]
    pub legend: bool,

    /// Enable zoom functionality
    #[arg(long, default_value = "true")]
    pub zoom: bool,

    /// X-axis label
    #[arg(long, value_name = "LABEL")]
    pub x_label: Option<String>,

    /// Y-axis label
    #[arg(long, value_name = "LABEL")]
    pub y_label: Option<String>,

    /// Width of the chart in pixels
    #[arg(long, value_name = "PIXELS", default_value = "800")]
    pub width: u32,

    /// Height of the chart in pixels
    #[arg(long, value_name = "PIXELS", default_value = "600")]
    pub height: u32,
}

#[derive(Clone, Debug, ValueEnum)]
pub enum ChartTypeArg {
    Bar,
    Line,
    Scatter,
}

impl std::fmt::Display for ChartTypeArg {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ChartTypeArg::Bar => write!(f, "bar"),
            ChartTypeArg::Line => write!(f, "line"),
            ChartTypeArg::Scatter => write!(f, "scatter"),
        }
    }
}
