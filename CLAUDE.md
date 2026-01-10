# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **planning repository** for "DeepCode" - an AI-native development workflow engine written in Python 3.8.10, designed to run on Windows 7 in internal network environments. The project implements Claude Code's core design patterns including SDD (Spec-Driven Development), context management, slash commands, hooks, and security controls.

**Current Status**: Planning/spec phase. No production code exists yet.

**Target Environment**: Python 3.8.10 (strict), Windows 7 (primary), internal network with DeepSeek R1 70B LLM.

## Key Documentation

- `specs/spec.md` - Requirements specification with user stories and acceptance criteria
- `specs/plan.md` - Technical architecture, design patterns, and implementation strategy
- `specs/tasks.md` - Atomic task breakdown with dependencies and TDD markers
- `constitution.md` - **NON-NEGOTIABLE engineering principles** (YAGNI, TDD, explicit error handling)
- `DEVELOPMENT_WORKFLOW.md` - SDD/TDD workflow (spec → plan → tasks → code)
- `TODO.md` - Phase-by-phase task checklist

## Project Structure (Planned)

```
deep_code/
├── core/           # Agent engine, context, executor, SDD
├── interaction/    # Parser (@/!), commands, hooks
├── security/       # Permissions, sandbox, checkpoint
├── extensions/     # MCP, skills, subagents
├── llm/            # LLM client (ABC + openai/requests implementations)
├── config/         # Settings, loader
└── cli/            # CLI entry point
```

## Engineering Constitution (Non-Negotiable)

### 1. TDD is Mandatory
- **Red → Green → Refactor** order strictly enforced
- Write tests FIRST, never after implementation
- Prevents AI "self-consistency hallucination"
- Table-driven tests for core logic

### 2. YAGNI (You Aren't Gonna Need It)
- Only implement what `spec.md` explicitly requires
- No "future-proofing" or premature abstraction
- Standard library preferred over third-party

### 3. Python 3.8.10 Strict Compatibility
- No Python 3.9+ features
- Type hints: use `from typing import List, Dict, Optional...`
- Avoid `:=` walrus operator, `f"{var=}"` debug syntax
- Use `from __future__ import annotations` or string type annotations

### 4. Windows 7 Compatibility
- Paths: use `pathlib.Path` (never hardcode `/` or `\`)
- Commands: Windows 7 uses PowerShell (`powershell.exe -Command`), Unix uses bash
- Encoding: **always** specify `encoding='utf-8'`
- Terminal: `colorama==0.4.6` required for ANSI colors

### 5. Explicitness
- All errors must be explicitly handled (no `_` discard)
- Dependencies via constructor injection (no globals/singletons)
- All public APIs must have type hints and docstrings

### 6. Git Checkpointing
- After completing each feature/user story with passing tests: `pytest` → `git add` → `git commit` → `git push`
- Commit messages must reference task IDs (e.g., `T040`, `US-001`)

## Development Commands

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_parser.py

# Run with coverage
pytest --cov=deep_code
```

### Installation (Python 3.8.10)
```bash
# Online
pip install -r requirements.txt

# Offline (internal network)
pip install --no-index --find-links wheels/ -r requirements.txt
```

### Linting/Formatting
```bash
# Format code (if using black)
black deep_code/

# Type checking (if using mypy)
mypy deep_code/
```

## Architecture Highlights

### LLM Client Pattern
Uses **abstract base class + factory** for flexibility:
- `LLMClient` (ABC) - interface with `chat_completion()`, `get_model()`, etc.
- `OpenAIClient` - uses `openai==0.28.1` (last version supporting Python 3.8)
- `RequestsClient` - fallback using `requests==2.28.2`
- `LLMClientFactory` - creates appropriate implementation based on config

### Configuration Layers (Priority Order)
1. CLI arguments (highest)
2. Project local: `.deepcode/settings.local.json`
3. Project shared: `.deepcode/settings.json`
4. User global: `~/.deepcode/settings.json` (lowest)

### Interaction Model
- `@file` / `@dir` - Context injection (Git-aware, respects .gitignore)
- `!command` - Command execution (PowerShell on Win7, bash on Unix)
- Output from `!` commands automatically becomes context for next turn

### Long-Term Memory Files (Auto-discovered)
- `CLAUDE.md` - Project operations manual
- `AGENTS.md` - Cross-agent standards
- `constitution.md` - Non-negotiable principles
- Support modular imports via `@` syntax

## Key Dependencies (Version-Locked for Python 3.8.10)

| Package | Version | Purpose |
|---------|---------|---------|
| click | 7.1.2 | CLI framework |
| openai | 0.28.1 | LLM client (primary) |
| rich | 12.6.0 | Terminal formatting |
| prompt_toolkit | 3.0.39 | Interactive input |
| questionary | 1.10.0 | Menus/prompts |
| colorama | 0.4.6 | Windows 7 ANSI colors |
| pytest | 7.2.2 | Testing |

## Working with This Repository

1. **Before implementing**: Read `specs/spec.md`, `specs/plan.md`, `specs/tasks.md`, and `constitution.md`
2. **For new features**: Follow SDD workflow - spec should exist first
3. **When coding**: Strict TDD - write failing test, then make it pass
4. **Before committing**: Ensure tests pass, link to task ID in commit message
5. **Windows 7 testing**: Verify path handling, encoding (UTF-8), PowerShell commands

## Common Gotchas

- **PowerShell 2.0 limitations**: Windows 7 ships with PowerShell 2.0; avoid newer cmdlets
- **Path separators**: Never hardcode; use `pathlib.Path` or `os.path.join()`
- **Encoding defaults**: Always specify `encoding='utf-8'` for file operations
- **openai library**: Version 0.28.1 uses `functions` parameter, not `tools`
- **Type hints**: Use `from typing import` imports, not built-in types (Python 3.9+ feature)
