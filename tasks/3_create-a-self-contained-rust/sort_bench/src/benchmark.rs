//! Benchmarking framework for sorting algorithms
//!
//! Provides timing and result aggregation for benchmarking runs.

use std::time::{Duration, Instant};
use crate::algorithms::{Sorter, QuickSort, MergeSort, HeapSort, RadixSort};
use crate::data_gen::{Distribution, DataGenerator};

/// Algorithm types for benchmarking
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Algorithm {
    QuickSort,
    MergeSort,
    HeapSort,
    RadixSort,
}

impl Algorithm {
    pub fn all() -> Vec<Algorithm> {
        vec![
            Algorithm::QuickSort,
            Algorithm::MergeSort,
            Algorithm::HeapSort,
            Algorithm::RadixSort,
        ]
    }

    pub fn name(&self) -> &str {
        match self {
            Algorithm::QuickSort => "QuickSort",
            Algorithm::MergeSort => "MergeSort",
            Algorithm::HeapSort => "HeapSort",
            Algorithm::RadixSort => "RadixSort",
        }
    }
}

/// Result of a single benchmark run
#[derive(Debug, Clone)]
pub struct BenchmarkResult {
    pub algorithm: Algorithm,
    pub size: usize,
    pub distribution: Distribution,
    pub time: Duration,
    pub runs: usize,
}

impl BenchmarkResult {
    /// Format the time as a human-readable string
    pub fn format_time(&self) -> String {
        let nanos = self.time.as_nanos();
        if nanos < 1_000 {
            format!("{} ns", nanos)
        } else if nanos < 1_000_000 {
            format!("{:.2} μs", nanos as f64 / 1_000.0)
        } else if nanos < 1_000_000_000 {
            format!("{:.2} ms", nanos as f64 / 1_000_000.0)
        } else {
            format!("{:.2} s", self.time.as_secs_f64())
        }
    }

    /// Get time in microseconds for comparison
    pub fn time_micros(&self) -> f64 {
        self.time.as_nanos() as f64 / 1_000.0
    }
}

/// Aggregated results for visualization
#[derive(Debug, Clone)]
pub struct AggregatedResults {
    pub results: Vec<BenchmarkResult>,
}

impl AggregatedResults {
    pub fn new() -> Self {
        AggregatedResults {
            results: Vec::new(),
        }
    }

    pub fn add_result(&mut self, result: BenchmarkResult) {
        self.results.push(result);
    }

    /// Filter results by algorithm
    pub fn by_algorithm(&self, algorithm: Algorithm) -> Vec<&BenchmarkResult> {
        self.results.iter()
            .filter(|r| r.algorithm == algorithm)
            .collect()
    }

    /// Filter results by distribution
    pub fn by_distribution(&self, distribution: Distribution) -> Vec<&BenchmarkResult> {
        self.results.iter()
            .filter(|r| r.distribution == distribution)
            .collect()
    }

    /// Filter results by size
    pub fn by_size(&self, size: usize) -> Vec<&BenchmarkResult> {
        self.results.iter()
            .filter(|r| r.size == size)
            .collect()
    }
}

impl Default for AggregatedResults {
    fn default() -> Self {
        Self::new()
    }
}

/// Benchmark runner for executing sorting algorithm benchmarks
pub struct BenchmarkRunner {
    warmup_runs: usize,
    measured_runs: usize,
}

impl BenchmarkRunner {
    /// Create a new benchmark runner
    ///
    /// # Arguments
    /// * `warmup_runs` - Number of warmup runs (discarded from timing)
    /// * `measured_runs` - Number of measured runs (median is used)
    pub fn new(warmup_runs: usize, measured_runs: usize) -> Self {
        BenchmarkRunner {
            warmup_runs,
            measured_runs,
        }
    }

    /// Create a benchmark runner with default settings
    pub fn default_settings() -> Self {
        BenchmarkRunner::new(3, 5)
    }

    /// Run benchmarks for a single configuration
    pub fn run_benchmark(
        &self,
        algorithm: Algorithm,
        data: &[usize],
    ) -> BenchmarkResult {
        let size = data.len();
        let distribution = Distribution::Random; // We don't track this in the data itself

        // Warmup runs (not timed)
        for _ in 0..self.warmup_runs {
            let mut data_copy = data.to_vec();
            self.sort_with_algorithm(algorithm, &mut data_copy);
        }

        // Measured runs
        let mut times: Vec<Duration> = Vec::with_capacity(self.measured_runs);
        for _ in 0..self.measured_runs {
            let mut data_copy = data.to_vec();
            let start = Instant::now();
            self.sort_with_algorithm(algorithm, &mut data_copy);
            let elapsed = start.elapsed();
            times.push(elapsed);
        }

        // Use median time
        times.sort();
        let median_time = times[times.len() / 2];

        BenchmarkResult {
            algorithm,
            size,
            distribution,
            time: median_time,
            runs: self.measured_runs,
        }
    }

    /// Run benchmarks across multiple configurations
    pub fn run_suite(
        &self,
        algorithms: &[Algorithm],
        sizes: &[usize],
        distributions: &[Distribution],
    ) -> AggregatedResults {
        let mut results = AggregatedResults::new();
        let mut gen = DataGenerator::new();

        for &size in sizes {
            for &distribution in distributions {
                println!("Generating {} elements ({})...", size, distribution.name());
                let data = gen.generate(size, distribution);

                for &algorithm in algorithms {
                    let result = self.run_benchmark(algorithm, &data);
                    println!("  {} - {}", algorithm.name(), result.format_time());
                    results.add_result(result);
                }
            }
        }

        results
    }

    fn sort_with_algorithm(&self, algorithm: Algorithm, data: &mut [usize]) {
        match algorithm {
            Algorithm::QuickSort => QuickSort.sort(data),
            Algorithm::MergeSort => MergeSort.sort(data),
            Algorithm::HeapSort => HeapSort.sort(data),
            Algorithm::RadixSort => RadixSort.sort(data),
        }
    }
}

impl Default for BenchmarkRunner {
    fn default() -> Self {
        Self::default_settings()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_benchmark_runner() {
        let runner = BenchmarkRunner::new(1, 2);
        let data = vec![5, 3, 1, 4, 2];
        let result = runner.run_benchmark(Algorithm::QuickSort, &data);

        assert_eq!(result.algorithm, Algorithm::QuickSort);
        assert_eq!(result.size, 5);
        assert_eq!(result.runs, 2);
    }

    #[test]
    fn test_aggregated_results() {
        let mut results = AggregatedResults::new();
        let result = BenchmarkResult {
            algorithm: Algorithm::QuickSort,
            size: 100,
            distribution: Distribution::Random,
            time: Duration::from_millis(10),
            runs: 5,
        };
        results.add_result(result.clone());

        let quicksort_results = results.by_algorithm(Algorithm::QuickSort);
        assert_eq!(quicksort_results.len(), 1);
        assert_eq!(quicksort_results[0].algorithm, Algorithm::QuickSort);
    }

    #[test]
    fn test_time_formatting() {
        let result = BenchmarkResult {
            algorithm: Algorithm::QuickSort,
            size: 100,
            distribution: Distribution::Random,
            time: Duration::from_nanos(500),
            runs: 5,
        };
        assert_eq!(result.format_time(), "500 ns");

        let result2 = BenchmarkResult {
            algorithm: Algorithm::QuickSort,
            size: 100,
            distribution: Distribution::Random,
            time: Duration::from_micros(1500),
            runs: 5,
        };
        assert_eq!(result2.format_time(), "1.50 μs");

        let result3 = BenchmarkResult {
            algorithm: Algorithm::QuickSort,
            size: 100,
            distribution: Distribution::Random,
            time: Duration::from_millis(1500),
            runs: 5,
        };
        assert_eq!(result3.format_time(), "1500.00 ms");
    }
}
