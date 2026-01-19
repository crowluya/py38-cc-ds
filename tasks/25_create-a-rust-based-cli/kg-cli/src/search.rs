use crate::types::{KnowledgeGraph, SearchResult};
use std::collections::HashMap;

/// Search notes in the knowledge graph
pub fn search_notes(graph: &KnowledgeGraph, query: &str) -> Vec<SearchResult> {
    if query.is_empty() {
        return Vec::new();
    }

    let query_lower = query.to_lowercase();
    let mut results = Vec::new();

    for (note_id, note) in &graph.notes {
        let score = calculate_relevance(&query_lower, note);
        if score > 0.0 {
            let matched_lines = find_matching_lines(&query_lower, &note.content);
            results.push(SearchResult::new(
                note_id.clone(),
                note.title.clone(),
                score,
                matched_lines,
            ));
        }
    }

    // Sort by score (descending)
    results.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap());

    results
}

/// Calculate relevance score for a note
fn calculate_relevance(query: &str, note: &crate::types::Note) -> f64 {
    let mut score = 0.0;

    // Title match (highest weight)
    if note.title.to_lowercase().contains(query) {
        score += 10.0;
        if note.title.to_lowercase() == query {
            score += 20.0; // Exact title match bonus
        }
    }

    // Content matches
    let content_lower = note.content.to_lowercase();
    let content_matches = content_lower.matches(query).count();
    score += content_matches as f64 * 1.0;

    // Tag matches
    for tag in &note.tags {
        if tag.to_lowercase().contains(query) {
            score += 5.0;
        }
    }

    score
}

/// Find lines in content that match the query
fn find_matching_lines(query: &str, content: &str) -> Vec<String> {
    let mut matched_lines = Vec::new();

    for line in content.lines() {
        if line.to_lowercase().contains(query) {
            // Truncate long lines
            let truncated = if line.len() > 100 {
                format!("{}...", &line[..100])
            } else {
                line.to_string()
            };
            matched_lines.push(truncated);
        }
    }

    matched_lines.truncate(5); // Limit to 5 matches
    matched_lines
}

/// Fuzzy search using simple substring matching with tolerance
pub fn fuzzy_search(graph: &KnowledgeGraph, query: &str) -> Vec<SearchResult> {
    if query.is_empty() || query.len() < 2 {
        return Vec::new();
    }

    let query_lower = query.to_lowercase();
    let mut results = Vec::new();

    for (note_id, note) in &graph.notes {
        let score = fuzzy_relevance(&query_lower, note);
        if score > 0.0 {
            let matched_lines = find_matching_lines(&query_lower, &note.content);
            results.push(SearchResult::new(
                note_id.clone(),
                note.title.clone(),
                score,
                matched_lines,
            ));
        }
    }

    results.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap());
    results
}

/// Calculate fuzzy relevance score
fn fuzzy_relevance(query: &str, note: &crate::types::Note) -> f64 {
    let mut score = 0.0;

    // Check for subsequence matches in title
    if is_subsequence(query, &note.title.to_lowercase()) {
        score += 8.0;
    }

    // Check for subsequence matches in content
    let content_lower = note.content.to_lowercase();
    for line in content_lower.lines() {
        if is_subsequence(query, line) {
            score += 0.5;
        }
    }

    score
}

/// Check if query is a subsequence of text (characters appear in order)
fn is_subsequence(query: &str, text: &str) -> bool {
    let mut query_chars = query.chars().peekable();
    let mut text_chars = text.chars();

    while let Some(qc) = query_chars.peek() {
        loop {
            match text_chars.next() {
                Some(tc) if tc == *qc => {
                    query_chars.next();
                    break;
                }
                Some(_) => continue,
                None => return false,
            }
        }
    }

    true
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::Note;
    use chrono::Utc;

    #[test]
    fn test_search_by_title() {
        let note = Note::new("Test Note".to_string(), "Some content".to_string());
        let mut graph = crate::types::KnowledgeGraph::new();
        graph.add_note(note);

        let results = search_notes(&graph, "test");
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].title, "Test Note");
    }

    #[test]
    fn test_search_by_content() {
        let note = Note::new("Random".to_string(), "The word test appears here".to_string());
        let mut graph = crate::types::KnowledgeGraph::new();
        graph.add_note(note);

        let results = search_notes(&graph, "test");
        assert_eq!(results.len(), 1);
    }

    #[test]
    fn test_empty_query() {
        let graph = crate::types::KnowledgeGraph::new();
        let results = search_notes(&graph, "");
        assert_eq!(results.len(), 0);
    }

    #[test]
    fn test_is_subsequence() {
        assert!(is_subsequence("test", "this is a test string"));
        assert!(is_subsequence("tst", "test"));
        assert!(!is_subsequence("abc", "def"));
    }
}
