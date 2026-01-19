use std::collections::VecDeque;

/// Efficient percentile calculator using reservoir sampling for large datasets
pub struct PercentileCalculator {
    samples: VecDeque<f64>,
    max_samples: usize,
}

impl PercentileCalculator {
    /// Create a new percentile calculator with a maximum sample size
    pub fn new(max_samples: usize) -> Self {
        Self {
            samples: VecDeque::with_capacity(max_samples),
            max_samples,
        }
    }

    /// Add a response time sample
    pub fn add_sample(&mut self, value: f64) {
        if self.samples.len() < self.max_samples {
            self.samples.push_back(value);
        } else {
            // Reservoir sampling: replace random element with probability 1/n
            use std::ops::Index;
            let idx = rand::random::<usize>() % self.samples.len();
            self.samples[idx] = value;
        }
    }

    /// Calculate percentile from the samples (0.0 to 1.0)
    pub fn calculate(&self, percentile: f64) -> f64 {
        if self.samples.is_empty() {
            return 0.0;
        }

        let mut sorted: Vec<f64> = self.samples.iter().cloned().collect();
        sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());

        let idx = ((sorted.len() - 1) as f64 * percentile) as usize;
        sorted[idx]
    }

    /// Get p50 (median)
    pub fn p50(&self) -> f64 {
        self.calculate(0.50)
    }

    /// Get p95
    pub fn p95(&self) -> f64 {
        self.calculate(0.95)
    }

    /// Get p99
    pub fn p99(&self) -> f64 {
        self.calculate(0.99)
    }

    /// Get minimum value
    pub fn min(&self) -> f64 {
        self.samples.iter().cloned().fold(f64::INFINITY, f64::min)
    }

    /// Get maximum value
    pub fn max(&self) -> f64 {
        self.samples.iter().cloned().fold(f64::NEG_INFINITY, f64::max)
    }

    /// Calculate mean
    pub fn mean(&self) -> f64 {
        if self.samples.is_empty() {
            return 0.0;
        }
        let sum: f64 = self.samples.iter().sum();
        sum / self.samples.len() as f64
    }

    /// Calculate standard deviation
    pub fn std_dev(&self) -> f64 {
        if self.samples.len() < 2 {
            return 0.0;
        }

        let mean = self.mean();
        let variance: f64 = self
            .samples
            .iter()
            .map(|&x| (x - mean).powi(2))
            .sum::<f64>()
            / (self.samples.len() - 1) as f64;

        variance.sqrt()
    }

    /// Get number of samples
    pub fn count(&self) -> usize {
        self.samples.len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_percentiles() {
        let mut calc = PercentileCalculator::new(100);

        // Add known values
        for i in 1..=100 {
            calc.add_sample(i as f64);
        }

        assert!((calc.p50() - 50.0).abs() < 2.0);
        assert!((calc.p95() - 95.0).abs() < 2.0);
        assert!((calc.p99() - 99.0).abs() < 2.0);
    }

    #[test]
    fn test_min_max() {
        let mut calc = PercentileCalculator::new(10);
        calc.add_sample(10.0);
        calc.add_sample(50.0);
        calc.add_sample(100.0);

        assert_eq!(calc.min(), 10.0);
        assert_eq!(calc.max(), 100.0);
    }

    #[test]
    fn test_mean() {
        let mut calc = PercentileCalculator::new(10);
        calc.add_sample(10.0);
        calc.add_sample(20.0);
        calc.add_sample(30.0);

        assert_eq!(calc.mean(), 20.0);
    }

    #[test]
    fn test_std_dev() {
        let mut calc = PercentileCalculator::new(10);
        calc.add_sample(2.0);
        calc.add_sample(4.0);
        calc.add_sample(4.0);
        calc.add_sample(4.0);
        calc.add_sample(5.0);
        calc.add_sample(5.0);
        calc.add_sample(7.0);
        calc.add_sample(9.0);

        let std_dev = calc.std_dev();
        assert!(std_dev > 2.0 && std_dev < 2.1);
    }
}
