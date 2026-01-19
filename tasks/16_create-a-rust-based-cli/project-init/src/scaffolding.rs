use anyhow::Result;
use handlebars::Handlebars;
use serde_json::json;
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;
use crate::config;
use crate::templates::{self, Template};
use crate::git;
use indicatif::{ProgressBar, ProgressStyle};
use dialoguer::{Input, theme::ColorfulTheme};

pub async fn create_project(
    template_name: &str,
    project_name: &str,
    custom_path: Option<&str>,
    init_git: bool,
    user_variables: &HashMap<String, String>,
) -> Result<()> {
    let template_path = templates::get_template_path(template_name)?;

    if !template_path.exists() {
        return Err(crate::error::ProjectInitError::TemplateNotFound(
            template_name.to_string(),
        )
        .into());
    }

    let template = templates::load_template(&template_path)?;

    let project_path = if let Some(path) = custom_path {
        PathBuf::from(path)
    } else {
        PathBuf::from(project_name)
    };

    if project_path.exists() {
        return Err(crate::error::ProjectInitError::FileSystemError(
            format!("Directory '{}' already exists", project_path.display()),
        )
        .into());
    }

    println!("\nCreating project '{}' from template '{}'...\n", project_name, template_name);

    let variables = collect_variables(&template, project_name, user_variables)?;

    let total_steps = template.directories.len() + template.files.len() + 1;
    let pb = ProgressBar::new(total_steps as u64);
    pb.set_style(
        ProgressStyle::default_bar()
            .template("[{elapsed_precise}] [{bar:40.cyan/blue}] {pos}/{len} {msg}")
            .unwrap()
            .progress_chars("=>-"),
    );
    pb.set_message("Initializing...");

    fs::create_dir_all(&project_path)?;
    pb.inc(1);
    pb.set_message("Creating directories...");

    for dir in &template.directories {
        let dir_path = substitute_path_variables(dir, &variables);
        let full_path = project_path.join(&dir_path);
        fs::create_dir_all(&full_path)?;
        pb.inc(1);
        pb.set_message(&format!("Created: {}", dir_path));
    }

    pb.set_message("Generating files...");

    let handlebars = setup_handlebars();

    for file in &template.files {
        let file_path = substitute_path_variables(&file.path, &variables);
        let full_path = project_path.join(&file_path);

        if let Some(parent) = full_path.parent() {
            fs::create_dir_all(parent)?;
        }

        let content = if file.template {
            render_template(&handlebars, &file.content, &variables)?
        } else {
            file.content.clone()
        };

        fs::write(&full_path, content)?;
        pb.inc(1);
        pb.set_message(&format!("Generated: {}", file_path));
    }

    pb.finish_with_message("Project created successfully!");

    if !template.gitignore.is_empty() {
        create_gitignore(&project_path, &template)?;
        println!("Created .gitignore");
    }

    if init_git {
        git::initialize_git(&project_path, project_name)?;
        println!("Git repository initialized");
    }

    println!("\n✨ Project '{}' created successfully!", project_name);
    println!("   Location: {}", project_path.display());
    println!("\nNext steps:");
    println!("  cd {}", project_name);
    if !init_git {
        println!("  git init");
    }
    println!("  # Start developing!");

    Ok(())
}

fn collect_variables(
    template: &Template,
    project_name: &str,
    user_variables: &HashMap<String, String>,
) -> Result<HashMap<String, String>> {
    let mut variables = HashMap::new();

    variables.insert("project_name".to_string(), project_name.to_string());
    variables.insert("project_name_kebab".to_string(), to_kebab_case(project_name));
    variables.insert("project_name_snake".to_string(), to_snake_case(project_name));
    variables.insert("project_name_pascal".to_string(), to_pascal_case(project_name));

    let config = config::load_config()?;
    variables.insert("author".to_string(), config.default_author.clone());
    variables.insert("license".to_string(), config.default_license.clone());
    variables.insert("year".to_string(), chrono::Utc::now().format("%Y").to_string());

    for var in &template.variables {
        let value = if let Some(user_val) = user_variables.get(&var.name) {
            user_val.clone()
        } else if !var.default.is_empty() && !var.required {
            var.default.clone()
        } else {
            let theme = ColorfulTheme::default();
            Input::with_theme(&theme)
                .with_prompt(&var.description)
                .with_initial(&var.default)
                .allow_empty(false)
                .interact()?
        };

        if !value.is_empty() {
            variables.insert(var.name.clone(), value);
        } else if var.required {
            return Err(crate::error::ProjectInitError::InvalidTemplate(
                format!("Required variable '{}' is empty", var.name),
            )
            .into());
        }
    }

    Ok(variables)
}

fn setup_handlebars() -> Handlebars<'static> {
    let handlebars = Handlebars::new();

    handlebars.register_helper(
        "kebab-case",
        Box::new(
            |h: &handlebars::Helper<'_>,
             _: &Handlebars<'_>,
             _: &handlebars::Context,
             _: &mut handlebars::RenderContext<'_, '_>,
             out| -> handlebars::HelperResult {
                let param = h.param(0).unwrap();
                let value = param.value().as_str().unwrap();
                out.write(&to_kebab_case(value))?;
                Ok(())
            },
        ),
    );

    handlebars.register_helper(
        "snake-case",
        Box::new(
            |h: &handlebars::Helper<'_>,
             _: &Handlebars<'_>,
             _: &handlebars::Context,
             _: &mut handlebars::RenderContext<'_, '_>,
             out| -> handlebars::HelperResult {
                let param = h.param(0).unwrap();
                let value = param.value().as_str().unwrap();
                out.write(&to_snake_case(value))?;
                Ok(())
            },
        ),
    );

    handlebars.register_helper(
        "pascal-case",
        Box::new(
            |h: &handlebars::Helper<'_>,
             _: &Handlebars<'_>,
             _: &handlebars::Context,
             _: &mut handlebars::RenderContext<'_, '_>,
             out| -> handlebars::HelperResult {
                let param = h.param(0).unwrap();
                let value = param.value().as_str().unwrap();
                out.write(&to_pascal_case(value))?;
                Ok(())
            },
        ),
    );

    handlebars
}

fn render_template(
    handlebars: &Handlebars<'static>,
    template: &str,
    variables: &HashMap<String, String>,
) -> Result<String> {
    let data = json!(variables);
    Ok(handlebars.render_template(template, &data)?)
}

fn substitute_path_variables(path: &str, variables: &HashMap<String, String>) -> String {
    let mut result = path.to_string();

    for (key, value) in variables {
        let placeholder = format!("{{{{{} }}}}", key);
        result = result.replace(&placeholder, value);
    }

    result
}

fn create_gitignore(project_path: &PathBuf, template: &Template) -> Result<()> {
    let gitignore_path = project_path.join(".gitignore");
    let content = template.gitignore.join("\n");
    fs::write(&gitignore_path, content)?;
    Ok(())
}

fn to_kebab_case(s: &str) -> String {
    s.chars()
        .map(|c| {
            if c.is_uppercase() {
                format!("-{}", c.to_lowercase().collect::<String>())
            } else if c == '_' || c == ' ' {
                "-".to_string()
            } else {
                c.to_string()
            }
        })
        .collect::<String>()
        .trim_start_matches('-')
        .to_string()
}

fn to_snake_case(s: &str) -> String {
    s.chars()
        .map(|c| {
            if c.is_uppercase() {
                format!("_{}", c.to_lowercase().collect::<String>())
            } else if c == '-' || c == ' ' {
                "_".to_string()
            } else {
                c.to_string()
            }
        })
        .collect::<String>()
        .trim_start_matches('_')
        .to_string()
}

fn to_pascal_case(s: &str) -> String {
    s.split(['-', '_', ' '])
        .map(|word| {
            let mut chars = word.chars();
            match chars.next() {
                None => String::new(),
                Some(first) => {
                    first.to_uppercase().collect::<String>() + chars.as_str()
                }
            }
        })
        .collect()
}
