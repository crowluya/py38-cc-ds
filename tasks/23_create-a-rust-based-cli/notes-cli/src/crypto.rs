//! Cryptography module for note encryption and decryption
//!
//! This module provides AES-256-GCM encryption for secure note storage.
//! Each encryption operation uses a unique nonce to prevent cross-note attacks.

use aes_gcm::{
    aead::{Aead, AeadCore, KeyInit, OsRng},
    Aes256Gcm, Nonce, Key,
};
use anyhow::{anyhow, Result};
use rand::RngCore;

/// Size of the AES-256 key in bytes (32 bytes = 256 bits)
pub const KEY_SIZE: usize = 32;

/// Size of the nonce for GCM mode (12 bytes is recommended for GCM)
pub const NONCE_SIZE: usize = 12;

/// Encrypted data structure containing ciphertext, nonce, and tag
/// The tag is automatically appended by AES-GCM
#[derive(Debug, Clone)]
pub struct EncryptedData {
    /// Nonce used for encryption (unique per encryption)
    pub nonce: Vec<u8>,
    /// Ciphertext with authentication tag appended
    pub ciphertext: Vec<u8>,
}

/// Encrypt plaintext using AES-256-GCM
///
/// # Arguments
/// * `key` - 32-byte encryption key
/// * `plaintext` - Data to encrypt
///
/// # Returns
/// EncryptedData containing nonce and ciphertext
///
/// # Security
/// - Each encryption uses a cryptographically secure random nonce
/// - AES-256-GCM provides both confidentiality and integrity
/// - Never reuse nonces with the same key
pub fn encrypt(key: &[u8; KEY_SIZE], plaintext: &[u8]) -> Result<EncryptedData> {
    // Validate key size
    if key.len() != KEY_SIZE {
        return Err(anyhow!("Invalid key size: expected {} bytes", KEY_SIZE));
    }

    // Create cipher instance
    let cipher_key = Key::<Aes256Gcm>::from_slice(key);
    let cipher = Aes256Gcm::new(cipher_key);

    // Generate random nonce (critical: never reuse nonces!)
    let nonce = Aes256Gcm::generate_nonce(&mut OsRng);
    let nonce_bytes = nonce.to_vec();

    // Encrypt plaintext
    let ciphertext = cipher
        .encrypt(&nonce, plaintext)
        .map_err(|e| anyhow!("Encryption failed: {}", e))?;

    Ok(EncryptedData {
        nonce: nonce_bytes,
        ciphertext,
    })
}

/// Decrypt ciphertext using AES-256-GCM
///
/// # Arguments
/// * `key` - 32-byte encryption key
/// * `encrypted` - EncryptedData containing nonce and ciphertext
///
/// # Returns
/// Decrypted plaintext
///
/// # Security
/// - GCM authentication tag verification happens automatically
/// - Decryption fails if ciphertext was tampered with
pub fn decrypt(key: &[u8; KEY_SIZE], encrypted: &EncryptedData) -> Result<Vec<u8>> {
    // Validate key size
    if key.len() != KEY_SIZE {
        return Err(anyhow!("Invalid key size: expected {} bytes", KEY_SIZE));
    }

    // Validate nonce size
    if encrypted.nonce.len() != NONCE_SIZE {
        return Err(anyhow!("Invalid nonce size: expected {} bytes", NONCE_SIZE));
    }

    // Create cipher instance
    let cipher_key = Key::<Aes256Gcm>::from_slice(key);
    let cipher = Aes256Gcm::new(cipher_key);

    // Convert nonce bytes to Nonce type
    let nonce = Nonce::from_slice(&encrypted.nonce);

    // Decrypt and verify authentication tag
    let plaintext = cipher
        .decrypt(nonce, encrypted.ciphertext.as_ref())
        .map_err(|e| anyhow!("Decryption failed: {}. Data may be tampered or wrong key.", e))?;

    Ok(plaintext)
}

/// Encrypt a string to base64-encoded format for storage
///
/// # Arguments
/// * `key` - 32-byte encryption key
/// * `plaintext` - String to encrypt
///
/// # Returns
/// Base64-encoded encrypted data in format: {nonce_base64}:{ciphertext_base64}
pub fn encrypt_to_base64(key: &[u8; KEY_SIZE], plaintext: &str) -> Result<String> {
    let encrypted = encrypt(key, plaintext.as_bytes())?;

    let nonce_b64 = base64_encode(&encrypted.nonce);
    let ciphertext_b64 = base64_encode(&encrypted.ciphertext);

    Ok(format!("{}:{}", nonce_b64, ciphertext_b64))
}

/// Decrypt from base64-encoded format
///
/// # Arguments
/// * `key` - 32-byte encryption key
/// * `encoded` - Base64-encoded encrypted data in format: {nonce_base64}:{ciphertext_base64}
///
/// # Returns
/// Decrypted string
pub fn decrypt_from_base64(key: &[u8; KEY_SIZE], encoded: &str) -> Result<String> {
    let parts: Vec<&str> = encoded.split(':').collect();
    if parts.len() != 2 {
        return Err(anyhow!("Invalid encrypted data format"));
    }

    let nonce = base64_decode(parts[0])?;
    let ciphertext = base64_decode(parts[1])?;

    let encrypted = EncryptedData { nonce, ciphertext };
    let plaintext_bytes = decrypt(key, &encrypted)?;

    String::from_utf8(plaintext_bytes)
        .map_err(|e| anyhow!("Decrypted data is not valid UTF-8: {}", e))
}

/// Simple base64 encoding using standard alphabet
fn base64_encode(data: &[u8]) -> String {
    use base64::prelude::*;
    BASE64_STANDARD.encode(data)
}

/// Simple base64 decoding
fn base64_decode(encoded: &str) -> Result<Vec<u8>> {
    use base64::prelude::*;
    BASE64_STANDARD
        .decode(encoded)
        .map_err(|e| anyhow!("Base64 decode failed: {}", e))
}

/// Generate a cryptographically secure random key
pub fn generate_key() -> [u8; KEY_SIZE] {
    let mut key = [0u8; KEY_SIZE];
    OsRng.fill_bytes(&mut key);
    key
}

/// Zero out sensitive data in memory
///
/// This is a best-effort attempt to clear sensitive data from memory.
/// Note: compiler optimizations may remove this, and it doesn't protect
/// against memory dumps or swap files.
pub fn zero_bytes(data: &mut [u8]) {
    // Use volatile_write to prevent compiler from optimizing away
    for byte in data.iter_mut() {
        std::ptr::write_volatile(byte, 0);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_encrypt_decrypt_roundtrip() {
        let key = generate_key();
        let plaintext = "This is a secret note";

        let encrypted = encrypt(&key, plaintext.as_bytes()).unwrap();
        let decrypted = decrypt(&key, &encrypted).unwrap();

        assert_eq!(plaintext.as_bytes(), decrypted.as_slice());
    }

    #[test]
    fn test_encrypt_decrypt_base64_roundtrip() {
        let key = generate_key();
        let plaintext = "Secret note with special chars: äöü ñ 漢字";

        let encrypted = encrypt_to_base64(&key, plaintext).unwrap();
        let decrypted = decrypt_from_base64(&key, &encrypted).unwrap();

        assert_eq!(plaintext, decrypted);
    }

    #[test]
    fn test_wrong_key_fails() {
        let key1 = generate_key();
        let key2 = generate_key();
        let plaintext = "Secret data";

        let encrypted = encrypt(&key1, plaintext.as_bytes()).unwrap();

        // Decryption with wrong key should fail
        let result = decrypt(&key2, &encrypted);
        assert!(result.is_err());
    }

    #[test]
    fn test_tampered_data_fails() {
        let key = generate_key();
        let plaintext = "Secret data";

        let mut encrypted = encrypt(&key, plaintext.as_bytes()).unwrap();

        // Tamper with ciphertext
        if let Some(byte) = encrypted.ciphertext.get_mut(0) {
            *byte = byte.wrapping_add(1);
        }

        // Decryption should fail due to authentication tag mismatch
        let result = decrypt(&key, &encrypted);
        assert!(result.is_err());
    }

    #[test]
    fn test_unique_nonces() {
        let key = generate_key();
        let plaintext = "Same plaintext";

        let enc1 = encrypt(&key, plaintext.as_bytes()).unwrap();
        let enc2 = encrypt(&key, plaintext.as_bytes()).unwrap();

        // Nonces should be different
        assert_ne!(enc1.nonce, enc2.nonce);

        // Ciphertexts should be different (due to different nonces)
        assert_ne!(enc1.ciphertext, enc2.ciphertext);
    }

    #[test]
    fn test_invalid_key_size() {
        let small_key = [0u8; 16]; // Wrong size
        let plaintext = "Test";

        let result = encrypt(&small_key, plaintext.as_bytes());
        assert!(result.is_err());
    }

    #[test]
    fn test_empty_data() {
        let key = generate_key();
        let plaintext = "";

        let encrypted = encrypt(&key, plaintext.as_bytes()).unwrap();
        let decrypted = decrypt(&key, &encrypted).unwrap();

        assert_eq!(plaintext.as_bytes(), decrypted.as_slice());
    }
}
