# DeepCode

An AI-native development workflow engine written in Python 3.8.10, designed for Windows 7 internal network environments with DeepSeek R1 70B LLM integration.

## Overview

DeepCode implements core design patterns from Claude Code including:
- **Spec-Driven Development (SDD)**: Complete workflow from requirements to implementation
- **Context Management**: Solve context friction in AI collaboration with `@file` and `@dir` syntax
- **Workflow Encapsulation**: Encode team best practices as reusable slash commands
- **Security Controls**: Permission rules, sandbox isolation, and checkpoint rollback

**Target Environment**: Python 3.8.10 (strict), Windows 7 (primary), internal network with DeepSeek R1 70B.

## Features

- **Interactive Context Injection**: Use `@file` and `@dir` to inject codebase context
- **Command Execution**: Use `!command` to execute shell commands (PowerShell on Win7, bash on Unix)
- **Long-term Memory**: Auto-discovery of `CLAUDE.md`, `AGENTS.md`, and `constitution.md`
- **Slash Commands**: Custom workflows (e.g., `/review`, `/commit`) with parameter support
- **SDD Workflow**: Generate spec → plan → tasks → implementation automatically
- **Security**: Permission-based access control, approval mechanisms, and checkpoint rollback
- **Headless Mode**: Non-interactive execution with structured output

## Installation

### Prerequisites

- Python 3.8.10 (exact version required)
- Windows 7 (primary) or Unix-like systems
- PowerShell 2.0+ on Windows 7

### Online Installation

```bash
# Clone repository
git clone <repository-url>
cd py38-cc-jk

# Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install package in development mode
pip install -e .
```

### Offline Installation (Internal Network)

```bash
# Prepare wheel files on an online machine
pip download -r requirements.txt -d wheels/

# Transfer wheels directory to internal network machine
# On internal network machine:
pip install --no-index --find-links=wheels/ -r requirements.txt
pip install -e .
```

## Configuration

### 1. DeepSeek LLM Configuration

Create or edit `~/.pycc/settings.json`:

```json
{
  "llm": {
    "provider": "openai",
    "apiBase": "https://your-deepseek-endpoint.com/v1",
    "apiKey": "your-deepseek-api-key",
    "model": "deepseek-r1-70b"
  }
}
```

Or use environment variables:

```bash
export DEEPSEEK_API_KEY="your-api-key"
export DEEPSEEK_BASE_URL="https://your-deepseek-endpoint.com/v1"
```

### 2. Project Configuration

Create `.pycc/settings.json` in your project directory:

```json
{
  "respectGitignore": true,
  "permissions": {
    "defaultMode": "ask",
    "allow": [
      "Read(**/*)",
      "Edit(**/*.py)",
      "Write(**/*.py)"
    ]
  }
}
```

### Configuration Priority (highest to lowest)

1. CLI arguments
2. Project local: `.pycc/settings.local.json`
3. Project shared: `.pycc/settings.json`
4. User global: `~/.pycc/settings.json`

Note: `.deepcode/` in this repository is used by external tools (e.g., Claude Code IDE integrations) and is not read by this Python project.

## Usage

### Interactive Mode (Default)

```bash
# Start interactive session
claude-code

# Start with custom settings file
claude-code --config /path/to/settings.json

# Start with specific model
claude-code --model deepseek-r1-70b
```

### Context Injection Examples

```bash
# Inject a single file
@core/agent.py Please explain this file's architecture

# Inject a directory (respects .gitignore)
@core/ How should I refactor this module?

# Inject multiple files
@config/loader.py @core/agent.py Compare these two files
```

### Command Execution Examples

```bash
# Execute shell commands (cmd.exe on Windows, bash on Unix)
! git status
! pytest tests/test_agent.py -v

# Command output becomes context for next turn
! git diff
# AI will see the diff in its response
```

### Slash Commands

```bash
# Use built-in or custom commands
/review core/agent.py
/commit -m "feat: implement agent engine"
/test

# Pass arguments
/command arg1 arg2

# List available commands
/help
```

#### Creating Custom Slash Commands

Create `.pycc/commands/code_review.md`:

```markdown
---
description: Run comprehensive code review
model: deepseek-r1-70b
allowed-tools: ["Read", "Bash"]
---

Please review the code in `$ARGUMENTS`:
1. Check for bugs and potential issues
2. Suggest improvements
3. Verify adherence to constitution.md

Read the files and provide a structured report.
```

Usage: `/review core/agent.py`

### Headless Mode (Non-interactive)

```bash
# Print mode (single prompt, exit after response)
claude-code -p "Explain @core/agent.py"

# Structured JSON output
claude-code -p "! git status" --output-format json

# Stream JSON for integration
claude-code -p "Analyze @core/" --output-format stream-json

# Pipe from stdin
echo "@core/agent.py Explain this" | claude-code -p
```

### SDD Workflow

```bash
# Generate spec from idea
/sdd "I want to add feature X"

# This will:
# 1. Generate specs/spec.md (requirements)
# 2. Generate specs/plan.md (technical design)
# 3. Generate specs/tasks.md (atomic tasks)
# 4. Execute implementation following TDD
```

## Project Structure

```
deep_code/
├── core/           # Agent engine, context, executor, SDD
├── interaction/    # Parser (@/!), commands, hooks
├── security/       # Permissions, sandbox, checkpoint
├── extensions/     # MCP, skills, subagents
├── llm/            # LLM client (ABC + implementations)
├── config/         # Settings, loader
└── cli/            # CLI entry point
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_agent.py

# Run with coverage
pytest --cov=deep_code

# Run with verbose output
pytest -v
```

### Code Quality

```bash
# Type checking (if using mypy)
mypy deep_code/

# Format code (if using black)
black deep_code/
```

## Windows 7 Compatibility Notes

### Path Handling
- Always use `pathlib.Path` for cross-platform paths
- Never hardcode `/` or `\` separators
- User home directory: `pathlib.Path.home()` or `~/.pycc/`

### Command Execution
- Windows: Uses cmd.exe (`cmd.exe /c`)
- Unix: Uses bash (`/bin/bash -c`)
- All commands capture UTF-8 output

### Encoding
- All file operations use `encoding='utf-8'`
- PowerShell 2.0 has limited features; use compatible syntax
- ANSI colors supported via `colorama==0.4.6`

### Common Gotchas

1. **PowerShell 2.0**: Avoid newer cmdlets and features
2. **Path separators**: Use `os.path.join()` or `pathlib.Path`
3. **Encoding defaults**: Always specify `encoding='utf-8'`
4. **OpenAI library**: Version 0.28.1 uses `functions` parameter, not `tools`
5. **Type hints**: Use `from typing import` imports, not built-in types (Python 3.9+)

## Long-term Memory Files

These files are auto-discovered and loaded at session start:

- **CLAUDE.md**: Project operations manual (tech stack, coding standards, workflows)
- **AGENTS.md**: Cross-agent standards (language, how to start/build, test/lint, Git/PR)
- **constitution.md**: Non-negotiable engineering principles (YAGNI, TDD, explicitness)

### Modular Imports

In `CLAUDE.md`, use `@` to import other files:

```markdown
# Project Standards

@docs/coding-standards.md
@docs/git-workflow.md
```

## Permission System

### Permission Modes

- `dontAsk`: Automatically allow all allowed operations
- `ask`: Prompt user for dangerous operations
- `deny`: Automatically deny all operations (read-only)

### Permission Rules

```json
{
  "permissions": {
    "defaultMode": "ask",
    "allow": [
      "Read(**/*.py)",
      "Edit(**/*.py)",
      "Bash(pytest, git status, git diff)"
    ],
    "deny": [
      "Read(**/.env)",
      "Edit(**/.env)",
      "Bash(git push --force:*, rm -rf:*)"
    ]
  }
}
```

## Checkpointing & Rollback

```bash
# Create checkpoint automatically before dangerous operations

# Rollback options
/rewind                    # Interactive rollback menu
/rewind --code             # Rollback code only
/rewind --conversation     # Rollback conversation only
/rewind --both             # Rollback both (default)
```

## Troubleshooting

### Python 3.8.10 Issues

```bash
# Verify Python version
python --version  # Must be 3.8.10

# If using wrong Python version
pyenv install 3.8.10
pyenv local 3.8.10
```

### PowerShell Encoding Issues

```bash
# Set PowerShell to UTF-8 (Windows 7)
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

### DeepSeek Connection Issues

```bash
# Test endpoint connectivity
curl -X POST https://your-endpoint.com/v1/chat/completions \
  -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-r1-70b","messages":[{"role":"user","content":"test"}]}'

# Disable SSL verification for internal networks (use with caution)
# In settings.json:
{
  "llm": {
    "verify_ssl": false
  }
}
```

## Key Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| click | 7.1.2 | CLI framework |
| openai | 0.28.1 | LLM client (primary) |
| rich | 12.6.0 | Terminal formatting |
| prompt_toolkit | 3.0.39 | Interactive input |
| questionary | 1.10.0 | Menus/prompts |
| colorama | 0.4.6 | Windows 7 ANSI colors |
| pytest | 7.2.2 | Testing |

## Documentation

- [Specification](specs/spec.md) - Requirements and user stories
- [Technical Plan](specs/plan.md) - Architecture and design patterns
- [Task Breakdown](specs/tasks.md) - Atomic implementation tasks
- [Constitution](constitution.md) - Non-negotiable engineering principles
- [Development Workflow](DEVELOPMENT_WORKFLOW.md) - SDD/TDD workflow guide
- [TODO](TODO.md) - Phase-by-phase task checklist

## Contributing

This project follows strict development practices:

1. **Spec-Driven Development**: All features start with spec.md
2. **Test-Driven Development**: Red → Green → Refactor cycle
3. **Constitution Compliance**: All code must follow constitution.md principles
4. **Git Checkpointing**: Commit after each feature with passing tests

See [DEVELOPMENT_WORKFLOW.md](DEVELOPMENT_WORKFLOW.md) for details.

## License

[Specify your license here]

## Acknowledgments

Inspired by [Claude Code](https://claude.ai/code) - Anthropic's official CLI for Claude.

---

**Status**: Planning/Development Phase
**Python Version**: 3.8.10 (strict)
**Platform**: Windows 7 (primary), Unix (supported)
