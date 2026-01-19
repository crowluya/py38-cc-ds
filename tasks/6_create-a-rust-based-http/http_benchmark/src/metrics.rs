use crate::percentile::PercentileCalculator;
use crate::rate_tracker::RateTracker;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use std::sync::Mutex;
use std::time::Duration;

/// Thread-safe metrics collector
#[derive(Clone)]
pub struct MetricsCollector {
    inner: Arc<Mutex<MetricsData>>,
}

struct MetricsData {
    response_times: PercentileCalculator,
    rate_tracker: RateTracker,
    status_codes: HashMap<u16, u64>,
    total_bytes_received: u64,
    total_bytes_sent: u64,
    success_count: u64,
    error_count: u64,
    connection_errors: u64,
    timeout_errors: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BenchmarkResult {
    pub duration: Duration,
    pub total_requests: u64,
    pub successful_requests: u64,
    pub failed_requests: u64,
    pub requests_per_second: f64,
    pub bytes_received: u64,
    pub bytes_sent: u64,
    pub response_times: ResponseTimeMetrics,
    pub status_codes: HashMap<u16, u64>,
    pub errors: ErrorMetrics,
    pub rps_history: Vec<(f64, f64)>,
    pub pool_config: PoolConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResponseTimeMetrics {
    pub min: f64,
    pub max: f64,
    pub mean: f64,
    pub std_dev: f64,
    pub p50: f64,
    pub p95: f64,
    pub p99: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ErrorMetrics {
    pub connection_errors: u64,
    pub timeout_errors: u64,
    pub other_errors: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PoolConfig {
    pub pool_size: Option<usize>,
    pub max_idle: Option<usize>,
    pub timeout_secs: Option<u64>,
}

impl MetricsCollector {
    pub fn new() -> Self {
        Self {
            inner: Arc::new(Mutex::new(MetricsData {
                response_times: PercentileCalculator::new(10000),
                rate_tracker: RateTracker::new(1, 300), // 1-second buckets, keep 5 minutes
                status_codes: HashMap::new(),
                total_bytes_received: 0,
                total_bytes_sent: 0,
                success_count: 0,
                error_count: 0,
                connection_errors: 0,
                timeout_errors: 0,
            })),
        }
    }

    pub fn start_tracking(&self) {
        let mut data = self.inner.lock().unwrap();
        data.rate_tracker.start();
    }

    pub fn record_success(&self, duration: Duration, status_code: u16, bytes_received: u64, bytes_sent: u64) {
        let mut data = self.inner.lock().unwrap();
        let duration_ms = duration.as_secs_f64() * 1000.0;
        data.response_times.add_sample(duration_ms);
        data.rate_tracker.record_request();
        *data.status_codes.entry(status_code).or_insert(0) += 1;
        data.total_bytes_received += bytes_received;
        data.total_bytes_sent += bytes_sent;
        data.success_count += 1;
    }

    pub fn record_error(&self, error_type: ErrorType) {
        let mut data = self.inner.lock().unwrap();
        data.rate_tracker.record_request();
        data.error_count += 1;

        match error_type {
            ErrorType::Connection => data.connection_errors += 1,
            ErrorType::Timeout => data.timeout_errors += 1,
            ErrorType::Other => {}
        }
    }

    pub fn get_result(&self, total_duration: Duration, pool_config: PoolConfig) -> BenchmarkResult {
        let data = self.inner.lock().unwrap();

        let response_times = ResponseTimeMetrics {
            min: data.response_times.min(),
            max: data.response_times.max(),
            mean: data.response_times.mean(),
            std_dev: data.response_times.std_dev(),
            p50: data.response_times.p50(),
            p95: data.response_times.p95(),
            p99: data.response_times.p99(),
        };

        let other_errors = data.error_count - data.connection_errors - data.timeout_errors;

        BenchmarkResult {
            duration: total_duration,
            total_requests: data.success_count + data.error_count,
            successful_requests: data.success_count,
            failed_requests: data.error_count,
            requests_per_second: data.rate_tracker.average_rps(),
            bytes_received: data.total_bytes_received,
            bytes_sent: data.total_bytes_sent,
            response_times,
            status_codes: data.status_codes.clone(),
            errors: ErrorMetrics {
                connection_errors: data.connection_errors,
                timeout_errors: data.timeout_errors,
                other_errors,
            },
            rps_history: data.rate_tracker.rps_history(),
            pool_config,
        }
    }
}

pub enum ErrorType {
    Connection,
    Timeout,
    Other,
}
