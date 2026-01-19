# CodeQuality CLI 🔍

An interactive CLI tool that analyzes code quality metrics across your project, generating comprehensive reports on complexity, duplication, and maintainability with actionable suggestions for improvements.

## Features

- **Complexity Analysis**: Calculates cyclomatic complexity for functions and methods
- **Duplication Detection**: Identifies duplicated code blocks across your project
- **Maintainability Index**: Computes maintainability scores for better code assessment
- **Code Smell Detection**: Flags long functions, too many parameters, and other issues
- **Multi-Language Support**: Supports JavaScript and TypeScript (with extensible architecture)
- **Multiple Output Formats**: Console, JSON, HTML, and Markdown reports
- **Interactive CLI**: User-friendly command-line interface with colored output
- **Configurable Thresholds**: Customize warning and critical levels
- **Smart File Discovery**: Automatic file discovery with ignore patterns

## Installation

```bash
npm install -g codequality-cli
```

Or use directly with npx:

```bash
npx codequality-cli analyze
```

## Quick Start

```bash
# Analyze current directory
codequality analyze

# Analyze specific directory
codequality analyze ./src

# Generate JSON report
codequality analyze -o json -f report.json

# Use custom configuration
codequality analyze -c .codequalityrc.json

# Verbose output
codequality analyze -v
```

## Commands

### `analyze`

Analyze code quality of a project.

```bash
codequality analyze [path] [options]
```

**Arguments:**
- `path` - Path to the project directory (default: current directory)

**Options:**
- `-c, --config <path>` - Path to configuration file
- `-o, --output <format>` - Output format: console, json, html, markdown (default: console)
- `-f, --output-file <path>` - Write output to file
- `-e, --extensions <exts>` - Comma-separated list of file extensions
- `-i, --ignore <patterns>` - Comma-separated list of ignore patterns
- `--no-colors` - Disable colored output
- `-v, --verbose` - Verbose output

### `init`

Initialize a new configuration file.

```bash
codequality init [--force]
```

**Options:**
- `-f, --force` - Overwrite existing configuration file

Creates a `.codequalityrc.json` file in the current directory with default settings.

### `config`

Show current configuration.

```bash
codequality config [-c <path>]
```

## Configuration

Create a `.codequalityrc.json` file in your project root:

```json
{
  "thresholds": {
    "complexity": {
      "warning": 10,
      "critical": 20
    },
    "duplication": {
      "warning": 5,
      "critical": 10
    },
    "maintainability": {
      "warning": 50,
      "critical": 30
    },
    "functionLength": {
      "warning": 50,
      "critical": 100
    },
    "parameterCount": {
      "warning": 5,
      "critical": 8
    }
  },
  "ignore": [
    "node_modules/**",
    "dist/**",
    "build/**",
    "**/*.min.js",
    "**/*.bundle.js"
  ],
  "extensions": [
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".mjs"
  ],
  "output": {
    "format": "console",
    "colors": true
  }
}
```

## Metrics Explained

### Cyclomatic Complexity

Measures the number of linearly independent paths through a program's source code.

- **1-10**: Simple, low risk
- **11-20**: Moderate complexity, medium risk
- **21+**: High complexity, high risk

### Maintainability Index

A composite measure of code maintainability based on volume, complexity, and lines of code.

- **85-100**: Highly maintainable
- **65-85**: Moderately maintainable
- **0-65**: Difficult to maintain

### Code Duplication

Percentage of duplicated code across your project.

- **0-5%**: Low duplication
- **5-10%**: Moderate duplication
- **10%+**: High duplication

## Output Examples

### Console Output

```
🔍 Code Quality Analysis

📊 Summary
─────────────────────────────────────
┌───────────────────────── ──────────────┐
│ Files Analyzed            42           │
│ Lines of Code             12567        │
│ Functions                 234          │
│ Avg Complexity           4.52         │
│ Max Complexity           15           │
│ Avg Maintainability      72%          │
│ Critical Issues          5            │
│ Warnings                 23           │
│ Info                     12           │
└───────────────────────── ──────────────┘

💡 Suggestions
─────────────────────────────────────
🔴 3 file(s) have high complexity
   Action: Consider breaking down complex functions into smaller, more manageable units
```

### JSON Output

```json
{
  "summary": {
    "totalFiles": 42,
    "totalLinesOfCode": 12567,
    "averageComplexity": 4.52,
    "maxComplexity": 15,
    "averageMaintainability": 72,
    "criticalIssues": 5,
    "warningIssues": 23
  },
  "files": [...],
  "suggestions": [...]
}
```

## Use Cases

1. **Pre-commit Checks**: Ensure code quality before committing
2. **CI/CD Integration**: Automated quality gates in pipelines
3. **Code Reviews**: Objective metrics for review discussions
4. **Technical Debt Tracking**: Monitor quality trends over time
5. **Refactoring Priority**: Identify files that need attention

## Examples

```bash
# Analyze TypeScript project
codequality analyze src -e .ts,.tsx

# Generate JSON report for CI/CD
codequality analyze -o json -f quality-report.json

# Exclude test files
codequality analyze -i "**/*.test.ts,**/*.spec.ts"

# Analyze with custom thresholds
codequality analyze -c custom-config.json
```

## Development

```bash
# Install dependencies
npm install

# Build the project
npm run build

# Run in development mode
npm run dev

# Run tests
npm test
```

## Architecture

The tool is built with a modular architecture:

- **Analyzers**: Complexity, duplication, and maintainability analyzers
- **Parsers**: Language-specific AST parsers (JavaScript/TypeScript)
- **Reporters**: Multiple output format generators
- **File Discovery**: Smart file system scanner with ignore patterns
- **CLI Interface**: Interactive command-line interface using Commander.js

## Contributing

Contributions are welcome! The tool is designed to be extensible:

1. Add new language parsers in `src/parsers/`
2. Implement custom analyzers in `src/analyzers/`
3. Create new output reporters in `src/reporters/`

## License

MIT

## Author

Built with ❤️ for better code quality
