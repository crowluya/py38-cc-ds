# Sort Bench 🔨⚡

A comprehensive Rust CLI tool for benchmarking and comparing sorting algorithms with beautiful ASCII visualizations.

## Features

- **Multiple Sorting Algorithms**: Quicksort, Mergesort, Heapsort, and Radix Sort
- **Various Data Distributions**: Random, sorted, reverse-sorted, mostly sorted, and duplicate-heavy datasets
- **Flexible Input Sizes**: Test with any array size from 1 to millions of elements
- **ASCII Visualizations**: Bar charts, tables, and summary views
- **Statistical Rigor**: Warmup runs and multiple measurements with median calculation
- **Easy CLI Interface**: Simple command-line arguments with sensible defaults

## Installation

### Prerequisites

- Rust 1.70 or later
- Cargo (comes with Rust)

### Build from Source

```bash
cd sort_bench
cargo build --release
```

The compiled binary will be available at `target/release/sort_bench`.

### Install System-Wide

```bash
cargo install --path .
```

## Usage

### Basic Usage

Run with default settings (100, 1000, 10000, 100000 elements, all algorithms, all distributions):

```bash
cargo run --release
```

Or if installed:

```bash
sort_bench
```

### Command-Line Options

```bash
sort_bench [OPTIONS]

OPTIONS:
    -s, --sizes <SIZE>              Input sizes to benchmark [default: 100,1000,10000,100000]
    -a, --algorithms <ALGORITHM>    Algorithms: quicksort,mergesort,heapsort,radix [default: all]
    -d, --distributions <DIST>      Distributions: random,sorted,reverse,mostly,duplicates [default: all]
    -y, --style <STYLE>             Visualization: bars,table,summary,all [default: all]
        --warmup-runs <COUNT>       Warmup runs (discarded) [default: 3]
        --measured-runs <COUNT>     Measured runs (median used) [default: 5]
        --bar-width <WIDTH>         Max bar width for charts [default: 40]
    -h, --help                      Print help information
    -V, --version                   Print version information
```

### Examples

#### Benchmark specific sizes

```bash
sort_bench --sizes 1000,10000,50000,100000
```

#### Compare only two algorithms

```bash
sort_bench --algorithms quicksort,mergesort
```

#### Test specific data distributions

```bash
sort_bench --distributions random,sorted,reverse
```

#### Show only bar charts

```bash
sort_bench --style bars
```

#### Show only detailed tables

```bash
sort_bench --style table
```

#### Custom benchmark settings

```bash
sort_bench --sizes 10000,100000 --algorithms quicksort,radix --warmup-runs 5 --measured-runs 10
```

#### Quick test with small sizes

```bash
sort_bench --sizes 10,100,1000 --distributions random --style bars
```

## Output Examples

### Summary View

```
╔══════════════════════════════════════════════════════════════╗
║                    SORT BENCHMARK TOOL                       ║
╚══════════════════════════════════════════════════════════════╝

Configuration:
  Input sizes: [100, 1000, 10000, 100000]
  Algorithms: ["QuickSort", "MergeSort", "HeapSort", "RadixSort"]
  Distributions: ["Random", "Sorted", "Reverse Sorted", "Mostly Sorted", "Duplicates"]
  Warmup runs: 3
  Measured runs: 5

Starting benchmarks...
...
```

### Bar Chart Visualization

```
10000 elements (Random)
======================

QuickSort   │████████████████████████████████████  245.32 μs
RadixSort   │████████████████  145.21 μs
MergeSort   │████████████████████  198.45 μs
HeapSort    │███████████████████  178.93 μs
```

### Performance Summary

```
Size: 10000
----------
  Random:
    Fastest: RadixSort (145.21 μs)
    Slowest: QuickSort (245.32 μs)
    Speedup: 1.69x

  Sorted:
    Fastest: RadixSort (98.34 μs)
    Slowest: QuickSort (312.45 μs)
    Speedup: 3.18x
```

## Sorting Algorithms

### Quicksort
- **Average**: O(n log n)
- **Best**: O(n log n)
- **Worst**: O(n²) - mitigated with median-of-three pivot selection
- **Space**: O(log n) - in-place with recursion stack
- **Notes**: Uses median-of-three pivot selection to avoid worst-case scenarios

### Mergesort
- **Average**: O(n log n)
- **Best**: O(n log n)
- **Worst**: O(n log n)
- **Space**: O(n) - requires auxiliary array
- **Notes**: Stable sort, consistent performance regardless of input

### Heapsort
- **Average**: O(n log n)
- **Best**: O(n log n)
- **Worst**: O(n log n)
- **Space**: O(1) - truly in-place
- **Notes**: Consistent performance, minimal memory usage

### Radix Sort
- **Average**: O(nk) where k is number of digits
- **Best**: O(nk)
- **Worst**: O(nk)
- **Space**: O(n)
- **Notes**: Only works on integers, can be faster than comparison sorts for certain data

## Data Distributions

### Random
Uniform random distribution - the baseline for comparison.

### Sorted
Already sorted in ascending order - best case for some algorithms, worst for naive quicksort.

### Reverse Sorted
Sorted in descending order - stress test for comparison-based algorithms.

### Mostly Sorted
90% sorted with 10% random elements - simulates real-world partially ordered data.

### Duplicates
Only 10% unique values - tests handling of repeated elements.

## Implementation Details

### Benchmarking Methodology

1. **Warmup Runs**: 3 discarded runs to account for CPU cache and branch prediction effects
2. **Measured Runs**: 5 timed runs with median value used for reporting
3. **Fair Comparison**: Each algorithm sorts a fresh copy of the same data
4. **Precision**: High-resolution timing using `std::time::Instant`

### Visualization

- **Bar Charts**: Horizontal bars auto-scaled to fastest algorithm
- **Tables**: Detailed breakdowns grouped by algorithm or input size
- **Summary**: Highlights fastest/slowest with speedup calculations

## Project Structure

```
sort_bench/
├── Cargo.toml           # Project configuration
├── README.md            # This file
└── src/
    ├── main.rs          # CLI application
    ├── lib.rs           # Library exports
    ├── algorithms.rs    # Sorting algorithm implementations
    ├── data_gen.rs      # Data generation for benchmarks
    ├── benchmark.rs     # Benchmarking framework
    └── charts.rs        # ASCII visualization
```

## Running Tests

```bash
# Run all tests
cargo test

# Run with output
cargo test -- --nocapture

# Run specific test
cargo test test_quicksort
```

The project includes comprehensive unit tests for:
- Sorting algorithm correctness
- Edge cases (empty arrays, single elements, duplicates)
- Data generation
- Benchmark timing
- Chart rendering

## Performance Tips

1. **Start Small**: Begin with small sizes to verify correctness
2. **Adjust Runs**: Increase `--measured-runs` for more stable results on small inputs
3. **Filter Algorithms**: Use `--algorithms` to focus on specific implementations
4. **Choose Distribution**: `--distributions random` gives baseline performance
5. **Release Mode**: Always use `cargo run --release` for accurate benchmarks

## Troubleshooting

### Stack Overflow on Large Inputs

For very large inputs (>1,000,000), recursive algorithms may hit stack limits. Increase stack size:

```bash
cargo run --release -- -Z unstable-options --stack-size=$((64 * 1024 * 1024))
```

Or use iterative versions of the algorithms.

### Inconsistent Results

For small inputs (<100 elements), timing may be inconsistent. Increase measured runs:

```bash
sort_bench --measured-runs 20
```

### Terminal Width Issues

If bar charts overflow, reduce bar width:

```bash
sort_bench --bar-width 30
```

## License

This project is provided as-is for educational and benchmarking purposes.

## Contributing

Contributions are welcome! Areas for improvement:

- Add more sorting algorithms (introsort, timsort, smoothsort)
- Parallel sorting implementations
- Support for floating-point numbers
- Export results to CSV/JSON
- Interactive mode with real-time visualization

## Author

Created as a comprehensive benchmarking tool for understanding sorting algorithm performance characteristics.
