# Quick Start Guide

Get started with Sort Bench in 5 minutes!

## Installation

```bash
# Clone or navigate to the project
cd sort_bench

# Build the project
cargo build --release

# The binary is now at: ./target/release/sort_bench
```

## Your First Benchmark

Run a quick benchmark with default settings:

```bash
cargo run --release
```

This will test all algorithms (Quicksort, Mergesort, Heapsort, Radix Sort) with:
- Input sizes: 100, 1000, 10000, 100000
- All distributions: Random, Sorted, Reverse Sorted, Mostly Sorted, Duplicates
- Visualizations: Summary + Bar Charts + Tables

## Common Use Cases

### Quick Comparison

```bash
# Compare quicksort vs radixsort on random data
cargo run --release -- --algorithms quicksort,radix --distributions random --sizes 1000,10000,100000
```

### Stress Test

```bash
# Large input sizes
cargo run --release -- --sizes 100000,1000000 --distributions random,reverse
```

### Educational Demo

```bash
# Small sizes with all visualizations
cargo run --release -- --sizes 10,50,100 --style all
```

### Performance Investigation

```bash
# How do algorithms handle sorted data?
cargo run --release -- --distributions sorted --sizes 1000,10000,100000
```

## Understanding the Output

### Summary Section
Shows which algorithm is fastest/slowest for each configuration with speedup calculations.

### Bar Charts
Visual comparison with horizontal bars (█) showing relative performance.

### Tables
Detailed breakdown of timing data grouped by algorithm or input size.

## Tips

1. **Start small**: Use sizes 100-1000 for quick tests
2. **Focus**: Use `--algorithms` and `--distributions` to narrow scope
3. **Compare**: Use `--style bars` for visual comparison
4. **Details**: Use `--style table` for detailed data
5. **Release mode**: Always use `--release` for accurate benchmarks

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check [examples/basic_usage.rs](examples/basic_usage.rs) for programmatic usage
- See [CONTRIBUTING.md](CONTRIBUTING.md) to add new features

## Troubleshooting

**Build fails?**
```bash
# Update Rust
rustup update

# Clean and rebuild
cargo clean
cargo build --release
```

**Tests fail?**
```bash
# Run tests with output
cargo test -- --nocapture

# Check specific test
cargo test test_quicksort
```

Need help? Open an issue on GitHub!
