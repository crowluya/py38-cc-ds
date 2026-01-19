//! Log input sources (files, stdin, etc.).

use crate::core::LogEntry;
use crate::parsers::LogParser;
use anyhow::{Context, Result};
use notify::{Event, EventKind, RecursiveMode, Watcher};
use std::path::PathBuf;
use tokio::sync::mpsc;
use tokio::io::{AsyncBufReadExt, BufReader};
use std::fs::File;
use std::io::{BufRead, BufReader as StdBufReader};
use tokio::task::JoinHandle;

/// Trait for log sources that can be monitored.
pub trait LogSource: Send + Sync {
    /// Start reading from the source and sending entries through the channel.
    fn start(&mut self, tx: mpsc::UnboundedSender<LogEntry>) -> Result<()>;

    /// Stop reading from the source.
    fn stop(&mut self) -> Result<()>;

    /// Get the source name/description.
    fn name(&self) -> &str;
}

/// File-based log source that monitors a file for new entries.
pub struct FileLogSource {
    /// Path to the log file
    path: PathBuf,

    /// Whether to follow the file (like tail -f)
    follow: bool,

    /// Log parser for parsing entries
    parser: Box<dyn LogParser>,

    /// Current file offset for tracking position
    offset: u64,

    /// Watcher handle for file changes
    _watcher: Option<notify::RecommendedWatcher>,

    /// Handle for the monitoring task
    task_handle: Option<JoinHandle<()>>,

    /// Running state
    running: std::sync::Arc<std::sync::atomic::AtomicBool>,
}

impl FileLogSource {
    /// Create a new file log source.
    pub fn new(path: PathBuf, follow: bool, parser: Box<dyn LogParser>) -> Self {
        Self {
            path,
            follow,
            parser,
            offset: 0,
            _watcher: None,
            task_handle: None,
            running: std::sync::Arc::new(std::sync::atomic::AtomicBool::new(false)),
        }
    }

    /// Read existing content from the file.
    fn read_existing(&mut self, tx: &mpsc::UnboundedSender<LogEntry>) -> Result<u64> {
        let file = File::open(&self.path)
            .with_context(|| format!("Failed to open file: {:?}", self.path))?;

        let reader = StdBufReader::new(file);
        let mut bytes_read = 0u64;

        for line in reader.lines() {
            let line = line?;
            bytes_read += line.len() as u64 + 1; // +1 for newline

            if let Some(entry) = self.parser.parse(&line, self.path.display().to_string()) {
                tx.send(entry).ok();
            }
        }

        Ok(bytes_read)
    }

    /// Start monitoring the file for new entries.
    async fn monitor_file(&self, tx: mpsc::UnboundedSender<LogEntry>) -> Result<()> {
        let path = self.path.clone();
        let parser = self.parser.clone_box();
        let running = self.running.clone();

        // Spawn a task to monitor the file
        let handle = tokio::spawn(async move {
            let mut last_size = match std::fs::metadata(&path) {
                Ok(metadata) => metadata.len(),
                Err(_) => return,
            };

            while running.load(std::sync::atomic::Ordering::Relaxed) {
                tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;

                match std::fs::metadata(&path) {
                    Ok(metadata) => {
                        let current_size = metadata.len();

                        if current_size > last_size {
                            // File has new content
                            if let Ok(file) = File::open(&path) {
                                let mut reader = BufReader::new(file);
                                reader.seek(std::io::SeekFrom::Start(last_size)).ok();

                                let mut line = String::new();
                                while reader.read_line(&mut line).await.unwrap_or(0) > 0 {
                                    if let Some(entry) = parser.parse(&line.trim(), path.display().to_string()) {
                                        tx.send(entry).ok();
                                    }
                                    line.clear();
                                }

                                last_size = current_size;
                            }
                        } else if current_size < last_size {
                            // File was truncated or rotated
                            last_size = 0;
                        }
                    }
                    Err(_) => {
                        // File not accessible, wait and retry
                        tokio::time::sleep(tokio::time::Duration::from_secs(1)).await;
                    }
                }
            }
        });

        Ok(())
    }
}

impl LogSource for FileLogSource {
    fn start(&mut self, tx: mpsc::UnboundedSender<LogEntry>) -> Result<()> {
        self.running.store(true, std::sync::atomic::Ordering::Relaxed);

        // Read existing content if not following from start
        if !self.follow {
            self.offset = self.read_existing(&tx)?;
        }

        // Start monitoring for new content
        let tx_clone = tx.clone();
        let handle = tokio::spawn(async move {
            // File monitoring loop would go here
            // For now, this is a simplified version
        });

        self.task_handle = Some(handle);
        Ok(())
    }

    fn stop(&mut self) -> Result<()> {
        self.running.store(false, std::sync::atomic::Ordering::Relaxed);
        Ok(())
    }

    fn name(&self) -> &str {
        self.path.to_str().unwrap_or("unknown")
    }
}

/// Stdin-based log source for piped input.
pub struct StdinLogSource {
    /// Log parser for parsing entries
    parser: Box<dyn LogParser>,

    /// Running state
    running: std::sync::Arc<std::sync::atomic::AtomicBool>,

    /// Task handle
    task_handle: Option<JoinHandle<()>>,
}

impl StdinLogSource {
    /// Create a new stdin log source.
    pub fn new(parser: Box<dyn LogParser>) -> Self {
        Self {
            parser,
            running: std::sync::Arc::new(std::sync::atomic::AtomicBool::new(false)),
            task_handle: None,
        }
    }

    /// Start reading from stdin.
    async fn read_stdin(&self, tx: mpsc::UnboundedSender<LogEntry>) -> Result<()> {
        let parser = self.parser.clone_box();
        let running = self.running.clone();
        let source = "stdin".to_string();

        let handle = tokio::spawn(async move {
            let stdin = tokio::io::stdin();
            let reader = BufReader::new(stdin);
            let mut lines = reader.lines();

            while running.load(std::sync::atomic::Ordering::Relaxed) {
                match lines.next_line().await {
                    Ok(Some(line)) => {
                        if let Some(entry) = parser.parse(&line, source.clone()) {
                            tx.send(entry).ok();
                        }
                    }
                    Ok(None) => {
                        // EOF
                        break;
                    }
                    Err(_) => {
                        break;
                    }
                }
            }
        });

        Ok(())
    }
}

impl LogSource for StdinLogSource {
    fn start(&mut self, tx: mpsc::UnboundedSender<LogEntry>) -> Result<()> {
        self.running.store(true, std::sync::atomic::Ordering::Relaxed);
        Ok(())
    }

    fn stop(&mut self) -> Result<()> {
        self.running.store(false, std::sync::atomic::Ordering::Relaxed);
        Ok(())
    }

    fn name(&self) -> &str {
        "stdin"
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::parsers::GenericLogParser;

    #[test]
    fn test_file_log_source_creation() {
        let parser = Box::new(GenericLogParser::new());
        let source = FileLogSource::new(
            PathBuf::from("/tmp/test.log"),
            false,
            parser,
        );
        assert_eq!(source.name(), "/tmp/test.log");
    }
}
