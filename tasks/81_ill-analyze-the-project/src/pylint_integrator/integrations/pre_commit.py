"""Pre-commit hook generator."""

from typing import List


class PreCommitGenerator:
    """Generate pre-commit hook configuration for pylint."""

    @staticmethod
    def generate_hook(
        paths: List[str] = None,
        exclude: str = None,
        args: List[str] = None,
    ) -> dict:
        """
        Generate pre-commit hook configuration.

        Args:
            paths: Files/directories to check
            exclude: Pattern to exclude
            args: Additional arguments

        Returns:
            Pre-commit hook dictionary
        """
        if paths is None:
            paths = ["src/"]

        if args is None:
            args = []

        hook = {
            "repo": "local",
            "hooks": [
                {
                    "id": "pylint-integrator",
                    "name": "pylint-integrator",
                    "entry": "pylint-integrator check",
                    "language": "system",
                    "types": ["python"],
                    "files": "\\.(py)$",
                }
            ]
        }

        # Add files filter if paths specified
        if paths:
            hook["hooks"][0]["files"] = "|".join(paths)

        # Add exclude if specified
        if exclude:
            hook["hooks"][0]["exclude"] = exclude

        return hook

    @staticmethod
    def generate_full_config(
        additional_hooks: List[dict] = None,
    ) -> str:
        """
        Generate complete .pre-commit-config.yaml file.

        Args:
            additional_hooks: Additional pre-commit hooks to include

        Returns:
            YAML configuration content
        """
        import yaml

        config = {
            "repos": [
                {
                    "repo": "https://github.com/pre-commit/pre-commit-hooks",
                    "rev": "v4.5.0",
                    "hooks": [
                        {"id": "trailing-whitespace"},
                        {"id": "end-of-file-fixer"},
                        {"id": "check-yaml"},
                        {"id": "check-added-large-files"},
                    ],
                },
                {
                    "repo": "local",
                    "hooks": [
                        {
                            "id": "pylint-integrator",
                            "name": "pylint-integrator",
                            "entry": "pylint-integrator check src/",
                            "language": "system",
                            "types": ["python"],
                            "pass_filenames": false,
                        }
                    ]
                },
            ]
        }

        # Add additional hooks if provided
        if additional_hooks:
            for hook in additional_hooks:
                config["repos"].append(hook)

        return yaml.dump(config, default_flow_style=False, sort_keys=False)

    @staticmethod
    def write_config_file(
        filename: str = ".pre-commit-config.yaml",
        content: str = None,
    ) -> None:
        """
        Write pre-commit config file to disk.

        Args:
            filename: Path to config file
            content: YAML content (if None, uses default config)
        """
        from pathlib import Path

        if content is None:
            content = PreCommitGenerator.generate_full_config()

        config_path = Path(filename)
        config_path.write_text(content)

        print(f"Pre-commit config written to {config_path}")
        print("\nTo install pre-commit hooks, run:")
        print("  pip install pre-commit")
        print("  pre-commit install")
