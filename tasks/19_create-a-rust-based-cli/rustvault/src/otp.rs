//! TOTP (Time-based One-Time Password) functionality
//!
//! This module implements TOTP code generation according to RFC 6238,
//! supporting various hash algorithms and time steps.

use anyhow::{anyhow, Result};
use chrono::{Duration, Utc};
use std::time::SystemTime;

/// Default TOTP time step in seconds
const DEFAULT_TIME_STEP: u64 = 30;

/// Default TOTP digit count
const DEFAULT_DIGITS: u32 = 6;

/// TOTP configuration
#[derive(Debug, Clone)]
pub struct TotpConfig {
    /// Time step in seconds (default: 30)
    pub time_step: u64,

    /// Number of digits (6 or 8)
    pub digits: u32,

    /// Hash algorithm (SHA1, SHA256, SHA512)
    pub algorithm: TotpAlgorithm,
}

impl Default for TotpConfig {
    fn default() -> Self {
        Self {
            time_step: DEFAULT_TIME_STEP,
            digits: DEFAULT_DIGITS,
            algorithm: TotpAlgorithm::Sha1,
        }
    }
}

/// TOTP hash algorithms
#[derive(Debug, Clone, Copy)]
pub enum TotpAlgorithm {
    Sha1,
    Sha256,
    Sha512,
}

impl TotpAlgorithm {
    /// Gets the hash size in bytes
    fn hash_size(&self) -> usize {
        match self {
            TotpAlgorithm::Sha1 => 20,
            TotpAlgorithm::Sha256 => 32,
            TotpAlgorithm::Sha512 => 64,
        }
    }
}

/// TOTP code with metadata
#[derive(Debug, Clone)]
pub struct TotpCode {
    /// The current TOTP code
    pub code: String,

    /// Seconds remaining until code expires
    pub remaining_seconds: u64,

    /// Total time step duration
    pub time_step: u64,
}

/// Generates a TOTP code from a base32-encoded secret
pub fn generate_totp(secret: &str, config: &TotpConfig) -> Result<TotpCode> {
    // Decode base32 secret
    let secret_bytes = decode_base32_secret(secret)?;

    // Get current time counter
    let counter = calculate_time_counter(config.time_step)?;

    // Generate HOTP for the counter
    let code = generate_hotp(&secret_bytes, counter, config.digits, config.algorithm)?;

    // Calculate time remaining
    let now = Utc::now();
    let elapsed = now.timestamp() as u64 % config.time_step;
    let remaining = config.time_step - elapsed;

    Ok(TotpCode {
        code,
        remaining_seconds: remaining,
        time_step: config.time_step,
    })
}

/// Generates a TOTP code with default settings
pub fn generate_totp_default(secret: &str) -> Result<TotpCode> {
    generate_totp(secret, &TotpConfig::default())
}

/// Decodes a base32-encoded secret
fn decode_base32_secret(secret: &str) -> Result<Vec<u8>> {
    // Clean the secret (remove spaces, convert to uppercase)
    let cleaned: String = secret
        .chars()
        .map(|c| c.to_ascii_uppercase())
        .filter(|c| c.is_ascii_alphanumeric())
        .collect();

    // Use base32 crate for decoding
    let bytes = base32::decode(base32::Alphabet::RFC4648 { padding: true }, &cleaned)
        .ok_or_else(|| anyhow!("Invalid base32 secret"))?;

    if bytes.is_empty() {
        return Err(anyhow!("Secret is empty after decoding"));
    }

    Ok(bytes)
}

/// Encodes bytes to base32
pub fn encode_base32_secret(bytes: &[u8]) -> String {
    base32::encode(base32::Alphabet::RFC4648 { padding: true }, bytes)
}

/// Calculates the time counter for TOTP
fn calculate_time_counter(time_step: u64) -> Result<u64> {
    let now = SystemTime::now()
        .duration_since(SystemTime::UNIX_EPOCH)
        .map_err(|e| anyhow!("Failed to get system time: {}", e))?;

    Ok(now.as_secs() / time_step)
}

/// Generates an HMAC-based One-Time Password (HOTP)
fn generate_hotp(secret: &[u8], counter: u64, digits: u32, algorithm: TotpAlgorithm) -> Result<String> {
    use hmac::{Hmac, Mac};
    use sha1::Sha1;
    use sha2::{Sha256, Sha512};

    // Convert counter to bytes (big-endian)
    let counter_bytes = counter.to_be_bytes();

    // Create HMAC based on algorithm
    let hmac_output = match algorithm {
        TotpAlgorithm::Sha1 => {
            type HmacSha1 = Hmac<Sha1>;
            let mut mac = HmacSha1::new_from_slice(secret)
                .map_err(|e| anyhow!("Invalid HMAC key: {}", e))?;
            mac.update(&counter_bytes);
            mac.finalize().into_bytes().to_vec()
        }
        TotpAlgorithm::Sha256 => {
            type HmacSha256 = Hmac<Sha256>;
            let mut mac = HmacSha256::new_from_slice(secret)
                .map_err(|e| anyhow!("Invalid HMAC key: {}", e))?;
            mac.update(&counter_bytes);
            mac.finalize().into_bytes().to_vec()
        }
        TotpAlgorithm::Sha512 => {
            type HmacSha512 = Hmac<Sha512>;
            let mut mac = HmacSha512::new_from_slice(secret)
                .map_err(|e| anyhow!("Invalid HMAC key: {}", e))?;
            mac.update(&counter_bytes);
            mac.finalize().into_bytes().to_vec()
        }
    };

    // Dynamic truncation
    let offset = (hmac_output.last().unwrap() & 0x0f) as usize;
    let binary = ((hmac_output[offset] & 0x7f) as u32) << 24
        | ((hmac_output[offset + 1] & 0xff) as u32) << 16
        | ((hmac_output[offset + 2] & 0xff) as u32) << 8
        | (hmac_output[offset + 3] & 0xff) as u32;

    let otp = binary % 10u32.pow(digits);
    Ok(format!("{:0width$}", otp, width = digits as usize))
}

/// Validates a TOTP code (checks if it matches within a window of time steps)
pub fn validate_totp(secret: &str, code: &str, config: &TotpConfig, window: u64) -> Result<bool> {
    let secret_bytes = decode_base32_secret(secret)?;
    let counter = calculate_time_counter(config.time_step)?;

    // Check current and adjacent time steps
    for i in 0..=(window * 2 + 1) {
        let offset = i as i64 - window as i64;
        let check_counter = (counter as i64 + offset) as u64;

        let expected_code = generate_hotp(&secret_bytes, check_counter, config.digits, config.algorithm)?;

        if expected_code == code {
            return Ok(true);
        }
    }

    Ok(false)
}

/// Generates a random TOTP secret (base32 encoded)
pub fn generate_secret() -> String {
    use rand::Rng;
    const SECRET_SIZE: usize = 20; // 160 bits

    let mut rng = rand::thread_rng();
    let secret: Vec<u8> = (0..SECRET_SIZE).map(|_| rng.gen()).collect();

    encode_base32_secret(&secret)
}

/// Gets the URL for setting up TOTP in authenticator apps (OTP URL format)
pub fn get_otp_url(account_name: &str, secret: &str, issuer: &str) -> String {
    let encoded_account = urlencoding::encode(account_name);
    let encoded_issuer = urlencoding::encode(issuer);
    format!(
        "otpauth://totp/{}:{}?secret={}&issuer={}&algorithm=SHA1&digits=6&period=30",
        encoded_issuer, encoded_account, secret, encoded_issuer
    )
}

/// Formats remaining time in a human-readable way
pub fn format_time_remaining(seconds: u64) -> String {
    if seconds < 10 {
        format!("{}s", seconds)
    } else {
        format!("{}s", seconds)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_secret_generation() {
        let secret = generate_secret();
        assert!(!secret.is_empty());
        assert!(secret.len() > 20);

        // Verify it's valid base32
        let decoded = decode_base32_secret(&secret);
        assert!(decoded.is_ok());
    }

    #[test]
    fn test_base32_encoding() {
        let bytes = b"HelloWorld";
        let encoded = encode_base32_secret(bytes);
        let decoded = decode_base32_secret(&encoded).unwrap();
        assert_eq!(bytes.to_vec(), decoded);
    }

    #[test]
    fn test_totp_generation() {
        let secret = "JBSWY3DPEHPK3PXP"; // Known test secret
        let code = generate_totp_default(secret).unwrap();
        assert_eq!(code.code.len(), 6);
        assert!(code.remaining_seconds <= 30);
    }

    #[test]
    fn test_hotp_known_values() {
        // Test vectors from RFC 4226
        let secret = decode_base32_secret("12345678901234567890").unwrap();

        let code0 = generate_hotp(&secret, 0, 6, TotpAlgorithm::Sha1).unwrap();
        assert_eq!(code0, "755224");

        let code1 = generate_hotp(&secret, 1, 6, TotpAlgorithm::Sha1).unwrap();
        assert_eq!(code1, "287082");
    }

    #[test]
    fn test_totp_different_algorithms() {
        let secret = generate_secret();

        let config_sha1 = TotpConfig {
            algorithm: TotpAlgorithm::Sha1,
            ..Default::default()
        };
        let code_sha1 = generate_totp(&secret, &config_sha1).unwrap();

        let config_sha256 = TotpConfig {
            algorithm: TotpAlgorithm::Sha256,
            ..Default::default()
        };
        let code_sha256 = generate_totp(&secret, &config_sha256).unwrap();

        // Codes should likely be different with different algorithms
        // (though not guaranteed due to timing)
        assert_eq!(code_sha1.code.len(), 6);
        assert_eq!(code_sha256.code.len(), 6);
    }

    #[test]
    fn test_totp_validation() {
        let secret = generate_secret();
        let config = TotpConfig::default();

        let totp = generate_totp(&secret, &config).unwrap();
        let valid = validate_totp(&secret, &totp.code, &config, 0).unwrap();

        assert!(valid);
    }

    #[test]
    fn test_invalid_secret() {
        let result = decode_base32_secret("invalid@#$");
        assert!(result.is_err());
    }

    #[test]
    fn test_otp_url_format() {
        let secret = "JBSWY3DPEHPK3PXP";
        let url = get_otp_url("user@example.com", secret, "ServiceName");

        assert!(url.starts_with("otpauth://totp/"));
        assert!(url.contains(&format!("secret={}", secret)));
        assert!(url.contains("issuer=ServiceName"));
    }

    #[test]
    fn test_time_remaining() {
        let secret = generate_secret();
        let totp = generate_totp_default(secret).unwrap();

        assert!(totp.remaining_seconds > 0);
        assert!(totp.remaining_seconds <= 30);
    }
}
