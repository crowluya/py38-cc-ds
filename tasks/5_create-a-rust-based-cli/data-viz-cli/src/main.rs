mod cli;
mod config;
mod data;
mod charts;
mod output;
mod error;

use anyhow::Result;
use clap::Parser;
use cli::Args;
use config::Config;
use data::{DataReader, DataType};
use charts::{Chart, ChartType};
use output::HtmlWriter;

fn main() -> Result<()> {
    // Parse CLI arguments
    let args = Args::parse();

    // Create configuration from arguments
    let config = Config::from_args(args)?;

    // Read input data
    let reader = DataReader::new(&config.input_path);
    let dataset = reader.read()?;

    // Create chart based on type
    let chart = Chart::new(config.chart_type, dataset, config.title, config.style)?
        .with_labels(config.x_label, config.y_label);

    // Generate HTML output
    let writer = HtmlWriter::new(&config.output_path);
    writer.write(&chart)?;

    println!("Chart successfully generated at: {}", config.output_path);
    Ok(())
}
