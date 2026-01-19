use crate::error::{PasswordManagerError, Result};
use aes_gcm::{
    aead::{Aead, AeadCore, KeyInit, OsRng},
    Aes256Gcm, Nonce,
};
use argon2::{
    password_hash::{rand_core::OsRng as ArgonOsRng, PasswordHasher, SaltString},
    Argon2, Params,
};
use zeroize::Zeroize;

/// Derives a 256-bit encryption key from the master password and salt
///
/// Uses Argon2id with secure parameters:
/// - t=3 iterations
/// - m=64MB memory
/// - p=4 parallelism
/// - output length = 32 bytes (256 bits)
pub fn derive_key(master_password: &str, salt: &[u8; 32]) -> [u8; 32] {
    // Argon2id with secure parameters (OWASP recommendations)
    let params = Params::new(65536, 3, 4, None).expect("Failed to create Argon2 params");

    let argon2 = Argon2::new(argon2::Algorithm::Argon2id, argon2::Version::V0x13, params);

    // Prepare the password hash
    let password_bytes = master_password.as_bytes();

    // Derive the key using Argon2
    let mut key = [0u8; 32];
    argon2
        .hash_password_into(password_bytes, salt, &mut key)
        .expect("Failed to derive key");

    key
}

/// Encrypts vault data using AES-256-GCM
///
/// Returns the encrypted data and the nonce used for encryption
pub fn encrypt_vault(data: &[u8], key: &[u8; 32]) -> Result<(Vec<u8>, [u8; 12])> {
    // Create cipher from key
    let cipher = Aes256Gcm::new(key.into());

    // Generate random nonce (96-bit as recommended for GCM)
    let nonce = Aes256Gcm::generate_nonce(&mut OsRng);

    // Encrypt the data
    let ciphertext = cipher
        .encrypt(&nonce, data)
        .map_err(|e| PasswordManagerError::EncryptionFailed(e.to_string()))?;

    // Copy nonce to array
    let nonce_array = nonce.into();

    Ok((ciphertext, nonce_array))
}

/// Decrypts vault data using AES-256-GCM
///
/// Verifies authentication tag during decryption
pub fn decrypt_vault(encrypted_data: &[u8], nonce: &[u8; 12], key: &[u8; 32]) -> Result<Vec<u8>> {
    // Create cipher from key
    let cipher = Aes256Gcm::new(key.into());

    // Create nonce from array
    let nonce = Nonce::from_slice(nonce);

    // Decrypt and verify
    let plaintext = cipher
        .decrypt(nonce, encrypted_data)
        .map_err(|e| PasswordManagerError::DecryptionFailed(e.to_string()))?;

    Ok(plaintext)
}

/// Securely wipes sensitive data from memory
pub fn secure_wipe(data: &mut Vec<u8>) {
    data.zeroize();
}

/// Securely wipes a string from memory
pub fn secure_wipe_string(s: &mut String) {
    s.zeroize();
}

/// Wrapper for sensitive strings that automatically zeroizes on drop
#[derive(Clone, Debug)]
pub struct SecureString {
    data: String,
}

impl SecureString {
    pub fn new(s: String) -> Self {
        Self { data: s }
    }

    pub fn as_str(&self) -> &str {
        &self.data
    }

    pub fn into_string(self) -> String {
        self.data
    }
}

impl Drop for SecureString {
    fn drop(&mut self) {
        self.data.zeroize();
    }
}

impl From<String> for SecureString {
    fn from(s: String) -> Self {
        Self::new(s)
    }
}

/// Generates a random salt for key derivation
pub fn generate_salt() -> [u8; 32] {
    let mut salt = [0u8; 32];
    use rand::RngCore;
    OsRng.fill_bytes(&mut salt);
    salt
}

/// Generates a random nonce for encryption
pub fn generate_nonce() -> [u8; 12] {
    let mut nonce = [0u8; 12];
    use rand::RngCore;
    OsRng.fill_bytes(&mut nonce);
    nonce
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_key_derivation() {
        let password = "test_password_123!";
        let salt = generate_salt();

        let key1 = derive_key(password, &salt);
        let key2 = derive_key(password, &salt);

        assert_eq!(key1, key2, "Same input should produce same key");
        assert_eq!(key1.len(), 32, "Key should be 256 bits");
    }

    #[test]
    fn test_different_passwords_different_keys() {
        let salt = generate_salt();
        let key1 = derive_key("password1", &salt);
        let key2 = derive_key("password2", &salt);

        assert_ne!(key1, key2, "Different passwords should produce different keys");
    }

    #[test]
    fn test_encryption_decryption_roundtrip() {
        let key = [0u8; 32]; // Simplified for testing
        let plaintext = b"Hello, this is a test vault data!";

        let (encrypted, nonce) = encrypt_vault(plaintext, &key).unwrap();

        assert!(!encrypted.is_empty(), "Encrypted data should not be empty");
        assert_ne!(encrypted, plaintext.to_vec(), "Encrypted data should differ from plaintext");

        let decrypted = decrypt_vault(&encrypted, &nonce, &key).unwrap();

        assert_eq!(decrypted, plaintext, "Decrypted text should match original");
    }

    #[test]
    fn test_decryption_with_wrong_key_fails() {
        let key1 = [1u8; 32];
        let key2 = [2u8; 32];
        let plaintext = b"Secret data";

        let (encrypted, nonce) = encrypt_vault(plaintext, &key1).unwrap();

        let result = decrypt_vault(&encrypted, &nonce, &key2);
        assert!(result.is_err(), "Decryption with wrong key should fail");
    }

    #[test]
    fn test_wrong_nonce_fails() {
        let key = [0u8; 32];
        let plaintext = b"Test data";

        let (encrypted, _nonce) = encrypt_vault(plaintext, &key).unwrap();
        let wrong_nonce = [99u8; 12];

        let result = decrypt_vault(&encrypted, &wrong_nonce, &key);
        assert!(result.is_err(), "Decryption with wrong nonce should fail");
    }

    #[test]
    fn test_secure_string() {
        let s = SecureString::new("Sensitive data".to_string());
        assert_eq!(s.as_str(), "Sensitive data");
    }

    #[test]
    fn test_generate_salt() {
        let salt1 = generate_salt();
        let salt2 = generate_salt();

        assert_ne!(salt1, salt2, "Each salt should be unique");
        assert_eq!(salt1.len(), 32, "Salt should be 256 bits");
    }

    #[test]
    fn test_generate_nonce() {
        let nonce1 = generate_nonce();
        let nonce2 = generate_nonce();

        assert_ne!(nonce1, nonce2, "Each nonce should be unique");
        assert_eq!(nonce1.len(), 12, "Nonce should be 96 bits");
    }
}
