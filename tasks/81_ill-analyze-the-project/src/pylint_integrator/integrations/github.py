"""GitHub Actions integration generator."""

from typing import Optional


class GitHubActionsGenerator:
    """Generate GitHub Actions workflow files for pylint integration."""

    @staticmethod
    def generate_basic_workflow(
        name: str = "Pylint Analysis",
        python_version: str = "3.11",
        run_on: Optional[list] = None,
    ) -> str:
        """
        Generate basic GitHub Actions workflow.

        Args:
            name: Workflow name
            python_version: Python version to use
            run_on: Events to trigger workflow (default: [push, pull_request])

        Returns:
            YAML workflow content
        """
        if run_on is None:
            run_on = ["push", "pull_request"]

        return f"""name: {name}

on:
  {", ".join(run_on)}

jobs:
  pylint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '{python_version}'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pylint-integrator

      - name: Run pylint analysis
        run: |
          pylint-integrator analyze src/ --output-format json --output pylint-results.json

      - name: Upload results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: pylint-results
          path: pylint-results.json

      - name: Check score threshold
        run: |
          pylint-integrator check src/
"""

    @staticmethod
    def generate_advanced_workflow(
        score_threshold: float = 7.0,
        fail_on_error: bool = True,
        generate_html_report: bool = True,
    ) -> str:
        """
        Generate advanced GitHub Actions workflow with reporting.

        Args:
            score_threshold: Minimum acceptable score
            fail_on_error: Whether to fail on errors
            generate_html_report: Whether to generate HTML report

        Returns:
            YAML workflow content
        """
        return f"""name: Pylint Quality Check

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  pylint:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pylint-integrator

      - name: Run pylint analysis
        run: |
          pylint-integrator analyze \\
            src/ \\
            --score-threshold {score_threshold} \\
            --fail-on-error {str(fail_on_error).lower()} \\
            --output-format json \\
            --output pylint-results.json

      - name: Generate HTML report
        if: always()
        run: |
          pylint-integrator report \\
            --output pylint-report.html \\
            src/

      - name: Upload artifacts
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: pylint-reports
          path: |
            pylint-results.json
            pylint-report.html
          retention-days: 30

      - name: Comment PR with results
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const results = JSON.parse(fs.readFileSync('pylint-results.json', 'utf8'));

            const comment = `## Pylint Analysis Results\\n` +
              `- **Score**: ${{results.global_score.toFixed(2)}}/10\\n` +
              `- **Total Issues**: ${{results.total_issues}}\\n` +
              `- **Errors**: ${{results.error_count}}\\n` +
              `- **Warnings**: ${{results.warning_count}}\\n`;

            github.rest.issues.createComment({{
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: comment
            }});
"""

    @staticmethod
    def generate_comment_workflow() -> str:
        """Generate workflow that comments on PRs with pylint results."""
        return """name: Pylint PR Comment

on:
  pull_request:
    types: [opened, synchronize, reopened]

permissions:
  contents: read
  pull-requests: write

jobs:
  pylint-comment:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install pylint-integrator
        run: pip install pylint-integrator

      - name: Run pylint
        run: |
          pylint-integrator analyze . --output-format json --output pylint-results.json

      - name: Comment on PR
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            try {
              const results = JSON.parse(fs.readFileSync('pylint-results.json', 'utf8'));

              let body = '## 🔍 Pylint Analysis Results\\n\\n';
              body += `**Score**: ${results.global_score.toFixed(2)}/10\\n\\n`;
              body += '### Issue Summary\\n\\n';
              body += '| Type | Count |\\n';
              body += '|------|-------|\\n';
              body += `| Fatal | ${results.fatal_count} |\\n`;
              body += `| Error | ${results.error_count} |\\n`;
              body += `| Warning | ${results.warning_count} |\\n`;
              body += `| Convention | ${results.convention_count} |\\n`;
              body += `| Refactor | ${results.refactor_count} |\\n`;

              github.rest.issues.createComment({
                issue_number: context.issue.number,
                owner: context.repo.owner,
                repo: context.repo.repo,
                body: body
              });
            } catch (error) {
              console.log('Could not read pylint results:', error);
            }
"""

    @staticmethod
    def write_workflow_file(filename: str = ".github/workflows/pylint.yml", content: str = None) -> None:
        """
        Write workflow file to disk.

        Args:
            filename: Path to workflow file
            content: YAML content (if None, uses basic workflow)
        """
        from pathlib import Path

        if content is None:
            content = GitHubActionsGenerator.generate_basic_workflow()

        workflow_path = Path(filename)
        workflow_path.parent.mkdir(parents=True, exist_ok=True)
        workflow_path.write_text(content)

        print(f"Workflow written to {workflow_path}")
