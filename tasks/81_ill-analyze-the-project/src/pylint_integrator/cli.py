"""
Command-line interface for pylint integrator.
"""

import sys
from pathlib import Path
from typing import List, Optional

import click

from pylint_integrator.core.analyzer import PylintAnalyzer
from pylint_integrator.core.config import Configuration
from pylint_integrator.formatters import get_formatter


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Pylint Integrator - Advanced pylint integration for code quality analysis."""
    pass


@cli.command()
@click.argument("paths", nargs=-1, required=True, type=click.Path(exists=True))
@click.option(
    "--config", "-c",
    type=click.Path(exists=True),
    help="Path to configuration file (TOML)"
)
@click.option(
    "--output-format", "-f",
    type=click.Choice(["console", "json", "html", "junit"], case_sensitive=False),
    default="console",
    help="Output format"
)
@click.option(
    "--output", "-o",
    type=click.Path(),
    help="Output file (if not specified, prints to stdout)"
)
@click.option(
    "--pylintrc", "-r",
    type=click.Path(exists=True),
    help="Path to pylint configuration file"
)
@click.option(
    "--score-threshold", "-s",
    type=float,
    help="Fail if score is below this threshold (0-10)"
)
@click.option(
    "--fail-on-error",
    is_flag=True,
    help="Exit with error code if any errors found"
)
@click.option(
    "--fail-on-warning",
    is_flag=True,
    help="Exit with error code if any warnings found"
)
@click.option(
    "--ignore",
    multiple=True,
    help="Patterns to ignore (can be used multiple times)"
)
@click.option(
    "--baseline", "-b",
    type=click.Path(exists=True),
    help="Baseline file for comparison"
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Verbose output"
)
@click.option(
    "--quiet", "-q",
    is_flag=True,
    help="Quiet mode (minimal output)"
)
@click.option(
    "--ci",
    is_flag=True,
    help="CI mode (optimized for CI/CD systems)"
)
@click.option(
    "--github-annotations",
    is_flag=True,
    help="Output GitHub Actions annotations"
)
def analyze(
    paths: tuple,
    config: Optional[str],
    output_format: str,
    output: Optional[str],
    pylintrc: Optional[str],
    score_threshold: Optional[float],
    fail_on_error: bool,
    fail_on_warning: bool,
    ignore: tuple,
    baseline: Optional[str],
    verbose: bool,
    quiet: bool,
    ci: bool,
    github_annotations: bool,
):
    """
    Run pylint analysis on specified paths.

    PATHS: One or more files or directories to analyze
    """
    # Build configuration
    config_obj = Configuration(
        paths=list(paths),
        output_format=output_format,
        output_file=output,
        pylintrc=pylintrc,
        score_threshold=score_threshold,
        fail_on_error=fail_on_error,
        fail_on_warning=fail_on_warning,
        ignore_patterns=list(ignore) if ignore else [],
        baseline_file=baseline,
        verbose=verbose,
        quiet=quiet,
        ci_mode=ci,
        github_annotations=github_annotations,
    )

    # Load config file if specified
    if config:
        try:
            file_config = Configuration.from_file(config)
            config_obj = file_config.merge_with(config_obj)
        except Exception as e:
            click.echo(f"Error loading config file: {e}", err=True)
            sys.exit(1)

    # Run analysis
    analyzer = PylintAnalyzer(config_obj)
    result = analyzer.analyze()

    # Format output
    formatter = get_formatter(output_format)
    formatted_output = formatter.format(result)

    # Write output
    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w") as f:
            f.write(formatted_output)
        if not quiet:
            click.echo(f"Results written to {output}")
    else:
        click.echo(formatted_output)

    # Exit with appropriate code
    if not result.success:
        sys.exit(1)


@cli.command()
@click.argument("path", type=click.Path(exists=True))
def init(path: str):
    """
    Initialize configuration in current directory.

    Creates a pyproject.toml with pylint-integrator configuration.
    """
    config_path = Path(path) / "pyproject.toml"

    if config_path.exists():
        if not click.confirm(f"{config_path} already exists. Overwrite?"):
            click.echo("Aborted.")
            return

    default_config = """[tool.pylint-integrator]
# Directories to analyze (default: ["src", "tests"])
paths = ["src", "tests"]

# Output format: console, json, html, junit
output_format = "console"

# Pylint configuration file
pylintrc = ".pylintrc"

# Patterns to ignore
ignore_patterns = ["*.pyc", "__pycache__", ".git"]

# Score threshold (fail if below this)
score_threshold = 7.0

# Fail on error/warning
fail_on_error = false
fail_on_warning = false

# Verbose output
verbose = false

# Include tests in analysis
include_tests = true
"""

    config_path.write_text(default_config)
    click.echo(f"Configuration written to {config_path}")
    click.echo("\nEdit the configuration to customize pylint-integrator for your project.")


@cli.command()
@click.argument("paths", nargs=-1, type=click.Path(exists=True))
def check(paths: tuple):
    """
    Quick check - analyze paths and exit with code 0 if no errors found.

    Useful for CI/CD pipelines.
    """
    if not paths:
        click.echo("No paths specified", err=True)
        sys.exit(1)

    config = Configuration(
        paths=list(paths),
        output_format="console",
        quiet=True,
        fail_on_error=True,
    )

    analyzer = PylintAnalyzer(config)
    result = analyzer.analyze()

    if not result.success:
        if result.error_count > 0:
            click.echo(f"Found {result.error_count} error(s)", err=True)
        sys.exit(1)
    else:
        if result.total_issues == 0:
            click.echo("✅ No issues found")
        else:
            click.echo(f"⚠️  Found {result.total_issues} issue(s) but no errors")
        sys.exit(0)


@cli.command()
@click.option("--output", "-o", type=click.Path(), default="pylint-report.html", help="Output HTML file")
@click.argument("paths", nargs=-1, required=True, type=click.Path(exists=True))
def report(output: str, paths: tuple):
    """
    Generate HTML report for analysis results.

    Creates a detailed HTML report with all issues and metrics.
    """
    config = Configuration(
        paths=list(paths),
        output_format="html",
        output_file=output,
    )

    analyzer = PylintAnalyzer(config)
    result = analyzer.analyze()

    formatter = get_formatter("html")
    html_output = formatter.format(result)

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_output)

    click.echo(f"HTML report generated: {output_path}")
    click.echo(f"Score: {result.global_score:.2f}/10")
    click.echo(f"Total issues: {result.total_issues}")


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
