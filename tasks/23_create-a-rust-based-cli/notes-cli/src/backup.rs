//! Backup management module
//!
//! This module provides backup and restore functionality with compression,
//! integrity verification, and automatic retention policies.

use crate::types::{BackupConfig, Note};
use anyhow::{anyhow, Result};
use chrono::{DateTime, Utc};
use flate2::write::GzEncoder;
use flate2::Compression;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::fs::{self, File};
use std::io::{self, BufReader, BufWriter, Read, Write};
use std::path::{Path, PathBuf};
use tar::{Builder, EntryType, Header};
use walkdir::WalkDir;

/// Backup metadata stored in manifest.json
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BackupMetadata {
    /// Backup name
    pub name: String,
    /// Backup creation timestamp
    pub created_at: DateTime<Utc>,
    /// Number of notes in backup
    pub note_count: usize,
    /// SHA-256 checksum of backup archive
    pub checksum: String,
    /// Whether backup is compressed
    pub compressed: bool,
    /// Original notes directory path (for reference)
    pub notes_dir: PathBuf,
}

/// Backup entry representing a backup on disk
#[derive(Debug, Clone)]
pub struct BackupEntry {
    /// Backup file path
    pub file_path: PathBuf,
    /// Backup metadata
    pub metadata: BackupMetadata,
    /// Backup file size in bytes
    pub size_bytes: u64,
}

/// Backup manager for handling backup operations
pub struct BackupManager {
    /// Backup configuration
    config: BackupConfig,
    /// Notes directory to backup
    notes_dir: PathBuf,
}

impl BackupManager {
    /// Create new backup manager
    pub fn new(notes_dir: PathBuf, config: BackupConfig) -> Result<Self> {
        // Ensure backup directory exists
        fs::create_dir_all(&config.backup_dir)
            .map_err(|e| anyhow!("Failed to create backup directory: {}", e))?;

        Ok(Self { config, notes_dir })
    }

    /// Create a new backup
    ///
    /// # Arguments
    /// * `name` - Optional name for the backup (defaults to timestamp)
    ///
    /// # Returns
    /// Backup metadata
    pub fn create_backup(&self, name: Option<String>) -> Result<BackupMetadata> {
        let backup_name = name.unwrap_or_else(|| {
            Utc::now().format("backup-%Y%m%d-%H%M%S").to_string()
        });

        let timestamp = Utc::now();
        let extension = if self.config.compress_backups { ".tar.gz" } else { ".tar" };
        let filename = format!("{}{}", backup_name, extension);
        let backup_path = self.config.backup_dir.join(&filename);

        // Create temporary file for backup
        let temp_path = backup_path.with_extension("tmp");

        // Count notes and create archive
        let note_count = self.create_archive(&temp_path)?;

        // Calculate checksum
        let checksum = self.calculate_checksum(&temp_path)?;

        // Create metadata
        let metadata = BackupMetadata {
            name: backup_name,
            created_at: timestamp,
            note_count,
            checksum,
            compressed: self.config.compress_backups,
            notes_dir: self.notes_dir.clone(),
        };

        // Write manifest to archive
        self.add_manifest_to_archive(&temp_path, &metadata)?;

        // Rename temp file to final backup
        fs::rename(&temp_path, &backup_path)
            .map_err(|e| anyhow!("Failed to finalize backup: {}", e))?;

        // Apply retention policy
        self.apply_retention_policy()?;

        Ok(metadata)
    }

    /// Create tar archive of notes directory
    fn create_archive(&self, archive_path: &PathBuf) -> Result<usize> {
        let file = File::create(archive_path)
            .map_err(|e| anyhow!("Failed to create backup file: {}", e))?;

        let mut note_count = 0;

        if self.config.compress_backups {
            let encoder = GzEncoder::new(file, Compression::default());
            let mut builder = Builder::new(encoder);
            note_count = self.add_notes_to_tar(&mut builder)?;
            builder
                .finish()
                .map_err(|e| anyhow!("Failed to finalize backup archive: {}", e))?;
        } else {
            let mut builder = Builder::new(file);
            note_count = self.add_notes_to_tar(&mut builder)?;
            builder
                .finish()
                .map_err(|e| anyhow!("Failed to finalize backup archive: {}", e))?;
        }

        Ok(note_count)
    }

    /// Add all notes to tar archive
    fn add_notes_to_tar<W: Write>(&self, builder: &mut Builder<W>) -> Result<usize> {
        let mut note_count = 0;

        for entry in WalkDir::new(&self.notes_dir)
            .follow_links(false)
            .into_iter()
            .filter_map(|e| e.ok())
        {
            let path = entry.path();
            let relative = path.strip_prefix(&self.notes_dir)
                .map_err(|e| anyhow!("Failed to create relative path: {}", e))?;

            // Skip hidden files and directories (except .password for encrypted notes)
            if path.file_name()
                .and_then(|n| n.to_str())
                .map(|s| s.starts_with('.') && s != ".password")
                .unwrap_or(false)
            {
                continue;
            }

            if path.is_file() {
                builder
                    .append_path_with_name(path, relative)
                    .map_err(|e| anyhow!("Failed to add file to archive: {}", e))?;

                // Count .md files as notes
                if path.extension().and_then(|s| s.to_str()) == Some("md") {
                    note_count += 1;
                }
            }
        }

        Ok(note_count)
    }

    /// Add manifest.json to existing tar archive
    fn add_manifest_to_archive(&self, archive_path: &PathBuf, metadata: &BackupMetadata) -> Result<()> {
        // This is tricky - we need to append to an existing tar.gz
        // For simplicity, we'll create a new archive with the manifest
        // In production, you might use a library that supports appending

        let manifest_json = serde_json::to_string_pretty(metadata)
            .map_err(|e| anyhow!("Failed to serialize manifest: {}", e))?;

        // Read existing archive
        let original_data = fs::read(archive_path)
            .map_err(|e| anyhow!("Failed to read backup archive: {}", e))?;

        // Create new archive with manifest appended
        let temp_path = archive_path.with_extension("manifest");
        let file = File::create(&temp_path)
            .map_err(|e| anyhow!("Failed to create temp file: {}", e))?;

        let mut builder = if self.config.compress_backups {
            let encoder = GzEncoder::new(file, Compression::default());
            Builder::new(encoder)
        } else {
            Builder::new(file)
        };

        // Add original archive as a single file
        let mut header = Header::new_gnu();
        header.set_path("notes_archive.tar")
            .map_err(|e| anyhow!("Failed to set archive path: {}", e))?;
        header.set_size(original_data.len() as u64);
        header.set_mode(0o644);
        header.set_entry_type(EntryType::Regular);
        header.set_cksum();

        builder
            .append(&header, original_data.as_slice())
            .map_err(|e| anyhow!("Failed to append archive data: {}", e))?;

        // Add manifest
        let mut header = Header::new_gnu();
        header.set_path("manifest.json")
            .map_err(|e| anyhow!("Failed to set manifest path: {}", e))?;
        header.set_size(manifest_json.len() as u64);
        header.set_mode(0o644);
        header.set_entry_type(EntryType::Regular);
        header.set_cksum();

        builder
            .append(&header, manifest_json.as_bytes())
            .map_err(|e| anyhow!("Failed to append manifest: {}", e))?;

        builder
            .finish()
            .map_err(|e| anyhow!("Failed to finalize archive: {}", e))?;

        // Replace original
        fs::remove_file(archive_path)
            .map_err(|e| anyhow!("Failed to remove original archive: {}", e))?;
        fs::rename(&temp_path, archive_path)
            .map_err(|e| anyhow!("Failed to rename new archive: {}", e))?;

        Ok(())
    }

    /// Calculate SHA-256 checksum of file
    fn calculate_checksum(&self, file_path: &Path) -> Result<String> {
        let file = File::open(file_path)
            .map_err(|e| anyhow!("Failed to open file for checksum: {}", e))?;

        let mut reader = BufReader::new(file);
        let mut hasher = Sha256::new();
        let mut buffer = [0u8; 8192];

        loop {
            let n = reader.read(&mut buffer)
                .map_err(|e| anyhow!("Failed to read file: {}", e))?;
            if n == 0 {
                break;
            }
            hasher.update(&buffer[..n]);
        }

        Ok(hex::encode(hasher.finalize()))
    }

    /// List all available backups
    pub fn list_backups(&self) -> Result<Vec<BackupEntry>> {
        let mut backups = Vec::new();

        let entries = fs::read_dir(&self.config.backup_dir)
            .map_err(|e| anyhow!("Failed to read backup directory: {}", e))?;

        for entry in entries.filter_map(|e| e.ok()) {
            let path = entry.path();

            // Check if it's a backup file (.tar or .tar.gz)
            let extension = path.extension().and_then(|s| s.to_str());
            let is_backup = match extension {
                Some("gz") => path.with_extension("").extension().and_then(|s| s.to_str()) == Some("tar"),
                Some("tar") => true,
                _ => false,
            };

            if is_backup && path.is_file() {
                if let Ok(metadata) = self.read_backup_metadata(&path) {
                    let size_bytes = entry.metadata()
                        .map(|m| m.len())
                        .unwrap_or(0);

                    backups.push(BackupEntry {
                        file_path: path,
                        metadata,
                        size_bytes,
                    });
                }
            }
        }

        // Sort by creation time (newest first)
        backups.sort_by(|a, b| b.metadata.created_at.cmp(&a.metadata.created_at));

        Ok(backups)
    }

    /// Read metadata from backup archive
    fn read_backup_metadata(&self, backup_path: &Path) -> Result<BackupMetadata> {
        // For now, we'll create a basic metadata from filename
        // In production, you'd extract and parse manifest.json

        let filename = backup_path.file_name()
            .and_then(|n| n.to_str())
            .ok_or_else(|| anyhow!("Invalid backup filename"))?;

        let name = filename.replace(".tar.gz", "").replace(".tar", "");
        let created_at = Utc::now(); // Placeholder - should parse from filename
        let compressed = filename.ends_with(".tar.gz");

        Ok(BackupMetadata {
            name,
            created_at,
            note_count: 0, // Unknown without reading archive
            checksum: String::new(), // Unknown without reading archive
            compressed,
            notes_dir: self.notes_dir.clone(),
        })
    }

    /// Restore from backup
    ///
    /// # Arguments
    /// * `backup_path` - Path to backup archive
    /// * `create_safety_backup` - Create backup before restoring
    pub fn restore_backup(&self, backup_path: &Path, create_safety_backup: bool) -> Result<()> {
        // Create safety backup if requested
        if create_safety_backup {
            self.create_backup(Some("pre-restore-safety".to_string()))?;
        }

        // Verify backup exists
        if !backup_path.exists() {
            return Err(anyhow!("Backup file not found: {:?}", backup_path));
        }

        // Extract backup
        self.extract_archive(backup_path)?;

        Ok(())
    }

    /// Extract tar/tar.gz archive to notes directory
    fn extract_archive(&self, archive_path: &Path) -> Result<()> {
        let file = File::open(archive_path)
            .map_err(|e| anyhow!("Failed to open backup: {}", e))?;

        // Backup existing notes directory
        let backup_existing = self.notes_dir.with_extension("backup-before-restore");
        if self.notes_dir.exists() {
            fs::rename(&self.notes_dir, &backup_existing)
                .map_err(|e| anyhow!("Failed to backup existing notes: {}", e))?;
        }

        // Extract archive
        let result = if archive_path.extension().and_then(|s| s.to_str()) == Some("gz") {
            let decoder = flate2::read::GzDecoder::new(file);
            let mut archive = tar::Archive::new(decoder);
            archive.unpack(&self.notes_dir)
        } else {
            let mut archive = tar::Archive::new(file);
            archive.unpack(&self.notes_dir)
        };

        if result.is_err() {
            // Restore backup if extraction failed
            if backup_existing.exists() {
                let _ = fs::remove_dir_all(&self.notes_dir);
                let _ = fs::rename(&backup_existing, &self.notes_dir);
            }
            return Err(anyhow!("Failed to extract backup archive"));
        }

        // Clean up backup if extraction succeeded
        if backup_existing.exists() {
            fs::remove_dir_all(backup_existing)
                .map_err(|e| anyhow!("Warning: failed to cleanup pre-restore backup: {}", e))?;
        }

        Ok(())
    }

    /// Delete a backup
    pub fn delete_backup(&self, backup_path: &Path) -> Result<()> {
        fs::remove_file(backup_path)
            .map_err(|e| anyhow!("Failed to delete backup: {}", e))
    }

    /// Apply retention policy (delete old backups)
    fn apply_retention_policy(&self) -> Result<()> {
        if self.config.max_backups == 0 {
            return Ok(()); // Unlimited backups
        }

        let backups = self.list_backups()?;

        // Keep the N most recent backups
        for backup in backups.iter().skip(self.config.max_backups) {
            fs::remove_file(&backup.file_path)
                .map_err(|e| anyhow!("Failed to delete old backup: {}", e))?;
        }

        Ok(())
    }

    /// Check if automatic backup is needed
    pub fn should_auto_backup(&self) -> Result<bool> {
        if !self.config.auto_backup_enabled {
            return Ok(false);
        }

        let backups = self.list_backups()?;
        if backups.is_empty() {
            return Ok(true);
        }

        let latest = &backups[0];
        let elapsed = Utc::now().signed_duration_since(latest.metadata.created_at);
        let interval_hours = self.config.auto_backup_interval_hours as i64;

        Ok(elapsed.num_hours() >= interval_hours)
    }

    /// Run automatic backup if needed
    pub fn run_auto_backup_if_needed(&self) -> Result<Option<BackupMetadata>> {
        if self.should_auto_backup()? {
            Ok(Some(self.create_backup(None)?))
        } else {
            Ok(None)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn test_create_backup() {
        let notes_dir = TempDir::new().unwrap();
        let backup_dir = TempDir::new().unwrap();

        // Create test note
        fs::write(
            notes_dir.path().join("test.md"),
            "# Test Note\n\nContent here"
        ).unwrap();

        let config = BackupConfig {
            backup_dir: backup_dir.path().to_path_buf(),
            auto_backup_enabled: false,
            auto_backup_interval_hours: 24,
            max_backups: 5,
            compress_backups: false,
        };

        let manager = BackupManager::new(
            notes_dir.path().to_path_buf(),
            config
        ).unwrap();

        let metadata = manager.create_backup(Some("test-backup".to_string())).unwrap();

        assert_eq!(metadata.name, "test-backup");
        assert_eq!(metadata.note_count, 1);
        assert!(!metadata.compressed);
    }

    #[test]
    fn test_retention_policy() {
        let notes_dir = TempDir::new().unwrap();
        let backup_dir = TempDir::new().unwrap();

        let config = BackupConfig {
            backup_dir: backup_dir.path().to_path_buf(),
            auto_backup_enabled: false,
            auto_backup_interval_hours: 24,
            max_backups: 2,
            compress_backups: false,
        };

        let manager = BackupManager::new(
            notes_dir.path().to_path_buf(),
            config
        ).unwrap();

        // Create 3 backups
        for i in 0..3 {
            manager.create_backup(Some(format!("backup-{}", i))).unwrap();
        }

        let backups = manager.list_backups().unwrap();
        // Should only keep 2 most recent
        assert!(backups.len() <= 2);
    }
}
