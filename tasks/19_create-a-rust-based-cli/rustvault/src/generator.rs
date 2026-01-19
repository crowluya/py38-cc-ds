//! Password generation with configurable policies
//!
//! This module provides secure password generation with various options including
//! character sets, passphrases, and strength estimation.

use rand::Rng;
use anyhow::{anyhow, Result};

/// Password generation policy
#[derive(Debug, Clone)]
pub struct PasswordPolicy {
    /// Minimum password length
    pub min_length: usize,

    /// Maximum password length
    pub max_length: usize,

    /// Include uppercase letters (A-Z)
    pub uppercase: bool,

    /// Include lowercase letters (a-z)
    pub lowercase: bool,

    /// Include digits (0-9)
    pub digits: bool,

    /// Include symbols/special characters
    pub symbols: bool,

    /// Exclude ambiguous characters (0/O, 1/l/I)
    pub exclude_ambiguous: bool,

    /// Exclude similar characters (i, l, 1, L, o, 0, O)
    pub exclude_similar: bool,
}

impl Default for PasswordPolicy {
    fn default() -> Self {
        Self {
            min_length: 16,
            max_length: 16,
            uppercase: true,
            lowercase: true,
            digits: true,
            symbols: true,
            exclude_ambiguous: false,
            exclude_similar: false,
        }
    }
}

impl PasswordPolicy {
    /// Creates a new policy with specified length
    pub fn new(length: usize) -> Self {
        Self {
            min_length: length,
            max_length: length,
            ..Default::default()
        }
    }

    /// Validates the policy configuration
    pub fn validate(&self) -> Result<()> {
        if self.min_length < 8 {
            return Err(anyhow!("Password length must be at least 8 characters"));
        }
        if self.max_length > 128 {
            return Err(anyhow!("Password length must not exceed 128 characters"));
        }
        if self.min_length > self.max_length {
            return Err(anyhow!("min_length cannot be greater than max_length"));
        }

        if !self.uppercase && !self.lowercase && !self.digits && !self.symbols {
            return Err(anyhow!("At least one character type must be enabled"));
        }

        Ok(())
    }
}

/// Passphrase generation policy
#[derive(Debug, Clone)]
pub struct PassphrasePolicy {
    /// Number of words in the passphrase
    pub word_count: usize,

    /// Separator between words
    pub separator: String,

    /// Capitalize each word
    pub capitalize: bool,

    /// Include a number in the passphrase
    pub include_number: bool,
}

impl Default for PassphrasePolicy {
    fn default() -> Self {
        Self {
            word_count: 5,
            separator: "-".to_string(),
            capitalize: false,
            include_number: false,
        }
    }
}

/// Password strength level
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum PasswordStrength {
    Weak,
    Fair,
    Good,
    Strong,
    VeryStrong,
}

impl PasswordStrength {
    /// Gets a description of the strength level
    pub fn description(&self) -> &str {
        match self {
            PasswordStrength::Weak => "Weak",
            PasswordStrength::Fair => "Fair",
            PasswordStrength::Good => "Good",
            PasswordStrength::Strong => "Strong",
            PasswordStrength::VeryStrong => "Very Strong",
        }
    }
}

/// Character sets for password generation
const LOWERCASE: &str = "abcdefghijklmnopqrstuvwxyz";
const UPPERCASE: &str = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
const DIGITS: &str = "0123456789";
const SYMBOLS: &str = "!@#$%^&*()_+-=[]{}|;:,.<>?";

/// Ambiguous characters
const AMBIGUOUS: &str = "0O1lI";

/// Similar characters
const SIMILAR: &str = "il1Lo0O";

/// Common words for passphrase generation
const WORD_LIST: &[&str] = &[
    "correct", "horse", "battery", "staple", "cloud", "mountain", "river", "forest",
    "ocean", "desert", "sky", "thunder", "lightning", "rain", "snow", "wind", "fire",
    "earth", "stone", "metal", "glass", "wood", "paper", "canvas", "brush", "pencil",
    "planet", "star", "moon", "galaxy", "universe", "quantum", "physics", "chemistry",
    "biology", "geology", "history", "philosophy", "art", "music", "dance", "theater",
    "literature", "poetry", "novel", "story", "legend", "myth", "adventure", "journey",
    "bridge", "castle", "tower", "palace", "garden", "park", "forest", "meadow", "valley",
    "canyon", "peak", "summit", "horizon", "sunset", "sunrise", "dawn", "dusk", "twilight",
    "shadow", "light", "darkness", "brightness", "color", "sound", "silence", "echo",
    "rhythm", "melody", "harmony", "balance", "peace", "joy", "hope", "dream", "wish",
    "wonder", "magic", "mystery", "secret", "treasure", "gift", "blessing", "gratitude",
    "courage", "wisdom", "justice", "freedom", "truth", "beauty", "love", "friendship",
];

/// Generates a random password based on the specified policy
pub fn generate_password(policy: &PasswordPolicy) -> Result<String> {
    policy.validate()?;

    let mut charset = String::new();
    let mut required_chars = Vec::new();

    // Build character set based on policy
    if policy.lowercase {
        let chars = if policy.exclude_similar {
            LOWERCASE.replace(&['i', 'l'][..], "")
        } else {
            LOWERCASE.to_string()
        };
        charset.push_str(&chars);
        // Ensure at least one lowercase character
        required_chars.push(random_char_from_set(&chars));
    }

    if policy.uppercase {
        let chars = if policy.exclude_similar {
            UPPERCASE.replace(&['I', 'L', 'O'][..], "")
        } else if policy.exclude_ambiguous {
            UPPERCASE.replace(&['O', 'I'][..], "")
        } else {
            UPPERCASE.to_string()
        };
        charset.push_str(&chars);
        required_chars.push(random_char_from_set(&chars));
    }

    if policy.digits {
        let chars = if policy.exclude_similar || policy.exclude_ambiguous {
            DIGITS.replace(&['0', '1'][..], "")
        } else {
            DIGITS.to_string()
        };
        charset.push_str(&chars);
        required_chars.push(random_char_from_set(&chars));
    }

    if policy.symbols {
        charset.push_str(SYMBOLS);
        required_chars.push(random_char_from_set(SYMBOLS));
    }

    if charset.is_empty() {
        return Err(anyhow!("No valid characters available for password generation"));
    }

    let length = policy.min_length;
    let mut password = String::with_capacity(length);
    let mut rng = rand::thread_rng();

    // Fill remaining length with random characters from full charset
    for _ in 0..(length.saturating_sub(required_chars.len())) {
        let idx = rng.gen_range(0..charset.len());
        password.push(charset.chars().nth(idx).unwrap());
    }

    // Add required characters
    for c in required_chars {
        let idx = rng.gen_range(0..=password.len());
        password.insert(idx, c);
    }

    Ok(password)
}

/// Generates a random passphrase based on the specified policy
pub fn generate_passphrase(policy: &PassphrasePolicy) -> Result<String> {
    if policy.word_count < 3 {
        return Err(anyhow!("Passphrase must have at least 3 words"));
    }
    if policy.word_count > 10 {
        return Err(anyhow!("Passphrase must not exceed 10 words"));
    }

    let mut rng = rand::thread_rng();
    let mut words: Vec<String> = Vec::with_capacity(policy.word_count);

    for _ in 0..policy.word_count {
        let idx = rng.gen_range(0..WORD_LIST.len());
        let mut word = WORD_LIST[idx].to_string();
        if policy.capitalize {
            word = word.chars().enumerate().map(|(i, c)| {
                if i == 0 { c.to_ascii_uppercase() } else { c }
            }).collect();
        }
        words.push(word);
    }

    // Add number if requested
    if policy.include_number {
        let num: u32 = rng.gen_range(0..1000);
        words.push(num.to_string());
    }

    Ok(words.join(&policy.separator))
}

/// Estimates password strength based on various factors
pub fn estimate_strength(password: &str) -> PasswordStrength {
    let length = password.len();
    let has_lower = password.chars().any(|c| c.is_ascii_lowercase());
    let has_upper = password.chars().any(|c| c.is_ascii_uppercase());
    let has_digit = password.chars().any(|c| c.is_ascii_digit());
    let has_symbol = password.chars().any(|c| !c.is_alphanumeric());

    // Calculate entropy approximation
    let charset_size = if has_lower { 26 } else { 0 }
        + if has_upper { 26 } else { 0 }
        + if has_digit { 10 } else { 0 }
        + if has_symbol { 32 } else { 0 };

    let entropy = if charset_size > 0 {
        length as f64 * (charset_size as f64).log2()
    } else {
        0.0
    };

    // Add variety bonus
    let variety_bonus = [has_lower, has_upper, has_digit, has_symbol]
        .iter()
        .filter(|&&x| x)
        .count() as f64 * 5.0;

    let total_score = entropy + variety_bonus;

    match total_score {
        s if s < 40.0 => PasswordStrength::Weak,
        s if s < 60.0 => PasswordStrength::Fair,
        s if s < 80.0 => PasswordStrength::Good,
        s if s < 100.0 => PasswordStrength::Strong,
        _ => PasswordStrength::VeryStrong,
    }
}

/// Gets entropy bits of a password
pub fn get_entropy_bits(password: &str) -> f64 {
    let has_lower = password.chars().any(|c| c.is_ascii_lowercase());
    let has_upper = password.chars().any(|c| c.is_ascii_uppercase());
    let has_digit = password.chars().any(|c| c.is_ascii_digit());
    let has_symbol = password.chars().any(|c| !c.is_alphanumeric());

    let charset_size = if has_lower { 26 } else { 0 }
        + if has_upper { 26 } else { 0 }
        + if has_digit { 10 } else { 0 }
        + if has_symbol { 32 } else { 0 };

    if charset_size == 0 {
        0.0
    } else {
        password.len() as f64 * (charset_size as f64).log2()
    }
}

/// Helper function to get a random character from a character set
fn random_char_from_set(set: &str) -> char {
    let mut rng = rand::thread_rng();
    let idx = rng.gen_range(0..set.len());
    set.chars().nth(idx).unwrap()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_password_generation() {
        let policy = PasswordPolicy::default();
        let password = generate_password(&policy).unwrap();
        assert_eq!(password.len(), 16);
    }

    #[test]
    fn test_custom_length() {
        let policy = PasswordPolicy::new(24);
        let password = generate_password(&policy).unwrap();
        assert_eq!(password.len(), 24);
    }

    #[test]
    fn test_no_symbols() {
        let mut policy = PasswordPolicy::new(16);
        policy.symbols = false;
        let password = generate_password(&policy).unwrap();
        assert!(password.chars().all(|c| c.is_alphanumeric()));
    }

    #[test]
    fn test_exclude_ambiguous() {
        let mut policy = PasswordPolicy::new(32);
        policy.exclude_ambiguous = true;
        let password = generate_password(&policy).unwrap();
        assert!(!password.contains('0') || !password.contains('O'));
    }

    #[test]
    fn test_minimum_length_validation() {
        let policy = PasswordPolicy::new(4);
        assert!(policy.validate().is_err());
    }

    #[test]
    fn test_passphrase_generation() {
        let policy = PassphrasePolicy::default();
        let passphrase = generate_passphrase(&policy).unwrap();
        let word_count = passphrase.split('-').count();
        assert_eq!(word_count, 5);
    }

    #[test]
    fn test_passphrase_with_number() {
        let mut policy = PassphrasePolicy::default();
        policy.include_number = true;
        let passphrase = generate_passphrase(&policy).unwrap();
        assert!(passphrase.chars().any(|c| c.is_ascii_digit()));
    }

    #[test]
    fn test_strength_estimation() {
        let weak = "password";
        let fair = "Password1";
        let good = "Password123!";
        let strong = "MyP@ssw0rd!23#$";

        assert!(estimate_strength(weak) < estimate_strength(fair));
        assert!(estimate_strength(fair) < estimate_strength(good));
        assert!(estimate_strength(good) <= estimate_strength(strong));
    }

    #[test]
    fn test_entropy_calculation() {
        let password = "abc123";
        let entropy = get_entropy_bits(password);
        assert!(entropy > 0.0);
    }
}
