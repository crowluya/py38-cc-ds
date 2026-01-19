//! Sorting algorithm implementations
//!
//! This module provides implementations of various sorting algorithms:
//! - Quicksort with median-of-three pivot selection
//! - Mergesort (top-down)
//! - Heapsort
//! - Radix sort (LSD base-10)

use std::cmp::Ordering;

/// Sorter trait for consistent interface across algorithms
pub trait Sorter<T: Ord + Copy> {
    fn sort(&self, data: &mut [T]);
}

/// Quicksort with median-of-three pivot selection
pub struct QuickSort;

impl<T: Ord + Copy> Sorter<T> for QuickSort {
    fn sort(&self, data: &mut [T]) {
        if data.len() <= 1 {
            return;
        }
        quicksort_helper(data, 0, data.len() - 1);
    }
}

fn quicksort_helper<T: Ord + Copy>(data: &mut [T], low: usize, high: usize) {
    if low < high {
        let pivot_index = partition(data, low, high);
        if pivot_index > 0 {
            quicksort_helper(data, low, pivot_index - 1);
        }
        quicksort_helper(data, pivot_index + 1, high);
    }
}

fn partition<T: Ord + Copy>(data: &mut [T], low: usize, high: usize) -> usize {
    // Median-of-three pivot selection
    let mid = low + (high - low) / 2;
    let pivot = median_of_three(data[low], data[mid], data[high]);

    // Move pivot to the end
    let mut pivot_index = high;
    if data[low] == pivot {
        pivot_index = low;
    } else if data[mid] == pivot {
        pivot_index = mid;
    }
    data.swap(pivot_index, high);

    // Partition
    let mut i = low;
    for j in low..high {
        if data[j] <= pivot {
            data.swap(i, j);
            i += 1;
        }
    }
    data.swap(i, high);
    i
}

fn median_of_three<T: Ord>(a: T, b: T, c: T) -> T {
    if a <= b {
        if b <= c {
            b
        } else if a <= c {
            c
        } else {
            a
        }
    } else {
        if a <= c {
            a
        } else if b <= c {
            c
        } else {
            b
        }
    }
}

/// Convenience function for quicksort
pub fn quicksort<T: Ord + Copy>(data: &mut [T]) {
    QuickSort.sort(data);
}

/// Mergesort (top-down implementation)
pub struct MergeSort;

impl<T: Ord + Copy> Sorter<T> for MergeSort {
    fn sort(&self, data: &mut [T]) {
        if data.len() <= 1 {
            return;
        }
        let mut temp = Vec::with_capacity(data.len());
        temp.resize(data.len(), data[0]);
        mergesort_helper(data, &mut temp, 0, data.len() - 1);
    }
}

fn mergesort_helper<T: Ord + Copy>(data: &mut [T], temp: &mut [T], left: usize, right: usize) {
    if left < right {
        let mid = left + (right - left) / 2;
        mergesort_helper(data, temp, left, mid);
        mergesort_helper(data, temp, mid + 1, right);
        merge(data, temp, left, mid, right);
    }
}

fn merge<T: Ord + Copy>(data: &mut [T], temp: &mut [T], left: usize, mid: usize, right: usize) {
    let mut i = left;
    let mut j = mid + 1;
    let mut k = left;

    while i <= mid && j <= right {
        if data[i] <= data[j] {
            temp[k] = data[i];
            i += 1;
        } else {
            temp[k] = data[j];
            j += 1;
        }
        k += 1;
    }

    while i <= mid {
        temp[k] = data[i];
        i += 1;
        k += 1;
    }

    while j <= right {
        temp[k] = data[j];
        j += 1;
        k += 1;
    }

    for k in left..=right {
        data[k] = temp[k];
    }
}

/// Convenience function for mergesort
pub fn mergesort<T: Ord + Copy>(data: &mut [T]) {
    MergeSort.sort(data);
}

/// Heapsort implementation
pub struct HeapSort;

impl<T: Ord + Copy> Sorter<T> for HeapSort {
    fn sort(&self, data: &mut [T]) {
        if data.len() <= 1 {
            return;
        }
        let n = data.len();

        // Build max heap
        for i in (0..n / 2).rev() {
            heapify(data, n, i);
        }

        // Extract elements from heap one by one
        for end in (1..n).rev() {
            data.swap(0, end);
            heapify(data, end, 0);
        }
    }
}

fn heapify<T: Ord + Copy>(data: &mut [T], n: usize, i: usize) {
    let mut largest = i;
    let left = 2 * i + 1;
    let right = 2 * i + 2;

    if left < n && data[left] > data[largest] {
        largest = left;
    }

    if right < n && data[right] > data[largest] {
        largest = right;
    }

    if largest != i {
        data.swap(i, largest);
        heapify(data, n, largest);
    }
}

/// Convenience function for heapsort
pub fn heapsort<T: Ord + Copy>(data: &mut [T]) {
    HeapSort.sort(data);
}

/// Radix sort (LSD base-10) for unsigned integers
pub struct RadixSort;

impl Sorter<usize> for RadixSort {
    fn sort(&self, data: &mut [usize]) {
        if data.len() <= 1 {
            return;
        }

        // Find the maximum number to know number of digits
        let max = *data.iter().max().unwrap();

        // Do counting sort for every digit
        let mut exp = 1;
        while max / exp > 0 {
            counting_sort_by_digit(data, exp);
            exp *= 10;
        }
    }
}

fn counting_sort_by_digit(data: &mut [usize], exp: usize) {
    let n = data.len();
    let mut output = vec![0; n];
    let mut count = [0usize; 10];

    // Store count of occurrences
    for &num in data.iter() {
        let digit = (num / exp) % 10;
        count[digit] += 1;
    }

    // Change count[i] so it contains actual position of this digit in output
    for i in 1..10 {
        count[i] += count[i - 1];
    }

    // Build output array (traverse from right to left for stability)
    for i in (0..n).rev() {
        let digit = (data[i] / exp) % 10;
        count[digit] -= 1;
        output[count[digit]] = data[i];
    }

    // Copy output back to data
    data.copy_from_slice(&output);
}

/// Convenience function for radix sort
pub fn radix_sort(data: &mut [usize]) {
    RadixSort.sort(data);
}

#[cfg(test)]
mod tests {
    use super::*;

    fn verify_sorted<T: Ord>(data: &[T]) -> bool {
        data.windows(2).all(|w| w[0] <= w[1])
    }

    #[test]
    fn test_quicksort() {
        let mut data = vec![64, 34, 25, 12, 22, 11, 90];
        quicksort(&mut data);
        assert!(verify_sorted(&data));
        assert_eq!(data, vec![11, 12, 22, 25, 34, 64, 90]);
    }

    #[test]
    fn test_mergesort() {
        let mut data = vec![64, 34, 25, 12, 22, 11, 90];
        mergesort(&mut data);
        assert!(verify_sorted(&data));
        assert_eq!(data, vec![11, 12, 22, 25, 34, 64, 90]);
    }

    #[test]
    fn test_heapsort() {
        let mut data = vec![64, 34, 25, 12, 22, 11, 90];
        heapsort(&mut data);
        assert!(verify_sorted(&data));
        assert_eq!(data, vec![11, 12, 22, 25, 34, 64, 90]);
    }

    #[test]
    fn test_radix_sort() {
        let mut data: Vec<usize> = vec![64, 34, 25, 12, 22, 11, 90];
        radix_sort(&mut data);
        assert!(verify_sorted(&data));
        assert_eq!(data, vec![11, 12, 22, 25, 34, 64, 90]);
    }

    #[test]
    fn test_empty_array() {
        let mut data: Vec<i32> = vec![];
        quicksort(&mut data);
        assert!(data.is_empty());
    }

    #[test]
    fn test_single_element() {
        let mut data = vec![42];
        quicksort(&mut data);
        assert_eq!(data, vec![42]);
    }

    #[test]
    fn test_already_sorted() {
        let mut data = vec![1, 2, 3, 4, 5];
        quicksort(&mut data);
        assert_eq!(data, vec![1, 2, 3, 4, 5]);
    }

    #[test]
    fn test_reverse_sorted() {
        let mut data = vec![5, 4, 3, 2, 1];
        quicksort(&mut data);
        assert_eq!(data, vec![1, 2, 3, 4, 5]);
    }

    #[test]
    fn test_duplicates() {
        let mut data = vec![3, 1, 4, 1, 5, 9, 2, 6, 5, 3];
        quicksort(&mut data);
        assert_eq!(data, vec![1, 1, 2, 3, 3, 4, 5, 5, 6, 9]);
    }
}
