# Project Init - Usage Examples

This document provides detailed examples for using Project Init in various scenarios.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Basic Usage](#basic-usage)
3. [Working with Templates](#working-with-templates)
4. [Advanced Scenarios](#advanced-scenarios)
5. [Custom Templates](#custom-templates)
6. [Integration Examples](#integration-examples)

## Getting Started

### First-Time Setup

```bash
# Step 1: Initialize configuration
project-init init

# Step 2: List available templates
project-init template list

# Step 3: Create your first project
project-init new --template rust --name hello-world
```

## Basic Usage

### Creating a Rust Project

```bash
# Simple Rust project
project-init new --template rust --name my-cli

# With custom path
project-init new --template rust --name my-cli --path ./projects/my-cli

# Without Git
project-init new --template rust --name my-cli --no-git
```

### Creating a React Application

```bash
# Basic React app
project-init new --template react --name my-app

# With custom variables
project-init new --template react --name dashboard \
  --var author="John Doe" \
  --var license=MIT
```

### Creating a Python API

```bash
# FastAPI project
project-init new --template python --name my-api

# Custom path and variables
project-init new --template python --name backend-api \
  --path ./backend \
  --var author="Jane Developer"
```

### Creating a Node.js Server

```bash
# Node.js/Express server
project-init new --template node --name my-server

# With TypeScript
project-init new --template node --name api-server \
  --var node_version=20
```

## Working with Templates

### Listing Templates

```bash
# List all templates
project-init template list

# Get detailed info about a template
project-init template info rust
```

### Managing Templates

```bash
# Add a local template
project-init template add ./my-custom-template

# Add with custom name
project-init template add ./templates/go-template --name golang

# Remove a template
project-init template remove my-custom-template
```

## Advanced Scenarios

### Monorepo Setup

```bash
# Create a monorepo structure
project-init new --template node --name api --path ./monorepo/api --no-git
project-init new --template react --name web --path ./monorepo/web --no-git

# Initialize Git at root
cd monorepo
git init
git add .
git commit -m "Initial commit: Monorepo setup"
```

### Microservices Architecture

```bash
# Create multiple microservices
for service in auth users payments; do
  project-init new --template node --name $service-service \
    --path ./microservices/$service --no-git
done

# Create API gateway
project-init new --template node --name gateway \
  --path ./microservices/gateway --no-git
```

### Full-Stack Application

```bash
# Backend (Python/FastAPI)
project-init new --template python --name backend --path ./fullstack/backend

# Frontend (React)
project-init new --template react --name frontend --path ./fullstack/frontend

# Mobile (can add mobile template later)
project-init new --template rust --name mobile-api --path ./fullstack/mobile-api
```

### Custom Configuration

```bash
# Set your details globally
project-init config default_author "Your Name"
project-init config default_license "MIT"
project-init config default_git true

# Verify configuration
project-init config
```

## Custom Templates

### Creating a Simple Template

```bash
# 1. Create template directory
mkdir -p my-templates/basic

# 2. Create template.yaml
cat > my-templates/basic/template.yaml << 'EOF'
name: basic
description: A basic project template
language: Generic
version: 1.0.0

variables:
  - name: author_name
    description: Author name
    default: "Anonymous"
    required: false

files:
  - path: README.md
    content: |
      # {{project_name}}

      Created by {{author_name}} on {{year}}.
    template: true

  - path: .gitignore
    content: |
      node_modules/
      *.log
    template: false

directories:
  - src
  - tests
EOF

# 3. Add and use template
project-init template add ./my-templates/basic
project-init new --template basic --name test-project
```

### Advanced Template with Handlebars

```yaml
name: go-api
description: Go REST API template
language: Go
version: 1.0.0

variables:
  - name: use_cors
    description: Enable CORS
    default: "false"
    required: false

files:
  - path: main.go
    content: |
      package main

      import "fmt"

      func main() {
          fmt.Println("{{project_name}} API")
          {{#if use_cors}}
          fmt.Println("CORS enabled")
          {{/if}}
      }
    template: true
```

## Integration Examples

### CI/CD Integration

```yaml
# .github/workflows/create-project.yml
name: Create Project from Template

on:
  workflow_dispatch:
    inputs:
      project_name:
        required: true
      template:
        required: true
        default: rust

jobs:
  create:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Install project-init
        run: cargo install project-init
      - name: Create project
        run: |
          project-init new \
            --template ${{ inputs.template }} \
            --name ${{ inputs.project_name }} \
            --path ./${{ inputs.project_name }}
```

### Docker Integration

```dockerfile
# Dockerfile for generated projects
FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm ci --only=production

COPY dist ./dist

EXPOSE 3000

CMD ["node", "dist/index.js"]
```

### Makefile Integration

```makefile
# Makefile for project management
.PHONY: dev build test clean install-tools

install-tools:
	@echo "Installing project-init..."
	cargo install project-init

create-rust:
	project-init new --template rust --name $(NAME)

create-react:
	project-init new --template react --name $(NAME)

dev:
	npm run dev

build:
	npm run build

test:
	npm test

clean:
	rm -rf node_modules dist
```

## Tips and Tricks

### 1. Use Shell Aliases

```bash
# Add to ~/.bashrc or ~/.zshrc
alias pi='project-init'
alias pi-new='project-init new'
alias pi-list='project-init template list'
alias pi-rust='project-init new --template rust'
alias pi-react='project-init new --template react'
```

### 2. Create Project Scripts

```bash
#!/bin/bash
# create-microservice.sh

SERVICE_NAME=$1
project-init new --template node --name $SERVICE_NAME --path ./services/$SERVICE_NAME --no-git

echo "Microservice $SERVICE_NAME created at ./services/$SERVICE_NAME"
```

### 3. Template Variables Cheatsheet

```bash
# Built-in variables available in all templates
{{project_name}}          # Original project name
{{project_name_kebab}}    # kebab-case (my-project)
{{project_name_snake}}    # snake_case (my_project)
{{project_name_pascal}}   # PascalCase (MyProject)
{{author}}                # From config or variable
{{license}}               # License type
{{year}}                  # Current year
```

### 4. Handlebars Helpers

```handlebars
{{kebab-case "MyString"}}      # my-string
{{snake-case "MyString"}}      # my_string
{{pascal-case "my-string"}}    # MyString
```

### 5. Batch Project Creation

```bash
#!/bin/bash
# Create multiple projects
templates=("rust" "react" "node" "python")

for template in "${templates[@]}"; do
  project-init new --template $template --name test-$template --path ./test-projects/test-$template --no-git
done
```

## Troubleshooting

### Issue: Template Not Found

```bash
# Verify template exists
project-init template list

# Add template if missing
project-init template add ./path/to/template
```

### Issue: Git Initialization Failed

```bash
# Create without Git first
project-init new --template rust --name my-project --no-git

# Initialize manually
cd my-project
git init
```

### Issue: Permission Errors

```bash
# Check directory permissions
ls -la

# Ensure write permissions
chmod +w ./target-directory
```

## Best Practices

1. **Always initialize config first**: Run `project-init init` to set up defaults
2. **Use version control**: Keep templates in Git for versioning
3. **Document custom variables**: Document required variables in template description
4. **Test templates**: Test new templates before sharing
5. **Use descriptive names**: Use clear names for projects and templates
6. **Leverage variables**: Use template variables for flexibility
7. **Keep templates simple**: Start simple, add complexity as needed

## More Examples

For more examples and community templates, visit:
- GitHub Issues: https://github.com/yourusername/project-init/issues
- Discussion Forum: [Link to forum]
- Community Templates: [Link to marketplace]
