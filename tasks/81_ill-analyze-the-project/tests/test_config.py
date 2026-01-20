"""Tests for Configuration class."""

import pytest
from pathlib import Path
import tempfile

from pylint_integrator.core.config import Configuration


class TestConfiguration:
    """Test Configuration class."""

    def test_default_configuration(self):
        """Test creating default configuration."""
        config = Configuration()
        assert config.paths == []
        assert config.output_format == "console"
        assert config.recursive is True
        assert config.fail_on_error is False

    def test_configuration_with_values(self):
        """Test creating configuration with specific values."""
        config = Configuration(
            paths=["src/"],
            output_format="json",
            score_threshold=7.0,
            fail_on_error=True,
        )
        assert config.paths == ["src/"]
        assert config.output_format == "json"
        assert config.score_threshold == 7.0
        assert config.fail_on_error is True

    def test_invalid_output_format(self):
        """Test that invalid output format raises error."""
        with pytest.raises(ValueError, match="Invalid output format"):
            Configuration(output_format="invalid")

    def test_invalid_score_threshold(self):
        """Test that invalid score threshold raises error."""
        with pytest.raises(ValueError, match="score_threshold must be between 0 and 10"):
            Configuration(score_threshold=11)

    def test_from_dict(self):
        """Test creating configuration from dictionary."""
        data = {
            "paths": ["src/", "tests/"],
            "output_format": "html",
            "score_threshold": 8.0,
        }
        config = Configuration.from_dict(data)
        assert config.paths == ["src/", "tests/"]
        assert config.output_format == "html"
        assert config.score_threshold == 8.0

    def test_to_dict(self):
        """Test converting configuration to dictionary."""
        config = Configuration(
            paths=["src/"],
            output_format="json",
            score_threshold=7.0,
        )
        data = config.to_dict()
        assert data["paths"] == ["src/"]
        assert data["output_format"] == "json"
        assert data["score_threshold"] == 7.0

    def test_merge_with(self):
        """Test merging two configurations."""
        config1 = Configuration(
            paths=["src/"],
            output_format="console",
            score_threshold=7.0,
        )
        config2 = Configuration(
            paths=["tests/"],
            output_format="json",
            fail_on_error=True,
        )
        merged = config1.merge_with(config2)
        assert "tests/" in merged.paths
        assert merged.output_format == "json"
        assert merged.score_threshold == 7.0
        assert merged.fail_on_error is True

    def test_validate_with_errors(self):
        """Test validation returns errors for invalid config."""
        config = Configuration(paths=["nonexistent/"])
        errors = config.validate()
        assert len(errors) > 0
        assert "does not exist" in errors[0]

    def test_validate_success(self):
        """Test validation succeeds for valid config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Configuration(paths=[tmpdir])
            errors = config.validate()
            assert len(errors) == 0

    def test_get_pylint_args(self):
        """Test generating pylint command-line arguments."""
        config = Configuration(
            paths=["src/", "tests/"],
            pylintrc=".pylintrc",
            ignore_patterns=["*.pyc", "__pycache__"],
            output_format="json",
        )
        args = config.get_pylint_args()
        assert "--output-format=json" in args
        assert "--rcfile" in args
        assert ".pylintrc" in args
        assert "--ignore" in args
        assert "src/" in args
        assert "tests/" in args
