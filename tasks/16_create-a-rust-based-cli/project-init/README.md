# Project Init

A powerful Rust-based CLI productivity tool for managing project templates with customizable scaffolding, supporting multiple frameworks/languages, file generation from templates, and Git integration for rapid project initialization.

## Features

- 🚀 **Quick Project Creation**: Generate new projects from templates in seconds
- 📦 **Multiple Templates**: Built-in templates for Rust, React, Node.js, Python, and more
- 🎨 **Customizable Scaffolding**: Create your own templates with variable substitution
- 🔧 **Template Variables**: Flexible variable system with Handlebars templating
- 🌳 **Git Integration**: Automatic Git initialization and initial commit
- 📝 **Smart File Generation**: Create files and directories with custom content
- 🎯 **Interactive CLI**: User-friendly commands with helpful prompts
- ⚙️ **Configuration Management**: Customizable global settings

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/yourusername/project-init.git
cd project-init

# Build the project
cargo build --release

# Install globally
cargo install --path .
```

### Using Cargo (when published)

```bash
cargo install project-init
```

## Quick Start

### 1. Initialize Configuration

```bash
project-init init
```

This creates the configuration file in `~/.project-init/config.yaml` with default settings.

### 2. List Available Templates

```bash
project-init template list
```

### 3. Create a New Project

```bash
# Create a Rust project
project-init new --template rust --name my-rust-app

# Create a React application
project-init new --template react --name my-react-app

# Create a Python FastAPI project
project-init new --template python --name my-api

# Create a Node.js application
project-init new --template node --name my-server
```

## Usage

### Commands

#### `init` - Initialize Configuration

```bash
# Interactive mode
project-init init --interactive

# Quick setup with defaults
project-init init
```

#### `new` - Create New Project

```bash
# Basic usage
project-init new --template <template> --name <project-name>

# With custom path
project-init new --template rust --name my-app --path ./projects/my-app

# Without Git initialization
project-init new --template react --name my-app --no-git

# With custom variables
project-init new --template rust --name my-app --var author="John Doe" --var license=Apache-2.0
```

#### `template` - Manage Templates

```bash
# List all templates
project-init template list

# Add a template from local directory
project-init template add ./my-custom-template

# Add a template with custom name
project-init template add ./template --name my-template

# Remove a template
project-init template remove my-template

# Show template details
project-init template info rust
```

#### `config` - Manage Configuration

```bash
# Show all configuration
project-init config

# Get specific value
project-init config templates_dir

# Set configuration value
project-init config default_author "John Doe"
project-init config default_git true
```

## Built-in Templates

### Rust Template

A minimal Rust project with Cargo setup:

```bash
project-init new --template rust --name my-rust-project
```

**Features:**
- Pre-configured `Cargo.toml`
- Basic `main.rs` with hello world
- Comprehensive `.gitignore`
- README with getting started guide

### React Template

Modern React application with Vite:

```bash
project-init new --template react --name my-react-app
```

**Features:**
- ⚡️ Vite for fast development
- ⚛️ React 18 with TypeScript
- 🎨 ESLint & Prettier configuration
- 📦 Modern build setup

### Python Template

FastAPI application with best practices:

```bash
project-init new --template python --name my-api
```

**Features:**
- 🚀 FastAPI framework
- ✅ Pytest configuration
- 📝 Comprehensive `.gitignore`
- 🔧 Environment variable support

### Node.js Template

TypeScript-powered Node.js server:

```bash
project-init new --template node --name my-server
```

**Features:**
- 🚀 Express.js framework
- 📦 TypeScript setup
- ✨ ESLint & Prettier
- 🎯 Jest testing framework

## Creating Custom Templates

### Template Structure

A template is a directory with a `template.yaml` file:

```yaml
name: my-template
description: My custom template
language: JavaScript
version: 1.0.0

variables:
  - name: author_name
    description: Author name
    default: "Your Name"
    required: false

files:
  - path: package.json
    content: |
      {
        "name": "{{project_name_kebab}}",
        "version": "1.0.0",
        "author": "{{author_name}}"
      }
    template: true

directories:
  - src
  - tests
```

### Template Variables

Templates support special variables:

- `{{project_name}}` - Original project name
- `{{project_name_kebab}}` - kebab-case version
- `{{project_name_snake}}` - snake_case version
- `{{project_name_pascal}}` - PascalCase version
- `{{author}}` - From config or custom
- `{{license}}` - License type
- `{{year}}` - Current year

### Handlebars Helpers

Templates support Handlebars helpers:

- `{{kebab-case "MyString"}}` → `my-string`
- `{{snake-case "MyString"}}` → `my_string`
- `{{pascal-case "my-string"}}` → `MyString`

Example usage:

```handlebars
const {{pascal-case project_name}} = {
  name: "{{project_name_kebab}}",
  slug: "{{snake-case project_name}}"
};
```

## Configuration

Configuration is stored in `~/.project-init/config.yaml`:

```yaml
templates_dir: /home/user/.project-init/templates
default_git: true
default_author: Your Name
default_license: MIT
```

### Configuration Options

| Key | Description | Default |
|-----|-------------|---------|
| `templates_dir` | Directory for storing templates | `~/.project-init/templates` |
| `default_git` | Initialize Git by default | `true` |
| `default_author` | Default author name | `Your Name` |
| `default_license` | Default license | `MIT` |

## Examples

### Example 1: Create a Rust Project

```bash
# Create a new Rust project with Git
project-init new --template rust --name my-cli

cd my-cli
cargo build
cargo run
```

### Example 2: Create a React App with Custom Variables

```bash
project-init new \
  --template react \
  --name dashboard \
  --var author="Jane Doe" \
  --var use_router=true

cd dashboard
npm install
npm run dev
```

### Example 3: Create Multiple Projects

```bash
# Create backend (Python)
project-init new --template python --name my-api --path ./backend

# Create frontend (React)
project-init new --template react --name my-frontend --path ./frontend

# Create documentation
project-init new --template markdown --name docs --path ./docs
```

### Example 4: Add and Use Custom Template

```bash
# Create a custom template directory
mkdir -p my-templates/golang-template

# Create template.yaml in that directory
# (see template structure above)

# Add the template
project-init template add ./my-templates/golang-template

# Use it
project-init new --template golang-template --name my-go-app
```

## Development

### Project Structure

```
project-init/
├── Cargo.toml              # Project metadata and dependencies
├── src/
│   ├── main.rs            # CLI entry point
│   ├── cli.rs             # Command definitions
│   ├── config.rs          # Configuration handling
│   ├── templates.rs       # Template management
│   ├── scaffolding.rs     # File generation logic
│   ├── git.rs             # Git operations
│   └── error.rs           # Error types
├── templates/             # Built-in templates
│   ├── rust/
│   ├── react/
│   ├── node/
│   └── python/
└── README.md
```

### Building

```bash
# Debug build
cargo build

# Release build
cargo build --release

# Run tests
cargo test

# Format code
cargo fmt

# Lint code
cargo clippy
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Built with [Rust](https://www.rust-lang.org/)
- CLI powered by [clap](https://github.com/clap-rs/clap)
- Template engine by [Handlebars](https://handlebarsjs.com/)
- Git operations via [git2](https://github.com/rust-lang/git2-rs)

## Roadmap

- [ ] Template marketplace/community templates
- [ ] Remote template support (Git URLs)
- [ ] Interactive template builder wizard
- [ ] Template versioning and updates
- [ ] Plugin system for custom helpers
- [ ] Docker integration
- [ ] CI/CD configuration generation

## Support

For issues, questions, or suggestions, please open an issue on GitHub.

---

Made with ❤️ by the Project Init team
