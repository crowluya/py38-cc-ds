use crate::error::{NotesError, Result};
use crate::semantic::{Embedder, EmbeddingStore};
use crate::types::{SemanticConfig, NoteMetadata};
use std::collections::HashMap;

/// Search result with similarity score
#[derive(Debug, Clone)]
pub struct SearchResult {
    /// Note metadata
    pub metadata: NoteMetadata,
    /// Similarity score (0.0 to 1.0)
    pub score: f32,
}

/// Semantic search engine
pub struct SemanticSearcher {
    embedder: Box<dyn Embedder>,
    store: EmbeddingStore,
    config: SemanticConfig,
}

impl SemanticSearcher {
    /// Create a new semantic searcher
    pub fn new(
        embedder: Box<dyn Embedder>,
        store: EmbeddingStore,
        config: SemanticConfig,
    ) -> Self {
        Self {
            embedder,
            store,
            config,
        }
    }

    /// Search for notes similar to the query
    pub async fn search(&self, query: &str, all_notes: &[NoteMetadata]) -> Result<Vec<SearchResult>> {
        // Generate embedding for query
        let query_embedding = self.embedder.embed(query).await?;

        // Calculate similarities
        let mut results = Vec::new();

        for note_metadata in all_notes {
            // Check if we have an embedding for this note
            if let Some(entry) = self.store.get(&note_metadata.id) {
                let similarity = cosine_similarity(&query_embedding, &entry.embedding);

                // Filter by threshold
                if similarity >= self.config.similarity_threshold {
                    results.push(SearchResult {
                        metadata: note_metadata.clone(),
                        score: similarity,
                    });
                }
            }
        }

        // Sort by similarity (highest first)
        results.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(std::cmp::Ordering::Equal));

        // Limit results
        results.truncate(self.config.max_results);

        Ok(results)
    }

    /// Search with custom limit
    pub async fn search_with_limit(
        &self,
        query: &str,
        all_notes: &[NoteMetadata],
        limit: usize,
    ) -> Result<Vec<SearchResult>> {
        let original_max = self.config.max_results;
        // Note: We'd need to make this mutable in the struct for a true implementation
        // For now, just truncate after search
        let mut results = self.search(query, all_notes).await?;
        results.truncate(limit);
        Ok(results)
    }

    /// Index a note (generate and store embedding)
    pub async fn index_note(&mut self, note_id: &str, content: &str) -> Result<()> {
        let content_hash = crate::semantic::store::compute_content_hash(content);

        // Check if already indexed and up to date
        if self.store.is_valid(note_id, &content_hash) {
            return Ok(());
        }

        // Generate embedding
        let embedding = self.embedder.embed(content).await?;

        // Store embedding
        self.store.upsert(note_id.to_string(), embedding, content_hash);

        Ok(())
    }

    /// Index multiple notes in batch
    pub async fn index_notes_batch(&mut self, notes: &[(String, String)]) -> Result<()> {
        if notes.is_empty() {
            return Ok(());
        }

        let contents: Vec<String> = notes.iter().map(|(_, c)| c.clone()).collect();
        let embeddings = self.embedder.embed_batch(&contents).await?;

        for ((note_id, content), embedding) in notes.iter().zip(embeddings.iter()) {
            let content_hash = crate::semantic::store::compute_content_hash(content);
            self.store.upsert(note_id.clone(), embedding.clone(), content_hash);
        }

        Ok(())
    }

    /// Remove a note from the index
    pub fn remove_note(&mut self, note_id: &str) {
        self.store.remove(note_id);
    }

    /// Save the index to disk
    pub fn save(&mut self) -> Result<()> {
        self.store.save()
    }

    /// Get the number of indexed notes
    pub fn indexed_count(&self) -> usize {
        self.store.len()
    }

    /// Check if a note is indexed
    pub fn is_indexed(&self, note_id: &str) -> bool {
        self.store.get(note_id).is_some()
    }
}

/// Calculate cosine similarity between two vectors
///
/// Returns a value between -1.0 and 1.0, where:
/// - 1.0 = identical direction (most similar)
/// - 0.0 = orthogonal (unrelated)
/// - -1.0 = opposite direction (opposite meaning)
pub fn cosine_similarity(a: &[f32], b: &[f32]) -> f32 {
    if a.len() != b.len() {
        panic!("Vectors must have same length");
    }

    let mut dot_product = 0.0_f32;
    let mut norm_a = 0.0_f32;
    let mut norm_b = 0.0_f32;

    for i in 0..a.len() {
        dot_product += a[i] * b[i];
        norm_a += a[i] * a[i];
        norm_b += b[i] * b[i];
    }

    let denominator = norm_a.sqrt() * norm_b.sqrt();

    if denominator == 0.0 {
        0.0
    } else {
        dot_product / denominator
    }
}

/// Calculate dot product (faster if vectors are normalized)
pub fn dot_product(a: &[f32], b: &[f32]) -> f32 {
    if a.len() != b.len() {
        panic!("Vectors must have same length");
    }

    a.iter()
        .zip(b.iter())
        .map(|(x, y)| x * y)
        .sum()
}

/// Calculate Euclidean distance between two vectors
pub fn euclidean_distance(a: &[f32], b: &[f32]) -> f32 {
    if a.len() != b.len() {
        panic!("Vectors must have same length");
    }

    a.iter()
        .zip(b.iter())
        .map(|(x, y)| (x - y).powi(2))
        .sum::<f32>()
        .sqrt()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cosine_similarity() {
        let a = vec![1.0, 2.0, 3.0];
        let b = vec![1.0, 2.0, 3.0];

        let sim = cosine_similarity(&a, &b);
        assert!((sim - 1.0).abs() < 0.001);

        let c = vec![-1.0, -2.0, -3.0];
        let sim_opp = cosine_similarity(&a, &c);
        assert!((sim_opp - (-1.0)).abs() < 0.001);

        let d = vec![0.0, 0.0, 0.0];
        let sim_zero = cosine_similarity(&a, &d);
        assert_eq!(sim_zero, 0.0);
    }

    #[test]
    fn test_dot_product() {
        let a = vec![1.0, 2.0, 3.0];
        let b = vec![2.0, 3.0, 4.0];

        let dp = dot_product(&a, &b);
        assert_eq!(dp, 20.0); // 1*2 + 2*3 + 3*4 = 20
    }

    #[test]
    fn test_euclidean_distance() {
        let a = vec![0.0, 0.0];
        let b = vec![3.0, 4.0];

        let dist = euclidean_distance(&a, &b);
        assert!((dist - 5.0).abs() < 0.001); // sqrt(3^2 + 4^2) = 5
    }
}
