use anyhow::{Context, Result};
use console::Term;
use dialoguer::{
    theme::ColorfulTheme,
    Confirm, Input, MultiSelect, Select,
};
use crate::session::{Session, SessionType, TemplateDraft};
use crate::variables::{EnhancedVariable, VariableType};
use crate::templates;
use std::collections::HashMap;
use std::path::PathBuf;

/// Wizard steps
const WIZARD_STEPS: &[&str] = &[
    "basic_info",
    "variables",
    "files",
    "review",
    "complete",
];

/// Run the template creation wizard
pub fn run_template_wizard(resume_session_id: Option<String>) -> Result<()> {
    let mut session = if let Some(session_id) = resume_session_id {
        crate::session::resume_session(&session_id)?
    } else {
        let mut new_session = Session::new(SessionType::TemplateCreation);
        new_session.set_current_step("basic_info");
        new_session
    };

    let theme = ColorfulTheme::default();
    let term = Term::stdout();

    println!();
    println!("╔════════════════════════════════════════════════════════════╗");
    println!("║          Template Creation Wizard                        ║");
    println!("╚════════════════════════════════════════════════════════════╝");
    println!();

    loop {
        match session.data.current_step.as_str() {
            "basic_info" => {
                if let Some(new_session) = step_basic_info(&session, &theme)? {
                    session = new_session;
                    session.set_current_step("variables");
                    crate::session::save_session(&session)?;
                } else {
                    // User cancelled
                    println!("Wizard cancelled.");
                    return Ok(());
                }
            }
            "variables" => {
                if let Some(new_session) = step_variables(&session, &theme)? {
                    session = new_session;
                    session.set_current_step("files");
                    crate::session::save_session(&session)?;
                } else {
                    // User wants to go back
                    session.set_current_step("basic_info");
                    crate::session::save_session(&session)?;
                }
            }
            "files" => {
                if let Some(new_session) = step_files(&session, &theme)? {
                    session = new_session;
                    session.set_current_step("review");
                    crate::session::save_session(&session)?;
                } else {
                    // User wants to go back
                    session.set_current_step("variables");
                    crate::session::save_session(&session)?;
                }
            }
            "review" => {
                if let Some(new_session) = step_review(&session, &theme)? {
                    session = new_session;
                    session.set_current_step("complete");
                    crate::session::save_session(&session)?;
                } else {
                    // User wants to go back
                    session.set_current_step("files");
                    crate::session::save_session(&session)?;
                }
            }
            "complete" => {
                step_complete(&session)?;
                break;
            }
            _ => {
                anyhow::bail!("Unknown wizard step: {}", session.data.current_step);
            }
        }
    }

    Ok(())
}

/// Step 1: Basic template information
fn step_basic_info(session: &Session, theme: &ColorfulTheme) -> Result<Option<Session>> {
    println!("─ Step 1: Basic Information");
    println!();

    let name: String = Input::with_theme(theme)
        .with_prompt("Template name")
        .with_initial(
            session.data.template_data.as_ref()
                .and_then(|d| if d.name.is_empty() { None } else { Some(&d.name) })
                .unwrap_or(&String::new())
                .clone()
        )
        .interact()?;

    let description: String = Input::with_theme(theme)
        .with_prompt("Template description")
        .with_initial(
            session.data.template_data.as_ref()
                .and_then(|d| if d.description.is_empty() { None } else { Some(&d.description) })
                .unwrap_or(&String::new())
                .clone()
        )
        .interact()?;

    let language_options = vec!["Rust", "Go", "Python", "JavaScript", "TypeScript", "Other"];
    let selection = Select::with_theme(theme)
        .with_prompt("Programming language")
        .default(
            session.data.template_data.as_ref()
                .and_then(|d| {
                    language_options.iter().position(|&l| l == d.language)
                })
                .unwrap_or(0)
        )
        .items(&language_options)
        .interact()?;

    let language = language_options[selection].to_string();

    let version: String = Input::with_theme(theme)
        .with_prompt("Template version")
        .with_initial(
            session.data.template_data.as_ref()
                .and_then(|d| if d.version.is_empty() { None } else { Some(&d.version) })
                .unwrap_or(&"0.1.0".to_string())
                .clone()
        )
        .default("0.1.0".to_string())
        .interact()?;

    let mut new_session = session.clone();
    let draft = session.data.template_data.clone().unwrap_or_else(|| {
        TemplateDraft {
            name: String::new(),
            description: String::new(),
            language: String::new(),
            version: String::new(),
            variables: Vec::new(),
            files: Vec::new(),
            directories: Vec::new(),
        }
    });

    let updated_draft = TemplateDraft {
        name,
        description,
        language,
        version,
        variables: draft.variables,
        files: draft.files,
        directories: draft.directories,
    };

    new_session.data.template_data = Some(updated_draft);
    Ok(Some(new_session))
}

/// Step 2: Define template variables
fn step_variables(session: &Session, theme: &ColorfulTheme) -> Result<Option<Session>> {
    println!("─ Step 2: Template Variables");
    println!();

    let add_variables = Confirm::with_theme(theme)
        .with_prompt("Would you like to add template variables?")
        .default(true)
        .interact()?;

    if !add_variables {
        // Skip but continue
        let mut new_session = session.clone();
        if new_session.data.template_data.is_none() {
            new_session.data.template_data = Some(TemplateDraft {
                name: String::new(),
                description: String::new(),
                language: String::new(),
                version: String::new(),
                variables: Vec::new(),
                files: Vec::new(),
                directories: Vec::new(),
            });
        }
        return Ok(Some(new_session));
    }

    let mut variables = session.data.template_data.as_ref()
        .map(|d| d.variables.clone())
        .unwrap_or_default();

    loop {
        println!();
        println!("Current variables:");
        if variables.is_empty() {
            println!("  (none)");
        } else {
            for (i, var) in variables.iter().enumerate() {
                println!("  {}. {} - {}", i + 1, var.name, var.description);
            }
        }
        println!();

        let options = vec![
            "Add a new variable",
            "Continue to next step",
            "Go back",
        ];

        let selection = Select::with_theme(theme)
            .with_prompt("What would you like to do?")
            .items(&options)
            .interact()?;

        match selection {
            0 => {
                // Add variable
                if let Some(new_var) = prompt_for_variable(theme)? {
                    variables.push(new_var);
                }
            }
            1 => {
                // Continue
                let mut new_session = session.clone();
                if let Some(draft) = &mut new_session.data.template_data {
                    draft.variables = variables;
                } else {
                    new_session.data.template_data = Some(TemplateDraft {
                        name: String::new(),
                        description: String::new(),
                        language: String::new(),
                        version: String::new(),
                        variables,
                        files: Vec::new(),
                        directories: Vec::new(),
                    });
                }
                return Ok(Some(new_session));
            }
            2 => {
                // Go back
                return Ok(None);
            }
            _ => unreachable!(),
        }
    }
}

/// Prompt user to create a new variable
fn prompt_for_variable(theme: &ColorfulTheme) -> Result<Option<EnhancedVariable>> {
    println!();
    println!("Adding a new variable...");

    let name: String = Input::with_theme(theme)
        .with_prompt("Variable name")
        .interact()?;

    let description: String = Input::with_theme(theme)
        .with_prompt("Variable description")
        .interact()?;

    let default: String = Input::with_theme(theme)
        .with_prompt("Default value")
        .interact()?;

    let type_options = vec!["String", "Number", "Boolean", "Choice"];
    let type_selection = Select::with_theme(theme)
        .with_prompt("Variable type")
        .default(0)
        .items(&type_options)
        .interact()?;

    let variable_type = match type_selection {
        0 => VariableType::String,
        1 => VariableType::Number,
        2 => VariableType::Boolean,
        3 => {
            let choices_str: String = Input::with_theme(theme)
                .with_prompt("Choices (comma-separated)")
                .interact()?;
            let choices: Vec<String> = choices_str
                .split(',')
                .map(|s| s.trim().to_string())
                .collect();
            VariableType::Choice(choices)
        }
        _ => unreachable!(),
    };

    let required = Confirm::with_theme(theme)
        .with_prompt("Is this variable required?")
        .default(false)
        .interact()?;

    Ok(Some(EnhancedVariable {
        name,
        description,
        variable_type,
        default,
        required,
        validation: None,
        depends_on: None,
        prompt: None,
    }))
}

/// Step 3: Select files and directories
fn step_files(session: &Session, theme: &ColorfulTheme) -> Result<Option<Session>> {
    println!("─ Step 3: Files and Directories");
    println!();

    println!("Enter the path to the source directory you want to template:");
    let source_path: String = Input::with_theme(theme)
        .with_prompt("Source directory path")
        .interact()?;

    let path = PathBuf::from(&source_path);
    if !path.exists() {
        println!("Error: Path does not exist.");
        return Ok(None); // Go back
    }

    // Scan for files
    let mut files = Vec::new();
    let mut directories = Vec::new();

    if path.is_dir() {
        for entry in walkdir::WalkDir::new(&path)
            .min_depth(1)
            .max_depth(5)
            .into_iter()
            .filter_map(|e| e.ok())
        {
            let rel_path = entry.path()
                .strip_prefix(&path)
                .unwrap_or(entry.path())
                .to_string_lossy()
                .to_string();

            if entry.path().is_dir() {
                directories.push(rel_path);
            } else {
                files.push(rel_path);
            }
        }
    }

    println!();
    println!("Found {} files and {} directories", files.len(), directories.len());

    let mut new_session = session.clone();
    if let Some(draft) = &mut new_session.data.template_data {
        draft.files = files;
        draft.directories = directories;
    } else {
        new_session.data.template_data = Some(TemplateDraft {
            name: String::new(),
            description: String::new(),
            language: String::new(),
            version: String::new(),
            variables: Vec::new(),
            files,
            directories,
        });
    }

    Ok(Some(new_session))
}

/// Step 4: Review and confirm
fn step_review(session: &Session, theme: &ColorfulTheme) -> Result<Option<Session>> {
    println!("─ Step 4: Review Template");
    println!();

    if let Some(draft) = &session.data.template_data {
        println!("Template Name: {}", draft.name);
        println!("Description: {}", draft.description);
        println!("Language: {}", draft.language);
        println!("Version: {}", draft.version);
        println!();
        println!("Variables ({}):", draft.variables.len());
        for var in &draft.variables {
            println!("  - {} ({}): {} - default: {}",
                var.name, var.description,
                format_variable_type(&var.variable_type), var.default);
        }
        println!();
        println!("Files: {}", draft.files.len());
        println!("Directories: {}", draft.directories.len());
        println!();

        let confirm = Confirm::with_theme(theme)
            .with_prompt("Create this template?")
            .default(true)
            .interact()?;

        if confirm {
            Ok(Some(session.clone()))
        } else {
            println!("Template not created.");
            Ok(None)
        }
    } else {
        println!("Error: No template data found.");
        Ok(None)
    }
}

/// Step 5: Complete the template creation
fn step_complete(session: &Session) -> Result<()> {
    println!("─ Creating Template...");
    println!();

    if let Some(draft) = &session.data.template_data {
        // Create the template directory
        let config = crate::config::load_config()?;
        let template_dir = config.templates_dir.join(&draft.name);

        if template_dir.exists() {
            println!("Error: Template '{}' already exists.", draft.name);
            return Ok(());
        }

        std::fs::create_dir_all(&template_dir)?;

        // Save template metadata
        let template = templates::Template {
            name: draft.name.clone(),
            description: draft.description.clone(),
            language: draft.language.clone(),
            version: draft.version.clone(),
            variables: draft.variables.iter()
                .map(|v| templates::TemplateVariable {
                    name: v.name.clone(),
                    description: v.description.clone(),
                    default: v.default.clone(),
                    required: v.required,
                    validation: v.validation.as_ref()
                        .and_then(|v| v.pattern.clone()),
                })
                .collect(),
            files: draft.files.iter()
                .map(|f| templates::TemplateFile {
                    path: f.clone(),
                    content: String::new(),
                    template: true,
                })
                .collect(),
            directories: draft.directories.clone(),
            gitignore: Vec::new(),
        };

        let yaml = serde_yaml::to_string(&template)?;
        std::fs::write(template_dir.join("template.yaml"), yaml)?;

        println!("✓ Template '{}' created successfully!", draft.name);
        println!();
        println!("You can now use this template with:");
        println!("  project-init new -t {} <project-name>", draft.name);

        // Clean up session
        crate::session::delete_session(&session.id)?;
    }

    Ok(())
}

/// Format variable type for display
fn format_variable_type(var_type: &VariableType) -> String {
    match var_type {
        VariableType::String => "string".to_string(),
        VariableType::Number => "number".to_string(),
        VariableType::Boolean => "boolean".to_string(),
        VariableType::Choice(choices) => format!("choice: {}", choices.join(", ")),
    }
}

/// List all wizard sessions that can be resumed
pub fn list_resumable_sessions() -> Result<Vec<Session>> {
    let sessions = crate::session::list_sessions()?;
    Ok(sessions.into_iter()
        .filter(|s| s.session_type == SessionType::TemplateCreation)
        .collect())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_format_variable_type() {
        assert_eq!(format_variable_type(&VariableType::String), "string");
        assert_eq!(format_variable_type(&VariableType::Boolean), "boolean");
    }
}
