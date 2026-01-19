use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;
use dirs::home_dir;

#[derive(Debug, Serialize, Deserialize)]
pub struct Config {
    pub templates_dir: PathBuf,
    pub default_git: bool,
    pub default_author: String,
    pub default_license: String,
}

impl Default for Config {
    fn default() -> Self {
        let mut templates_dir = home_dir().unwrap_or_else(|| PathBuf::from("."));
        templates_dir.push(".project-init");
        templates_dir.push("templates");

        Config {
            templates_dir,
            default_git: true,
            default_author: "Your Name".to_string(),
            default_license: "MIT".to_string(),
        }
    }
}

pub fn init_config(interactive: bool) -> Result<()> {
    let config_path = get_config_path()?;

    if config_path.exists() {
        println!("Configuration already exists at: {}", config_path.display());
        return Ok(());
    }

    let config = if interactive {
        create_interactive_config()?
    } else {
        Config::default()
    };

    save_config(&config)?;
    println!("Configuration created at: {}", config_path.display());
    Ok(())
}

pub fn handle_config(key: Option<String>, value: Option<String>) -> Result<()> {
    let mut config = load_config()?;

    match (key, value) {
        (Some(k), Some(v)) => {
            match k.as_str() {
                "templates_dir" => config.templates_dir = PathBuf::from(v),
                "default_git" => config.default_git = v.parse().unwrap_or(true),
                "default_author" => config.default_author = v,
                "default_license" => config.default_license = v,
                _ => println!("Unknown configuration key: {}", k),
            }
            save_config(&config)?;
            println!("Configuration updated: {} = {}", k, v);
        }
        (Some(k), None) => {
            let value = match k.as_str() {
                "templates_dir" => config.templates_dir.display().to_string(),
                "default_git" => config.default_git.to_string(),
                "default_author" => config.default_author.clone(),
                "default_license" => config.default_license.clone(),
                _ => "Unknown key".to_string(),
            };
            println!("{} = {}", k, value);
        }
        (None, None) => {
            println!("Current configuration:");
            println!("  templates_dir: {}", config.templates_dir.display());
            println!("  default_git: {}", config.default_git);
            println!("  default_author: {}", config.default_author);
            println!("  default_license: {}", config.default_license);
        }
        _ => {}
    }

    Ok(())
}

pub fn get_config_path() -> Result<PathBuf> {
    let config_dir = get_config_dir()?;
    Ok(config_dir.join("config.yaml"))
}

pub fn get_config_dir() -> Result<PathBuf> {
    let mut config_dir = home_dir().unwrap_or_else(|| PathBuf::from("."));
    config_dir.push(".project-init");
    Ok(config_dir)
}

pub fn load_config() -> Result<Config> {
    let config_path = get_config_path()?;

    if !config_path.exists() {
        return Ok(Config::default());
    }

    let contents = fs::read_to_string(&config_path)?;
    let config: Config = serde_yaml::from_str(&contents)?;
    Ok(config)
}

fn save_config(config: &Config) -> Result<()> {
    let config_path = get_config_path()?;
    let config_dir = config_path.parent().unwrap();

    fs::create_dir_all(config_dir)?;

    let yaml = serde_yaml::to_string(config)?;
    fs::write(&config_path, yaml)?;

    Ok(())
}

fn create_interactive_config() -> Result<Config> {
    use dialoguer::{Input, Confirm};

    let author = Input::new()
        .with_prompt("Default author name")
        .with_initial("Your Name")
        .interact()?;

    let license = Input::new()
        .with_prompt("Default license")
        .with_initial("MIT")
        .interact()?;

    let use_git = Confirm::new()
        .with_prompt("Initialize Git by default?")
        .with_default(true)
        .interact()?;

    let mut templates_dir = home_dir().unwrap_or_else(|| PathBuf::from("."));
    templates_dir.push(".project-init");
    templates_dir.push("templates");

    Ok(Config {
        templates_dir,
        default_git: use_git,
        default_author: author,
        default_license: license,
    })
}
