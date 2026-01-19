use crate::cli::{Args, Endpoint};
use crate::client::HttpClient;
use crate::metrics::{BenchmarkResult, MetricsCollector, PoolConfig};
use colored::Colorize;
use indicatif::{MultiProgress, ProgressBar, ProgressStyle};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::time::{Duration, Instant};

/// Configuration for comparative analysis
#[derive(Clone, Debug)]
pub struct ComparisonConfig {
    pub endpoints: Vec<Endpoint>,
    pub shared_args: SharedTestConfig,
    pub threshold: f64,
    pub sort_by: SortMetric,
    pub output_format: OutputFormat,
}

#[derive(Clone, Debug)]
pub struct SharedTestConfig {
    pub method: String,
    pub concurrency: usize,
    pub duration: u64,
    pub requests: Option<u64>,
    pub timeout: u64,
    pub pool_size: Option<usize>,
    pub max_idle_connections: Option<usize>,
    pub connection_timeout: Option<u64>,
    pub request_body: Option<String>,
    pub headers: HashMap<String, String>,
}

#[derive(Clone, Debug, PartialEq)]
pub enum SortMetric {
    Latency,
    Throughput,
    Errors,
}

#[derive(Clone, Debug, PartialEq)]
pub enum OutputFormat {
    Table,
    Markdown,
    Json,
    Csv,
}

/// Result from comparing multiple endpoints
pub struct ComparisonResult {
    pub results: Vec<EndpointResult>,
    pub config: ComparisonConfig,
    pub total_duration: Duration,
}

pub struct EndpointResult {
    pub label: String,
    pub url: String,
    pub result: Result<BenchmarkResult, String>,
    pub start_time: Instant,
    pub end_time: Instant,
}

/// Comparative statistics between endpoints
pub struct ComparativeStats {
    pub best_latency: Option<String>,
    pub worst_latency: Option<String>,
    pub best_throughput: Option<String>,
    pub worst_throughput: Option<String>,
    pub best_errors: Option<String>,
    pub worst_errors: Option<String>,
    pub latency_deltas: Vec<(String, f64, f64)>, // label, abs_diff, pct_diff
    pub throughput_deltas: Vec<(String, f64, f64)>,
}

impl From<&Args> for ComparisonConfig {
    fn from(args: &Args) -> Self {
        let sort_by = match args.sort_by.to_lowercase().as_str() {
            "throughput" => SortMetric::Throughput,
            "errors" => SortMetric::Errors,
            _ => SortMetric::Latency,
        };

        let output_format = match args.output_format.to_lowercase().as_str() {
            "markdown" => OutputFormat::Markdown,
            "json" => OutputFormat::Json,
            "csv" => OutputFormat::Csv,
            _ => OutputFormat::Table,
        };

        Self {
            endpoints: args.endpoint.clone(),
            shared_args: SharedTestConfig {
                method: args.method.clone(),
                concurrency: args.concurrency,
                duration: args.duration,
                requests: args.requests,
                timeout: args.timeout,
                pool_size: args.pool_size,
                max_idle_connections: args.max_idle_connections,
                connection_timeout: args.connection_timeout,
                request_body: args.request_body.clone(),
                headers: args.headers.clone(),
            },
            threshold: args.compare_threshold,
            sort_by,
            output_format,
        }
    }
}

/// Execute benchmarks against multiple endpoints in parallel
pub async fn execute_parallel_benchmarks(
    config: &ComparisonConfig,
) -> Result<ComparisonResult, Box<dyn std::error::Error>> {
    let client = HttpClient::new(
        config.shared_args.pool_size,
        config.shared_args.max_idle_connections,
        config.shared_args.connection_timeout,
    )?;

    let multi_progress = MultiProgress::new();
    let mut progress_bars = Vec::new();

    // Create progress bars for each endpoint
    for endpoint in &config.endpoints {
        let pb = multi_progress.add(ProgressBar::new(
            config.shared_args.requests.unwrap_or(config.shared_args.duration * 1000),
        ));
        pb.set_style(
            ProgressStyle::default_bar()
                .template(&format!(
                    "{{spinner:.green}} [{}] [{{elapsed_precise}}] [{{bar:40.cyan/blue}}] {{pos}}/{{len}} {{msg}}",
                    endpoint.label.bold()
                ))
                .progress_chars("##-"),
        );
        progress_bars.push((endpoint.label.clone(), pb));
    }

    println!();
    println!("{}", "Running Comparative Analysis...".bold().cyan());
    println!(
        "{}",
        "━".repeat(80).cyan()
    );
    println!();

    let start_time = Instant::now();
    let mut handles = Vec::new();
    let mut endpoint_results = Vec::new();

    // Spawn a task for each endpoint
    for (idx, endpoint) in config.endpoints.iter().enumerate() {
        let client = client.clone();
        let endpoint = endpoint.clone();
        let config = config.clone();
        let pb = progress_bars[idx].1.clone();

        let handle = tokio::spawn(async move {
            let endpoint_start = Instant::now();
            let metrics = MetricsCollector::new();

            // Create a synthetic Args for the single endpoint
            let args = create_single_endpoint_args(&endpoint, &config.shared_args);

            let result = client
                .execute_benchmark(
                    &args,
                    &metrics,
                    &pb,
                    config.shared_args.duration,
                    config.shared_args.requests,
                    endpoint_start,
                )
                .await;

            let endpoint_end = Instant::now();

            EndpointResult {
                label: endpoint.label.clone(),
                url: endpoint.url,
                result,
                start_time: endpoint_start,
                end_time: endpoint_end,
            }
        });

        handles.push(handle);
    }

    // Wait for all benchmarks to complete
    for handle in handles {
        let endpoint_result = handle.await?;
        endpoint_results.push(endpoint_result);
    }

    let total_duration = start_time.elapsed();

    // Finish all progress bars
    for (_, pb) in progress_bars {
        pb.finish_with_message("Complete");
    }

    Ok(ComparisonResult {
        results: endpoint_results,
        config: config.clone(),
        total_duration,
    })
}

fn create_single_endpoint_args(endpoint: &Endpoint, shared: &SharedTestConfig) -> Args {
    Args {
        url: Some(endpoint.url.clone()),
        compare: false,
        endpoint: vec![],
        method: shared.method.clone(),
        concurrency: shared.concurrency,
        duration: shared.duration,
        requests: shared.requests,
        pool_size: shared.pool_size,
        max_idle_connections: shared.max_idle_connections,
        connection_timeout: shared.connection_timeout,
        request_body: shared.request_body.clone(),
        headers: shared.headers.clone(),
        timeout: shared.timeout,
        verbose: false,
        compare_threshold: 10.0,
        sort_by: "latency".to_string(),
        output_format: "table".to_string(),
    }
}

/// Calculate comparative statistics from multiple benchmark results
pub fn calculate_comparative_stats(
    results: &[EndpointResult],
) -> Result<ComparativeStats, String> {
    let mut valid_results: Vec<_> = results
        .iter()
        .filter_map(|r| {
            r.result
                .as_ref()
                .ok()
                .map(|res| (r.label.clone(), res))
        })
        .collect();

    if valid_results.is_empty() {
        return Err("No successful benchmark results to compare".to_string());
    }

    // Find best and worst for each metric
    let best_latency = valid_results
        .iter()
        .min_by_key(|(_, r)| (r.response_times.p50 * 1000.0) as u64)
        .map(|(l, _)| l.clone());

    let worst_latency = valid_results
        .iter()
        .max_by_key(|(_, r)| (r.response_times.p50 * 1000.0) as u64)
        .map(|(l, _)| l.clone());

    let best_throughput = valid_results
        .iter()
        .max_by(|a, b| {
            a.1.requests_per_second
                .partial_cmp(&b.1.requests_per_second)
                .unwrap()
        })
        .map(|(l, _)| l.clone());

    let worst_throughput = valid_results
        .iter()
        .min_by(|a, b| {
            a.1.requests_per_second
                .partial_cmp(&b.1.requests_per_second)
                .unwrap()
        })
        .map(|(l, _)| l.clone());

    let best_errors = valid_results
        .iter()
        .min_by_key(|(_, r)| r.failed_requests)
        .map(|(l, _)| l.clone());

    let worst_errors = valid_results
        .iter()
        .max_by_key(|(_, r)| r.failed_requests)
        .map(|(l, _)| l.clone());

    // Calculate deltas relative to best performer
    let best_p50 = best_latency
        .as_ref()
        .and_then(|label| {
            valid_results
                .iter()
                .find(|(l, _)| l == label)
                .map(|(_, r)| r.response_times.p50)
        })
        .unwrap_or(0.0);

    let latency_deltas: Vec<_> = valid_results
        .iter()
        .map(|(label, res)| {
            let abs_diff = res.response_times.p50 - best_p50;
            let pct_diff = if best_p50 > 0.0 {
                (abs_diff / best_p50) * 100.0
            } else {
                0.0
            };
            (label.clone(), abs_diff, pct_diff)
        })
        .collect();

    let best_rps = best_throughput
        .as_ref()
        .and_then(|label| {
            valid_results
                .iter()
                .find(|(l, _)| l == label)
                .map(|(_, r)| r.requests_per_second)
        })
        .unwrap_or(0.0);

    let throughput_deltas: Vec<_> = valid_results
        .iter()
        .map(|(label, res)| {
            let abs_diff = res.requests_per_second - best_rps;
            let pct_diff = if best_rps > 0.0 {
                (abs_diff / best_rps) * 100.0
            } else {
                0.0
            };
            (label.clone(), abs_diff, pct_diff)
        })
        .collect();

    Ok(ComparativeStats {
        best_latency,
        worst_latency,
        best_throughput,
        worst_throughput,
        best_errors,
        worst_errors,
        latency_deltas,
        throughput_deltas,
    })
}

/// Generate a comparison report
pub fn generate_comparison_report(
    comparison: &ComparisonResult,
) -> Result<(), Box<dyn std::error::Error>> {
    match comparison.config.output_format {
        OutputFormat::Table => generate_table_report(comparison),
        OutputFormat::Markdown => generate_markdown_report(comparison),
        OutputFormat::Json => generate_json_report(comparison),
        OutputFormat::Csv => generate_csv_report(comparison),
    }
}

fn generate_table_report(comparison: &ComparisonResult) -> Result<(), Box<dyn std::error::Error>> {
    println!();
    println!("{}", "━".repeat(80).cyan());
    println!("{}", "COMPARATIVE ANALYSIS REPORT".bold().cyan());
    println!("{}", "━".repeat(80).cyan());
    println!();

    // Calculate statistics
    let stats = calculate_comparative_stats(&comparison.results)?;

    // Summary section
    print_section("SUMMARY");
    println!(
        "  {:<20} {}",
        "Endpoints Tested:".cyan(),
        comparison.results.len()
    );
    println!(
        "  {:<20} {:.2}s",
        "Total Duration:".cyan(),
        comparison.total_duration.as_secs_f64()
    );

    let success_count = comparison
        .results
        .iter()
        .filter(|r| r.result.is_ok())
        .count();
    println!(
        "  {:<20} {}/{}",
        "Successful:".cyan(),
        success_count,
        comparison.results.len()
    );
    println!();

    // Winners table
    print_section("PERFORMANCE LEADERS");
    if let Some(best) = &stats.best_latency {
        println!(
            "  {:<20} {}",
            "Best Latency (p50):".cyan(),
            best.green().bold()
        );
    }
    if let Some(best) = &stats.best_throughput {
        println!(
            "  {:<20} {}",
            "Highest Throughput:".cyan(),
            best.green().bold()
        );
    }
    if let Some(best) = &stats.best_errors {
        println!(
            "  {:<20} {}",
            "Lowest Error Rate:".cyan(),
            best.green().bold()
        );
    }
    println!();

    // Comparison table
    print_section("DETAILED COMPARISON");
    print_comparison_table(&comparison.results, &stats, &comparison.config)?;
    println!();

    // Detailed results for each endpoint
    for endpoint_result in &comparison.results {
        print_endpoint_details(endpoint_result, &comparison.config)?;
    }

    println!("{}", "━".repeat(80).cyan());

    Ok(())
}

fn print_comparison_table(
    results: &[EndpointResult],
    stats: &ComparativeStats,
    config: &ComparisonConfig,
) -> Result<(), Box<dyn std::error::Error>> {
    // Header
    println!(
        "  {:<15} {:>12} {:>12} {:>12} {:>12} {:>10}",
        "Endpoint".bold(),
        "p50 (ms)",
        "p95 (ms)",
        "p99 (ms)",
        "RPS",
        "Errors %"
    );
    println!(
        "  {}",
        "─".repeat(75)
    );

    // Sort results based on configuration
    let mut sorted_results: Vec<_> = results
        .iter()
        .filter_map(|r| r.result.as_ref().ok().map(|res| (r, res)))
        .collect();

    match config.sort_by {
        SortMetric::Latency => {
            sorted_results.sort_by(|a, b| {
                a.1.response_times
                    .p50
                    .partial_cmp(&b.1.response_times.p50)
                    .unwrap()
            })
        }
        SortMetric::Throughput => {
            sorted_results.sort_by(|a, b| {
                b.1.requests_per_second
                    .partial_cmp(&a.1.requests_per_second)
                    .unwrap()
            })
        }
        SortMetric::Errors => {
            sorted_results.sort_by_key(|(_, res)| res.failed_requests);
        }
    }

    // Rows
    for (idx, (endpoint_result, result)) in sorted_results.iter().enumerate() {
        let label = &endpoint_result.label;
        let medal = if idx == 0 {
            "🥇 "
        } else if idx == 1 {
            "🥈 "
        } else if idx == 2 {
            "🥉 "
        } else {
            ""
        };

        let error_pct = if result.total_requests > 0 {
            (result.failed_requests as f64 / result.total_requests as f64) * 100.0
        } else {
            0.0
        };

        println!(
            "  {:<15} {:>12.2} {:>12.2} {:>12.2} {:>12.2} {:>10.2}",
            format!("{}{}", medal, label.bold()),
            result.response_times.p50,
            result.response_times.p95,
            result.response_times.p99,
            result.requests_per_second,
            error_pct
        );
    }

    Ok(())
}

fn print_endpoint_details(
    endpoint_result: &EndpointResult,
    config: &ComparisonConfig,
) -> Result<(), Box<dyn std::error::Error>> {
    println!(
        "{}",
        format!("{}: {}", "Endpoint".bold(), endpoint_result.label).cyan()
    );
    println!("  URL: {}", endpoint_result.url);

    match &endpoint_result.result {
        Ok(result) => {
            println!(
                "  {:<20} {:.2} ms",
                "Median Latency:".cyan(),
                result.response_times.p50
            );
            println!(
                "  {:<20} {:.2} req/s",
                "Throughput:".cyan(),
                result.requests_per_second
            );
            println!(
                "  {:<20} {}/{}",
                "Errors:".cyan(),
                result.failed_requests,
                result.total_requests
            );

            // Check if this endpoint is significantly different
            if let Some(stats) = calculate_comparative_stats(&[endpoint_result.clone()]).ok() {
                // This is simplified - in real implementation we'd compare against best
            }
        }
        Err(e) => {
            println!("  {} {}", "Error:".red(), e.red());
        }
    }

    println!();
    Ok(())
}

fn print_section(title: &str) {
    println!("{}", title.bold().white().on_blue());
}

fn generate_markdown_report(
    _comparison: &ComparisonResult,
) -> Result<(), Box<dyn std::error::Error>> {
    let mut output = String::new();
    output.push_str("# Comparative Analysis Report\n\n");

    println!("{}", output);
    Ok(())
}

fn generate_json_report(
    _comparison: &ComparisonResult,
) -> Result<(), Box<dyn std::error::Error>> {
    let json = serde_json::to_string_pretty(_comparison)?;
    println!("{}", json);
    Ok(())
}

fn generate_csv_report(
    _comparison: &ComparisonResult,
) -> Result<(), Box<dyn std::error::Error>> {
    println!("Endpoint,URL,Total Requests,Successful,Failed,RPS,p50,p95,p99,Error Rate");

    for endpoint_result in &_comparison.results {
        if let Ok(result) = &endpoint_result.result {
            let error_rate = if result.total_requests > 0 {
                (result.failed_requests as f64 / result.total_requests as f64) * 100.0
            } else {
                0.0
            };

            println!(
                "{},{},{},{},{},{:.2},{:.2},{:.2},{:.2},{:.2}",
                endpoint_result.label,
                endpoint_result.url,
                result.total_requests,
                result.successful_requests,
                result.failed_requests,
                result.requests_per_second,
                result.response_times.p50,
                result.response_times.p95,
                result.response_times.p99,
                error_rate
            );
        }
    }

    Ok(())
}
