use notes::types::Note;
use std::fs;
use tempfile::TempDir;

#[test]
fn test_note_lifecycle() {
    let temp_dir = TempDir::new().unwrap();
    let mut storage = notes::storage::Storage::new(temp_dir.path().to_path_buf()).unwrap();

    // Create a note
    let mut note = Note::new(
        "Test Note".to_string(),
        "This is test content".to_string(),
    );
    note.add_tag("test".to_string());
    note.add_tag("rust".to_string());

    // Save the note
    storage.save_note(&mut note).unwrap();

    // Load the note
    let loaded = storage.load_note(&note.id).unwrap();
    assert_eq!(loaded.title, "Test Note");
    assert_eq!(loaded.content, "This is test content");
    assert_eq!(loaded.tags.len(), 2);
    assert!(loaded.has_tag("test"));
    assert!(loaded.has_tag("rust"));

    // Update the note
    let mut loaded = storage.load_note(&note.id).unwrap();
    loaded.update_content("Updated content".to_string());
    storage.save_note(&mut loaded).unwrap();

    // Verify update
    let updated = storage.load_note(&note.id).unwrap();
    assert_eq!(updated.content, "Updated content");

    // List notes
    let notes = storage.list_notes().unwrap();
    assert_eq!(notes.len(), 1);
    assert_eq!(notes[0].title, "Test Note");

    // Search notes
    let results = storage.search_notes("Updated").unwrap();
    assert_eq!(results.len(), 1);

    // Filter by tag
    let tagged = storage.get_notes_by_tag("test").unwrap();
    assert_eq!(tagged.len(), 1);

    // Delete note
    storage.delete_note(&note.id).unwrap();
    let notes = storage.list_notes().unwrap();
    assert_eq!(notes.len(), 0);
}

#[test]
fn test_tag_operations() {
    let mut note = Note::new("Tag Test".to_string(), "Content".to_string());

    // Add tags
    note.add_tag("tag1".to_string());
    note.add_tag("tag2".to_string());
    assert_eq!(note.tags.len(), 2);

    // Don't add duplicate
    note.add_tag("tag1".to_string());
    assert_eq!(note.tags.len(), 2);

    // Remove tag
    assert!(note.remove_tag("tag1"));
    assert_eq!(note.tags.len(), 1);
    assert!(!note.has_tag("tag1"));

    // Try to remove non-existent tag
    assert!(!note.remove_tag("nonexistent"));
}

#[test]
fn test_slug_generation() {
    let note = Note::new("Hello World Test 123".to_string(), "Content".to_string());
    assert_eq!(note.slug(), "hello-world-test-123");
}

#[test]
fn test_multiple_notes_with_search() {
    let temp_dir = TempDir::new().unwrap();
    let mut storage = notes::storage::Storage::new(temp_dir.path().to_path_buf()).unwrap();

    // Create multiple notes
    let mut note1 = Note::new("Rust Programming".to_string(), "Learn Rust basics".to_string());
    note1.add_tag("rust".to_string());
    note1.add_tag("programming".to_string());
    storage.save_note(&mut note1).unwrap();

    let mut note2 = Note::new("Python Guide".to_string(), "Python tutorial".to_string());
    note2.add_tag("python".to_string());
    storage.save_note(&mut note2).unwrap();

    let mut note3 = Note::new("Rust Advanced".to_string(), "Advanced Rust concepts".to_string());
    note3.add_tag("rust".to_string());
    storage.save_note(&mut note3).unwrap();

    // List all
    let all = storage.list_notes().unwrap();
    assert_eq!(all.len(), 3);

    // Search for "Rust"
    let rust_notes = storage.search_notes("Rust").unwrap();
    assert_eq!(rust_notes.len(), 3); // Should match title and content

    // Filter by tag
    let rust_tagged = storage.get_notes_by_tag("rust").unwrap();
    assert_eq!(rust_tagged.len(), 2);

    let python_tagged = storage.get_notes_by_tag("python").unwrap();
    assert_eq!(python_tagged.len(), 1);
}

#[test]
fn test_note_metadata() {
    let note = Note::new("Metadata Test".to_string(), "Content".to_string());
    let metadata = notes::types::NoteMetadata::from(&note);

    assert_eq!(metadata.id, note.id);
    assert_eq!(metadata.title, note.title);
    assert_eq!(metadata.tags, note.tags);
}
