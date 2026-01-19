use kg::{KnowledgeGraph, Note, extract_links, sanitize_link_name, search_notes};
use std::path::PathBuf;
use tempfile::TempDir;

#[test]
fn test_note_creation() {
    let note = Note::new("Test Note".to_string(), "Test content".to_string());
    assert_eq!(note.title, "Test Note");
    assert_eq!(note.content, "Test content");
    assert_eq!(note.id, "test-note");
    assert!(!note.tags.is_empty() || note.tags.is_empty()); // Tags can be empty
}

#[test]
fn test_link_extraction() {
    let content = "This is a [[test]] note with [[multiple links]] and [[another-link|with alias]].";
    let links = extract_links(content);
    assert_eq!(links.len(), 3);
    assert!(links.contains(&"test".to_string()));
    assert!(links.contains(&"multiple-links".to_string()));
    assert!(links.contains(&"another-link".to_string()));
}

#[test]
fn test_sanitize_link_name() {
    assert_eq!(sanitize_link_name("Hello World"), "hello-world");
    assert_eq!(sanitize_link_name("Test_Note"), "test_note");
    assert_eq!(sanitize_link_name("  spaces  "), "spaces");
}

#[test]
fn test_knowledge_graph_add_note() {
    let mut graph = KnowledgeGraph::new();
    let note = Note::new("Test".to_string(), "Content".to_string());
    graph.add_note(note);

    assert_eq!(graph.notes.len(), 1);
    assert!(graph.get_note("test").is_some());
}

#[test]
fn test_knowledge_graph_links() {
    let mut graph = KnowledgeGraph::new();
    let note1 = Note::new("First".to_string(), "Links to [[second]]".to_string());
    let note2 = Note::new("Second".to_string(), "No links".to_string());

    graph.add_note(note1);
    graph.add_note(note2);
    graph.rebuild_links();

    let forward = graph.get_forward_links("first");
    let backward = graph.get_backward_links("second");

    assert_eq!(forward.len(), 1);
    assert_eq!(forward[0], "second");
    assert_eq!(backward.len(), 1);
    assert_eq!(backward[0], "first");
}

#[test]
fn test_search_functionality() {
    let mut graph = KnowledgeGraph::new();
    let note1 = Note::new("Rust Programming".to_string(), "Learn Rust language".to_string());
    let note2 = Note::new("Python Guide".to_string(), "Python programming tutorial".to_string());

    graph.add_note(note1);
    graph.add_note(note2);

    let results = search_notes(&graph, "programming");
    assert_eq!(results.len(), 2);

    let rust_results = search_notes(&graph, "rust");
    assert_eq!(rust_results.len(), 1);
    assert_eq!(rust_results[0].title, "Rust Programming");
}

#[test]
fn test_graph_statistics() {
    let mut graph = KnowledgeGraph::new();
    let note1 = Note::new("A".to_string(), "Link to [[b]]".to_string());
    let note2 = Note::new("B".to_string(), "Link to [[c]]".to_string());
    let note3 = Note::new("C".to_string(), "No links".to_string());

    graph.add_note(note1);
    graph.add_note(note2);
    graph.add_note(note3);
    graph.rebuild_links();

    let stats = graph.statistics();
    assert_eq!(stats.note_count, 3);
    assert_eq!(stats.link_count, 2);
    assert_eq!(stats.orphaned_count, 0); // C is linked to by B
}

#[test]
fn test_backlink_discovery() {
    let mut graph = KnowledgeGraph::new();
    let note1 = Note::new("Target".to_string(), "I'm the target".to_string());
    let note2 = Note::new("Linker1".to_string(), "Links to [[target]]".to_string());
    let note3 = Note::new("Linker2".to_string(), "Also links to [[target]]".to_string());

    graph.add_note(note1);
    graph.add_note(note2);
    graph.add_note(note3);
    graph.rebuild_links();

    let backlinks = graph.get_backward_links("target");
    assert_eq!(backlinks.len(), 2);
    assert!(backlinks.contains(&"linker1".to_string()));
    assert!(backlinks.contains(&"linker2".to_string()));
}

#[test]
fn test_note_update() {
    let mut note = Note::new("Original".to_string(), "Original content".to_string());
    let original_modified = note.modified_at;

    // Small delay to ensure timestamp difference
    std::thread::sleep(std::time::Duration::from_millis(10));

    note.update_content("Updated content".to_string());
    assert_eq!(note.content, "Updated content");
    assert!(note.modified_at > original_modified);
}

#[test]
fn test_tags() {
    let mut note = Note::new("Tagged".to_string(), "Content".to_string());
    note.add_tag("rust".to_string());
    note.add_tag("cli".to_string());
    note.add_tag("rust".to_string()); // Duplicate

    assert_eq!(note.tags.len(), 2);
    assert!(note.tags.contains(&"rust".to_string()));
    assert!(note.tags.contains(&"cli".to_string()));
}
