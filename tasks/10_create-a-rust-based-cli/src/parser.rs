use pulldown_cmark::{Event, Parser, Tag};
use crate::error::{AnalysisError, Result};

/// Extracts plain text from markdown content
pub fn extract_text_from_markdown(markdown_content: &str, include_code_blocks: bool) -> Result<String> {
    let parser = Parser::new(markdown_content);
    let mut plain_text = String::new();
    let mut in_code_block = false;

    for event in parser {
        match event {
            Event::Start(Tag::CodeBlock(_)) | Event::Start(Tag::FencedCodeBlock(_)) => {
                in_code_block = true;
            }
            Event::End(Tag::CodeBlock(_)) | Event::End(Tag::FencedCodeBlock(_)) => {
                in_code_block = false;
            }
            Event::Text(text) | Event::Code(text) => {
                if include_code_blocks || !in_code_block {
                    plain_text.push_str(&text);
                    plain_text.push(' ');
                }
            }
            Event::SoftBreak | Event::HardBreak => {
                plain_text.push(' ');
            }
            _ => {
                // Ignore other events
            }
        }
    }

    Ok(plain_text)
}

/// Cleans text by normalizing whitespace and removing excessive spacing
pub fn clean_text(text: &str) -> String {
    text.split_whitespace()
        .collect::<Vec<&str>>()
        .join(" ")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_simple_markdown() {
        let markdown = "# Hello World\n\nThis is a test.";
        let text = extract_text_from_markdown(markdown, false).unwrap();
        assert!(text.contains("Hello World"));
        assert!(text.contains("This is a test"));
    }

    #[test]
    fn test_exclude_code_blocks() {
        let markdown = "# Title\n\n```rust\nfn main() {}\n```\n\nSome text.";
        let text = extract_text_from_markdown(markdown, false).unwrap();
        assert!(!text.contains("fn main"));
        assert!(text.contains("Some text"));
    }

    #[test]
    fn test_include_code_blocks() {
        let markdown = "# Title\n\n```rust\nfn main() {}\n```\n\nSome text.";
        let text = extract_text_from_markdown(markdown, true).unwrap();
        assert!(text.contains("fn main"));
        assert!(text.contains("Some text"));
    }

    #[test]
    fn test_clean_text() {
        let text = "  This   is  a   test  \n\n  with  spaces  ";
        let cleaned = clean_text(text);
        assert_eq!(cleaned, "This is a test with spaces");
    }
}
