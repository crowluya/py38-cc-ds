"""
Tests for Config Schema Validation (T024)

Python 3.8.10 compatible
"""

import pytest
from typing import Any, Dict


class TestConfigSchema:
    """Tests for configuration schema."""

    def test_get_schema(self):
        """Test getting the config schema."""
        from deep_code.config.schema import get_config_schema

        schema = get_config_schema()

        assert schema is not None
        assert schema["type"] == "object"
        assert "properties" in schema

    def test_schema_has_llm_section(self):
        """Test schema has LLM section."""
        from deep_code.config.schema import get_config_schema

        schema = get_config_schema()

        assert "llm" in schema["properties"]
        llm_schema = schema["properties"]["llm"]
        assert llm_schema["type"] == "object"

    def test_schema_has_permissions_section(self):
        """Test schema has permissions section."""
        from deep_code.config.schema import get_config_schema

        schema = get_config_schema()

        assert "permissions" in schema["properties"]

    def test_schema_has_hooks_section(self):
        """Test schema has hooks section."""
        from deep_code.config.schema import get_config_schema

        schema = get_config_schema()

        assert "hooks" in schema["properties"]


class TestConfigValidation:
    """Tests for config validation."""

    def test_validate_valid_config(self):
        """Test validating a valid config."""
        from deep_code.config.schema import validate_config

        config = {
            "llm": {
                "provider": "openai",
                "model": "gpt-3.5-turbo",
                "temperature": 0.7,
            },
            "use_color": True,
        }

        result = validate_config(config)

        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_invalid_temperature(self):
        """Test validation catches invalid temperature."""
        from deep_code.config.schema import validate_config

        config = {
            "llm": {
                "temperature": 3.0,  # Invalid: > 2.0
            },
        }

        result = validate_config(config)

        assert not result.is_valid
        assert len(result.errors) > 0

    def test_validate_invalid_provider(self):
        """Test validation catches invalid provider."""
        from deep_code.config.schema import validate_config

        config = {
            "llm": {
                "provider": "invalid_provider",
            },
        }

        result = validate_config(config)

        assert not result.is_valid

    def test_validate_invalid_type(self):
        """Test validation catches type errors."""
        from deep_code.config.schema import validate_config

        config = {
            "llm": {
                "max_tokens": "not_a_number",  # Should be int
            },
        }

        result = validate_config(config)

        assert not result.is_valid

    def test_validate_invalid_log_level(self):
        """Test validation catches invalid log level."""
        from deep_code.config.schema import validate_config

        config = {
            "log_level": "INVALID",
        }

        result = validate_config(config)

        assert not result.is_valid

    def test_validate_empty_config(self):
        """Test validating empty config is valid (uses defaults)."""
        from deep_code.config.schema import validate_config

        config = {}

        result = validate_config(config)

        assert result.is_valid

    def test_validate_extra_fields_allowed(self):
        """Test that extra fields are allowed."""
        from deep_code.config.schema import validate_config

        config = {
            "custom_field": "value",
        }

        result = validate_config(config)

        # Extra fields should be allowed for extensibility
        assert result.is_valid


class TestValidationResult:
    """Tests for ValidationResult."""

    def test_validation_result_valid(self):
        """Test valid result."""
        from deep_code.config.schema import ValidationResult

        result = ValidationResult(is_valid=True, errors=[])

        assert result.is_valid
        assert result.errors == []

    def test_validation_result_invalid(self):
        """Test invalid result."""
        from deep_code.config.schema import ValidationResult

        result = ValidationResult(
            is_valid=False,
            errors=["Error 1", "Error 2"],
        )

        assert not result.is_valid
        assert len(result.errors) == 2

    def test_validation_result_format_errors(self):
        """Test formatting errors."""
        from deep_code.config.schema import ValidationResult

        result = ValidationResult(
            is_valid=False,
            errors=["Error 1", "Error 2"],
        )

        formatted = result.format_errors()

        assert "Error 1" in formatted
        assert "Error 2" in formatted


class TestConfigValidator:
    """Tests for ConfigValidator class."""

    def test_validator_validate(self):
        """Test validator validate method."""
        from deep_code.config.schema import ConfigValidator

        validator = ConfigValidator()

        config = {"llm": {"model": "test"}}
        result = validator.validate(config)

        assert result is not None

    def test_validator_with_custom_schema(self):
        """Test validator with custom schema."""
        from deep_code.config.schema import ConfigValidator

        custom_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
            "required": ["name"],
        }

        validator = ConfigValidator(schema=custom_schema)

        valid_config = {"name": "test"}
        invalid_config = {}

        assert validator.validate(valid_config).is_valid
        assert not validator.validate(invalid_config).is_valid


class TestSchemaGeneration:
    """Tests for schema generation from dataclass."""

    def test_generate_schema_from_settings(self):
        """Test generating schema from Settings dataclass."""
        from deep_code.config.schema import generate_schema_from_dataclass
        from deep_code.config.settings import Settings

        schema = generate_schema_from_dataclass(Settings)

        assert schema["type"] == "object"
        assert "properties" in schema

    def test_generate_schema_from_llm_settings(self):
        """Test generating schema from LLMSettings."""
        from deep_code.config.schema import generate_schema_from_dataclass
        from deep_code.config.settings import LLMSettings

        schema = generate_schema_from_dataclass(LLMSettings)

        assert "provider" in schema["properties"]
        assert "model" in schema["properties"]
        assert "temperature" in schema["properties"]


class TestConfigFileValidation:
    """Tests for config file validation."""

    def test_validate_config_file(self, tmp_path):
        """Test validating a config file."""
        from deep_code.config.schema import validate_config_file
        import json

        config_file = tmp_path / "settings.json"
        config_file.write_text(json.dumps({
            "llm": {"model": "test"},
            "use_color": True,
        }), encoding="utf-8")

        result = validate_config_file(str(config_file))

        assert result.is_valid

    def test_validate_invalid_json_file(self, tmp_path):
        """Test validating invalid JSON file."""
        from deep_code.config.schema import validate_config_file

        config_file = tmp_path / "settings.json"
        config_file.write_text("not valid json", encoding="utf-8")

        result = validate_config_file(str(config_file))

        assert not result.is_valid
        assert "JSON" in result.errors[0] or "json" in result.errors[0].lower()

    def test_validate_nonexistent_file(self):
        """Test validating nonexistent file."""
        from deep_code.config.schema import validate_config_file

        result = validate_config_file("/nonexistent/file.json")

        assert not result.is_valid


class TestMCPServerSchema:
    """Tests for MCP server config schema."""

    def test_mcp_server_schema(self):
        """Test MCP server schema validation."""
        from deep_code.config.schema import validate_config

        config = {
            "mcp_servers": {
                "filesystem": {
                    "command": "npx",
                    "args": ["-y", "@anthropic/mcp-server-filesystem"],
                },
            },
        }

        result = validate_config(config)

        assert result.is_valid

    def test_mcp_server_missing_command(self):
        """Test MCP server without command."""
        from deep_code.config.schema import validate_config

        config = {
            "mcp_servers": {
                "test": {
                    "args": ["arg1"],
                },
            },
        }

        result = validate_config(config)

        # Should fail - command is required
        assert not result.is_valid
