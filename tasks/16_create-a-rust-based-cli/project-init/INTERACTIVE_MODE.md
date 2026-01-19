# Interactive Mode Documentation

## Overview

The project-init CLI tool now includes a powerful interactive mode with command history, a multi-step template creation wizard, and enhanced template variable support.

## Features

### 1. Interactive Shell (REPL)

Launch an interactive shell for working with templates:

```bash
project-init interactive
```

Or use the short form:

```bash
project-init i
```

**Features:**
- Command history (use arrow keys to navigate)
- Tab completion for commands
- Session variables
- All template commands available in interactive mode

**Available Commands in Interactive Mode:**
- `new` - Create a new project from a template
- `list` - List all available templates
- `template` - Manage templates (add, remove, info)
- `wizard` - Run the template creation wizard
- `history` - Show command history
- `config` - Manage configuration
- `variables` - Manage template variables
- `clear` - Clear the screen
- `help` / `?` - Show help message
- `exit` / `quit` - Exit interactive mode

**Example Usage:**

```bash
$ project-init interactive
project-init> new
Select a template:
  0> rust-basic
  1> go-service
  2> python-cli
❯ 0
Project name: my-app
Template variables:
Author name (default: Your Name): John Doe
License (default: MIT): Apache-2.0
✓ Project created successfully!

project-init> list
Available templates:
  rust-basic - Basic Rust project with Cargo setup
  go-service - Go microservice with HTTP server

project-init> exit
Goodbye!
```

### 2. Template Creation Wizard

Create new templates through an interactive, multi-step wizard:

```bash
project-init wizard
```

**Wizard Steps:**

1. **Basic Information**
   - Template name
   - Description
   - Programming language
   - Version

2. **Template Variables**
   - Define custom variables
   - Set variable types (string, number, boolean, choice)
   - Add validation rules
   - Set default values

3. **Files and Directories**
   - Select source directory
   - Automatically scan for files
   - Choose which files to include

4. **Review and Confirm**
   - Review all settings
   - Make changes if needed
   - Create template

**Example Usage:**

```bash
$ project-init wizard
╔════════════════════════════════════════════════════════════╗
║          Template Creation Wizard                        ║
╚════════════════════════════════════════════════════════════╝

─ Step 1: Basic Information
Template name: rust-web-api
Template description: Rust REST API with Actix-web
Programming language:
  0> Rust
  1> Go
  2> Python
❯ 0
Template version (default: 0.1.0): 1.0.0

─ Step 2: Template Variables
Would you like to add template variables? [y/N]: y
Variable name: database_type
Variable description: Type of database to use
Default value: postgresql
Variable type:
  0> String
  1> Number
  2> Boolean
  3> Choice
❯ 3
Choices (comma-separated): postgresql,mysql,sqlite
Is this variable required? [y/N]: y

─ Step 3: Files and Directories
Enter the path to the source directory you want to template: ./template-src
Found 12 files and 3 directories

─ Step 4: Review Template
Template Name: rust-web-api
Description: Rust REST API with Actix-web
Language: Rust
Version: 1.0.0

Variables (1):
  - database_type (Type of database to use) - choice: postgresql, mysql, sqlite - default: postgresql

Files: 12
Directories: 3

Create this template? [Y/n]: y

✓ Template 'rust-web-api' created successfully!

You can now use this template with:
  project-init new -t rust-web-api <project-name>
```

**Resuming Wizard Sessions:**

Wizard sessions are automatically saved. You can resume an interrupted session:

```bash
project-init wizard --resume <session-id>
```

Or list available sessions:

```bash
project-init history list
```

### 3. Enhanced Variable System

The template variable system has been enhanced with new types and validation capabilities.

**Variable Types:**

1. **String** - Text values with optional regex validation
2. **Number** - Numeric values with min/max validation
3. **Boolean** - True/false values
4. **Choice** - Predefined list of options

**Variable Features:**

- **Validation Rules**
  - Pattern matching with regex
  - Length constraints (min/max)
  - Range constraints for numbers
  - Custom validators

- **Dependencies**
  - Variables can depend on other variables
  - Conditional display based on previous values

- **Environment Variables**
  - Reference environment variables in templates: `{{env:VAR_NAME}}`

- **Conditional Logic**
  - Use conditionals in templates: `{{#if var}}...{{/if}}`

**Example Template Variables:**

```yaml
variables:
  - name: project_name
    description: Name of the project
    default: my-project
    required: true
    validation:
      pattern: '^[a-z][a-z0-9-]+$'
      min_length: 3
      max_length: 50

  - name: enable_logging
    description: Enable logging
    default: "true"
    variable_type: boolean

  - name: log_level
    description: Logging level
    default: info
    variable_type: choice
    choices:
      - debug
      - info
      - warn
      - error
    depends_on: enable_logging
```

**Using Variables in Templates:**

```handlebars
// Cargo.toml
name = "{{project_name}}"
version = "0.1.0"
authors = ["{{author_name}}"]

{{#if enable_logging}}
[dependencies]
log = "{{log_level}}"
{{/if}}
```

### 4. Command History

Persistent command history across sessions with search and analytics.

**History Commands:**

```bash
# Show recent history
project-init history

# List all history
project-init history list

# Search history
project-init history search <pattern>

# Show frequent commands
project-init history frequent --count 10

# Clear history
project-init history clear
```

**History Features:**
- Automatic persistence across sessions
- Search by pattern
- Analytics (most used commands)
- Configurable history size (default: 1000 entries)

**Interactive History Navigation:**

In interactive mode:
- **Up/Down arrows** - Navigate through history
- **Ctrl+R** - Reverse search (coming soon)
- History is stored in `~/.project-init/history`

### 5. Interactive Project Creation

Create projects interactively with prompts for all variables:

```bash
project-init new -t rust-basic --interactive my-project
```

This will:
1. Load the template
2. Prompt for each variable interactively
3. Show default values
4. Validate inputs
5. Create the project

**Combining CLI and Interactive Mode:**

You can provide some variables via CLI and be prompted for others:

```bash
project-init new -t rust-basic my-project -v author="John Doe" --interactive
```

This will use "John Doe" for the author variable but prompt for all other variables.

### 6. Session Management

Wizard and interactive sessions are automatically saved and can be resumed.

**Session Features:**
- Automatic save after each step
- Resume interrupted sessions
- Session cleanup (old sessions deleted after 7 days)
- Session metadata tracking

**Session Storage:**

Sessions are stored in `~/.project-init/sessions/` as JSON files.

## Configuration

### History Settings

History is stored in `~/.project-init/history` with the following defaults:
- Maximum entries: 1000
- Automatic cleanup: disabled
- Session cleanup: 7 days

### Wizard Settings

Wizard sessions are stored in `~/.project-init/sessions/` with:
- Automatic save: enabled
- Cleanup: 7 days
- Session format: JSON

## Advanced Features

### Template Conditionals

Use conditional logic in your templates:

```handlebars
{{#if enable_feature_x}}
// Feature X code
{{#if use_advanced_mode}}
// Advanced mode implementation
{{/if}}
{{/if}}
```

### Environment Variables

Reference environment variables in templates:

```handlebars
database_url = "{{env:DATABASE_URL}}"
```

### Variable Dependencies

Variables can depend on other variables:

```yaml
variables:
  - name: use_database
    description: Use a database
    default: "true"
    variable_type: boolean

  - name: database_type
    description: Type of database
    default: postgresql
    variable_type: choice
    choices:
      - postgresql
      - mysql
      - sqlite
    depends_on: use_database
```

## Tips and Best Practices

1. **Use Interactive Mode for Learning**
   - Explore available templates
   - Understand variable requirements
   - Preview before creating projects

2. **Use Wizard for Template Creation**
   - Ensures all required fields are set
   - Validates template structure
   - Creates proper YAML metadata

3. **Leverage Command History**
   - Quickly repeat previous commands
   - Search for complex commands
   - Analyze usage patterns

4. **Create Reusable Variable Presets**
   - Save common variable combinations
   - Share across team members
   - Version control with templates

5. **Use Environment Variables for Secrets**
   - Never hardcode sensitive data
   - Use `{{env:VAR_NAME}}` syntax
   - Document required environment variables

## Troubleshooting

### Interactive Mode Not Working

**Issue:** TTY errors or prompts not appearing

**Solution:** Ensure you're running in a terminal with TTY support:
```bash
# Not a pipe or redirection
project-init interactive  # ✓ Correct
cat script | project-init  # ✗ Wrong
```

### History Not Persisting

**Issue:** Commands not saved to history

**Solution:** Check permissions:
```bash
ls -la ~/.project-init/history
chmod 600 ~/.project-init/history
```

### Wizard Sessions Not Saving

**Issue:** Cannot resume wizard sessions

**Solution:** Ensure sessions directory exists:
```bash
mkdir -p ~/.project-init/sessions
```

## Examples

### Example 1: Creating a Rust API Template

```bash
$ project-init wizard
Template name: rust-api
Description: REST API with Actix-web
Language: Rust
Version: 1.0.0

Add variables? [Y/n]: y
Variable name: database
Variable description: Database type
Variable type: Choice
Choices: postgresql,mysql,sqlite

Add variables? [Y/n]: y
Variable name: enable_auth
Variable description: Enable authentication
Variable type: Boolean
Default: true

Add variables? [Y/n]: n

Source path: ./rust-api-template
Found 15 files, 4 directories

Create template? [Y/n]: y
✓ Template created!

$ project-init new -t rust-api my-service --interactive
Project name: my-service
Database type (postgresql,mysql,sqlite) [postgresql]: postgresql
Enable authentication [Y/n]: Y
✓ Project created!
```

### Example 2: Interactive Mode Session

```bash
$ project-init interactive
project-init> list
Available templates:
  rust-api - REST API with Actix-web
  go-micro - Go microservice

project-init> new
Template: rust-api
Project name: user-service
Database: postgresql
Enable auth: Y
✓ Project created!

project-init> history frequent
Most frequent commands:
  new - 5 times
  list - 3 times

project-init> exit
```

## Future Enhancements

Planned features for future releases:

1. **Enhanced History Search**
   - Ctrl+R reverse search
   - Fuzzy matching
   - Tag-based filtering

2. **Template Marketplace**
   - Browse community templates
   - One-click template installation
   - Template ratings and reviews

3. **Variable Presets**
   - Save commonly used variable sets
   - Share presets with team
   - Preset management commands

4. **Advanced Wizard Features**
   - Custom wizard flows
   - Conditional steps
   - Multi-template projects

5. **Integration with Git**
   - Clone templates from Git
   - Auto-update templates
   - Version tracking
