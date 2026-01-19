# Contributing to Sort Bench

Thank you for your interest in contributing to Sort Bench! This document provides guidelines for contributing to the project.

## Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd sort_bench
   ```

2. **Build the project**
   ```bash
   cargo build
   ```

3. **Run tests**
   ```bash
   cargo test
   ```

4. **Run the CLI**
   ```bash
   cargo run -- --help
   ```

## Code Style

This project follows standard Rust conventions:

- Use `cargo fmt` for formatting
- Use `cargo clippy` for linting
- Follow Rust API guidelines
- Document all public APIs with doc comments

## Running Examples

```bash
# Run the basic usage example
cargo run --example basic_usage
```

## Adding New Sorting Algorithms

To add a new sorting algorithm:

1. **Implement the algorithm** in `src/algorithms.rs`:

```rust
pub struct MySort;

impl<T: Ord + Copy> Sorter<T> for MySort {
    fn sort(&self, data: &mut [T]) {
        // Your implementation here
    }
}

pub fn mysort<T: Ord + Copy>(data: &mut [T]) {
    MySort.sort(data);
}
```

2. **Add to Algorithm enum** in `src/benchmark.rs`:

```rust
pub enum Algorithm {
    // ... existing algorithms
    MySort,
}

impl Algorithm {
    pub fn name(&self) -> &str {
        match self {
            // ... existing cases
            Algorithm::MySort => "MySort",
        }
    }
}
```

3. **Add to BenchmarkRunner** in `src/benchmark.rs`:

```rust
fn sort_with_algorithm(&self, algorithm: Algorithm, data: &mut [usize]) {
    match algorithm {
        // ... existing cases
        Algorithm::MySort => MySort.sort(data),
    }
}
```

4. **Add CLI parsing** in `src/main.rs`:

```rust
"mysort" | "my" => Algorithm::MySort,
```

5. **Add tests** in `src/algorithms.rs`:

```rust
#[test]
fn test_mysort() {
    let mut data = vec![64, 34, 25, 12, 22, 11, 90];
    mysort(&mut data);
    assert!(verify_sorted(&data));
}
```

## Adding New Data Distributions

To add a new data distribution:

1. **Add to Distribution enum** in `src/data_gen.rs`:

```rust
pub enum Distribution {
    // ... existing distributions
    MyDistribution,
}
```

2. **Implement generation** in `src/data_gen.rs`:

```rust
pub fn generate(&mut self, size: usize, distribution: Distribution) -> Vec<usize> {
    match distribution {
        // ... existing cases
        Distribution::MyDistribution => self.my_distribution(size),
    }
}

fn my_distribution(&mut self, size: usize) -> Vec<usize> {
    // Your implementation here
}
```

3. **Add CLI parsing** in `src/main.rs`:

```rust
"mydist" => Distribution::MyDistribution,
```

## Testing Guidelines

- **Unit Tests**: Test individual functions and algorithms
- **Integration Tests**: Test complete workflows
- **Edge Cases**: Test empty arrays, single elements, duplicates
- **Correctness**: Verify sorting correctness
- **Performance**: Ensure algorithms meet expected complexity

Run tests with:
```bash
# All tests
cargo test

# Specific test
cargo test test_quicksort

# With output
cargo test -- --nocapture

# Show test names
cargo test -- --test-threads=1
```

## Documentation

- Add doc comments to all public items
- Include examples in doc comments
- Update README.md for user-facing changes
- Update this file for development changes

## Submitting Changes

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Pull Request Guidelines

- Describe what your PR does
- Reference related issues
- Include screenshots for UI changes
- Add/update tests as needed
- Update documentation
- Ensure all tests pass

## Areas for Contribution

Looking for ideas? Here are some areas where contributions would be valuable:

### Algorithms
- Introsort (hybrid quicksort/heapsort)
- Timsort (adaptive, stable)
- Smoothsort
- Bubble sort (for comparison)
- Insertion sort (for small arrays)
- Selection sort
- Shell sort
- Counting sort (for small integer ranges)
- Bucket sort
- Parallel/concurrent sorting variants

### Features
- Support for generic types beyond integers
- Stability testing and reporting
- Memory usage tracking
- Custom comparator support
- Multi-threaded benchmarking
- Export results to CSV/JSON
- Import datasets from files
- Interactive mode with live updates
- Web-based visualization

### Improvements
- Optimize existing algorithms
- Better visualization options
- More data distributions
- Configurable pivot selection for quicksort
- Iterative versions to avoid stack overflow
- SIMD optimizations where applicable

### Documentation
- More examples
- Performance analysis blog posts
- Algorithm explanations
- Video tutorials
- Translation to other languages

## Questions?

Feel free to open an issue for discussion before starting work on a significant change.

## Code of Conduct

Be respectful, constructive, and inclusive. We're all here to learn and build something great together.
