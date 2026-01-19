//! Streaming statistics for real-time analysis.

/// Streaming statistics calculator using Welford's online algorithm.
#[derive(Debug, Clone)]
pub struct StreamingStats {
    /// Number of samples
    count: u64,

    /// Running mean
    mean: f64,

    /// Running sum of squared differences from mean (M2)
    m2: f64,

    /// Minimum value
    min: f64,

    /// Maximum value
    max: f64,
}

impl StreamingStats {
    /// Create a new streaming statistics calculator.
    pub fn new() -> Self {
        Self {
            count: 0,
            mean: 0.0,
            m2: 0.0,
            min: f64::INFINITY,
            max: f64::NEG_INFINITY,
        }
    }

    /// Update with a new value.
    pub fn update(&mut self, value: f64) {
        self.count += 1;
        let delta = value - self.mean;
        self.mean += delta / self.count as f64;
        let delta2 = value - self.mean;
        self.m2 += delta * delta2;

        self.min = self.min.min(value);
        self.max = self.max.max(value);
    }

    /// Get the number of samples.
    pub fn count(&self) -> u64 {
        self.count
    }

    /// Get the mean (average).
    pub fn mean(&self) -> f64 {
        self.mean
    }

    /// Get the variance.
    pub fn variance(&self) -> f64 {
        if self.count < 2 {
            0.0
        } else {
            self.m2 / (self.count - 1) as f64
        }
    }

    /// Get the standard deviation.
    pub fn std_dev(&self) -> f64 {
        self.variance().sqrt()
    }

    /// Get the minimum value.
    pub fn min(&self) -> f64 {
        self.min
    }

    /// Get the maximum value.
    pub fn max(&self) -> f64 {
        self.max
    }

    /// Get the range (max - min).
    pub fn range(&self) -> f64 {
        self.max - self.min
    }

    /// Reset all statistics.
    pub fn reset(&mut self) {
        *self = Self::new();
    }
}

impl Default for StreamingStats {
    fn default() -> Self {
        Self::new()
    }
}

/// Exponential moving average for smoothing time series data.
#[derive(Debug, Clone)]
pub struct ExponentialMovingAverage {
    /// Current EMA value
    ema: f64,

    /// Smoothing factor (alpha)
    alpha: f64,

    /// Whether EMA has been initialized
    initialized: bool,
}

impl ExponentialMovingAverage {
    /// Create a new EMA with the given smoothing factor.
    ///
    /// # Arguments
    /// * `alpha` - Smoothing factor between 0.0 and 1.0.
    ///            Higher values give more weight to recent data.
    ///
    /// # Panics
    /// Panics if alpha is not between 0.0 and 1.0.
    pub fn new(alpha: f64) -> Self {
        assert!(alpha >= 0.0 && alpha <= 1.0, "alpha must be between 0.0 and 1.0");
        Self {
            ema: 0.0,
            alpha,
            initialized: false,
        }
    }

    /// Create an EMA with alpha calculated from the desired period.
    ///
    /// # Arguments
    /// * `period` - The number of periods to average over.
    pub fn with_period(period: u32) -> Self {
        let alpha = 2.0 / (period as f64 + 1.0);
        Self::new(alpha)
    }

    /// Update with a new value and return the new EMA.
    pub fn update(&mut self, value: f64) -> f64 {
        if !self.initialized {
            self.ema = value;
            self.initialized = true;
        } else {
            self.ema = self.alpha * value + (1.0 - self.alpha) * self.ema;
        }
        self.ema
    }

    /// Get the current EMA value.
    pub fn get(&self) -> Option<f64> {
        if self.initialized {
            Some(self.ema)
        } else {
            None
        }
    }

    /// Reset the EMA.
    pub fn reset(&mut self) {
        self.ema = 0.0;
        self.initialized = false;
    }
}

/// Sliding window for tracking recent values.
#[derive(Debug, Clone)]
pub struct SlidingWindow<T> {
    /// Circular buffer of values
    buffer: Vec<Option<T>>,

    /// Capacity of the window
    capacity: usize,

    /// Current write position
    write_pos: usize,

    /// Number of elements currently in the window
    len: usize,
}

impl<T: Clone> SlidingWindow<T> {
    /// Create a new sliding window with the given capacity.
    pub fn new(capacity: usize) -> Self {
        Self {
            buffer: vec![None; capacity],
            capacity,
            write_pos: 0,
            len: 0,
        }
    }

    /// Push a value into the window.
    pub fn push(&mut self, value: T) {
        self.buffer[self.write_pos] = Some(value);
        self.write_pos = (self.write_pos + 1) % self.capacity;
        self.len = self.len.min(self.capacity - 1) + 1;
    }

    /// Get the current number of elements in the window.
    pub fn len(&self) -> usize {
        self.len
    }

    /// Check if the window is empty.
    pub fn is_empty(&self) -> bool {
        self.len == 0
    }

    /// Check if the window is full.
    pub fn is_full(&self) -> bool {
        self.len == self.capacity
    }

    /// Get all values in the window in insertion order.
    pub fn values(&self) -> Vec<T> {
        let mut result = Vec::with_capacity(self.len);
        for i in 0..self.len {
            let pos = (self.write_pos - self.len + i + self.capacity) % self.capacity;
            if let Some(ref value) = self.buffer[pos] {
                result.push(value.clone());
            }
        }
        result
    }

    /// Clear the window.
    pub fn clear(&mut self) {
        self.buffer.fill(None);
        self.write_pos = 0;
        self.len = 0;
    }
}

impl<T: Clone + Copy> SlidingWindow<T> {
    /// Calculate statistics on numeric values in the window.
    pub fn stats(&self) -> Option<StreamingStats> {
        if self.is_empty() {
            return None;
        }

        let mut stats = StreamingStats::new();
        for value in self.values() {
            stats.update(value as f64);
        }
        Some(stats)
    }
}

/// Frequency counter for tracking occurrences of items.
#[derive(Debug, Clone)]
pub struct FrequencyCounter<T: Eq + std::hash::Hash> {
    /// Map of item to count
    counts: std::collections::HashMap<T, u64>,

    /// Total count of all items
    total: u64,
}

impl<T: Eq + std::hash::Hash> FrequencyCounter<T> {
    /// Create a new frequency counter.
    pub fn new() -> Self {
        Self {
            counts: std::collections::HashMap::new(),
            total: 0,
        }
    }

    /// Increment the count for an item.
    pub fn increment(&mut self, item: T) -> u64 {
        *self.counts.entry(item).or_insert(0) += 1;
        self.total += 1;
        *self.counts.get(&item).unwrap()
    }

    /// Get the count for a specific item.
    pub fn get(&self, item: &T) -> u64 {
        self.counts.get(item).copied().unwrap_or(0)
    }

    /// Get the total count of all items.
    pub fn total(&self) -> u64 {
        self.total
    }

    /// Get the number of unique items.
    pub fn unique_count(&self) -> usize {
        self.counts.len()
    }

    /// Get the frequency (proportion) for an item.
    pub fn frequency(&self, item: &T) -> f64 {
        if self.total == 0 {
            0.0
        } else {
            self.get(item) as f64 / self.total as f64
        }
    }

    /// Get the top N items by count.
    pub fn top_n(&self, n: usize) -> Vec<(&T, u64)> {
        let mut items: Vec<_> = self.counts.iter().map(|(k, v)| (k, *v)).collect();
        items.sort_by(|a, b| b.1.cmp(&a.1));
        items.into_iter().take(n).collect()
    }

    /// Clear all counts.
    pub fn clear(&mut self) {
        self.counts.clear();
        self.total = 0;
    }
}

impl<T: Eq + std::hash::Hash> Default for FrequencyCounter<T> {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_streaming_stats() {
        let mut stats = StreamingStats::new();
        stats.update(5.0);
        stats.update(7.0);
        stats.update(9.0);

        assert_eq!(stats.count(), 3);
        assert_eq!(stats.mean(), 7.0);
        assert!((stats.variance() - 4.0).abs() < 0.001);
    }

    #[test]
    fn test_ema() {
        let mut ema = ExponentialMovingAverage::with_period(5);
        let values = [1.0, 2.0, 3.0, 4.0, 5.0];

        for &value in &values {
            ema.update(value);
        }

        assert!(ema.get().is_some());
        let ema_value = ema.get().unwrap();
        assert!(ema_value > 1.0 && ema_value < 5.0);
    }

    #[test]
    fn test_sliding_window() {
        let mut window: SlidingWindow<i32> = SlidingWindow::new(3);

        assert!(window.is_empty());
        assert!(!window.is_full());

        window.push(1);
        window.push(2);
        window.push(3);

        assert!(!window.is_empty());
        assert!(window.is_full());
        assert_eq!(window.len(), 3);

        window.push(4);
        assert_eq!(window.len(), 3);
        assert_eq!(window.values(), vec![2, 3, 4]);
    }

    #[test]
    fn test_frequency_counter() {
        let mut counter = FrequencyCounter::new();

        counter.increment("a");
        counter.increment("b");
        counter.increment("a");

        assert_eq!(counter.get(&"a"), 2);
        assert_eq!(counter.get(&"b"), 1);
        assert_eq!(counter.total(), 3);
        assert_eq!(counter.unique_count(), 2);
        assert!((counter.frequency(&"a") - 0.666).abs() < 0.01);
    }
}
