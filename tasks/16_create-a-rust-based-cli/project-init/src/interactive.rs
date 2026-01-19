use anyhow::{anyhow, Result};
use rustyline::{
    completion::Completer, error::ReadlineError, highlight::Highlighter, hint::Hinter,
    history::History, Editor,
};
use rustyline_derive::{Helper, Validator};
use std::borrow::Cow::{self, Borrowed, Owned};
use std::collections::HashMap;

#[derive(Helper, Validator)]
struct InteractiveHelper {
    completer: CommandCompleter,
}

impl Highlighter for InteractiveHelper {
    fn highlight<'l>(&self, line: &'l str, _pos: usize) -> Cow<'l, str> {
        Borrowed(line)
    }

    fn highlight_prompt<'b, 's: 'b, 'p: 'b>(
        &'s self,
        prompt: &'p str,
        _default: bool,
    ) -> Cow<'b, str> {
        Borrowed(prompt)
    }
}

impl Hinter for InteractiveHelper {
    type Hint = String;
}

impl Completer for InteractiveHelper {
    type Candidate = String;

    fn complete(
        &self,
        line: &str,
        pos: usize,
        _ctx: &rustyline::Context<'_>,
    ) -> Result<(usize, Vec<String>), ReadlineError> {
        self.completer.complete(line, pos)
    }
}

struct CommandCompleter {
    commands: Vec<String>,
}

impl CommandCompleter {
    fn new() -> Self {
        CommandCompleter {
            commands: vec![
                "new".to_string(),
                "list".to_string(),
                "template".to_string(),
                "help".to_string(),
                "exit".to_string(),
                "quit".to_string(),
                "clear".to_string(),
                "history".to_string(),
                "wizard".to_string(),
                "config".to_string(),
                "variables".to_string(),
            ],
        }
    }

    fn complete(&self, line: &str, pos: usize) -> Result<(usize, Vec<String>), ReadlineError> {
        let start = line[..pos].rfind(' ').map_or(0, |i| i + 1);
        let partial = &line[start..pos];

        let matches: Vec<String> = self.commands
            .iter()
            .filter(|cmd| cmd.starts_with(partial))
            .map(|cmd| {
                if pos < line.len() {
                    cmd.to_string()
                } else {
                    format!("{} ", cmd)
                }
            })
            .collect();

        Ok((start, matches))
    }
}

/// Interactive REPL state
pub struct InteractiveShell {
    editor: Editor<InteractiveHelper>,
    session_variables: HashMap<String, String>,
}

impl InteractiveShell {
    /// Create a new interactive shell
    pub fn new() -> Result<Self> {
        let helper = InteractiveHelper {
            completer: CommandCompleter::new(),
        };

        let mut editor = Editor::new().map_err(|e| anyhow!("Failed to initialize editor: {}", e))?;
        editor.set_helper(Some(helper));

        // Load history
        if let Ok(history_path) = crate::history::get_history_path() {
            if history_path.exists() {
                let _ = editor.load_history(&history_path);
            }
        }

        Ok(InteractiveShell {
            editor,
            session_variables: HashMap::new(),
        })
    }

    /// Run the interactive shell
    pub fn run(&mut self) -> Result<()> {
        println!();
        println!("╔════════════════════════════════════════════════════════════╗");
        println!("║          Project-Init Interactive Mode                   ║");
        println!("╚════════════════════════════════════════════════════════════╝");
        println!();
        println!("Type 'help' for available commands or 'exit' to quit.");
        println!();

        loop {
            let readline = self.editor.readline("project-init> ");

            match readline {
                Ok(line) => {
                    let line = line.trim();
                    if line.is_empty() {
                        continue;
                    }

                    // Add to history
                    self.editor.add_history_entry(line)?;

                    // Parse and execute command
                    if let Err(e) = self.execute_command(line) {
                        println!("Error: {}", e);
                    }
                }
                Err(ReadlineError::Interrupted) => {
                    println!("Use 'exit' or 'quit' to exit.");
                }
                Err(ReadlineError::Eof) => {
                    println!("Goodbye!");
                    break;
                }
                Err(err) => {
                    println!("Error: {:?}", err);
                    break;
                }
            }
        }

        // Save history before exiting
        if let Ok(history_path) = crate::history::get_history_path() {
            let _ = self.editor.save_history(&history_path);
        }

        Ok(())
    }

    /// Execute a command in the REPL
    fn execute_command(&mut self, line: &str) -> Result<()> {
        let parts: Vec<&str> = line.split_whitespace().collect();
        if parts.is_empty() {
            return Ok(());
        }

        let command = parts[0];
        let args = &parts[1..];

        match command {
            "help" | "?" => {
                self.show_help();
            }
            "exit" | "quit" | "q" => {
                println!("Goodbye!");
                std::process::exit(0);
            }
            "clear" => {
                print!("\x1b[2J\x1b[1;1H");
                println!("Project-Init Interactive Mode");
            }
            "list" => {
                self.list_templates();
            }
            "new" => {
                self.create_project(args)?;
            }
            "template" => {
                self.handle_template_command(args)?;
            }
            "wizard" => {
                self.run_wizard(args)?;
            }
            "history" => {
                self.show_history(args)?;
            }
            "config" => {
                self.handle_config(args)?;
            }
            "variables" => {
                self.handle_variables(args)?;
            }
            _ => {
                println!("Unknown command: '{}'. Type 'help' for available commands.", command);
            }
        }

        Ok(())
    }

    /// Show help message
    fn show_help(&self) {
        println!();
        println!("Available Commands:");
        println!("  new              - Create a new project from a template");
        println!("  list             - List all available templates");
        println!("  template         - Manage templates (add, remove, info)");
        println!("  wizard           - Run the template creation wizard");
        println!("  history          - Show command history");
        println!("  config           - Manage configuration");
        println!("  variables        - Manage template variables");
        println!("  clear            - Clear the screen");
        println!("  help / ?         - Show this help message");
        println!("  exit / quit      - Exit interactive mode");
        println!();
        println!("Tips:");
        println!("  - Use arrow keys to navigate command history");
        println!("  - Press Tab for command completion");
        println!("  - Commands can be abbreviated (e.g., 'n' for 'new')");
        println!();
    }

    /// List all templates
    fn list_templates(&self) {
        if let Err(e) = crate::templates::list_templates() {
            println!("Error listing templates: {}", e);
        }
    }

    /// Create a new project
    fn create_project(&mut self, args: &[&str]) -> Result<()> {
        use dialoguer::{Input, Select};

        let template = if args.len() > 0 {
            args[0].to_string()
        } else {
            let config = crate::config::load_config()?;
            let templates_dir = &config.templates_dir;

            if !templates_dir.exists() {
                return Err(anyhow!("No templates found. Add templates first."));
            }

            // List available templates
            let mut template_names = Vec::new();
            for entry in std::fs::read_dir(templates_dir)? {
                if let Ok(entry) = entry {
                    if entry.path().is_dir() {
                        if let Some(name) = entry.file_name().to_str() {
                            template_names.push(name.to_string());
                        }
                    }
                }
            }

            if template_names.is_empty() {
                return Err(anyhow!("No templates found. Add templates first."));
            }

            let selection = Select::new()
                .with_prompt("Select a template")
                .items(&template_names)
                .interact()?;

            template_names[selection].clone()
        };

        let name = if args.len() > 1 {
            args[1].to_string()
        } else {
            Input::new()
                .with_prompt("Project name")
                .interact()?
        };

        let path = if args.len() > 2 {
            Some(args[2].to_string())
        } else {
            None
        };

        // Collect variables interactively
        let variables = self.collect_variables(&template)?;

        crate::scaffolding::create_project(&template, &name, path.as_deref(), true, &variables)?;
        Ok(())
    }

    /// Collect template variables interactively
    fn collect_variables(&mut self, template: &str) -> Result<HashMap<String, String>> {
        let config = crate::config::load_config()?;
        let template_dir = config.templates_dir.join(template);
        let template_data = crate::templates::load_template(&template_dir)?;

        let mut variables = HashMap::new();

        if !template_data.variables.is_empty() {
            println!();
            println!("Template variables:");

            for var in &template_data.variables {
                let prompt = format!("{} (default: {})", var.description, var.default);
                let input: String = dialoguer::Input::new()
                    .with_prompt(&prompt)
                    .default(var.default.clone())
                    .interact()?;

                variables.insert(var.name.clone(), input);
            }
        }

        Ok(variables)
    }

    /// Handle template commands
    fn handle_template_command(&self, args: &[&str]) -> Result<()> {
        if args.is_empty() {
            println!("Usage: template <list|add|remove|info> [args]");
            return Ok(());
        }

        match args[0] {
            "list" => {
                self.list_templates();
            }
            "add" => {
                if args.len() < 2 {
                    println!("Usage: template add <path> [name]");
                } else {
                    let path = std::path::PathBuf::from(args[1]);
                    let name = args.get(2).map(|s| s.to_string());
                    crate::templates::add_template(path, name)?;
                }
            }
            "remove" => {
                if args.len() < 2 {
                    println!("Usage: template remove <name>");
                } else {
                    crate::templates::remove_template(args[1])?;
                }
            }
            "info" => {
                if args.len() < 2 {
                    println!("Usage: template info <name>");
                } else {
                    crate::templates::show_template_info(args[1])?;
                }
            }
            _ => {
                println!("Unknown template command: {}", args[0]);
            }
        }

        Ok(())
    }

    /// Run the wizard
    fn run_wizard(&self, args: &[&str]) -> Result<()> {
        let session_id = args.get(0).map(|s| s.to_string());
        crate::wizard::run_template_wizard(session_id)?;
        Ok(())
    }

    /// Show command history
    fn show_history(&self, args: &[&str]) -> Result<()> {
        if args.is_empty() {
            // Show recent history
            let entries = self.editor.history().iter().rev().take(20).cloned().collect::<Vec<_>>();
            println!();
            println!("Recent commands:");
            for (i, entry) in entries.iter().enumerate() {
                println!("  {}  {}", i + 1, entry);
            }
        } else if args[0] == "clear" {
            if let Ok(history_path) = crate::history::get_history_path() {
                crate::history::clear_history()?;
                println!("History cleared.");
            }
        } else if args[0] == "search" {
            if args.len() > 1 {
                let pattern = args[1];
                let matches = crate::history::search_history(pattern)?;
                println!();
                println!("Matching commands:");
                for entry in matches {
                    println!("  {}", entry);
                }
            }
        } else {
            println!("Usage: history [clear|search <pattern>]");
        }

        Ok(())
    }

    /// Handle config commands
    fn handle_config(&self, args: &[&str]) -> Result<()> {
        let key = args.get(0).map(|s| s.to_string());
        let value = args.get(1).map(|s| s.to_string());
        crate::config::handle_config(key, value)?;
        Ok(())
    }

    /// Handle variable commands
    fn handle_variables(&mut self, args: &[&str]) -> Result<()> {
        if args.is_empty() {
            println!("Session variables:");
            if self.session_variables.is_empty() {
                println!("  (none)");
            } else {
                for (key, value) in &self.session_variables {
                    println!("  {} = {}", key, value);
                }
            }
        } else if args[0] == "set" {
            if args.len() >= 3 {
                let key = args[1].to_string();
                let value = args[2].to_string();
                self.session_variables.insert(key, value);
                println!("Variable set.");
            } else {
                println!("Usage: variables set <key> <value>");
            }
        } else if args[0] == "unset" {
            if args.len() >= 2 {
                self.session_variables.remove(args[1]);
                println!("Variable unset.");
            } else {
                println!("Usage: variables unset <key>");
            }
        } else {
            println!("Usage: variables [set|unset] ...");
        }

        Ok(())
    }
}

/// Run the interactive shell
pub fn run_interactive_mode() -> Result<()> {
    let mut shell = InteractiveShell::new()?;
    shell.run()
}

/// Create a project in interactive mode
pub fn create_project_interactive(
    template: &str,
    name: &str,
    path: Option<String>,
    git: bool,
    cli_variables: &[(String, String)],
) -> Result<()> {
    use std::collections::HashMap;

    // Start with CLI-provided variables
    let mut variables: HashMap<String, String> = cli_variables
        .iter()
        .cloned()
        .collect();

    // Load template to get required variables
    let config = crate::config::load_config()?;
    let template_dir = config.templates_dir.join(template);

    if !template_dir.exists() {
        return Err(anyhow!("Template '{}' not found", template));
    }

    let template_data = crate::templates::load_template(&template_dir)?;

    // Collect variables interactively if needed
    if !template_data.variables.is_empty() {
        println!();
        println!("Template variables:");

        for var in &template_data.variables {
            // Skip if already provided via CLI
            if variables.contains_key(&var.name) {
                continue;
            }

            let prompt = format!("{} (default: {})", var.description, var.default);
            let input: String = dialoguer::Input::new()
                .with_prompt(&prompt)
                .default(var.default.clone())
                .interact()?;

            variables.insert(var.name.clone(), input);
        }
    }

    // Convert back to Vec for scaffolding
    let vars_vec: Vec<(String, String)> = variables.into_iter().collect();

    crate::scaffolding::create_project(template, name, path.as_deref(), git, &vars_vec)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_shell_creation() {
        let shell = InteractiveShell::new();
        assert!(shell.is_ok());
    }
}
