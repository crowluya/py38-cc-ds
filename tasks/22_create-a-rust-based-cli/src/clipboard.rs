use crate::error::{PasswordManagerError, Result};
use clipboard::{ClipboardContext, ClipboardProvider};
use std::thread;
use std::time::Duration;

/// Copies text to the clipboard and optionally clears it after a timeout
pub fn copy_to_clipboard(text: &str, clear_after: Option<Duration>) -> Result<()> {
    if text.is_empty() {
        return Err(PasswordManagerError::InvalidInput(
            "Cannot copy empty text to clipboard".to_string(),
        ));
    }

    // Create clipboard context
    let mut ctx: ClipboardContext = ClipboardProvider::new()
        .map_err(|e| PasswordManagerError::ClipboardError(e.to_string()))?;

    // Copy to clipboard
    ctx.set_contents(text.to_string())
        .map_err(|e| PasswordManagerError::ClipboardError(e.to_string()))?;

    // If timeout specified, spawn thread to clear clipboard
    if let Some(timeout) = clear_after {
        let text_to_clear = text.to_string();
        thread::spawn(move || {
            thread::sleep(timeout);
            clear_clipboard(&text_to_clear);
        });
    }

    Ok(())
}

/// Clears the clipboard if it still contains the specified text
pub fn clear_clipboard(expected_content: &str) {
    if let Ok(mut ctx) = ClipboardContext::new() {
        if let Ok(current) = ctx.get_contents() {
            if current == expected_content {
                let _ = ctx.set_contents(String::new());
            }
        }
    }
}

/// Gets the current clipboard content
pub fn get_clipboard_content() -> Result<String> {
    let mut ctx: ClipboardContext = ClipboardProvider::new()
        .map_err(|e| PasswordManagerError::ClipboardError(e.to_string()))?;

    let content = ctx
        .get_contents()
        .map_err(|e| PasswordManagerError::ClipboardError(e.to_string()))?;

    Ok(content)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_copy_to_clipboard() {
        let test_text = "test_password_123";
        copy_to_clipboard(test_text, None).unwrap();

        let content = get_clipboard_content().unwrap();
        assert_eq!(content, test_text);

        // Clear after test
        clear_clipboard(test_text);
    }

    #[test]
    fn test_copy_empty_text() {
        let result = copy_to_clipboard("", None);
        assert!(result.is_err());
    }

    #[test]
    fn test_clear_clipboard() {
        let test_text = "test_clear_password";
        copy_to_clipboard(test_text, None).unwrap();

        clear_clipboard(test_text);

        // Give it a moment
        thread::sleep(Duration::from_millis(100));

        let content = get_clipboard_content().unwrap();
        assert_ne!(content, test_text);
    }
}
