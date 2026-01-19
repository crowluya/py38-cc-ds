use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;
use crate::config;
use crate::error::ProjectInitError;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Template {
    pub name: String,
    pub description: String,
    pub language: String,
    pub version: String,
    pub variables: Vec<TemplateVariable>,
    pub files: Vec<TemplateFile>,
    pub directories: Vec<String>,
    pub gitignore: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TemplateVariable {
    pub name: String,
    pub description: String,
    pub default: String,
    pub required: bool,
    pub validation: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TemplateFile {
    pub path: String,
    pub content: String,
    pub template: bool,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct TemplateMetadata {
    pub name: String,
    pub description: String,
    pub language: String,
    pub version: String,
}

pub fn handle_template_command(command: TemplateCommand) -> Result<()> {
    match command {
        TemplateCommand::List => {
            list_templates()?;
        }
        TemplateCommand::Add { path, name } => {
            add_template(path, name)?;
        }
        TemplateCommand::Remove { name } => {
            remove_template(&name)?;
        }
        TemplateCommand::Info { name } => {
            show_template_info(&name)?;
        }
    }
    Ok(())
}

pub fn list_templates() -> Result<()> {
    let config = config::load_config()?;
    let templates_dir = &config.templates_dir;

    if !templates_dir.exists() {
        println!("No templates directory found. Run 'project-init init' first.");
        return Ok(());
    }

    let entries = fs::read_dir(templates_dir)?;

    println!("Available templates:");
    println!();

    let mut has_templates = false;
    for entry in entries {
        if let Ok(entry) = entry {
            let path = entry.path();
            if path.is_dir() {
                let metadata_path = path.join("template.yaml");
                if metadata_path.exists() {
                    if let Ok(metadata) = load_template_metadata(&metadata_path) {
                        println!("  {} - {}", metadata.name, metadata.description);
                        println!("    Language: {} | Version: {}", metadata.language, metadata.version);
                        println!();
                        has_templates = true;
                    }
                }
            }
        }
    }

    if !has_templates {
        println!("  No templates found.");
        println!("  Add templates with: project-init template add <path>");
    }

    Ok(())
}

pub fn add_template(path: PathBuf, name: Option<String>) -> Result<()> {
    let source_path = if path.is_absolute() {
        path
    } else {
        fs::canonicalize(path)?
    };

    if !source_path.exists() {
        return Err(ProjectInitError::TemplateNotFound(
            source_path.display().to_string(),
        )
        .into());
    }

    let template_name = name.unwrap_or_else(|| {
        source_path
            .file_name()
            .unwrap_or_default()
            .to_string_lossy()
            .to_string()
    });

    let config = config::load_config().await?;
    let dest_dir = config.templates_dir.join(&template_name);

    if dest_dir.exists() {
        return Err(ProjectInitError::InvalidTemplate(
            format!("Template '{}' already exists", template_name),
        )
        .into());
    }

    fs_extra::dir::copy(&source_path, &dest_dir, &fs_extra::dir::CopyOptions::new())?;

    println!("Template '{}' added successfully!", template_name);
    Ok(())
}

pub fn remove_template(name: &str) -> Result<()> {
    use dialoguer::Confirm;

    let config = config::load_config()?;
    let template_dir = config.templates_dir.join(name);

    if !template_dir.exists() {
        return Err(ProjectInitError::TemplateNotFound(name.to_string()).into());
    }

    let should_remove = Confirm::new()
        .with_prompt(&format!("Are you sure you want to remove template '{}'?", name))
        .with_default(false)
        .interact()?;

    if should_remove {
        fs::remove_dir_all(&template_dir)?;
        println!("Template '{}' removed successfully!", name);
    } else {
        println!("Operation cancelled.");
    }

    Ok(())
}

pub fn show_template_info(name: &str) -> Result<()> {
    let config = config::load_config()?;
    let template_dir = config.templates_dir.join(name);

    if !template_dir.exists() {
        return Err(ProjectInitError::TemplateNotFound(name.to_string()).into());
    }

    let template = load_template(&template_dir)?;

    println!("Template: {}", template.name);
    println!("Description: {}", template.description);
    println!("Language: {}", template.language);
    println!("Version: {}", template.version);
    println!();
    println!("Variables:");
    for var in &template.variables {
        println!("  - {} ({}): {}", var.name, var.description, var.default);
    }
    println!();
    println!("Files: {}", template.files.len());
    println!("Directories: {}", template.directories.len());

    Ok(())
}

pub fn load_template(template_dir: &PathBuf) -> Result<Template> {
    let metadata_path = template_dir.join("template.yaml");
    let contents = fs::read_to_string(&metadata_path)?;
    let template: Template = serde_yaml::from_str(&contents)?;
    Ok(template)
}

fn load_template_metadata(path: &PathBuf) -> Result<TemplateMetadata> {
    let contents = fs::read_to_string(path)?;
    let metadata: TemplateMetadata = serde_yaml::from_str(&contents)?;
    Ok(metadata)
}

#[derive(Debug, clap::Subcommand)]
pub enum TemplateCommand {
    /// List all available templates
    List,
    /// Add a new template from a local directory
    Add {
        /// Path to the template directory
        path: PathBuf,
        /// Optional custom name for the template
        name: Option<String>,
    },
    /// Remove a template
    Remove {
        /// Name of the template to remove
        name: String,
    },
    /// Show detailed information about a template
    Info {
        /// Name of the template
        name: String,
    },
}

pub fn get_template_path(name: &str) -> Result<PathBuf> {
    let config = config::load_config()?;
    Ok(config.templates_dir.join(name))
}
