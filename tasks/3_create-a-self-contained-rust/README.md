# Task Workspace

Task #3: Create a self-contained Rust CLI tool that benchma

## Summary
- Priority: THOUGHT
- Project: None
- Created: 2026-01-19T09:39:48.844826

## Description
Create a self-contained Rust CLI tool that benchmarks and compares different sorting algorithms (quicksort, mergesort, heapsort, radix sort) with visual ASCII charts showing performance characteristics across various input sizes and data distributions.

## Plan & Analysis
This is a **fresh workspace** - the project needs to be built from scratch. Here's my analysis:

---

## Executive Summary
Build a Rust CLI benchmarking tool from scratch that implements and compares four sorting algorithms (quicksort, mergesort, heapsort, radix sort) across multiple input sizes and data distributions, with ASCII chart visualization of performance results.

---

## Analysis of the Task

The task requires creating a complete Rust project with:

1. **Sorting Algorithm Implementations**: Four classic O(n log n) algorithms plus linear-time radix sort
2. **Benchmarking Framework**: Timing mechanism to measure execution across different scenarios
3. **Test Data Generation**: Various data distributions (random, sorted, reverse-sorted, mostly sorted, duplicates)
4. **CLI Interface**: Command-line arguments to control benchmark parameters
5. **ASCII Visualization**: Charts showing performance comparisons
6. **Project Structure**: Proper Rust crate layout with dependencies

---

## Structured TODO List

### Phase 1: Project Setup (3 items)

1. **[Easy]** Initialize Rust project with `cargo new` and set up `Cargo.toml` with necessary dependencies (clap for CLI, rand for data generation)
2. **[Easy]** Create project module structure: main.rs, lib.rs, algorithms module, benchmarks module, charts module
3. **[Easy]** Set up basic CLI argument parsing with clap (input sizes, algorithms to test, data distribution types)

### Phase 2: Sorting Algorithms (4 items)

4. **[Medium]** Implement quicksort algorithm with median-of-three pivot selection
5. **[Medium]** Implement mergesort algorithm (top-down or bottom-up)
6. **[Medium]** Implement heapsort algorithm with heap construction
7. **[Medium]** Implement radix sort (LSD base-10 for integers)

### Phase 3: Data Generation (1 item)

8. **[Medium]** Create data generator module with functions for: random, sorted ascending, sorted descending, mostly sorted (90% sorted), duplicate-heavy (10% unique values)

### Phase 4: Benchmarking Framework (2 items)

9. **[Medium]** Implement benchmark runner that measures execution time using `std::time::Instant` across multiple runs for statistical significance
10. **[Medium]** Create result aggregation structure to store timing data by algorithm, input size, and distribution type

### Phase 5: ASCII Charts (2 items)

11. **[Hard]** Design and implement ASCII bar chart renderer showing time comparisons (horizontal bars with scaling)
12. **[Hard]** Create comparative table view with algorithms as rows and input sizes/distributions as columns

### Phase 6: CLI Integration & Output (3 items)

13. **[Medium]** Wire up CLI arguments to benchmark runner (select algorithms, specify input sizes like [100, 1000, 10000, 100000])
14. **[Medium]** Format and display results with clear headers, labels, and units (milliseconds/microseconds)
15. **[Easy]** Add usage help text and error handling for invalid inputs

### Phase 7: Testing & Polish (3 items)

16. **[Easy]** Add unit tests verifying each algorithm correctly sorts test arrays
17. **[Medium]** Add integration tests for edge cases (empty array, single element, already sorted)
18. **[Easy]** Create README with usage examples and build instructions

---

## Notes on Approach and Strategy

### Architecture Design
- **Library + Binary Structure**: Put algorithms in `src/lib.rs` for testability, CLI in `src/main.rs`
- **Trait-Based Design**: Define a `Sorter` trait for consistent interface across algorithms
- **Immutable Data**: Clone input arrays for each algorithm to ensure fair comparisons

### Performance Considerations
- **Warm-up Runs**: Discard first few runs to account for JIT/cache effects
- **Multiple Runs**: Take median or average of 5-10 runs per configuration
- **Memory Management**: Reuse allocations where possible to avoid allocation overhead in timing

### ASCII Chart Strategy
- **Horizontal Bars**: Easier to read than vertical for algorithm names
- **Auto-scaling**: Normalize to largest value with clear units (ms/μs)
- **Color/Style**: Use Unicode box-drawing characters for cleaner output

### Data Distributions
- **Random**: Uniform distribution (baseline)
- **Sorted**: Best case for some algorithms, worst for others
- **Reverse-sorted**: Worst case for naive quicksort
- **Mostly sorted**: Realistic scenario
- **Duplicate-heavy**: Tests stability and comparison handling

---

## Assumptions & Potential Blockers

### Assumptions
1. Target data type: `usize` or `i32` (integers for radix sort compatibility)
2. Input sizes: Powers of 10 or 2 (100, 1000, 10000, 100000, 1000000)
3. Benchmarking on same machine, no cross-platform timing normalization needed
4. Single-threaded execution (no parallel sorting)

### Potential Blockers
1. **Radix Sort Limitations**: Only works on integers; may need separate handling for floats or generic types
2. **Stack Overflow**: Recursive algorithms (quicksort, mergesort) may need optimization for large inputs
3. **Terminal Width**: ASCII charts may break on narrow terminals; need dynamic sizing
4. **Timing Precision**: Small arrays (<100 elements) may need high-resolution timers or more runs

### Recommended Rust Dependencies
```toml
[dependencies]
clap = { version = "4.5", features = ["derive"] }
rand = "0.8"
```

---

## Effort Estimates
- **Total TODO Items**: 18
- **Estimated Total Time**: 6-10 hours
- **Critical Path**: Items 4-7 (algorithms) → Item 9 (benchmarking) → Items 11-12 (charts)
- **Parallelizable**: Items 4-8 can be developed somewhat independently

## TODO List
(Updated by worker agent)

## Status: COMPLETE

## Outstanding Items
(None)

## Recommendations
(None)

## Execution Summary

### Execution 2026-01-19 09:54:05
- Status: ✅ COMPLETED
- Files Modified: 27
- Duration: 856s

## Execution Summary
