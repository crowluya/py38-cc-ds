//! Basic usage example of the sort_bench library
//!
//! This example demonstrates how to use the sorting algorithms
//! and benchmarking framework programmatically.

use sort_bench::{
    algorithms::{quicksort, mergesort, heapsort, radix_sort},
    data_gen::{DataGenerator, Distribution},
    benchmark::{BenchmarkRunner, Algorithm},
};

fn main() {
    println!("Sort Bench - Basic Usage Example\n");

    // Example 1: Using sorting algorithms directly
    println!("=== Example 1: Direct Algorithm Usage ===");
    let mut data = vec![64, 34, 25, 12, 22, 11, 90];
    println!("Original: {:?}", data);

    quicksort(&mut data);
    println!("Quicksort: {:?}\n", data);

    // Example 2: Different data distributions
    println!("=== Example 2: Data Distributions ===");
    let mut gen = DataGenerator::new();

    let random_data = gen.generate(10, Distribution::Random);
    println!("Random: {:?}", random_data);

    let sorted_data = gen.generate(10, Distribution::Sorted);
    println!("Sorted: {:?}", sorted_data);

    let reverse_data = gen.generate(10, Distribution::ReverseSorted);
    println!("Reverse Sorted: {:?}", reverse_data);

    // Example 3: Benchmarking a single algorithm
    println!("\n=== Example 3: Single Benchmark ===");
    let runner = BenchmarkRunner::default_settings();
    let test_data = gen.generate(1000, Distribution::Random);
    let result = runner.run_benchmark(Algorithm::QuickSort, &test_data);

    println!("Algorithm: {}", result.algorithm.name());
    println!("Size: {}", result.size);
    println!("Time: {}", result.format_time());
    println!("Runs: {}", result.runs);

    // Example 4: Comparing all algorithms
    println!("\n=== Example 4: Algorithm Comparison ===");
    let algorithms = Algorithm::all();
    let sizes = vec![100, 1000];
    let distributions = vec![Distribution::Random];

    let results = runner.run_suite(&algorithms, &sizes, &distributions);

    for result in &results.results {
        println!(
            "{} ({}): {}",
            result.algorithm.name(),
            result.size,
            result.format_time()
        );
    }

    println!("\nAll examples completed successfully!");
}
