use crate::error::{DataVizError, Result};
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;

/// Represents a single data point
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DataPoint {
    pub label: String,
    pub value: f64,
    pub x: Option<f64>,
    pub y: Option<f64>,
}

impl DataPoint {
    pub fn new(label: String, value: f64) -> Self {
        DataPoint {
            label,
            value,
            x: None,
            y: None,
        }
    }

    pub fn new_xy(x: f64, y: f64, label: Option<String>) -> Self {
        DataPoint {
            label: label.unwrap_or_else(|| format!("({}, {})", x, y)),
            value: y,
            x: Some(x),
            y: Some(y),
        }
    }
}

/// Represents a complete dataset
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DataSet {
    pub name: String,
    pub points: Vec<DataPoint>,
}

impl DataSet {
    pub fn new(name: String) -> Self {
        DataSet {
            name,
            points: Vec::new(),
        }
    }

    pub fn add_point(&mut self, point: DataPoint) {
        self.points.push(point);
    }

    pub fn is_empty(&self) -> bool {
        self.points.is_empty()
    }

    pub fn len(&self) -> usize {
        self.points.len()
    }
}

/// Input data type
#[derive(Debug, Clone, Copy)]
pub enum DataType {
    Json,
    Csv,
}

impl DataType {
    pub fn from_path(path: &Path) -> Result<Self> {
        match path.extension().and_then(|ext| ext.to_str()) {
            Some("json") => Ok(DataType::Json),
            Some("csv") => Ok(DataType::Csv),
            _ => Err(DataVizError::InvalidDataFormat(
                "Unsupported file format. Use .json or .csv".to_string(),
            )),
        }
    }
}

/// Data reader for JSON and CSV files
pub struct DataReader {
    path: String,
}

impl DataReader {
    pub fn new<P: AsRef<std::path::Path>>(path: P) -> Self {
        DataReader {
            path: path.as_ref().to_string_lossy().to_string(),
        }
    }

    pub fn read(&self) -> Result<DataSet> {
        let path = Path::new(&self.path);
        let data_type = DataType::from_path(path)?;

        match data_type {
            DataType::Json => self.read_json(),
            DataType::Csv => self.read_csv(),
        }
    }

    fn read_json(&self) -> Result<DataSet> {
        let content = fs::read_to_string(&self.path)
            .map_err(|e| DataVizError::FileReadError(format!("{}: {}", self.path, e)))?;

        // Try to parse as array of objects first
        if let Ok(raw_data) = serde_json::from_str::<Vec<serde_json::Value>>(&content) {
            return self.parse_json_array(raw_data);
        }

        // Try to parse as single object with data array
        if let Ok(raw_data) = serde_json::from_str::<serde_json::Value>(&content) {
            return self.parse_json_object(raw_data);
        }

        Err(DataVizError::InvalidDataFormat(
            "Could not parse JSON structure".to_string(),
        ))
    }

    fn parse_json_array(&self, data: Vec<serde_json::Value>) -> Result<DataSet> {
        let mut dataset = DataSet::new("Data".to_string());

        for (index, item) in data.iter().enumerate() {
            let point = self.parse_json_value(item, index)?;
            dataset.add_point(point);
        }

        Ok(dataset)
    }

    fn parse_json_object(&self, data: serde_json::Value) -> Result<DataSet> {
        // Try to find common JSON structures
        if let Some(name) = data.get("name").and_then(|v| v.as_str()) {
            if let Some(data_array) = data.get("data").and_then(|v| v.as_array()) {
                let mut dataset = DataSet::new(name.to_string());
                for (index, item) in data_array.iter().enumerate() {
                    let point = self.parse_json_value(item, index)?;
                    dataset.add_point(point);
                }
                return Ok(dataset);
            }
        }

        // Try data array at top level
        if let Some(data_array) = data.get("data").and_then(|v| v.as_array()) {
            return self.parse_json_array(data_array.clone());
        }

        Err(DataVizError::InvalidDataFormat(
            "Unsupported JSON structure".to_string(),
        ))
    }

    fn parse_json_value(&self, value: &serde_json::Value, index: usize) -> Result<DataPoint> {
        // Try to extract label and value
        let label = value
            .get("label")
            .or(value.get("name"))
            .or(value.get("category"))
            .and_then(|v| v.as_str())
            .unwrap_or(&format!("Point {}", index))
            .to_string();

        let value_f64 = value
            .get("value")
            .or(value.get("count"))
            .or(value.get("amount"))
            .and_then(|v| v.as_f64())
            .ok_or_else(|| DataVizError::MissingField("value".to_string()))?;

        // Check for x/y coordinates
        if let (Some(x), Some(y)) = (value.get("x").and_then(|v| v.as_f64()), value.get("y").and_then(|v| v.as_f64())) {
            return Ok(DataPoint::new_xy(x, y, Some(label)));
        }

        Ok(DataPoint::new(label, value_f64))
    }

    fn read_csv(&self) -> Result<DataSet> {
        let content = fs::read_to_string(&self.path)
            .map_err(|e| DataVizError::FileReadError(format!("{}: {}", self.path, e)))?;

        let mut rdr = csv::Reader::from_reader(content.as_bytes());
        let headers = rdr.headers()?.clone();

        let mut dataset = DataSet::new("Data".to_string());

        for result in rdr.records() {
            let record = result?;
            let point = self.parse_csv_record(&record, &headers)?;
            dataset.add_point(point);
        }

        Ok(dataset)
    }

    fn parse_csv_record(&self, record: &csv::StringRecord, headers: &csv::StringRecord) -> Result<DataPoint> {
        // Try to find label column
        let label_col = headers
            .iter()
            .find(|&h| h == "label" || h == "name" || h == "category")
            .or(headers.get(0));

        let label = label_col
            .and_then(|col| record.get(headers.iter().position(|&h| h == col).unwrap_or(0)))
            .unwrap_or("Unknown")
            .to_string();

        // Try to find value column
        let value_col = headers
            .iter()
            .find(|&h| h == "value" || h == "count" || h == "amount");

        let value = if let Some(col) = value_col {
            let idx = headers.iter().position(|&h| h == col).unwrap();
            record
                .get(idx)
                .and_then(|v| v.parse::<f64>().ok())
                .ok_or_else(|| DataVizError::ParseError(format!("Invalid value in column {}", col)))?
        } else {
            // Use second column as default
            record
                .get(1)
                .and_then(|v| v.parse::<f64>().ok())
                .ok_or_else(|| DataVizError::MissingField("value".to_string()))?
        };

        // Check for x/y columns
        if let (Some(x_idx), Some(y_idx)) = (
            headers.iter().position(|&h| h == "x"),
            headers.iter().position(|&h| h == "y"),
        ) {
            if let (Some(x_str), Some(y_str)) = (record.get(x_idx), record.get(y_idx)) {
                if let (Some(x), Some(y)) = (x_str.parse::<f64>().ok(), y_str.parse::<f64>().ok()) {
                    return Ok(DataPoint::new_xy(x, y, Some(label)));
                }
            }
        }

        Ok(DataPoint::new(label, value))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_datapoint_new() {
        let point = DataPoint::new("Test".to_string(), 42.0);
        assert_eq!(point.label, "Test");
        assert_eq!(point.value, 42.0);
    }

    #[test]
    fn test_dataset_new() {
        let dataset = DataSet::new("Test Dataset".to_string());
        assert_eq!(dataset.name, "Test Dataset");
        assert!(dataset.is_empty());
        assert_eq!(dataset.len(), 0);
    }

    #[test]
    fn test_dataset_add_point() {
        let mut dataset = DataSet::new("Test".to_string());
        dataset.add_point(DataPoint::new("A".to_string(), 10.0));
        assert_eq!(dataset.len(), 1);
        assert!(!dataset.is_empty());
    }
}
