use crate::cli::Args;
use crate::metrics::{ErrorType, MetricsCollector, PoolConfig};
use crate::rate_tracker::RateTracker;
use indicatif::ProgressBar;
use reqwest::Client;
use reqwest::Method;
use std::time::{Duration, Instant};
use std::collections::HashMap;

pub struct HttpClient {
    client: Client,
}

impl HttpClient {
    pub fn new(
        pool_size: Option<usize>,
        max_idle: Option<usize>,
        timeout_secs: Option<u64>,
    ) -> Result<Self, Box<dyn std::error::Error>> {
        // Validate pool configuration
        if let Some(size) = pool_size {
            if size == 0 {
                return Err("Pool size must be greater than 0".into());
            }
            if size > 10000 {
                return Err("Pool size cannot exceed 10000".into());
            }
        }

        if let Some(idle) = max_idle {
            if idle == 0 {
                return Err("Max idle connections must be greater than 0".into());
            }
            if idle > 1000 {
                return Err("Max idle connections cannot exceed 1000".into());
            }
        }

        let timeout = Duration::from_secs(timeout_secs.unwrap_or(30));

        // Build client with pool configuration
        let client_builder = Client::builder()
            .pool_max_idle_per_host(max_idle.unwrap_or(100))
            .pool_idle_timeout(Duration::from_secs(90))
            .connect_timeout(Duration::from_secs(10))
            .timeout(timeout);

        let client = client_builder.build()?;

        Ok(Self { client })
    }

    pub async fn execute_benchmark(
        &self,
        args: &Args,
        metrics: &MetricsCollector,
        pb: &ProgressBar,
        duration_secs: u64,
        total_requests: Option<u64>,
        start_time: Instant,
    ) -> Result<crate::metrics::BenchmarkResult, Box<dyn std::error::Error>> {
        metrics.start_tracking();

        let method = Method::from_bytes(args.method.to_uppercase().as_bytes())
            .map_err(|_| format!("Invalid HTTP method: {}", args.method))?;

        let url = args.url.clone();
        let request_body = args.request_body.clone();
        let headers = args.headers.clone();
        let timeout = Duration::from_secs(args.timeout);

        let duration = Duration::from_secs(duration_secs);
        let mut handles = vec![];

        // Spawn concurrent tasks
        for _ in 0..args.concurrency {
            let client = self.client.clone();
            let url = url.clone();
            let method = method.clone();
            let request_body = request_body.clone();
            let headers = headers.clone();
            let metrics = metrics.clone();
            let pb = pb.clone();
            let timeout = timeout;
            let start_time = start_time;
            let total_requests = total_requests;

            let handle = tokio::spawn(async move {
                let mut request_count = 0u64;

                loop {
                    // Check if we should stop
                    let elapsed = start_time.elapsed();
                    if total_requests.is_none() && elapsed >= duration {
                        break;
                    }
                    if let Some(total) = total_requests {
                        // Note: This is a simplified check. In production, you'd want
                        // a shared atomic counter for accurate total request counting
                        if elapsed >= duration {
                            break;
                        }
                    }

                    // Execute request
                    let request_start = Instant::now();
                    let bytes_sent = request_body.as_ref().map(|b| b.len()).unwrap_or(0);

                    let mut request_builder = match method {
                        Method::GET => client.get(&url),
                        Method::POST => client.post(&url),
                        Method::PUT => client.put(&url),
                        Method::DELETE => client.delete(&url),
                        Method::PATCH => client.patch(&url),
                        _ => client.request(method.clone(), &url),
                    };

                    // Add custom headers
                    for (key, value) in &headers {
                        request_builder = request_builder.header(key, value);
                    }

                    // Add body if provided
                    if let Some(body) = &request_body {
                        request_builder = request_builder.body(body.clone());
                    }

                    match request_builder.timeout(timeout).send().await {
                        Ok(response) => {
                            let status = response.status().as_u16();
                            let bytes_received = response.content_length().unwrap_or(0) as u64;
                            let duration = request_start.elapsed();

                            if status >= 200 && status < 400 {
                                metrics.record_success(duration, status, bytes_received, bytes_sent as u64);
                            } else {
                                metrics.record_success(duration, status, bytes_received, bytes_sent as u64);
                            }

                            pb.inc(1);
                            request_count += 1;
                        }
                        Err(e) => {
                            let error_type = if e.is_timeout() {
                                ErrorType::Timeout
                            } else if e.is_connect() {
                                ErrorType::Connection
                            } else {
                                ErrorType::Other
                            };
                            metrics.record_error(error_type);
                            pb.inc(1);
                            request_count += 1;
                        }
                    }
                }

                request_count
            });

            handles.push(handle);
        }

        // Wait for all tasks to complete
        for handle in handles {
            handle.await?;
        }

        let elapsed = start_time.elapsed();
        let pool_config = PoolConfig {
            pool_size: args.pool_size,
            max_idle: args.max_idle_connections,
            timeout_secs: args.connection_timeout,
        };

        Ok(metrics.get_result(elapsed, pool_config))
    }
}
