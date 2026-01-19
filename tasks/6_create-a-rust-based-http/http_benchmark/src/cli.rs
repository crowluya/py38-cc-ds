use clap::Parser;
use std::collections::HashMap;

/// HTTP benchmarking tool with advanced metrics
#[derive(Parser, Debug)]
#[command(name = "http_bench")]
#[command(author = "HTTP Benchmark Tool")]
#[command(version = "0.1.0")]
#[command(about = "Perform load testing on web services with detailed metrics", long_about = None)]
pub struct Args {
    /// Target URL to benchmark
    #[arg(short, long)]
    pub url: Option<String>,

    /// Enable comparative analysis mode with multiple endpoints
    #[arg(long)]
    pub compare: bool,

    /// Endpoints to compare in format "label:url" (can be used multiple times)
    #[arg(long, value_parser = parse_endpoint, required_if_eq("compare", "true"))]
    pub endpoint: Vec<Endpoint>,

    /// HTTP method to use (GET, POST, PUT, DELETE, PATCH)
    #[arg(short, long, default_value = "GET")]
    pub method: String,

    /// Number of concurrent requests
    #[arg(short = 'c', long, default_value_t = 10)]
    pub concurrency: usize,

    /// Duration of the benchmark in seconds
    #[arg(short = 'd', long, default_value_t = 10)]
    pub duration: u64,

    /// Total number of requests to send (overrides duration if set)
    #[arg(short = 'n', long)]
    pub requests: Option<u64>,

    /// Maximum size of the connection pool
    #[arg(long)]
    pub pool_size: Option<usize>,

    /// Maximum number of idle connections per host
    #[arg(long)]
    pub max_idle_connections: Option<usize>,

    /// Connection timeout in seconds
    #[arg(long)]
    pub connection_timeout: Option<u64>,

    /// Request body for POST/PUT/PATCH requests
    #[arg(short = 'b', long)]
    pub request_body: Option<String>,

    /// Custom headers in format "Key: Value" (can be used multiple times)
    #[arg(short = 'H', long, value_parser = parse_header)]
    pub headers: HashMap<String, String>,

    /// Timeout for individual requests in seconds
    #[arg(short = 't', long, default_value_t = 30)]
    pub timeout: u64,

    /// Enable verbose output
    #[arg(short, long)]
    pub verbose: bool,

    /// Threshold for highlighting significant differences (percentage)
    #[arg(long, default_value_t = 10.0)]
    pub compare_threshold: f64,

    /// Sort comparison results by metric (latency, throughput, errors)
    #[arg(long, default_value = "latency")]
    pub sort_by: String,

    /// Output format for comparison report (table, markdown, json, csv)
    #[arg(long, default_value = "table")]
    pub output_format: String,
}

#[derive(Clone, Debug)]
pub struct Endpoint {
    pub label: String,
    pub url: String,
}

fn parse_header(s: &str) -> Result<(String, String), String> {
    let parts: Vec<&str> = s.splitn(2, ':').collect();
    if parts.len() != 2 {
        return Err(format!("Invalid header format: '{}'. Expected 'Key: Value'", s));
    }

    let key = parts[0].trim().to_string();
    let value = parts[1].trim().to_string();

    if key.is_empty() {
        return Err("Header key cannot be empty".to_string());
    }

    Ok((key, value))
}

fn parse_endpoint(s: &str) -> Result<Endpoint, String> {
    let parts: Vec<&str> = s.splitn(2, ':').collect();
    if parts.len() != 2 {
        return Err(format!("Invalid endpoint format: '{}'. Expected 'label:url'", s));
    }

    let label = parts[0].trim().to_string();
    let url = parts[1].trim().to_string();

    if label.is_empty() {
        return Err("Endpoint label cannot be empty".to_string());
    }

    if url.is_empty() {
        return Err("Endpoint URL cannot be empty".to_string());
    }

    // Basic URL validation
    if !url.starts_with("http://") && !url.starts_with("https://") {
        return Err(format!("Invalid URL: '{}'. URL must start with http:// or https://", url));
    }

    Ok(Endpoint { label, url })
}
