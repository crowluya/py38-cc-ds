//! Cryptographic operations for vault encryption and decryption
//!
//! This module provides secure encryption/decryption using Argon2id for key derivation
//! and AES-256-GCM for authenticated encryption.

use aes_gcm::{
    aead::{Aead, AeadCore, KeyInit, OsRng},
    Aes256Gcm, Nonce,
};
use anyhow::{anyhow, Result};
use argon2::{
    password_hash::{rand_core::OsRng as ArgonOsRng, PasswordHash, PasswordHasher, SaltString},
    Argon2, Params,
};
use zeroize::Zeroize;

/// Size of the encryption key in bytes (256 bits)
const KEY_SIZE: usize = 32;

/// Size of the nonce in bytes (96 bits)
const NONCE_SIZE: usize = 12;

/// Configuration for Argon2id key derivation
#[derive(Debug, Clone)]
pub struct KdfConfig {
    /// Memory cost in KiB (default: 64 MiB)
    pub m_cost: u32,

    /// Time cost (number of iterations)
    pub t_cost: u32,

    /// Parallelism (number of lanes)
    pub p_cost: u32,

    /// Output length (key size in bytes)
    pub output_len: usize,
}

impl Default for KdfConfig {
    fn default() -> Self {
        Self {
            // OWASP recommended parameters as of 2024
            m_cost: 64 * 1024, // 64 MiB
            t_cost: 3,         // 3 iterations
            p_cost: 4,         // 4 lanes
            output_len: KEY_SIZE,
        }
    }
}

/// Encryption result containing nonce and ciphertext
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct EncryptedData {
    pub nonce: Vec<u8>,
    pub ciphertext: Vec<u8>,
}

/// Derives an encryption key from a master password using Argon2id
///
/// # Arguments
/// * `password` - The master password
/// * `salt` - The salt for key derivation (stored with the vault)
/// * `config` - Key derivation function parameters
///
/// # Returns
/// A 32-byte encryption key
pub fn derive_key(password: &str, salt: &str, config: &KdfConfig) -> Result<Vec<u8>> {
    let params = Params::new(config.m_cost, config.t_cost, config.p_cost, config.output_len)
        .map_err(|e| anyhow!("Invalid Argon2 parameters: {}", e))?;

    let argon2 = Argon2::new_with_memory(params, argon2::Algorithm::Argon2id, argon2::Version::V0x13);

    let password_hash = argon2
        .hash_password(password.as_bytes(), SaltString::from_b64(salt).map_err(|e| anyhow!("Invalid salt: {}", e))?)
        .map_err(|e| anyhow!("Key derivation failed: {}", e))?;

    let hash = PasswordHash::parse(&password_hash.to_string(), &argon2::password_hash::Encoding::B64)
        .map_err(|e| anyhow!("Failed to parse password hash: {}", e))?;

    let key = hash.hash.ok_or_else(|| anyhow!("No hash output"))?;
    let key_bytes = key.as_bytes();

    if key_bytes.len() != KEY_SIZE {
        return Err(anyhow!(
            "Invalid key length: expected {} bytes, got {}",
            KEY_SIZE,
            key_bytes.len()
        ));
    }

    Ok(key_bytes.to_vec())
}

/// Generates a new random salt for key derivation
pub fn generate_salt() -> String {
    SaltString::generate(&mut ArgonOsRng).to_string()
}

/// Encrypts data using AES-256-GCM
///
/// # Arguments
/// * `plaintext` - The data to encrypt
/// * `key` - The encryption key (32 bytes)
///
/// # Returns
/// Encrypted data with nonce
pub fn encrypt(plaintext: &[u8], key: &[u8]) -> Result<EncryptedData> {
    if key.len() != KEY_SIZE {
        return Err(anyhow!(
            "Invalid key length: expected {} bytes, got {}",
            KEY_SIZE,
            key.len()
        ));
    }

    let cipher = Aes256Gcm::new(key.into());
    let nonce = Aes256Gcm::generate_nonce(&mut OsRng);

    let ciphertext = cipher
        .encrypt(&nonce, plaintext)
        .map_err(|e| anyhow!("Encryption failed: {}", e))?;

    Ok(EncryptedData {
        nonce: nonce.to_vec(),
        ciphertext,
    })
}

/// Decrypts data using AES-256-GCM
///
/// # Arguments
/// * `encrypted` - The encrypted data with nonce
/// * `key` - The decryption key (32 bytes)
///
/// # Returns
/// The decrypted plaintext
pub fn decrypt(encrypted: &EncryptedData, key: &[u8]) -> Result<Vec<u8>> {
    if key.len() != KEY_SIZE {
        return Err(anyhow!(
            "Invalid key length: expected {} bytes, got {}",
            KEY_SIZE,
            key.len()
        ));
    }

    if encrypted.nonce.len() != NONCE_SIZE {
        return Err(anyhow!(
            "Invalid nonce length: expected {} bytes, got {}",
            NONCE_SIZE,
            encrypted.nonce.len()
        ));
    }

    let cipher = Aes256Gcm::new(key.into());
    let nonce = Nonce::from_slice(&encrypted.nonce);

    let plaintext = cipher
        .decrypt(nonce, encrypted.ciphertext.as_ref())
        .map_err(|e| anyhow!("Decryption failed: {}", e))?;

    Ok(plaintext)
}

/// Securely zeroes out sensitive data
pub fn secure_zero<T: Zeroize>(data: &mut T) {
    data.zeroize();
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_key_derivation() {
        let password = "test_password_123";
        let salt = generate_salt();
        let config = KdfConfig::default();

        let key1 = derive_key(password, &salt, &config).unwrap();
        let key2 = derive_key(password, &salt, &config).unwrap();

        assert_eq!(key1, key2, "Same password and salt should produce same key");
        assert_eq!(key1.len(), KEY_SIZE);
    }

    #[test]
    fn test_different_passwords_different_keys() {
        let salt = generate_salt();
        let config = KdfConfig::default();

        let key1 = derive_key("password1", &salt, &config).unwrap();
        let key2 = derive_key("password2", &salt, &config).unwrap();

        assert_ne!(key1, key2, "Different passwords should produce different keys");
    }

    #[test]
    fn test_encryption_decryption() {
        let plaintext = b"Hello, secure world!";
        let key = vec![0u8; KEY_SIZE]; // Test key (all zeros)

        let encrypted = encrypt(plaintext, &key).unwrap();
        let decrypted = decrypt(&encrypted, &key).unwrap();

        assert_eq!(plaintext.to_vec(), decrypted, "Decrypted text should match original");
    }

    #[test]
    fn test_wrong_key_fails() {
        let plaintext = b"Secret data";
        let key1 = vec![1u8; KEY_SIZE];
        let key2 = vec![2u8; KEY_SIZE];

        let encrypted = encrypt(plaintext, &key1).unwrap();
        let result = decrypt(&encrypted, &key2);

        assert!(result.is_err(), "Decryption with wrong key should fail");
    }

    #[test]
    fn test_salt_generation() {
        let salt1 = generate_salt();
        let salt2 = generate_salt();

        assert_ne!(salt1, salt2, "Each salt should be unique");
    }
}
