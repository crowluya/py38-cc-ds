//! ASCII chart visualization for benchmark results
//!
//! Provides various visualization styles for benchmark results:
//! - Bar charts showing time comparisons
//! - Tables comparing algorithms across different configurations

use crate::benchmark::{Algorithm, BenchmarkResult, AggregatedResults};
use crate::data_gen::Distribution;

/// Visualization styles
#[derive(Debug, Clone, Copy)]
pub enum VisualizationStyle {
    BarChart,
    Table,
    Both,
}

/// Chart renderer for ASCII visualization
pub struct ChartRenderer {
    bar_width: usize,
    max_label_width: usize,
}

impl ChartRenderer {
    /// Create a new chart renderer
    pub fn new() -> Self {
        ChartRenderer {
            bar_width: 40,
            max_label_width: 12,
        }
    }

    /// Set the maximum width for bars
    pub fn with_bar_width(mut self, width: usize) -> Self {
        self.bar_width = width;
        self
    }

    /// Render a bar chart comparing algorithms for a specific size and distribution
    pub fn render_bar_chart(
        &self,
        results: &[&BenchmarkResult],
        title: &str,
    ) -> String {
        if results.is_empty() {
            return String::from("No results to display");
        }

        let mut output = String::new();
        output.push_str(&format!("{}\n", title));
        output.push_str(&str::repeat("=", title.len()));
        output.push_str("\n\n");

        // Find maximum time for scaling
        let max_time = results.iter()
            .map(|r| r.time_micros())
            .fold(0.0f64, f64::max);

        // Sort results by time
        let mut sorted_results = results.to_vec();
        sorted_results.sort_by(|a, b| {
            a.time_micros().partial_cmp(&b.time_micros()).unwrap()
        });

        // Render bars
        for result in sorted_results {
            let time = result.time_micros();
            let bar_length = if max_time > 0.0 {
                ((time / max_time) * self.bar_width as f64) as usize
            } else {
                0
            };

            let label = result.algorithm.name();
            let padded_label = format!("{:<width$}", label, width = self.max_label_width);

            output.push_str(&format!("{} │", padded_label));

            // Draw bar
            if bar_length > 0 {
                output.push_str(&str::repeat("█", bar_length));
            }

            // Add time label
            output.push_str(&format!(" {:.2} μs\n", time));
        }

        output.push_str("\n");
        output
    }

    /// Render a comparison table
    pub fn render_table(
        &self,
        results: &AggregatedResults,
        group_by: TableGroupBy,
    ) -> String {
        let mut output = String::new();

        match group_by {
            TableGroupBy::Algorithm => {
                output.push_str("Algorithm Comparison by Input Size\n");
                output.push_str(&str::repeat("=", 80));
                output.push_str("\n\n");

                // Get unique sizes and distributions
                let sizes: Vec<usize> = {
                    let mut set = std::collections::HashSet::new();
                    for r in &results.results {
                        set.insert(r.size);
                    }
                    let mut vec: Vec<_> = set.into_iter().collect();
                    vec.sort();
                    vec
                };

                let distributions: Vec<Distribution> = {
                    let mut set = std::collections::HashSet::new();
                    for r in &results.results {
                        set.insert(r.distribution);
                    }
                    let mut vec: Vec<_> = set.into_iter().collect();
                    vec.sort_by_key(|d| d.name());
                    vec
                };

                for algorithm in Algorithm::all() {
                    output.push_str(&format!("{}\n", algorithm.name()));
                    output.push_str(&str::repeat("-", algorithm.name().len()));
                    output.push_str("\n");

                    for &distribution in &distributions {
                        output.push_str(&format!("  {}:\n", distribution.name()));

                        for &size in &sizes {
                            if let Some(result) = results.results.iter()
                                .find(|r| r.algorithm == algorithm && r.size == size && r.distribution == distribution)
                            {
                                output.push_str(&format!("    {:>8}: {}\n", size, result.format_time()));
                            }
                        }
                        output.push_str("\n");
                    }
                }
            }
            TableGroupBy::Size => {
                output.push_str("Performance by Input Size\n");
                output.push_str(&str::repeat("=", 80));
                output.push_str("\n\n");

                let sizes: Vec<usize> = {
                    let mut set = std::collections::HashSet::new();
                    for r in &results.results {
                        set.insert(r.size);
                    }
                    let mut vec: Vec<_> = set.into_iter().collect();
                    vec.sort();
                    vec
                };

                let distributions: Vec<Distribution> = {
                    let mut set = std::collections::HashSet::new();
                    for r in &results.results {
                        set.insert(r.distribution);
                    }
                    let mut vec: Vec<_> = set.into_iter().collect();
                    vec.sort_by_key(|d| d.name());
                    vec
                };

                for &size in &sizes {
                    output.push_str(&format!("Input Size: {}\n", size));
                    output.push_str(&str::repeat("-", format!("Input Size: {}", size).len()));
                    output.push_str("\n");

                    for &distribution in &distributions {
                        output.push_str(&format!("  {}:\n", distribution.name()));

                        for algorithm in Algorithm::all() {
                            if let Some(result) = results.results.iter()
                                .find(|r| r.algorithm == algorithm && r.size == size && r.distribution == distribution)
                            {
                                output.push_str(&format!("    {:>12}: {}\n", algorithm.name(), result.format_time()));
                            }
                        }
                        output.push_str("\n");
                    }
                }
            }
        }

        output
    }

    /// Render a summary comparison
    pub fn render_summary(&self, results: &AggregatedResults) -> String {
        let mut output = String::new();

        output.push_str("┌─────────────────────────────────────────────────────────────┐\n");
        output.push_str("│                    BENCHMARK SUMMARY                        │\n");
        output.push_str("└─────────────────────────────────────────────────────────────┘\n\n");

        // Calculate statistics
        let total_runs = results.results.len();
        let algorithms: Vec<Algorithm> = {
            let mut set = std::collections::HashSet::new();
            for r in &results.results {
                set.insert(r.algorithm);
            }
            set.into_iter().collect()
        };

        output.push_str(&format!("Total benchmark runs: {}\n", total_runs));
        output.push_str(&format!("Algorithms tested: {}\n\n", algorithms.len()));

        // Show fastest/slowest for each configuration
        let sizes: Vec<usize> = {
            let mut set = std::collections::HashSet::new();
            for r in &results.results {
                set.insert(r.size);
            }
            let mut vec: Vec<_> = set.into_iter().collect();
            vec.sort();
            vec
        };

        for &size in &sizes {
            output.push_str(&format!("Size: {}\n", size));
            output.push_str(&str::repeat("-", format!("Size: {}", size).len()));
            output.push_str("\n");

            let distributions: Vec<Distribution> = {
                let mut set = std::collections::HashSet::new();
                for r in &results.results {
                    if r.size == size {
                        set.insert(r.distribution);
                    }
                }
                let mut vec: Vec<_> = set.into_iter().collect();
                vec.sort_by_key(|d| d.name());
                vec
            };

            for &distribution in &distributions {
                let mut size_results: Vec<&BenchmarkResult> = results.results.iter()
                    .filter(|r| r.size == size && r.distribution == distribution)
                    .collect();

                if !size_results.is_empty() {
                    size_results.sort_by(|a, b| {
                        a.time_micros().partial_cmp(&b.time_micros()).unwrap()
                    });

                    let fastest = &size_results[0];
                    let slowest = &size_results[size_results.len() - 1];

                    output.push_str(&format!("  {}:\n", distribution.name()));
                    output.push_str(&format!("    Fastest: {} ({})\n", fastest.algorithm.name(), fastest.format_time()));
                    output.push_str(&format!("    Slowest: {} ({})\n", slowest.algorithm.name(), slowest.format_time()));

                    if fastest.time_micros() > 0.0 {
                        let speedup = slowest.time_micros() / fastest.time_micros();
                        output.push_str(&format!("    Speedup: {:.2}x\n", speedup));
                    }

                    output.push_str("\n");
                }
            }
        }

        output
    }
}

impl Default for ChartRenderer {
    fn default() -> Self {
        Self::new()
    }
}

/// Table grouping options
pub enum TableGroupBy {
    Algorithm,
    Size,
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::Duration;

    #[test]
    fn test_bar_chart_rendering() {
        let renderer = ChartRenderer::new();

        let results = vec![
            &BenchmarkResult {
                algorithm: Algorithm::QuickSort,
                size: 1000,
                distribution: Distribution::Random,
                time: Duration::from_micros(100),
                runs: 5,
            },
            &BenchmarkResult {
                algorithm: Algorithm::MergeSort,
                size: 1000,
                distribution: Distribution::Random,
                time: Duration::from_micros(150),
                runs: 5,
            },
        ];

        let output = renderer.render_bar_chart(&results, "Test Chart");
        assert!(output.contains("Test Chart"));
        assert!(output.contains("QuickSort"));
        assert!(output.contains("MergeSort"));
    }

    #[test]
    fn test_summary_rendering() {
        let renderer = ChartRenderer::new();
        let mut results = AggregatedResults::new();

        results.add_result(BenchmarkResult {
            algorithm: Algorithm::QuickSort,
            size: 100,
            distribution: Distribution::Random,
            time: Duration::from_micros(100),
            runs: 5,
        });

        let output = renderer.render_summary(&results);
        assert!(output.contains("BENCHMARK SUMMARY"));
        assert!(output.contains("Total benchmark runs"));
    }
}
