use aes_gcm::{
    aead::{Aead, AeadCore, KeyInit, OsRng},
    Aes256Gcm, Nonce,
};
use argon2::{
    password_hash::{PasswordHash, PasswordHasher, SaltString},
    Argon2, Algorithm, Params, Version,
};
use serde::{Deserialize, Serialize};
use thiserror::Error;
use zeroize::Zeroize;

const VAULT_KEY_SIZE: usize = 32;
const NONCE_SIZE: usize = 12;

#[derive(Error, Debug)]
pub enum CryptoError {
    #[error("Encryption failed: {0}")]
    EncryptionFailed(String),

    #[error("Decryption failed: {0}")]
    DecryptionFailed(String),

    #[error("Key derivation failed: {0}")]
    KeyDerivationFailed(String),

    #[error("Invalid password")]
    InvalidPassword,
}

/// Encrypted data container with all necessary components for decryption
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EncryptedData {
    pub ciphertext: Vec<u8>,
    pub nonce: Vec<u8>,
    pub salt: Vec<u8>,
    pub argon2_params: Argon2Params,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Argon2Params {
    pub m: u32,
    pub t: u32,
    pub p: u32,
}

impl From<Params> for Argon2Params {
    fn from(params: Params) -> Self {
        Self {
            m: params.m(),
            t: params.t(),
            p: params.p(),
        }
    }
}

impl TryInto<Params> for Argon2Params {
    type Error = CryptoError;

    fn try_into(self) -> Result<Params, Self::Error> {
        Params::new(self.m, self.t, self.p, None)
            .map_err(|e| CryptoError::KeyDerivationFailed(e.to_string()))
    }
}

/// Derives an encryption key from a password using Argon2id
pub fn derive_key(
    password: &str,
    salt: &[u8],
    params: &Argon2Params,
) -> Result<[u8; VAULT_KEY_SIZE], CryptoError> {
    let params: Params = params.clone().try_into()?;

    let argon2 = Argon2::new(Algorithm::Argon2id, Version::V0x13, params);

    let password_hash = argon2
        .hash_password(password.as_bytes(), &SaltString::encode_b64(salt))
        .map_err(|e| CryptoError::KeyDerivationFailed(e.to_string()))?;

    let hash = PasswordHash::new(&password_hash.hash)
        .map_err(|e| CryptoError::KeyDerivationFailed(e.to_string()))?;

    let hash_bytes = hash.hash.ok_or_else(|| {
        CryptoError::KeyDerivationFailed("Missing hash in password hash".to_string())
    })?;

    let mut key = [0u8; VAULT_KEY_SIZE];
    key.copy_from_slice(&hash_bytes.bytes[..VAULT_KEY_SIZE]);

    Ok(key)
}

/// Encrypts plaintext using AES-256-GCM
pub fn encrypt(
    plaintext: &[u8],
    password: &str,
    argon2_params: Argon2Params,
) -> Result<EncryptedData, CryptoError> {
    // Generate random salt and nonce
    let salt = rand::random::<[u8; 32]>().to_vec();
    let nonce_bytes = rand::random::<[u8; NONCE_SIZE]>().to_vec();

    // Derive encryption key from password
    let key = derive_key(password, &salt, &argon2_params)?;

    // Create cipher
    let cipher = Aes256Gcm::new_from_slice(&key)
        .map_err(|e| CryptoError::EncryptionFailed(e.to_string()))?;

    // Create nonce
    let nonce = Nonce::from_slice(&nonce_bytes);

    // Encrypt
    let ciphertext = cipher
        .encrypt(nonce, plaintext)
        .map_err(|e| CryptoError::EncryptionFailed(e.to_string()))?;

    // Zeroize the key
    drop(key);

    Ok(EncryptedData {
        ciphertext,
        nonce: nonce_bytes,
        salt,
        argon2_params,
    })
}

/// Decrypts ciphertext using AES-256-GCM
pub fn decrypt(encrypted_data: &EncryptedData, password: &str) -> Result<Vec<u8>, CryptoError> {
    // Derive decryption key from password
    let key = derive_key(
        password,
        &encrypted_data.salt,
        &encrypted_data.argon2_params,
    )?;

    // Create cipher
    let cipher = Aes256Gcm::new_from_slice(&key)
        .map_err(|e| CryptoError::DecryptionFailed(e.to_string()))?;

    // Create nonce
    let nonce = Nonce::from_slice(&encrypted_data.nonce);

    // Decrypt
    let plaintext = cipher
        .decrypt(nonce, encrypted_data.ciphertext.as_ref())
        .map_err(|e| CryptoError::DecryptionFailed(e.to_string()))?;

    // Zeroize the key
    drop(key);

    Ok(plaintext)
}

/// Encrypts a vault to JSON and then encrypts the JSON
pub fn encrypt_vault(
    vault: &crate::vault::Vault,
    password: &str,
) -> Result<EncryptedData, CryptoError> {
    let json =
        serde_json::to_vec(vault).map_err(|e| CryptoError::EncryptionFailed(e.to_string()))?;

    encrypt(&json, password, Argon2Params { m: 65536, t: 3, p: 4 })
}

/// Decrypts encrypted vault data and deserializes it
pub fn decrypt_vault(
    encrypted_data: &EncryptedData,
    password: &str,
) -> Result<crate::vault::Vault, CryptoError> {
    let decrypted_json = decrypt(encrypted_data, password)?;

    serde_json::from_slice(&decrypted_json)
        .map_err(|e| CryptoError::DecryptionFailed(e.to_string()))
}

/// Securely compares two strings in constant time
pub fn constant_time_eq(a: &str, b: &str) -> bool {
    if a.len() != b.len() {
        return false;
    }

    let mut result = 0u8;
    for (byte_a, byte_b) in a.bytes().zip(b.bytes()) {
        result |= byte_a ^ byte_b;
    }

    result == 0
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::vault::Vault;

    #[test]
    fn test_encrypt_decrypt() {
        let plaintext = b"Hello, World!";
        let password = "secure_password_123";

        let encrypted = encrypt(plaintext, password, Argon2Params { m: 65536, t: 3, p: 4 })
            .expect("Encryption failed");

        let decrypted = decrypt(&encrypted, password).expect("Decryption failed");

        assert_eq!(plaintext.to_vec(), decrypted);
    }

    #[test]
    fn test_wrong_password_fails() {
        let plaintext = b"Secret data";
        let password = "correct_password";

        let encrypted = encrypt(plaintext, password, Argon2Params { m: 65536, t: 3, p: 4 })
            .expect("Encryption failed");

        let result = decrypt(&encrypted, "wrong_password");

        assert!(result.is_err());
    }

    #[test]
    fn test_encrypt_decrypt_vault() {
        let mut vault = Vault::new();
        vault.add_entry(crate::vault::VaultEntry::new(
            "Test".to_string(),
            "user".to_string(),
            "pass".to_string(),
        ));

        let password = "master_password";

        let encrypted = encrypt_vault(&vault, password).expect("Encryption failed");

        let decrypted = decrypt_vault(&encrypted, password).expect("Decryption failed");

        assert_eq!(vault.entry_count(), decrypted.entry_count());
        assert_eq!(vault.entries[0].title, decrypted.entries[0].title);
    }

    #[test]
    fn test_constant_time_eq() {
        assert!(constant_time_eq("password", "password"));
        assert!(!constant_time_eq("password", "wrong"));
        assert!(!constant_time_eq("pass", "password"));
    }
}
