use clap::Parser;
use std::path::PathBuf;

/// Comprehensive text analysis tool for markdown files
#[derive(Parser, Debug)]
#[command(name = "md_analysis")]
#[command(author = "Your Name <your.email@example.com>")]
#[command(version = "0.1.0")]
#[command(about = "Analyze markdown files for readability, word frequency, sentence complexity, and writing style", long_about = None)]
pub struct Args {
    /// Path to the markdown file to analyze
    #[arg(value_name = "FILE")]
    pub file_path: PathBuf,

    /// Output format for the analysis results
    #[arg(short, long, value_name = "FORMAT", default_value = "console")]
    pub output: OutputFormat,

    /// Output file path (if not specified, prints to stdout)
    #[arg(short, long, value_name = "OUTPUT_FILE")]
    pub output_file: Option<PathBuf>,

    /// Number of top frequent words to display
    #[arg(long, value_name = "NUM", default_value = "20")]
    pub top_words: usize,

    /// Verbose output (show more detailed metrics)
    #[arg(short, long)]
    pub verbose: bool,

    /// Include code blocks in analysis
    #[arg(long, default_value = "false")]
    pub include_code_blocks: bool,

    /// Minimum word length to include in frequency analysis
    #[arg(long, value_name = "NUM", default_value = "3")]
    pub min_word_length: usize,
}

/// Output format options
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum OutputFormat {
    Console,
    Json,
    Csv,
}

impl std::str::FromStr for OutputFormat {
    type Err = String;

    fn from_str(s: &str) -> std::result::Result<Self, Self::Err> {
        match s.to_lowercase().as_str() {
            "console" => Ok(OutputFormat::Console),
            "json" => Ok(OutputFormat::Json),
            "csv" => Ok(OutputFormat::Csv),
            _ => Err(format!("Invalid output format: {}. Valid options are: console, json, csv", s)),
        }
    }
}

impl std::fmt::Display for OutputFormat {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            OutputFormat::Console => write!(f, "console"),
            OutputFormat::Json => write!(f, "json"),
            OutputFormat::Csv => write!(f, "csv"),
        }
    }
}
