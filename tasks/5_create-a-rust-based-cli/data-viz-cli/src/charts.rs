use crate::data::DataSet;
use anyhow::Result;
use serde::{Deserialize, Serialize};

/// Chart type enumeration
#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum ChartType {
    Bar,
    Line,
    Scatter,
}

impl ChartType {
    pub fn as_str(&self) -> &str {
        match self {
            ChartType::Bar => "bar",
            ChartType::Line => "line",
            ChartType::Scatter => "scatter",
        }
    }
}

/// Chart style configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChartStyle {
    pub theme: String,
    pub primary_color: Option<String>,
    pub show_legend: bool,
    pub enable_zoom: bool,
    pub width: u32,
    pub height: u32,
}

impl Default for ChartStyle {
    fn default() -> Self {
        ChartStyle {
            theme: "default".to_string(),
            primary_color: None,
            show_legend: true,
            enable_zoom: true,
            width: 800,
            height: 600,
        }
    }
}

impl ChartStyle {
    pub fn new(
        theme: String,
        primary_color: Option<String>,
        show_legend: bool,
        enable_zoom: bool,
        width: u32,
        height: u32,
    ) -> Self {
        ChartStyle {
            theme,
            primary_color,
            show_legend,
            enable_zoom,
            width,
            height,
        }
    }

    pub fn get_color_palette(&self) -> Vec<String> {
        if let Some(ref color) = self.primary_color {
            return vec![color.clone()];
        }

        match self.theme.as_str() {
            "default" => vec![
                "#3498db".to_string(),
                "#e74c3c".to_string(),
                "#2ecc71".to_string(),
                "#f39c12".to_string(),
                "#9b59b6".to_string(),
                "#1abc9c".to_string(),
                "#34495e".to_string(),
                "#16a085".to_string(),
                "#27ae60".to_string(),
                "#2980b9".to_string(),
            ],
            "pastel" => vec![
                "#FFB3BA".to_string(),
                "#FFDFBA".to_string(),
                "#FFFFBA".to_string(),
                "#BAFFC9".to_string(),
                "#BAE1FF".to_string(),
            ],
            "dark" => vec![
                "#2c3e50".to_string(),
                "#34495e".to_string(),
                "#7f8c8d".to_string(),
                "#95a5a6".to_string(),
                "#bdc3c7".to_string(),
            ],
            "vibrant" => vec![
                "#FF6B6B".to_string(),
                "#4ECDC4".to_string(),
                "#45B7D1".to_string(),
                "#FFA07A".to_string(),
                "#98D8C8".to_string(),
            ],
            _ => vec![
                "#3498db".to_string(),
                "#e74c3c".to_string(),
                "#2ecc71".to_string(),
            ],
        }
    }
}

/// Main chart structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Chart {
    pub chart_type: ChartType,
    pub title: String,
    pub dataset: DataSet,
    pub style: ChartStyle,
    pub x_label: Option<String>,
    pub y_label: Option<String>,
}

impl Chart {
    pub fn new(chart_type: ChartType, dataset: DataSet, title: String, style: ChartStyle) -> Result<Self> {
        if dataset.is_empty() {
            return Err(anyhow::anyhow!("Dataset cannot be empty"));
        }

        Ok(Chart {
            chart_type,
            title,
            dataset,
            style,
            x_label: None,
            y_label: None,
        })
    }

    pub fn with_labels(mut self, x_label: Option<String>, y_label: Option<String>) -> Self {
        self.x_label = x_label;
        self.y_label = y_label;
        self
    }

    pub fn get_chart_data(&self) -> ChartData {
        let labels: Vec<String> = self.dataset.points.iter().map(|p| p.label.clone()).collect();
        let data: Vec<f64> = self.dataset.points.iter().map(|p| p.value).collect();

        let (x_data, y_data) = if self.chart_type == ChartType::Scatter {
            let x: Vec<f64> = self.dataset.points.iter().map(|p| p.x.unwrap_or(0.0)).collect();
            let y: Vec<f64> = self.dataset.points.iter().map(|p| p.y.unwrap_or(p.value)).collect();
            (Some(x), Some(y))
        } else {
            (None, None)
        };

        ChartData {
            labels,
            data,
            x_data,
            y_data,
            dataset_name: self.dataset.name.clone(),
            colors: self.style.get_color_palette(),
        }
    }
}

/// Serialized chart data for JavaScript
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChartData {
    pub labels: Vec<String>,
    pub data: Vec<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub x_data: Option<Vec<f64>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub y_data: Option<Vec<f64>>,
    pub dataset_name: String,
    pub colors: Vec<String>,
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::data::DataPoint;

    #[test]
    fn test_chart_type_as_str() {
        assert_eq!(ChartType::Bar.as_str(), "bar");
        assert_eq!(ChartType::Line.as_str(), "line");
        assert_eq!(ChartType::Scatter.as_str(), "scatter");
    }

    #[test]
    fn test_chart_style_default() {
        let style = ChartStyle::default();
        assert_eq!(style.theme, "default");
        assert!(style.show_legend);
    }

    #[test]
    fn test_chart_new() {
        let mut dataset = DataSet::new("Test".to_string());
        dataset.add_point(DataPoint::new("A".to_string(), 10.0));

        let style = ChartStyle::default();
        let chart = Chart::new(ChartType::Bar, dataset, "Test Chart".to_string(), style);

        assert!(chart.is_ok());
        let chart = chart.unwrap();
        assert_eq!(chart.title, "Test Chart");
    }

    #[test]
    fn test_chart_empty_dataset() {
        let dataset = DataSet::new("Test".to_string());
        let style = ChartStyle::default();

        let chart = Chart::new(ChartType::Bar, dataset, "Test Chart".to_string(), style);
        assert!(chart.is_err());
    }

    #[test]
    fn test_get_color_palette() {
        let style = ChartStyle::default();
        let colors = style.get_color_palette();
        assert!(!colors.is_empty());
        assert_eq!(colors[0], "#3498db");
    }

    #[test]
    fn test_get_chart_data() {
        let mut dataset = DataSet::new("Test".to_string());
        dataset.add_point(DataPoint::new("A".to_string(), 10.0));
        dataset.add_point(DataPoint::new("B".to_string(), 20.0));

        let style = ChartStyle::default();
        let chart = Chart::new(ChartType::Bar, dataset, "Test".to_string(), style).unwrap();
        let chart_data = chart.get_chart_data();

        assert_eq!(chart_data.labels.len(), 2);
        assert_eq!(chart_data.data.len(), 2);
        assert_eq!(chart_data.labels[0], "A");
        assert_eq!(chart_data.data[0], 10.0);
    }
}
