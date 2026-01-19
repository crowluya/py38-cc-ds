use serde::{Deserialize, Serialize};
use zxcvbn::zxcvbn;

/// Password strength levels
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum PasswordStrength {
    Weak,
    Fair,
    Good,
    Strong,
}

impl PasswordStrength {
    pub fn as_str(&self) -> &str {
        match self {
            PasswordStrength::Weak => "Weak",
            PasswordStrength::Fair => "Fair",
            PasswordStrength::Good => "Good",
            PasswordStrength::Strong => "Strong",
        }
    }

    pub fn color_code(&self) -> &str {
        match self {
            PasswordStrength::Weak => "red",
            PasswordStrength::Fair => "yellow",
            PasswordStrength::Good => "blue",
            PasswordStrength::Strong => "green",
        }
    }

    pub fn from_score(score: u8) -> Self {
        match score {
            0..=1 => PasswordStrength::Weak,
            2 => PasswordStrength::Fair,
            3 => PasswordStrength::Good,
            4 => PasswordStrength::Strong,
            _ => PasswordStrength::Weak,
        }
    }
}

/// Result of password strength analysis
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PasswordAnalysis {
    pub strength: PasswordStrength,
    pub score: u8,
    pub entropy: f64,
    pub crack_time_seconds: f64,
    pub crack_time_display: String,
    pub suggestions: Vec<String>,
    pub warning: Option<String>,
}

impl PasswordAnalysis {
    pub fn is_acceptable(&self) -> bool {
        matches!(
            self.strength,
            PasswordStrength::Good | PasswordStrength::Strong
        )
    }
}

/// Analyzes password strength using zxcvbn
pub fn analyze_password(password: &str, user_inputs: &[&str]) -> PasswordAnalysis {
    if password.is_empty() {
        return PasswordAnalysis {
            strength: PasswordStrength::Weak,
            score: 0,
            entropy: 0.0,
            crack_time_seconds: 0.0,
            crack_time_display: "instantly".to_string(),
            suggestions: vec!["Password cannot be empty".to_string()],
            warning: Some("Empty password".to_string()),
        };
    }

    let estimate = zxcvbn(password, user_inputs);

    let strength = PasswordStrength::from_score(estimate.score());
    let entropy = estimate.guesses_log10();
    let crack_time = estimate.crack_times().offline_slow_hashing_1e4_per_second();
    let crack_time_display = format_crack_time(crack_time);

    let suggestions: Vec<String> = estimate
        .feedback()
        .suggestions()
        .iter()
        .map(|s| s.to_string())
        .collect();

    let warning = estimate.feedback().warning().map(|w| w.to_string());

    PasswordAnalysis {
        strength,
        score: estimate.score(),
        entropy,
        crack_time_seconds: crack_time,
        crack_time_display,
        suggestions,
        warning,
    }
}

/// Formats crack time in human-readable format
fn format_crack_time(seconds: f64) -> String {
    const MINUTE: f64 = 60.0;
    const HOUR: f64 = MINUTE * 60.0;
    const DAY: f64 = HOUR * 24.0;
    const MONTH: f64 = DAY * 30.0;
    const YEAR: f64 = DAY * 365.0;
    const CENTURY: f64 = YEAR * 100.0;

    if seconds < 1.0 {
        "instantly".to_string()
    } else if seconds < MINUTE {
        format!("{:.0} seconds", seconds)
    } else if seconds < HOUR {
        format!("{:.1} minutes", seconds / MINUTE)
    } else if seconds < DAY {
        format!("{:.1} hours", seconds / HOUR)
    } else if seconds < MONTH {
        format!("{:.1} days", seconds / DAY)
    } else if seconds < YEAR {
        format!("{:.1} months", seconds / MONTH)
    } else if seconds < CENTURY {
        format!("{:.1} years", seconds / YEAR)
    } else {
        "centuries".to_string()
    }
}

/// Validates a password against common security requirements
pub fn validate_password_requirements(password: &str) -> Result<(), Vec<String>> {
    let mut errors = Vec::new();

    if password.len() < 8 {
        errors.push("Password must be at least 8 characters long".to_string());
    }

    if password.len() > 128 {
        errors.push("Password must not exceed 128 characters".to_string());
    }

    if !password.chars().any(|c| c.is_ascii_lowercase()) {
        errors.push("Password must contain at least one lowercase letter".to_string());
    }

    if !password.chars().any(|c| c.is_ascii_uppercase()) {
        errors.push("Password must contain at least one uppercase letter".to_string());
    }

    if !password.chars().any(|c | c.is_ascii_digit()) {
        errors.push("Password must contain at least one digit".to_string());
    }

    if !password.chars().any(|c| !c.is_alphanumeric()) {
        errors.push("Password must contain at least one special character".to_string());
    }

    if errors.is_empty() {
        Ok(())
    } else {
        Err(errors)
    }
}

/// Generates a strong random password
pub fn generate_password(length: usize, use_symbols: bool) -> String {
    use rand::Rng;
    use rand::seq::SliceRandom;

    const LOWERCASE: &[u8] = b"abcdefghijklmnopqrstuvwxyz";
    const UPPERCASE: &[u8] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZ";
    const DIGITS: &[u8] = b"0123456789";
    const SYMBOLS: &[u8] = b"!@#$%^&*()_+-=[]{}|;:,.<>?";

    let mut rng = rand::thread_rng();
    let mut password = String::with_capacity(length);

    // Ensure at least one of each required character type
    password.push(LOWCASE.choose(&mut rng).unwrap().to_ascii_char() as char);
    password.push(UPPERCASE.choose(&mut rng).unwrap().to_ascii_char() as char);
    password.push(DIGITS.choose(&mut rng).unwrap().to_ascii_char() as char);

    if use_symbols {
        password.push(SYMBOLS.choose(&mut rng).unwrap().to_ascii_char() as char);
    }

    // Fill the rest with random characters from all sets
    let all_chars: Vec<char> = [
        LOWERCASE, UPPERCASE, DIGITS,
        if use_symbols { SYMBOLS } else { &[] },
    ]
    .concat()
    .iter()
    .map(|&b| b as char)
    .collect();

    for _ in password.len()..length {
        password.push(*all_chars.choose(&mut rng).unwrap());
    }

    // Shuffle to avoid predictable patterns
    let mut chars: Vec<char> = password.chars().collect();
    chars.shuffle(&mut rng);
    chars.into_iter().collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_weak_password() {
        let analysis = analyze_password("password", &[]);
        assert_eq!(analysis.strength, PasswordStrength::Weak);
        assert!(!analysis.is_acceptable());
    }

    #[test]
    fn test_strong_password() {
        let analysis = analyze_password("Correct-Horse-Battery-Staple-123", &[]);
        assert!(matches!(
            analysis.strength,
            PasswordStrength::Good | PasswordStrength::Strong
        ));
    }

    #[test]
    fn test_empty_password() {
        let analysis = analyze_password("", &[]);
        assert_eq!(analysis.strength, PasswordStrength::Weak);
        assert!(!analysis.suggestions.is_empty());
    }

    #[test]
    fn test_password_requirements() {
        assert!(validate_password_requirements("").is_err());
        assert!(validate_password_requirements("short").is_err());
        assert!(validate_password_requirements("lowercaseonly").is_err());
        assert!(validate_password_requirements("UPPERCASEONLY").is_err());
        assert!(validate_password_requirements("NoDigitsHere!").is_err());
        assert!(validate_password_requirements("NoSymbols123").is_err());
        assert!(validate_password_requirements("ValidPassword123!").is_ok());
    }

    #[test]
    fn test_generate_password() {
        let password = generate_password(16, true);
        assert_eq!(password.len(), 16);

        // Verify it contains all required character types
        assert!(password.chars().any(|c| c.is_ascii_lowercase()));
        assert!(password.chars().any(|c| c.is_ascii_uppercase()));
        assert!(password.chars().any(|c| c.is_ascii_digit()));
        assert!(password.chars().any(|c| !c.is_alphanumeric()));
    }

    #[test]
    fn test_format_crack_time() {
        assert_eq!(format_crack_time(0.5), "instantly");
        assert_eq!(format_crack_time(30.0), "30 seconds");
        assert_eq!(format_crack_time(120.0), "2.0 minutes");
        assert_eq!(format_crack_time(3600.0 * 2.5), "2.5 hours");
    }
}
