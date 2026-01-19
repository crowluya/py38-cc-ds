use std::collections::VecDeque;

/// Tracks request rate over time using time-bucketed approach
pub struct RateTracker {
    buckets: VecDeque<RateBucket>,
    bucket_duration: std::time::Duration,
    max_buckets: usize,
    start_time: Option<std::time::Instant>,
}

struct RateBucket {
    timestamp: std::time::Instant,
    count: u64,
}

impl RateTracker {
    /// Create a new rate tracker
    pub fn new(bucket_duration_secs: u64, max_buckets: usize) -> Self {
        Self {
            buckets: VecDeque::with_capacity(max_buckets),
            bucket_duration: std::time::Duration::from_secs(bucket_duration_secs),
            max_buckets,
            start_time: None,
        }
    }

    /// Start tracking
    pub fn start(&mut self) {
        self.start_time = Some(std::time::Instant::now());
        self.add_bucket();
    }

    /// Record a request
    pub fn record_request(&mut self) {
        let now = std::time::Instant::now();

        // Check if we need a new bucket
        if let Some(last_bucket) = self.buckets.back() {
            if now.duration_since(last_bucket.timestamp) >= self.bucket_duration {
                self.add_bucket();
            }
        } else {
            self.add_bucket();
        }

        // Increment current bucket count
        if let Some(bucket) = self.buckets.back_mut() {
            bucket.count += 1;
        }
    }

    /// Add a new time bucket
    fn add_bucket(&mut self) {
        let now = std::time::Instant::now();

        self.buckets.push_back(RateBucket { timestamp: now, count: 0 });

        // Remove old buckets if we exceed max
        while self.buckets.len() > self.max_buckets {
            self.buckets.pop_front();
        }
    }

    /// Get current RPS (requests per second)
    pub fn current_rps(&self) -> f64 {
        if let Some(bucket) = self.buckets.back() {
            if bucket.count > 0 {
                return bucket.count as f64 / self.bucket_duration.as_secs_f64();
            }
        }
        0.0
    }

    /// Get average RPS over all buckets
    pub fn average_rps(&self) -> f64 {
        if self.buckets.is_empty() {
            return 0.0;
        }

        let total_requests: u64 = self.buckets.iter().map(|b| b.count).sum();
        let elapsed = self.elapsed().as_secs_f64();

        if elapsed > 0.0 {
            total_requests as f64 / elapsed
        } else {
            0.0
        }
    }

    /// Get peak RPS
    pub fn peak_rps(&self) -> f64 {
        self.buckets
            .iter()
            .map(|b| b.count as f64 / self.bucket_duration.as_secs_f64())
            .fold(0.0_f64, f64::max)
    }

    /// Get elapsed time since start
    pub fn elapsed(&self) -> std::time::Duration {
        self.start_time
            .map(|t| t.elapsed())
            .unwrap_or_default()
    }

    /// Get RPS history for graphing
    pub fn rps_history(&self) -> Vec<(f64, f64)> {
        self.buckets
            .iter()
            .enumerate()
            .map(|(i, bucket)| {
                let time_offset = i as f64 * self.bucket_duration.as_secs_f64();
                let rps = bucket.count as f64 / self.bucket_duration.as_secs_f64();
                (time_offset, rps)
            })
            .collect()
    }

    /// Get total request count
    pub fn total_requests(&self) -> u64 {
        self.buckets.iter().map(|b| b.count).sum()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::thread;
    use std::time::Duration;

    #[test]
    fn test_rate_tracking() {
        let mut tracker = RateTracker::new(1, 10);
        tracker.start();

        // Record some requests
        for _ in 0..10 {
            tracker.record_request();
        }

        assert_eq!(tracker.total_requests(), 10);
        assert!(tracker.current_rps() > 0.0);
    }

    #[test]
    fn test_peak_rps() {
        let mut tracker = RateTracker::new(1, 10);
        tracker.start();

        // First bucket: 5 requests
        for _ in 0..5 {
            tracker.record_request();
        }

        thread::sleep(Duration::from_millis(1100));

        // Second bucket: 10 requests (should be peak)
        for _ in 0..10 {
            tracker.record_request();
        }

        let peak = tracker.peak_rps();
        assert!(peak >= 10.0);
    }
}
