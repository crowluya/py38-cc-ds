# Contributing to AI Command Palette

Thank you for your interest in contributing to AI Command Palette! This document provides guidelines and instructions for contributors.

## Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/ai-command-palette.git
   cd ai-command-palette
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -e ".[dev,ml]"
   ```

4. **Initialize the tool**
   ```bash
   aicp init
   ```

## Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_core.py

# Run with coverage
pytest --cov=ai_command_palette tests/

# Run with verbose output
pytest -v tests/
```

## Code Style

This project uses:
- **Black** for code formatting
- **Ruff** for linting
- **MyPy** for type checking

Format and check your code before submitting:

```bash
# Format code
black src/ tests/

# Run linter
ruff check src/ tests/

# Type check
mypy src/
```

## Project Structure

```
ai_command_palette/
├── cli.py              # Main CLI entry point
├── ui/                 # Textual-based TUI components
├── core/               # Core business logic
│   ├── tracker.py      # Usage tracking
│   ├── registry.py     # Command registry
│   ├── scorer.py       # Scoring algorithms
│   └── workflows.py    # Workflow automation
├── ml/                 # ML and recommendation engine
│   ├── recommend.py    # Recommendation algorithms
│   └── context.py      # Context awareness
├── storage/            # Data persistence
│   ├── database.py     # SQLAlchemy models
│   └── config.py       # Configuration management
└── integrations/       # External integrations
    ├── notes.py        # Note-taking CLI
    └── shell.py        # Shell integration
```

## Making Changes

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write clear, concise code
   - Add docstrings to functions and classes
   - Include type hints
   - Add tests for new functionality

3. **Test your changes**
   ```bash
   pytest tests/
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

   Use conventional commit messages:
   - `feat:` - New feature
   - `fix:` - Bug fix
   - `docs:` - Documentation changes
   - `test:` - Test changes
   - `refactor:` - Code refactoring

5. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```

## Adding New Features

### Adding a New Command Type

1. Update `CommandType` enum in `core/registry.py`
2. Register commands with the new type
3. Update documentation

### Adding a New Integration

1. Create a new file in `integrations/`
2. Implement the integration class
3. Register commands in the main registry
4. Add tests

### Adding ML Features

1. Update `ml/recommend.py` for new recommendation algorithms
2. Update `ml/context.py` for new context features
3. Ensure backward compatibility

## Documentation

- Update README.md for user-facing changes
- Add docstrings following Google style
- Update this CONTRIBUTING.md if needed

## Questions?

Feel free to open an issue for questions or discussion.
