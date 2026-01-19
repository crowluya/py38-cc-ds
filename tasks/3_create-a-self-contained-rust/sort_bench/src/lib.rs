//! Sort Bench - A sorting algorithm benchmarking library
//!
//! This library provides implementations of various sorting algorithms
//! along with benchmarking and visualization capabilities.

pub mod algorithms;
pub mod data_gen;
pub mod benchmark;
pub mod charts;

pub use algorithms::{quicksort, mergesort, heapsort, radix_sort};
pub use data_gen::{Distribution, DataGenerator};
pub use benchmark::{BenchmarkRunner, BenchmarkResult};
pub use charts::{ChartRenderer, VisualizationStyle};

/// Re-export common types
pub type SortResult<T> = Result<Vec<T>, String>;
