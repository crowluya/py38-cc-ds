use crate::crypto::{decrypt_vault, derive_key, encrypt_vault, generate_salt};
use crate::error::{PasswordManagerError, Result};
use crate::models::{Vault, VaultHeader};
use std::fs::File;
use std::io::{self, Read, Write};
use std::path::Path;
use std::time::Duration;

/// Lock file extension
const LOCK_EXTENSION: &str = ".lock";

/// Creates a new vault with the given master password
pub fn create_vault(path: &Path, master_password: &str) -> Result<()> {
    // Check if vault already exists
    if path.exists() {
        return Err(PasswordManagerError::InvalidInput(format!(
            "Vault already exists at {}",
            path.display()
        )));
    }

    // Generate salt and create empty vault
    let salt = generate_salt();
    let vault = Vault::new();
    let vault_json = serde_json::to_vec(&vault)?;

    // Derive encryption key
    let key = derive_key(master_password, &salt);

    // Encrypt vault data
    let (encrypted, nonce) = encrypt_vault(&vault_json, &key)?;

    // Create vault header
    let header = VaultHeader::new(salt, nonce);

    // Ensure parent directory exists
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }

    // Write vault file
    write_vault_file(path, &header, &encrypted)?;

    // Set secure file permissions (Unix only)
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let mut perms = std::fs::metadata(path)?.permissions();
        perms.set_mode(0o600);
        std::fs::set_permissions(path, perms)?;
    }

    Ok(())
}

/// Unlocks and decrypts a vault with the given master password
pub fn unlock_vault(path: &Path, master_password: &str) -> Result<Vault> {
    // Acquire lock
    let _lock = acquire_lock(path)?;

    // Read vault file
    let (header, encrypted_data) = read_vault_file(path)?;

    // Validate header
    if !header.validate() {
        return Err(PasswordManagerError::VaultCorrupted(
            "Invalid vault header or version".to_string(),
        ));
    }

    // Derive encryption key
    let key = derive_key(master_password, &header.salt);

    // Decrypt vault
    let decrypted_data = decrypt_vault(&encrypted_data, &header.nonce, &key)?;

    // Deserialize vault
    let vault: Vault = serde_json::from_slice(&decrypted_data)?;

    Ok(vault)
}

/// Saves a vault to disk with encryption
pub fn save_vault(path: &Path, vault: &Vault, master_password: &str) -> Result<()> {
    // Read existing vault to get salt
    let (header, _) = read_vault_file(path)?;

    // Derive encryption key
    let key = derive_key(master_password, &header.salt);

    // Serialize vault
    let vault_json = serde_json::to_vec(vault)?;

    // Encrypt with new nonce (recommended for GCM)
    let (encrypted, new_nonce) = encrypt_vault(&vault_json, &key)?;

    // Create new header with updated nonce
    let new_header = VaultHeader::new(header.salt, new_nonce);

    // Write vault file
    write_vault_file(path, &new_header, &encrypted)?;

    Ok(())
}

/// Reads a vault file from disk
fn read_vault_file(path: &Path) -> Result<(VaultHeader, Vec<u8>)> {
    if !path.exists() {
        return Err(PasswordManagerError::VaultNotFound(path.display().to_string()));
    }

    let mut file = File::open(path)?;

    // Read header
    let magic = read_bytes(&mut file, 4)?;
    let version = read_u16(&mut file)?;
    let salt = read_bytes(&mut file, 32)?;
    let nonce = read_bytes(&mut file, 12)?;

    let header = VaultHeader {
        magic: magic.try_into().unwrap(),
        version,
        salt: salt.try_into().unwrap(),
        nonce: nonce.try_into().unwrap(),
    };

    // Read encrypted data
    let mut encrypted_data = Vec::new();
    file.read_to_end(&mut encrypted_data)?;

    if encrypted_data.is_empty() {
        return Err(PasswordManagerError::VaultCorrupted(
            "Vault data is empty".to_string(),
        ));
    }

    Ok((header, encrypted_data))
}

/// Writes a vault file to disk
fn write_vault_file(path: &Path, header: &VaultHeader, encrypted_data: &[u8]) -> Result<()> {
    let mut file = File::create(path)?;

    // Write header
    file.write_all(&header.magic)?;
    file.write_all(&header.version.to_be_bytes())?;
    file.write_all(&header.salt)?;
    file.write_all(&header.nonce)?;

    // Write encrypted data
    file.write_all(encrypted_data)?;

    file.flush()?;

    Ok(())
}

/// Reads exactly n bytes from the file
fn read_bytes(file: &mut File, n: usize) -> Result<Vec<u8>> {
    let mut buffer = vec![0u8; n];
    file.read_exact(&mut buffer)?;
    Ok(buffer)
}

/// Reads a u16 in big-endian format
fn read_u16(file: &mut File) -> Result<u16> {
    let mut buffer = [0u8; 2];
    file.read_exact(&mut buffer)?;
    Ok(u16::from_be_bytes(buffer))
}

/// Acquires a lock on the vault file to prevent concurrent access
fn acquire_lock(path: &Path) -> Result<FileLock> {
    let lock_path = path.with_extension(LOCK_EXTENSION);

    // Try to create lock file
    loop {
        match File::create(&lock_path) {
            Ok(file) => {
                // Try to get exclusive lock
                #[cfg(unix)]
                {
                    use std::os::unix::io::AsRawFd;
                    unsafe {
                        if libc::flock(file.as_raw_fd(), libc::LOCK_EX | libc::LOCK_NB) != 0 {
                            return Err(PasswordManagerError::VaultLocked);
                        }
                    }
                }

                return Ok(FileLock {
                    file: Some(file),
                    path: lock_path,
                });
            }
            Err(e) if e.kind() == io::ErrorKind::PermissionDenied => {
                return Err(PasswordManagerError::VaultLocked);
            }
            Err(e) => return Err(PasswordManagerError::IoError(e)),
        }
    }
}

/// File lock guard that releases the lock when dropped
struct FileLock {
    file: Option<File>,
    path: std::path::PathBuf,
}

impl Drop for FileLock {
    fn drop(&mut self) {
        // Release lock
        #[cfg(unix)]
        {
            if let Some(file) = &self.file {
                use std::os::unix::io::AsRawFd;
                unsafe {
                    libc::flock(file.as_raw_fd(), libc::LOCK_UN);
                }
            }
        }

        // Remove lock file
        let _ = std::fs::remove_file(&self.path);
    }
}

/// Checks if a vault exists at the given path
pub fn vault_exists(path: &Path) -> bool {
    path.exists()
}

/// Checks if a vault is locked by another process
pub fn is_vault_locked(path: &Path) -> bool {
    let lock_path = path.with_extension(LOCK_EXTENSION);
    lock_path.exists()
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::NamedTempFile;

    #[test]
    fn test_create_and_unlock_vault() {
        let temp_file = NamedTempFile::new().unwrap();
        let path = temp_file.path();

        let password = "test_password_123!";

        // Create vault
        create_vault(path, password).unwrap();
        assert!(vault_exists(path));

        // Unlock vault
        let vault = unlock_vault(path, password).unwrap();
        assert_eq!(vault.credential_count(), 0);

        // Wrong password should fail
        let result = unlock_vault(path, "wrong_password");
        assert!(result.is_err());
    }

    #[test]
    fn test_save_and_reload_vault() {
        let temp_file = NamedTempFile::new().unwrap();
        let path = temp_file.path();
        let password = "test_password_123!";

        // Create vault
        create_vault(path, password).unwrap();

        // Unlock, modify, and save
        let mut vault = unlock_vault(path, password).unwrap();
        let cred = crate::models::Credential::new(
            "Test".to_string(),
            "user".to_string(),
            "pass".to_string(),
        );
        vault.add_credential(cred);
        save_vault(path, &vault, password).unwrap();

        // Reload and verify
        let vault2 = unlock_vault(path, password).unwrap();
        assert_eq!(vault2.credential_count(), 1);
        assert_eq!(vault2.get_credential(&vault.credentials[0].id).unwrap().title, "Test");
    }

    #[test]
    fn test_vault_already_exists() {
        let temp_file = NamedTempFile::new().unwrap();
        let path = temp_file.path();
        let password = "test_password_123!";

        create_vault(path, password).unwrap();

        let result = create_vault(path, password);
        assert!(result.is_err());
    }

    #[test]
    fn test_vault_not_found() {
        let result = unlock_vault(Path::new("/nonexistent/vault"), "password");
        assert!(matches!(
            result.unwrap_err(),
            PasswordManagerError::VaultNotFound(_)
        ));
    }

    #[test]
    fn test_vault_file_permissions() {
        let temp_file = NamedTempFile::new().unwrap();
        let path = temp_file.path();
        let password = "test_password_123!";

        create_vault(path, password).unwrap();

        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            let metadata = fs::metadata(path).unwrap();
            let perms = metadata.permissions();
            let mode = perms.mode() & 0o777;
            assert_eq!(mode, 0o600, "Vault file should have 0600 permissions");
        }
    }
}
