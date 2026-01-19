//! Data generation for benchmarks
//!
//! Provides various data distributions for testing sorting algorithms:
//! - Random: Uniform distribution
//! - Sorted: Already sorted in ascending order
//! - Reverse sorted: Sorted in descending order
//! - Mostly sorted: 90% sorted, 10% random
//! - Duplicates: Only 10% unique values

use rand::Rng;

/// Data distribution types
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Distribution {
    Random,
    Sorted,
    ReverseSorted,
    MostlySorted,
    Duplicates,
}

impl Distribution {
    pub fn all() -> Vec<Distribution> {
        vec![
            Distribution::Random,
            Distribution::Sorted,
            Distribution::ReverseSorted,
            Distribution::MostlySorted,
            Distribution::Duplicates,
        ]
    }

    pub fn name(&self) -> &str {
        match self {
            Distribution::Random => "Random",
            Distribution::Sorted => "Sorted",
            Distribution::ReverseSorted => "Reverse Sorted",
            Distribution::MostlySorted => "Mostly Sorted",
            Distribution::Duplicates => "Duplicates",
        }
    }
}

/// Data generator for creating test datasets
pub struct DataGenerator {
    rng: rand::rngs::ThreadRng,
}

impl DataGenerator {
    pub fn new() -> Self {
        DataGenerator {
            rng: rand::thread_rng(),
        }
    }

    /// Generate a dataset of the specified size and distribution
    pub fn generate(&mut self, size: usize, distribution: Distribution) -> Vec<usize> {
        match distribution {
            Distribution::Random => self.random(size),
            Distribution::Sorted => self.sorted(size),
            Distribution::ReverseSorted => self.reverse_sorted(size),
            Distribution::MostlySorted => self.mostly_sorted(size),
            Distribution::Duplicates => self.duplicates(size),
        }
    }

    fn random(&mut self, size: usize) -> Vec<usize> {
        (0..size).map(|_| self.rng.gen_range(0..size * 10)).collect()
    }

    fn sorted(&mut self, size: usize) -> Vec<usize> {
        let mut data: Vec<usize> = (0..size).map(|_| self.rng.gen_range(0..size * 10)).collect();
        data.sort();
        data
    }

    fn reverse_sorted(&mut self, size: usize) -> Vec<usize> {
        let mut data: Vec<usize> = (0..size).map(|_| self.rng.gen_range(0..size * 10)).collect();
        data.sort();
        data.reverse();
        data
    }

    fn mostly_sorted(&mut self, size: usize) -> Vec<usize> {
        let mut data: Vec<usize> = (0..size).map(|_| self.rng.gen_range(0..size * 10)).collect();
        data.sort();

        // Scramble 10% of the elements
        let scramble_count = size / 10;
        for _ in 0..scramble_count {
            let i = self.rng.gen_range(0..size);
            let j = self.rng.gen_range(0..size);
            data.swap(i, j);
        }

        data
    }

    fn duplicates(&mut self, size: usize) -> Vec<usize> {
        // Only 10% unique values
        let unique_count = (size / 10).max(1);
        (0..size).map(|_| self.rng.gen_range(0..unique_count)).collect()
    }
}

impl Default for DataGenerator {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_random_generation() {
        let mut gen = DataGenerator::new();
        let data = gen.generate(100, Distribution::Random);
        assert_eq!(data.len(), 100);
        // Random data shouldn't be sorted
        let is_sorted = data.windows(2).all(|w| w[0] <= w[1]);
        assert!(!is_sorted || data.len() <= 1); // Might be sorted by chance
    }

    #[test]
    fn test_sorted_generation() {
        let mut gen = DataGenerator::new();
        let data = gen.generate(100, Distribution::Sorted);
        assert_eq!(data.len(), 100);
        assert!(data.windows(2).all(|w| w[0] <= w[1]));
    }

    #[test]
    fn test_reverse_sorted_generation() {
        let mut gen = DataGenerator::new();
        let data = gen.generate(100, Distribution::ReverseSorted);
        assert_eq!(data.len(), 100);
        assert!(data.windows(2).all(|w| w[0] >= w[1]));
    }

    #[test]
    fn test_mostly_sorted_generation() {
        let mut gen = DataGenerator::new();
        let data = gen.generate(100, Distribution::MostlySorted);
        assert_eq!(data.len(), 100);
        // Should have some disorder but not completely random
        let sorted_count = data.windows(2).filter(|w| w[0] <= w[1]).count();
        assert!(sorted_count > 50); // At least 50% in order
    }

    #[test]
    fn test_duplicates_generation() {
        let mut gen = DataGenerator::new();
        let data = gen.generate(100, Distribution::Duplicates);
        assert_eq!(data.len(), 100);
        // Count unique values
        let unique_count = data.iter().collect::<std::collections::HashSet<_>>().len();
        assert!(unique_count <= 15); // Should have relatively few unique values
    }

    #[test]
    fn test_empty_generation() {
        let mut gen = DataGenerator::new();
        let data = gen.generate(0, Distribution::Random);
        assert!(data.is_empty());
    }

    #[test]
    fn test_single_element() {
        let mut gen = DataGenerator::new();
        let data = gen.generate(1, Distribution::Random);
        assert_eq!(data.len(), 1);
    }
}
