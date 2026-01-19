use anyhow::{Context, Result};
use clipboard::{ClipboardContext, ClipboardProvider};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;

/// Default clipboard clear timeout in seconds
pub const DEFAULT_CLEAR_TIMEOUT: u64 = 15;

/// Clipboard manager for secure password copying
pub struct ClipboardManager {
    ctx: Arc<Mutex<ClipboardContext>>,
}

impl ClipboardManager {
    /// Creates a new ClipboardManager
    pub fn new() -> Result<Self> {
        let ctx: ClipboardContext = ClipboardProvider::new()
            .context("Failed to initialize clipboard")?;

        Ok(Self {
            ctx: Arc::new(Mutex::new(ctx)),
        })
    }

    /// Copies text to clipboard with optional auto-clear timeout
    ///
    /// # Arguments
    /// * `text` - The text to copy
    /// * `clear_after_secs` - Optional timeout in seconds after which to clear the clipboard.
    ///                       If None, clipboard will not be automatically cleared.
    ///
    /// # Example
    /// ```no_run
    /// # use vaultkeeper::clipboard::ClipboardManager;
    /// let clipboard = ClipboardManager::new().unwrap();
    ///
    /// // Copy with auto-clear after 15 seconds
    /// clipboard.copy_with_timeout("my_password", Some(15)).unwrap();
    ///
    /// // Copy without auto-clear
    /// clipboard.copy_with_timeout("my_password", None).unwrap();
    /// ```
    pub fn copy_with_timeout(&self, text: &str, clear_after_secs: Option<u64>) -> Result<()> {
        {
            let mut ctx = self.ctx.lock()
                .map_err(|e| anyhow::anyhow!("Failed to lock clipboard: {}", e))?;

            ctx.set_contents(text.to_string())
                .context("Failed to copy to clipboard")?;
        }

        // Spawn a background thread to clear the clipboard after timeout
        if let Some(timeout) = clear_after_secs {
            let ctx_clone = Arc::clone(&self.ctx);
            let _handle = thread::spawn(move || {
                thread::sleep(Duration::from_secs(timeout));

                if let Ok(mut ctx) = ctx_clone.lock() {
                    // Clear by setting to empty string
                    let _ = ctx.set_contents(String::new());
                }
            });
        }

        Ok(())
    }

    /// Copies text to clipboard with default timeout (15 seconds)
    pub fn copy(&self, text: &str) -> Result<()> {
        self.copy_with_timeout(text, Some(DEFAULT_CLEAR_TIMEOUT))
    }

    /// Clears the clipboard immediately
    pub fn clear(&self) -> Result<()> {
        let mut ctx = self.ctx.lock()
            .map_err(|e| anyhow::anyhow!("Failed to lock clipboard: {}", e))?;

        ctx.set_contents(String::new())
            .context("Failed to clear clipboard")?;

        Ok(())
    }

    /// Returns the current clipboard contents
    pub fn get_contents(&self) -> Result<String> {
        let ctx = self.ctx.lock()
            .map_err(|e| anyhow::anyhow!("Failed to lock clipboard: {}", e))?;

        let contents = ctx.get_contents()
            .context("Failed to read clipboard contents")?;

        Ok(contents)
    }
}

/// Helper function to copy password to clipboard securely
///
/// # Arguments
/// * `password` - The password to copy
/// * `timeout_secs` - Optional timeout in seconds (defaults to 15)
///
/// # Returns
/// Result indicating success or failure
pub fn copy_password(password: &str, timeout_secs: Option<u64>) -> Result<()> {
    let clipboard = ClipboardManager::new()?;
    clipboard.copy_with_timeout(password, timeout_secs)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_clipboard_copy() {
        let clipboard = ClipboardManager::new();

        if clipboard.is_err() {
            println!("Clipboard not available in test environment");
            return;
        }

        let clipboard = clipboard.unwrap();

        // Copy text
        clipboard.copy_with_timeout("test_text", None).unwrap();

        // Verify it was copied
        let contents = clipboard.get_contents().unwrap();
        assert_eq!(contents, "test_text");

        // Clear clipboard
        clipboard.clear().unwrap();

        let contents = clipboard.get_contents().unwrap();
        assert_eq!(contents, "");
    }

    #[test]
    fn test_copy_password_helper() {
        let result = copy_password("test_password", Some(1));
        if result.is_err() {
            println!("Clipboard not available in test environment");
            return;
        }

        // Give it time to copy
        thread::sleep(Duration::from_millis(100));

        // If we got here, the copy succeeded
        assert!(result.is_ok());
    }
}
