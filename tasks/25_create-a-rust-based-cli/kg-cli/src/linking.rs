use regex::Regex;

/// Extract all [[note_name]] links from note content
pub fn extract_links(content: &str) -> Vec<String> {
    let link_regex = Regex::new(r"\[\[([^\]]+)\]\]").unwrap();
    let mut links = Vec::new();

    for capture in link_regex.captures_iter(content) {
        if let Some(link) = capture.get(1) {
            let link_text = link.as_str().trim();
            // Handle [[link|alias]] syntax
            let note_name = if let Some(pos) = link_text.find('|') {
                &link_text[..pos]
            } else {
                link_text
            };
            // Convert to filename format
            let note_id = sanitize_link_name(note_name);
            links.push(note_id);
        }
    }

    // Remove duplicates while preserving order
    links.sort();
    links.dedup();
    links
}

/// Convert a link name to filename format (lowercase, hyphens for spaces)
pub fn sanitize_link_name(name: &str) -> String {
    name.to_lowercase()
        .chars()
        .map(|c| {
            if c.is_alphanumeric() || c == '-' || c == '_' {
                c
            } else if c.is_whitespace() {
                '-'
            } else {
                '_'
            }
        })
        .collect::<String>()
        .trim_matches('-')
        .to_string()
}

/// Validate if a link reference exists (check if note exists)
pub fn validate_link(link: &str, existing_notes: &[String]) -> bool {
    let sanitized = sanitize_link_name(link);
    existing_notes.contains(&sanitized)
}

/// Find broken links in content (links to non-existent notes)
pub fn find_broken_links(content: &str, existing_notes: &[String]) -> Vec<String> {
    let links = extract_links(content);
    links
        .into_iter()
        .filter(|link| !existing_notes.contains(link))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_basic_links() {
        let content = "This is a note with a [[link]] to another note.";
        let links = extract_links(content);
        assert_eq!(links, vec!["link"]);
    }

    #[test]
    fn test_extract_multiple_links() {
        let content = "[[first]] and [[second]] and [[third]]";
        let links = extract_links(content);
        assert_eq!(links, vec!["first", "second", "third"]);
    }

    #[test]
    fn test_extract_link_with_alias() {
        let content = "Check out [[my-note|My Great Note]] for more info";
        let links = extract_links(content);
        assert_eq!(links, vec!["my-note"]);
    }

    #[test]
    fn test_sanitize_link_name() {
        assert_eq!(sanitize_link_name("My Note"), "my-note");
        assert_eq!(sanitize_link_name("Hello World"), "hello-world");
        assert_eq!(sanitize_link_name("Test_Note"), "test_note");
    }

    #[test]
    fn test_duplicate_links_removed() {
        let content = "[[link]] and [[link]] again";
        let links = extract_links(content);
        assert_eq!(links, vec!["link"]);
    }
}
