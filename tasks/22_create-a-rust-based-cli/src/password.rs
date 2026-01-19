use crate::error::{PasswordManagerError, Result};
use rand::Rng;

/// Options for password generation
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct PasswordOptions {
    pub length: usize,
    pub use_uppercase: bool,
    pub use_lowercase: bool,
    pub use_numbers: bool,
    pub use_symbols: bool,
    pub exclude_ambiguous: bool,
}

impl Default for PasswordOptions {
    fn default() -> Self {
        Self {
            length: 20,
            use_uppercase: true,
            use_lowercase: true,
            use_numbers: true,
            use_symbols: true,
            exclude_ambiguous: false,
        }
    }
}

/// Character sets for password generation
const LOWERCASE: &[u8] = b"abcdefghijklmnopqrstuvwxyz";
const UPPERCASE: &[u8] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZ";
const NUMBERS: &[u8] = b"0123456789";
const SYMBOLS: &[u8] = b"!@#$%^&*()_+-=[]{}|;:,.<>?";
const AMBIGUOUS: &[u8] = b"0O1lI";

/// Generates a secure random password based on the given options
pub fn generate_password(options: PasswordOptions) -> Result<String> {
    if options.length < 4 {
        return Err(PasswordManagerError::InvalidInput(
            "Password length must be at least 4 characters".to_string(),
        ));
    }

    // Build character set
    let mut charset = Vec::new();
    let mut required_chars = Vec::new();

    if options.use_lowercase {
        let chars = if options.exclude_ambiguous {
            LOWERCASE.iter().filter(|&&c| !AMBIGUOUS.contains(&c)).copied().collect()
        } else {
            LOWERCASE.to_vec()
        };
        if !chars.is_empty() {
            charset.extend_from_slice(&chars);
            required_chars.push(rand::thread_rng().gen_range(0..chars.len()));
        }
    }

    if options.use_uppercase {
        let chars = if options.exclude_ambiguous {
            UPPERCASE.iter().filter(|&&c| !AMBIGUOUS.contains(&c)).copied().collect()
        } else {
            UPPERCASE.to_vec()
        };
        if !chars.is_empty() {
            charset.extend_from_slice(&chars);
            required_chars.push(rand::thread_rng().gen_range(0..chars.len()));
        }
    }

    if options.use_numbers {
        let chars = if options.exclude_ambiguous {
            NUMBERS.iter().filter(|&&c| !AMBIGUOUS.contains(&c)).copied().collect()
        } else {
            NUMBERS.to_vec()
        };
        if !chars.is_empty() {
            charset.extend_from_slice(&chars);
            required_chars.push(rand::thread_rng().gen_range(0..chars.len()));
        }
    }

    if options.use_symbols {
        let chars = if options.exclude_ambiguous {
            SYMBOLS.iter().filter(|&&c| !AMBIGUOUS.contains(&c)).copied().collect()
        } else {
            SYMBOLS.to_vec()
        };
        if !chars.is_empty() {
            charset.extend_from_slice(&chars);
            required_chars.push(rand::thread_rng().gen_range(0..chars.len()));
        }
    }

    if charset.is_empty() {
        return Err(PasswordManagerError::InvalidInput(
            "At least one character type must be selected".to_string(),
        ));
    }

    let mut password = vec![0u8; options.length];
    let mut rng = rand::thread_rng();

    // Fill the password with random characters
    for i in 0..options.length {
        password[i] = charset[rng.gen_range(0..charset.len())];
    }

    // Ensure at least one character from each selected type
    for (i, &char_idx) in required_chars.iter().enumerate() {
        if i < options.length {
            password[i] = charset[char_idx];
        }
    }

    // Shuffle the password
    for i in (1..options.length).rev() {
        let j = rng.gen_range(0..=i);
        password.swap(i, j);
    }

    String::from_utf8(password).map_err(|_| {
        PasswordManagerError::PasswordGenerationError(
            "Failed to generate valid UTF-8 password".to_string(),
        )
    })
}

/// Calculates password entropy (in bits)
pub fn calculate_entropy(password: &str) -> f64 {
    let mut pool_size = 0;

    if password.chars().any(|c| c.is_lowercase()) {
        pool_size += 26;
    }
    if password.chars().any(|c| c.is_uppercase()) {
        pool_size += 26;
    }
    if password.chars().any(|c| c.is_ascii_digit()) {
        pool_size += 10;
    }
    if password.chars().any(|c| !c.is_alphanumeric()) {
        pool_size += 32;
    }

    if pool_size == 0 {
        return 0.0;
    }

    (password.len() as f64) * (pool_size as f64).log2()
}

/// Estimates password strength based on entropy
pub fn estimate_strength(password: &str) -> PasswordStrength {
    let entropy = calculate_entropy(password);

    match entropy {
        e if e < 28.0 => PasswordStrength::VeryWeak,
        e if e < 36.0 => PasswordStrength::Weak,
        e if e < 60.0 => PasswordStrength::Moderate,
        e if e < 128.0 => PasswordStrength::Strong,
        _ => PasswordStrength::VeryStrong,
    }
}

/// Password strength rating
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PasswordStrength {
    VeryWeak,
    Weak,
    Moderate,
    Strong,
    VeryStrong,
}

impl PasswordStrength {
    pub fn as_str(&self) -> &'static str {
        match self {
            PasswordStrength::VeryWeak => "Very Weak",
            PasswordStrength::Weak => "Weak",
            PasswordStrength::Moderate => "Moderate",
            PasswordStrength::Strong => "Strong",
            PasswordStrength::VeryStrong => "Very Strong",
        }
    }

    pub fn color(&self) -> &'static str {
        match self {
            PasswordStrength::VeryWeak => "red",
            PasswordStrength::Weak => "yellow",
            PasswordStrength::Moderate => "yellow",
            PasswordStrength::Strong => "green",
            PasswordStrength::VeryStrong => "green",
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_generate_default_password() {
        let password = generate_password(PasswordOptions::default()).unwrap();
        assert_eq!(password.len(), 20);
    }

    #[test]
    fn test_generate_custom_length() {
        let options = PasswordOptions {
            length: 32,
            ..Default::default()
        };
        let password = generate_password(options).unwrap();
        assert_eq!(password.len(), 32);
    }

    #[test]
    fn test_generate_lowercase_only() {
        let options = PasswordOptions {
            length: 15,
            use_lowercase: true,
            use_uppercase: false,
            use_numbers: false,
            use_symbols: false,
            exclude_ambiguous: false,
        };
        let password = generate_password(options).unwrap();
        assert!(password.chars().all(|c| c.is_ascii_lowercase()));
    }

    #[test]
    fn test_generate_exclude_ambiguous() {
        let options = PasswordOptions {
            length: 20,
            exclude_ambiguous: true,
            ..Default::default()
        };
        let password = generate_password(options).unwrap();
        let ambiguous_chars = ['0', 'O', '1', 'l', 'I'];
        for c in ambiguous_chars {
            assert!(!password.contains(c), "Password should not contain ambiguous character '{}'", c);
        }
    }

    #[test]
    fn test_password_too_short() {
        let options = PasswordOptions {
            length: 3,
            ..Default::default()
        };
        assert!(generate_password(options).is_err());
    }

    #[test]
    fn test_no_character_types() {
        let options = PasswordOptions {
            length: 20,
            use_uppercase: false,
            use_lowercase: false,
            use_numbers: false,
            use_symbols: false,
            exclude_ambiguous: false,
        };
        assert!(generate_password(options).is_err());
    }

    #[test]
    fn test_calculate_entropy() {
        let entropy = calculate_entropy("password");
        assert!(entropy > 0.0);

        let entropy_complex = calculate_entropy("P@ssw0rd123!@#");
        assert!(entropy_complex > entropy);
    }

    #[test]
    fn test_estimate_strength() {
        assert_eq!(
            estimate_strength("abc"),
            PasswordStrength::VeryWeak
        );
        assert_eq!(
            estimate_strength("Password123!"),
            PasswordStrength::Moderate
        );
        assert!(matches!(
            estimate_strength("MyV3ry$tr0ng!P@ssw0rd#2024"),
            PasswordStrength::VeryStrong | PasswordStrength::Strong
        ));
    }
}
