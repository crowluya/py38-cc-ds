//! Sort Bench - CLI application for benchmarking sorting algorithms
//!
//! This tool benchmarks and compares various sorting algorithms
//! across different input sizes and data distributions.

use clap::Parser;
use sort_bench::{
    benchmark::{Algorithm, BenchmarkRunner},
    data_gen::Distribution,
    charts::{ChartRenderer, TableGroupBy, VisualizationStyle},
};

/// Sort Bench - Sorting Algorithm Benchmarking Tool
///
/// Benchmarks and compares different sorting algorithms with visual ASCII charts
/// showing performance characteristics across various input sizes and data distributions.
#[derive(Parser, Debug)]
#[command(name = "sort_bench")]
#[command(author = "Sort Bench Tool")]
#[command(version = "0.1.0")]
#[command(about = "Benchmark and compare sorting algorithms", long_about = None)]
struct Args {
    /// Input sizes to benchmark (comma-separated)
    ///
    /// Example: --sizes 100,1000,10000
    #[arg(short, long, value_delimiter = ',', default_value = "100,1000,10000,100000")]
    sizes: Vec<usize>,

    /// Algorithms to benchmark (comma-separated)
    ///
    /// Options: quicksort, mergesort, heapsort, radix
    /// Example: --algorithms quicksort,mergesort
    #[arg(short, long, value_delimiter = ',', default_value = "quicksort,mergesort,heapsort,radix")]
    algorithms: Vec<String>,

    /// Data distributions to test (comma-separated)
    ///
    /// Options: random, sorted, reverse, mostly, duplicates
    /// Example: --distributions random,sorted
    #[arg(short, long, value_delimiter = ',', default_value = "random,sorted,reverse,mostly,duplicates")]
    distributions: Vec<String>,

    /// Visualization style
    ///
    /// Options: bars, table, summary, all
    #[arg(short, long, default_value = "all")]
    style: String,

    /// Number of warmup runs (discarded from timing)
    #[arg(long, default_value = "3")]
    warmup_runs: usize,

    /// Number of measured runs (median is used)
    #[arg(long, default_value = "5")]
    measured_runs: usize,

    /// Maximum bar width for bar charts
    #[arg(long, default_value = "40")]
    bar_width: usize,
}

fn parse_algorithms(alg_strs: &[String]) -> Result<Vec<Algorithm>, String> {
    let mut algorithms = Vec::new();

    for alg_str in alg_strs {
        let algorithm = match alg_str.to_lowercase().as_str() {
            "quicksort" | "quick" => Algorithm::QuickSort,
            "mergesort" | "merge" => Algorithm::MergeSort,
            "heapsort" | "heap" => Algorithm::HeapSort,
            "radixsort" | "radix" => Algorithm::RadixSort,
            _ => return Err(format!("Unknown algorithm: {}", alg_str)),
        };
        algorithms.push(algorithm);
    }

    Ok(algorithms)
}

fn parse_distributions(dist_strs: &[String]) -> Result<Vec<Distribution>, String> {
    let mut distributions = Vec::new();

    for dist_str in dist_strs {
        let distribution = match dist_str.to_lowercase().as_str() {
            "random" => Distribution::Random,
            "sorted" => Distribution::Sorted,
            "reverse" | "reverse-sorted" | "reversesorted" => Distribution::ReverseSorted,
            "mostly" | "mostly-sorted" | "mostlysorted" => Distribution::MostlySorted,
            "duplicates" | "duplicate" => Distribution::Duplicates,
            _ => return Err(format!("Unknown distribution: {}", dist_str)),
        };
        distributions.push(distribution);
    }

    Ok(distributions)
}

fn parse_style(style_str: &str) -> Result<VisualizationStyle, String> {
    match style_str.to_lowercase().as_str() {
        "bars" | "bar" | "barchart" => Ok(VisualizationStyle::BarChart),
        "table" | "t" => Ok(VisualizationStyle::Table),
        "summary" | "s" => Ok(VisualizationStyle::Both), // Summary is part of Both
        "all" | "a" => Ok(VisualizationStyle::Both),
        _ => Err(format!("Unknown visualization style: {}", style_str)),
    }
}

fn run() -> Result<(), String> {
    let args = Args::parse();

    // Parse arguments
    let algorithms = parse_algorithms(&args.algorithms)?;
    let distributions = parse_distributions(&args.distributions)?;
    let style = parse_style(&args.style)?;

    // Validate sizes
    if args.sizes.is_empty() {
        return Err("At least one input size must be specified".to_string());
    }

    for &size in &args.sizes {
        if size == 0 {
            return Err("Input size must be greater than 0".to_string());
        }
    }

    // Print configuration
    println!("╔══════════════════════════════════════════════════════════════╗");
    println!("║                    SORT BENCHMARK TOOL                       ║");
    println!("╚══════════════════════════════════════════════════════════════╝");
    println!();

    println!("Configuration:");
    println!("  Input sizes: {:?}", args.sizes);
    println!("  Algorithms: {:?}", algorithms.iter().map(|a| a.name()).collect::<Vec<_>>());
    println!("  Distributions: {:?}", distributions.iter().map(|d| d.name()).collect::<Vec<_>>());
    println!("  Warmup runs: {}", args.warmup_runs);
    println!("  Measured runs: {}", args.measured_runs);
    println!();

    // Create benchmark runner
    let runner = BenchmarkRunner::new(args.warmup_runs, args.measured_runs);

    // Run benchmarks
    println!("Starting benchmarks...\n");

    let start_time = std::time::Instant::now();
    let results = runner.run_suite(&algorithms, &args.sizes, &distributions);
    let total_time = start_time.elapsed();

    println!("\nAll benchmarks completed in {}", format_duration(total_time));
    println!();

    // Create chart renderer
    let renderer = ChartRenderer::new().with_bar_width(args.bar_width);

    // Display results based on style
    match style {
        VisualizationStyle::BarChart => {
            // Render bar charts for each size and distribution
            for &size in &args.sizes {
                for &distribution in &distributions {
                    let size_results: Vec<_> = results.results.iter()
                        .filter(|r| r.size == size && r.distribution == distribution)
                        .collect();

                    if !size_results.is_empty() {
                        let title = format!("{} elements - {}", size, distribution.name());
                        let chart = renderer.render_bar_chart(&size_results, &title);
                        println!("{}", chart);
                    }
                }
            }
        }
        VisualizationStyle::Table => {
            let table = renderer.render_table(&results, TableGroupBy::Size);
            println!("{}", table);
        }
        VisualizationStyle::Both => {
            // Show summary
            let summary = renderer.render_summary(&results);
            println!("{}", summary);

            println!();

            // Show bar charts for random distribution
            println!("Performance Comparison (Random Distribution)\n");
            for &size in &args.sizes {
                let size_results: Vec<_> = results.results.iter()
                    .filter(|r| r.size == size && r.distribution == Distribution::Random)
                    .collect();

                if !size_results.is_empty() {
                    let title = format!("{} elements (Random)", size);
                    let chart = renderer.render_bar_chart(&size_results, &title);
                    println!("{}", chart);
                }
            }

            println!();

            // Show detailed table
            let table = renderer.render_table(&results, TableGroupBy::Algorithm);
            println!("{}", table);
        }
    }

    Ok(())
}

fn format_duration(duration: std::time::Duration) -> String {
    let secs = duration.as_secs();
    let millis = duration.subsec_millis();

    if secs > 0 {
        format!("{}s {}ms", secs, millis)
    } else if millis > 0 {
        format!("{}ms", millis)
    } else {
        format!("{}μs", duration.subsec_micros())
    }
}

fn main() {
    if let Err(e) = run() {
        eprintln!("Error: {}", e);
        std::process::exit(1);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_algorithms() {
        let result = parse_algorithms(&vec!["quicksort".to_string(), "mergesort".to_string()]);
        assert!(result.is_ok());
        let algos = result.unwrap();
        assert_eq!(algos.len(), 2);
        assert_eq!(algos[0], Algorithm::QuickSort);
        assert_eq!(algos[1], Algorithm::MergeSort);
    }

    #[test]
    fn test_parse_algorithms_invalid() {
        let result = parse_algorithms(&vec!["invalid".to_string()]);
        assert!(result.is_err());
    }

    #[test]
    fn test_parse_distributions() {
        let result = parse_distributions(&vec!["random".to_string(), "sorted".to_string()]);
        assert!(result.is_ok());
        let dists = result.unwrap();
        assert_eq!(dists.len(), 2);
        assert_eq!(dists[0], Distribution::Random);
        assert_eq!(dists[1], Distribution::Sorted);
    }

    #[test]
    fn test_parse_distributions_invalid() {
        let result = parse_distributions(&vec!["invalid".to_string()]);
        assert!(result.is_err());
    }

    #[test]
    fn test_parse_style() {
        assert!(matches!(parse_style("bars"), Ok(VisualizationStyle::BarChart)));
        assert!(matches!(parse_style("table"), Ok(VisualizationStyle::Table)));
        assert!(matches!(parse_style("all"), Ok(VisualizationStyle::Both)));
    }

    #[test]
    fn test_format_duration() {
        let duration = std::time::Duration::from_millis(1500);
        assert_eq!(format_duration(duration), "1s 500ms");

        let duration2 = std::time::Duration::from_millis(500);
        assert_eq!(format_duration(duration2), "500ms");
    }
}
