use std::fs;
use std::path::Path;
use crate::error::{AnalysisError, Result};

/// Reads a markdown file and returns its content as a string
pub fn read_markdown_file(path: &Path) -> Result<String> {
    if !path.exists() {
        return Err(AnalysisError::FileReadError(std::io::Error::new(
            std::io::ErrorKind::NotFound,
            format!("File not found: {}", path.display()),
        )));
    }

    if !path.is_file() {
        return Err(AnalysisError::FileReadError(std::io::Error::new(
            std::io::ErrorKind::InvalidInput,
            format!("Path is not a file: {}", path.display()),
        )));
    }

    let content = fs::read_to_string(path)?;

    if content.trim().is_empty() {
        return Err(AnalysisError::AnalysisError(
            "File is empty or contains only whitespace".to_string(),
        ));
    }

    Ok(content)
}

/// Writes analysis results to a file
pub fn write_to_file(path: &Path, content: &str) -> Result<()> {
    fs::write(path, content)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;
    use tempfile::NamedTempFile;

    #[test]
    fn test_read_valid_markdown_file() {
        let mut temp_file = NamedTempFile::new().unwrap();
        writeln!(temp_file, "# Test Header").unwrap();
        writeln!(temp_file, "Some content here.").unwrap();

        let content = read_markdown_file(temp_file.path()).unwrap();
        assert!(content.contains("Test Header"));
        assert!(content.contains("Some content here"));
    }

    #[test]
    fn test_read_nonexistent_file() {
        let result = read_markdown_file(Path::new("/nonexistent/file.md"));
        assert!(result.is_err());
    }

    #[test]
    fn test_read_empty_file() {
        let temp_file = NamedTempFile::new().unwrap();
        let result = read_markdown_file(temp_file.path());
        assert!(result.is_err());
    }
}
