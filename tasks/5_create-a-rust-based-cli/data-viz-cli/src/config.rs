use crate::cli::{Args, ChartTypeArg};
use crate::charts::{ChartType, ChartStyle};
use std::path::PathBuf;

#[derive(Debug, Clone)]
pub struct Config {
    pub input_path: PathBuf,
    pub output_path: PathBuf,
    pub chart_type: ChartType,
    pub title: String,
    pub style: ChartStyle,
    pub x_label: Option<String>,
    pub y_label: Option<String>,
}

impl Config {
    pub fn from_args(args: Args) -> anyhow::Result<Self> {
        let chart_type = match args.chart_type {
            ChartTypeArg::Bar => ChartType::Bar,
            ChartTypeArg::Line => ChartType::Line,
            ChartTypeArg::Scatter => ChartType::Scatter,
        };

        let style = ChartStyle::new(
            args.theme,
            args.color,
            args.legend,
            args.zoom,
            args.width,
            args.height,
        );

        Ok(Config {
            input_path: args.input,
            output_path: args.output,
            chart_type,
            title: args.title,
            style,
            x_label: args.x_label,
            y_label: args.y_label,
        })
    }
}
