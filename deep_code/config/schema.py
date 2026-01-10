"""
Config Schema Validation (T024)

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)

Provides:
- JSON Schema for configuration validation
- Validation functions with detailed error messages
- Schema generation from dataclasses
- Config file validation
"""

import json
import os
from dataclasses import dataclass, fields, is_dataclass
from typing import Any, Dict, List, Optional, Type, get_type_hints

# Try to import jsonschema, fall back to basic validation
try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


@dataclass
class ValidationResult:
    """Result of configuration validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []

    def format_errors(self) -> str:
        """
        Format errors as a string.

        Returns:
            Formatted error string
        """
        if not self.errors:
            return "No errors"

        lines = ["Configuration errors:"]
        for i, error in enumerate(self.errors, 1):
            lines.append(f"  {i}. {error}")

        return "\n".join(lines)


# ===== JSON Schema Definition =====

CONFIG_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "llm": {
            "type": "object",
            "properties": {
                "provider": {
                    "type": "string",
                    "enum": ["openai", "requests"],
                    "description": "LLM provider type",
                },
                "api_key": {
                    "type": ["string", "null"],
                    "description": "API key for LLM service",
                },
                "api_base": {
                    "type": ["string", "null"],
                    "description": "Base URL for API",
                },
                "model": {
                    "type": "string",
                    "description": "Model name",
                },
                "temperature": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 2.0,
                    "description": "Sampling temperature",
                },
                "max_tokens": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100000,
                    "description": "Maximum tokens to generate",
                },
                "timeout": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Request timeout in seconds",
                },
                "verify_ssl": {
                    "type": "boolean",
                    "description": "Whether to verify SSL certificates",
                },
                "ca_cert": {
                    "type": ["string", "null"],
                    "description": "Path to CA certificate",
                },
            },
            "additionalProperties": True,
        },
        "permissions": {
            "type": "object",
            "properties": {
                "default_mode": {
                    "type": "string",
                    "enum": ["allow", "deny", "ask"],
                    "description": "Default permission mode",
                },
                "file_read": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Allowed file read patterns",
                },
                "file_write": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Allowed file write patterns",
                },
                "command_execute": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Allowed command patterns",
                },
                "network_access": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Allowed network patterns",
                },
                "allow": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Allow rules in format: verb(pattern)",
                },
            },
            "additionalProperties": True,
        },
        "hooks": {
            "type": "object",
            "properties": {
                "session_start": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Commands to run on session start",
                },
                "pre_tool_use": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Commands to run before tool use",
                },
                "post_tool_use": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Commands to run after tool use",
                },
            },
            "additionalProperties": True,
        },
        "mcp_servers": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Command to start the MCP server",
                    },
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Arguments for the command",
                    },
                    "env": {
                        "type": "object",
                        "additionalProperties": {"type": "string"},
                        "description": "Environment variables",
                    },
                },
                "required": ["command"],
            },
            "description": "MCP server configurations",
        },
        "use_color": {
            "type": "boolean",
            "description": "Whether to use colored output",
        },
        "show_thinking": {
            "type": "boolean",
            "description": "Whether to show thinking process",
        },
        "debug": {
            "type": "boolean",
            "description": "Enable debug mode",
        },
        "log_level": {
            "type": "string",
            "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            "description": "Logging level",
        },
        "project_root": {
            "type": ["string", "null"],
            "description": "Project root directory",
        },
        "checkpoint_dir": {
            "type": ["string", "null"],
            "description": "Checkpoint directory",
        },
    },
    "additionalProperties": True,
}


def get_config_schema() -> Dict[str, Any]:
    """
    Get the configuration schema.

    Returns:
        JSON Schema dictionary
    """
    return CONFIG_SCHEMA.copy()


def validate_config(config: Dict[str, Any]) -> ValidationResult:
    """
    Validate a configuration dictionary.

    Args:
        config: Configuration dictionary to validate

    Returns:
        ValidationResult with validation status and errors
    """
    errors = []

    if HAS_JSONSCHEMA:
        # Use jsonschema for validation
        try:
            jsonschema.validate(config, CONFIG_SCHEMA)
        except jsonschema.ValidationError as e:
            errors.append(f"{e.json_path}: {e.message}")
        except jsonschema.SchemaError as e:
            errors.append(f"Schema error: {e.message}")
    else:
        # Basic validation without jsonschema
        errors = _basic_validate(config)

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
    )


def _basic_validate(config: Dict[str, Any]) -> List[str]:
    """
    Basic validation without jsonschema.

    Args:
        config: Configuration to validate

    Returns:
        List of error messages
    """
    errors = []

    # Validate LLM settings
    if "llm" in config:
        llm = config["llm"]
        if not isinstance(llm, dict):
            errors.append("llm: must be an object")
        else:
            # Validate provider
            if "provider" in llm:
                if llm["provider"] not in ["openai", "requests"]:
                    errors.append(f"llm.provider: must be 'openai' or 'requests', got '{llm['provider']}'")

            # Validate temperature
            if "temperature" in llm:
                temp = llm["temperature"]
                if not isinstance(temp, (int, float)):
                    errors.append("llm.temperature: must be a number")
                elif temp < 0 or temp > 2:
                    errors.append(f"llm.temperature: must be between 0 and 2, got {temp}")

            # Validate max_tokens
            if "max_tokens" in llm:
                if not isinstance(llm["max_tokens"], int):
                    errors.append("llm.max_tokens: must be an integer")

    # Validate log_level
    if "log_level" in config:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if config["log_level"] not in valid_levels:
            errors.append(f"log_level: must be one of {valid_levels}")

    # Validate MCP servers
    if "mcp_servers" in config:
        servers = config["mcp_servers"]
        if not isinstance(servers, dict):
            errors.append("mcp_servers: must be an object")
        else:
            for name, server in servers.items():
                if not isinstance(server, dict):
                    errors.append(f"mcp_servers.{name}: must be an object")
                elif "command" not in server:
                    errors.append(f"mcp_servers.{name}: missing required field 'command'")

    return errors


def validate_config_file(file_path: str) -> ValidationResult:
    """
    Validate a configuration file.

    Args:
        file_path: Path to the configuration file

    Returns:
        ValidationResult with validation status and errors
    """
    # Check file exists
    if not os.path.exists(file_path):
        return ValidationResult(
            is_valid=False,
            errors=[f"File not found: {file_path}"],
        )

    # Read and parse JSON
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        return ValidationResult(
            is_valid=False,
            errors=[f"Invalid JSON: {e}"],
        )
    except Exception as e:
        return ValidationResult(
            is_valid=False,
            errors=[f"Error reading file: {e}"],
        )

    # Validate config
    return validate_config(config)


class ConfigValidator:
    """
    Configuration validator with custom schema support.
    """

    def __init__(self, schema: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize validator.

        Args:
            schema: Custom schema (uses default if None)
        """
        self._schema = schema or CONFIG_SCHEMA

    def validate(self, config: Dict[str, Any]) -> ValidationResult:
        """
        Validate a configuration.

        Args:
            config: Configuration to validate

        Returns:
            ValidationResult
        """
        errors = []

        if HAS_JSONSCHEMA:
            try:
                jsonschema.validate(config, self._schema)
            except jsonschema.ValidationError as e:
                errors.append(f"{e.json_path}: {e.message}")
        else:
            # For custom schemas without jsonschema, do basic type checking
            errors = self._basic_schema_validate(config, self._schema)

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
        )

    def _basic_schema_validate(
        self,
        config: Dict[str, Any],
        schema: Dict[str, Any],
        path: str = "",
    ) -> List[str]:
        """Basic schema validation."""
        errors = []

        # Check required fields
        required = schema.get("required", [])
        for field in required:
            if field not in config:
                errors.append(f"{path}.{field}: required field missing" if path else f"{field}: required field missing")

        return errors


def generate_schema_from_dataclass(cls: Type) -> Dict[str, Any]:
    """
    Generate JSON Schema from a dataclass.

    Args:
        cls: Dataclass type

    Returns:
        JSON Schema dictionary
    """
    if not is_dataclass(cls):
        raise ValueError(f"{cls} is not a dataclass")

    schema: Dict[str, Any] = {
        "type": "object",
        "properties": {},
    }

    # Get type hints
    try:
        hints = get_type_hints(cls)
    except Exception:
        hints = {}

    # Process fields
    for field in fields(cls):
        field_schema = _type_to_schema(hints.get(field.name, type(None)))
        schema["properties"][field.name] = field_schema

    return schema


def _type_to_schema(python_type: Type) -> Dict[str, Any]:
    """
    Convert Python type to JSON Schema type.

    Args:
        python_type: Python type

    Returns:
        JSON Schema type definition
    """
    # Handle basic types
    type_map = {
        str: {"type": "string"},
        int: {"type": "integer"},
        float: {"type": "number"},
        bool: {"type": "boolean"},
        list: {"type": "array"},
        dict: {"type": "object"},
        type(None): {"type": "null"},
    }

    if python_type in type_map:
        return type_map[python_type]

    # Handle Optional types
    origin = getattr(python_type, "__origin__", None)
    if origin is not None:
        args = getattr(python_type, "__args__", ())

        # Optional[X] is Union[X, None]
        if str(origin) == "typing.Union" and type(None) in args:
            non_none_types = [a for a in args if a is not type(None)]
            if len(non_none_types) == 1:
                inner_schema = _type_to_schema(non_none_types[0])
                return {"type": [inner_schema.get("type", "string"), "null"]}

        # List[X]
        if origin is list:
            if args:
                item_schema = _type_to_schema(args[0])
                return {"type": "array", "items": item_schema}
            return {"type": "array"}

        # Dict[K, V]
        if origin is dict:
            return {"type": "object"}

    # Default to string
    return {"type": "string"}
