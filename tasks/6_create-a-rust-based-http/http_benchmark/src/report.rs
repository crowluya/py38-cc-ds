use crate::cli::Args;
use crate::metrics::BenchmarkResult;
use colored::Colorize;
use std::collections::HashMap;

pub fn generate_report(result: &BenchmarkResult, args: &Args) {
    println!("{}", "━".repeat(80).cyan());
    println!("{}", "BENCHMARK RESULTS".bold().cyan());
    println!("{}", "━".repeat(80).cyan());
    println!();

    // Summary Statistics
    print_section("SUMMARY");
    print_metric("Duration", &format!("{:.2}s", result.duration.as_secs_f64()));
    print_metric("Total Requests", &result.total_requests.to_string());
    print_metric("Successful", &format!("{}", result.successful_requests.to_string().green()));
    print_metric("Failed", &format!("{}", result.failed_requests.to_string().red()));
    print_metric("Requests/sec", &format!("{:.2}", result.requests_per_second));
    println!();

    // Throughput
    print_section("THROUGHPUT");
    print_metric("Bytes Received", &format_bytes(result.bytes_received));
    print_metric("Bytes Sent", &format_bytes(result.bytes_sent));
    let bytes_per_sec = (result.bytes_received as f64 / result.duration.as_secs_f64()) as u64;
    print_metric("Transfer Rate", &format!("{}/s", format_bytes(bytes_per_sec)));
    println!();

    // Latency Statistics
    print_section("LATENCY STATISTICS");
    print_metric("Min", &format!("{:.2} ms", result.response_times.min));
    print_metric("Max", &format!("{:.2} ms", result.response_times.max));
    print_metric("Mean", &format!("{:.2} ms", result.response_times.mean));
    print_metric("Std Dev", &format!("{:.2} ms", result.response_times.std_dev));
    print_metric("Median (p50)", &format!("{:.2} ms", result.response_times.p50));
    print_metric("p95", &format!("{:.2} ms", result.response_times.p95));
    print_metric("p99", &format!("{:.2} ms", result.response_times.p99));
    println!();

    // Status Codes
    if !result.status_codes.is_empty() {
        print_section("STATUS CODES");
        let mut codes: Vec<_> = result.status_codes.iter().collect();
        codes.sort_by_key(|&(k, _)| std::cmp::Reverse(*k));

        for (code, count) in codes {
            let colored_code = if *code >= 200 && *code < 300 {
                code.to_string().green()
            } else if *code >= 400 && *code < 500 {
                code.to_string().yellow()
            } else if *code >= 500 {
                code.to_string().red()
            } else {
                code.to_string().normal()
            };
            println!("  {:>6} {} {}", colored_code, "─".repeat(4), count);
        }
        println!();
    }

    // Errors
    if result.errors.connection_errors > 0 || result.errors.timeout_errors > 0 || result.errors.other_errors > 0 {
        print_section("ERRORS");
        if result.errors.connection_errors > 0 {
            println!("  Connection Errors: {}", result.errors.connection_errors.to_string().red());
        }
        if result.errors.timeout_errors > 0 {
            println!("  Timeout Errors:    {}", result.errors.timeout_errors.to_string().yellow());
        }
        if result.errors.other_errors > 0 {
            println!("  Other Errors:       {}", result.errors.other_errors.to_string().red());
        }
        println!();
    }

    // Request Rate Over Time Graph
    if !result.rps_history.is_empty() {
        print_section("REQUESTS PER SECOND (OVER TIME)");
        print_rps_graph(&result.rps_history);
        println!();
    }

    // Connection Pool Configuration
    print_section("CONNECTION POOL CONFIGURATION");
    if let Some(pool_size) = result.pool_config.pool_size {
        print_metric("Pool Size", &pool_size.to_string());
    } else {
        print_metric("Pool Size", "default");
    }

    if let Some(max_idle) = result.pool_config.max_idle {
        print_metric("Max Idle Per Host", &max_idle.to_string());
    } else {
        print_metric("Max Idle Per Host", "default");
    }

    if let Some(timeout) = result.pool_config.timeout_secs {
        print_metric("Connection Timeout", &format!("{}s", timeout));
    } else {
        print_metric("Connection Timeout", "default");
    }
    println!();

    // Request Details
    print_section("REQUEST DETAILS");
    println!("  Method:              {}", args.method.bold());
    println!("  URL:                 {}", args.url);
    if args.request_body.is_some() {
        println!("  Request Body Size:   {} bytes", args.request_body.as_ref().unwrap().len());
    }
    if !args.headers.is_empty() {
        println!("  Custom Headers:      {}", args.headers.len());
        for (key, value) in &args.headers {
            println!("    {}: {}", key.cyan(), value);
        }
    }
    println!();

    println!("{}", "━".repeat(80).cyan());
}

fn print_section(title: &str) {
    println!("{}", title.bold().white().on_blue());
}

fn print_metric(label: &str, value: &str) {
    println!("  {:<20} {}", label.cyan(), value.bold());
}

fn format_bytes(bytes: u64) -> String {
    const KB: u64 = 1024;
    const MB: u64 = KB * 1024;
    const GB: u64 = MB * 1024;

    if bytes >= GB {
        format!("{:.2} GB", bytes as f64 / GB as f64)
    } else if bytes >= MB {
        format!("{:.2} MB", bytes as f64 / MB as f64)
    } else if bytes >= KB {
        format!("{:.2} KB", bytes as f64 / KB as f64)
    } else {
        format!("{} B", bytes)
    }
}

fn print_rps_graph(history: &[(f64, f64)]) {
    if history.is_empty() {
        return;
    }

    let max_rps = history.iter().map(|(_, rps)| *rps).fold(0.0_f64, f64::max);
    let max_rps = if max_rps == 0.0 { 1.0 } else { max_rps };

    let height = 10;
    let width = 60;

    // Create graph
    for row in (0..height).rev() {
        let threshold = (row as f64 / height as f64) * max_rps;

        print!("  ");

        for (i, (_, rps)) in history.iter().enumerate() {
            let filled = if i * width / history.len() < (i + 1) * width / history.len() {
                *rps >= threshold
            } else {
                false
            };

            if filled {
                print!("█");
            } else if (row + 1) < height {
                // Print placeholder for empty space
                if i % (history.len() / 10) == 0 {
                    print!("┼");
                } else {
                    print!("─");
                }
            } else {
                print!(" ");
            }
        }

        // Print Y-axis label
        println!("  {:.0}", threshold);
    }

    // Print X-axis
    println!("  {}", "─".repeat(width));
    println!("  Time (seconds)");

    // Print time labels
    let total_time = history.last().map(|(t, _)| *t).unwrap_or(0.0);
    print!("  ");
    for i in 0..=5 {
        let time = (total_time / 5.0) * i as f64;
        print!("{:>8.1}", time);
    }
    println!();
}
