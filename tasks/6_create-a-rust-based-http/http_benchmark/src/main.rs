mod cli;
mod client;
mod comparison;
mod metrics;
mod percentile;
mod rate_tracker;
mod report;

use clap::Parser;
use colored::Colorize;
use indicatif::{ProgressBar, ProgressStyle};
use std::time::Duration;

use cli::Args;
use client::HttpClient;
use comparison::execute_parallel_benchmarks;
use metrics::MetricsCollector;
use report::generate_report;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = Args::parse();

    // Check if we're in comparison mode
    if args.compare {
        run_comparison_mode(&args).await?;
    } else {
        run_single_mode(&args).await?;
    }

    Ok(())
}

async fn run_comparison_mode(args: &Args) -> Result<(), Box<dyn std::error::Error>> {
    println!("\n{}", "HTTP Benchmark Tool - Comparative Mode".bold().cyan());
    println!("{}\n", "━".repeat(50));

    // Display configuration
    println!("{}", "Configuration:".bold());
    println!("  Mode:             {}", "Comparative Analysis".cyan());
    println!("  Endpoints:        {}", args.endpoint.len());
    for endpoint in &args.endpoint {
        println!("    - {}            {}", endpoint.label.bold(), endpoint.url);
    }
    println!("  Method:           {}", args.method);
    println!("  Concurrency:      {}", args.concurrency);
    println!("  Duration:         {}s", args.duration);
    println!("  Requests:         {}", args.requests.unwrap_or_else(|| "unlimited".to_string()));
    println!("  Sort By:          {}", args.sort_by);
    println!("  Output Format:    {}", args.output_format);
    println!();

    // Create comparison config and execute parallel benchmarks
    let config = comparison::ComparisonConfig::from(args);
    let comparison_result = execute_parallel_benchmarks(&config).await?;

    // Generate comparison report
    comparison::generate_comparison_report(&comparison_result)?;

    Ok(())
}

async fn run_single_mode(args: &Args) -> Result<(), Box<dyn std::error::Error>> {
    // Validate that URL is provided for single mode
    let url = args.url.as_ref().ok_or("URL is required for single-endpoint mode")?;

    println!("\n{}", "HTTP Benchmark Tool".bold().cyan());
    println!("{}\n", "━".repeat(50));

    // Display configuration
    println!("{}", "Configuration:".bold());
    println!("  URL:              {}", url);
    println!("  Method:           {}", args.method);
    println!("  Concurrency:      {}", args.concurrency);
    println!("  Duration:         {}s", args.duration);
    println!("  Requests:         {}", args.requests.unwrap_or_else(|| "unlimited".to_string()));

    if let Some(pool_size) = args.pool_size {
        println!("  Pool Size:        {}", pool_size);
    }
    if let Some(max_idle) = args.max_idle_connections {
        println!("  Max Idle:         {}", max_idle);
    }
    if let Some(timeout) = args.connection_timeout {
        println!("  Conn Timeout:     {}s", timeout);
    }

    if let Some(body) = &args.request_body {
        println!("  Request Body:     {} bytes", body.len());
    }

    if !args.headers.is_empty() {
        println!("  Custom Headers:   {}", args.headers.len());
    }
    println!();

    // Create HTTP client with configuration
    let client = HttpClient::new(
        args.pool_size,
        args.max_idle_connections,
        args.connection_timeout,
    )?;

    // Create metrics collector
    let metrics = MetricsCollector::new();

    // Setup progress bar
    let total_requests = args.requests.unwrap_or(args.duration * 1000);
    let pb = ProgressBar::new(total_requests);
    pb.set_style(
        ProgressStyle::default_bar()
            .template(
                "{spinner:.green} [{elapsed_precise}] [{bar:40.cyan/blue}] {pos}/{len} {msg}",
            )
            .progress_chars("##-"),
    );

    println!("{}", "Running benchmark...".bold());
    println!();

    // Create a mutable args with the URL set
    let mut single_args = args.clone();
    single_args.url = Some(url.clone());

    // Execute benchmark
    let start_time = std::time::Instant::now();
    let result = client
        .execute_benchmark(
            &single_args,
            &metrics,
            &pb,
            args.duration,
            args.requests,
            start_time,
        )
        .await?;

    pb.finish_with_message("Benchmark complete!");

    // Generate and display report
    println!();
    generate_report(&result, &single_args);

    Ok(())
}
