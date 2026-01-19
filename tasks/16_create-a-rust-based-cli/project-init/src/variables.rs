use anyhow::{anyhow, Result};
use regex::Regex;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Enhanced variable type system
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum VariableType {
    String,
    Number,
    Boolean,
    Choice(Vec<String>),
}

/// Enhanced template variable with validation and dependencies
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EnhancedVariable {
    pub name: String,
    pub description: String,
    pub variable_type: VariableType,
    pub default: String,
    pub required: bool,
    pub validation: Option<ValidationRule>,
    pub depends_on: Option<String>,
    pub prompt: Option<String>,
}

/// Validation rules for variables
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ValidationRule {
    pub pattern: Option<String>,
    pub min_length: Option<usize>,
    pub max_length: Option<usize>,
    pub min_value: Option<f64>,
    pub max_value: Option<f64>,
    pub custom_validator: Option<String>,
}

/// Variable preset for saving common configurations
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VariablePreset {
    pub name: String,
    pub description: String,
    pub variables: HashMap<String, String>,
    pub created_at: String,
}

impl EnhancedVariable {
    /// Create a new string variable
    pub fn new_string(name: &str, description: &str, default: &str) -> Self {
        EnhancedVariable {
            name: name.to_string(),
            description: description.to_string(),
            variable_type: VariableType::String,
            default: default.to_string(),
            required: false,
            validation: None,
            depends_on: None,
            prompt: None,
        }
    }

    /// Create a new boolean variable
    pub fn new_boolean(name: &str, description: &str, default: bool) -> Self {
        EnhancedVariable {
            name: name.to_string(),
            description: description.to_string(),
            variable_type: VariableType::Boolean,
            default: default.to_string(),
            required: false,
            validation: None,
            depends_on: None,
            prompt: None,
        }
    }

    /// Create a new choice variable
    pub fn new_choice(name: &str, description: &str, choices: Vec<String>, default: &str) -> Self {
        EnhancedVariable {
            name: name.to_string(),
            description: description.to_string(),
            variable_type: VariableType::Choice(choices),
            default: default.to_string(),
            required: false,
            validation: None,
            depends_on: None,
            prompt: None,
        }
    }

    /// Validate a value against this variable's rules
    pub fn validate(&self, value: &str) -> Result<()> {
        // Check if required and empty
        if self.required && value.is_empty() {
            return anyhow!("Variable '{}' is required but was not provided", self.name);
        }

        // If empty and not required, use default
        if value.is_empty() && !self.required {
            return Ok(());
        }

        match &self.variable_type {
            VariableType::String => {
                self.validate_string(value)?;
            }
            VariableType::Number => {
                self.validate_number(value)?;
            }
            VariableType::Boolean => {
                self.validate_boolean(value)?;
            }
            VariableType::Choice(choices) => {
                self.validate_choice(value, choices)?;
            }
        }

        Ok(())
    }

    fn validate_string(&self, value: &str) -> Result<()> {
        if let Some(validation) = &self.validation {
            if let Some(pattern) = &validation.pattern {
                let regex = Regex::new(pattern)
                    .map_err(|e| anyhow!("Invalid regex pattern: {}", e))?;
                if !regex.is_match(value) {
                    return anyhow!("Value '{}' does not match required pattern", value);
                }
            }

            if let Some(min_length) = validation.min_length {
                if value.len() < min_length {
                    return anyhow!("Value must be at least {} characters", min_length);
                }
            }

            if let Some(max_length) = validation.max_length {
                if value.len() > max_length {
                    return anyhow!("Value must be at most {} characters", max_length);
                }
            }
        }
        Ok(())
    }

    fn validate_number(&self, value: &str) -> Result<()> {
        let num = value.parse::<f64>()
            .map_err(|_| anyhow!("Value '{}' is not a valid number", value))?;

        if let Some(validation) = &self.validation {
            if let Some(min_value) = validation.min_value {
                if num < min_value {
                    return anyhow!("Value must be at least {}", min_value);
                }
            }

            if let Some(max_value) = validation.max_value {
                if num > max_value {
                    return anyhow!("Value must be at most {}", max_value);
                }
            }
        }
        Ok(())
    }

    fn validate_boolean(&self, value: &str) -> Result<()> {
        match value.to_lowercase().as_str() {
            "true" | "false" | "yes" | "no" | "1" | "0" => Ok(()),
            _ => anyhow!("Value '{}' is not a valid boolean", value),
        }
    }

    fn validate_choice(&self, value: &str, choices: &[String]) -> Result<()> {
        if !choices.contains(&value.to_string()) {
            return anyhow!("Value '{}' is not a valid choice. Valid options: {}",
                value, choices.join(", "));
        }
        Ok(())
    }
}

/// Parse environment variable syntax ({{env:VAR_NAME}})
pub fn parse_env_vars(content: &str) -> Result<String> {
    let re = Regex::new(r"\{\{env:([^}]+)\}\}")?;
    let mut result = content.to_string();

    for cap in re.captures_iter(content) {
        let var_name = &cap[1];
        let value = std::env::var(var_name)
            .unwrap_or_else(|_| String::new());
        result = result.replace(&cap[0], &value);
    }

    Ok(result)
}

/// Substitute variables in content using enhanced variable system
pub fn substitute_variables(
    content: &str,
    variables: &HashMap<String, String>,
) -> Result<String> {
    let mut result = content.to_string();

    // Handle environment variables first
    result = parse_env_vars(&result)?;

    // Then substitute template variables
    for (key, value) in variables {
        let placeholder = format!("{{{{{}}}}}", key);
        result = result.replace(&placeholder, value);
    }

    // Handle conditional logic: {{#if var}}...{{/if}}
    result = process_conditionals(&result, variables)?;

    Ok(result)
}

/// Process conditional logic in templates
fn process_conditionals(content: &str, variables: &HashMap<String, String>) -> Result<String> {
    let re = Regex::new(r"\{\{#if\s+(\w+)\}\}(.*?)\{\{/if\}\}")?;
    let mut result = content.to_string();

    while let Some(cap) = re.captures(&result.clone()) {
        let var_name = &cap[1];
        let inner_content = &cap[2];

        let should_include = variables.get(var_name)
            .map(|v| is_truthy(v))
            .unwrap_or(false);

        let replacement = if should_include {
            inner_content.to_string()
        } else {
            String::new()
        };

        let full_match = cap.get(0).unwrap().as_str();
        result = result.replace(full_match, &replacement);
    }

    Ok(result)
}

/// Check if a string value should be considered "truthy"
fn is_truthy(value: &str) -> bool {
    match value.to_lowercase().as_str() {
        "true" | "yes" | "1" | "on" => !value.is_empty(),
        _ => false,
    }
}

/// Convert legacy template variables to enhanced variables
pub fn upgrade_variable(legacy_var: &crate::templates::TemplateVariable) -> EnhancedVariable {
    EnhancedVariable {
        name: legacy_var.name.clone(),
        description: legacy_var.description.clone(),
        variable_type: VariableType::String,
        default: legacy_var.default.clone(),
        required: legacy_var.required,
        validation: legacy_var.validation.as_ref().map(|pattern| ValidationRule {
            pattern: Some(pattern.clone()),
            min_length: None,
            max_length: None,
            min_value: None,
            max_value: None,
            custom_validator: None,
        }),
        depends_on: None,
        prompt: None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_string_validation() {
        let var = EnhancedVariable::new_string("name", "Name", "test");
        assert!(var.validate("test").is_ok());
        assert!(var.validate("").is_ok()); // Not required
    }

    #[test]
    fn test_boolean_validation() {
        let var = EnhancedVariable::new_boolean("enabled", "Enabled", true);
        assert!(var.validate("true").is_ok());
        assert!(var.validate("false").is_ok());
        assert!(var.validate("invalid").is_err());
    }

    #[test]
    fn test_choice_validation() {
        let var = EnhancedVariable::new_choice("lang", "Language", vec!["rust".to_string(), "go".to_string()], "rust");
        assert!(var.validate("rust").is_ok());
        assert!(var.validate("invalid").is_err());
    }

    #[test]
    fn test_variable_substitution() {
        let mut vars = HashMap::new();
        vars.insert("name".to_string(), "test".to_string());

        let result = substitute_variables("Hello {{name}}!", &vars).unwrap();
        assert_eq!(result, "Hello test!");
    }

    #[test]
    fn test_env_var_substitution() {
        std::env::set_var("TEST_VAR", "test_value");
        let result = parse_env_vars("Value: {{env:TEST_VAR}}").unwrap();
        assert_eq!(result, "Value: test_value");
        std::env::remove_var("TEST_VAR");
    }
}
