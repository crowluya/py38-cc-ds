"""
LLM Client Factory

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)

Creates appropriate LLM client implementation based on configuration.
Supports fallback strategy.
"""

from typing import Any, Dict, Optional

from claude_code.config.settings import Settings
from claude_code.llm.client import LLMClient, LLMConfigError


class LLMClientFactory:
    """
    Factory for creating LLM client instances.

    Supports:
    - Multiple provider types (openai, requests)
    - Fallback strategy
    - Configuration-driven selection
    """

    # Registry of available client types
    _client_types: Dict[str, Any] = {}

    @classmethod
    def register_client(
        cls,
        client_type: str,
        client_class: Any,
    ) -> None:
        """
        Register a client implementation.

        Args:
            client_type: Provider identifier (e.g., "openai", "requests")
            client_class: Client class (must implement LLMClient)
        """
        cls._client_types[client_type] = client_class

    @classmethod
    def unregister_client(cls, client_type: str) -> None:
        """
        Unregister a client implementation.

        Args:
            client_type: Provider identifier to remove
        """
        if client_type in cls._client_types:
            del cls._client_types[client_type]

    @classmethod
    def create(
        cls,
        settings: Settings,
        fallback: bool = True,
    ) -> LLMClient:
        """
        Create LLM client from settings.

        Args:
            settings: Settings instance with LLM configuration
            fallback: Whether to try fallback providers on failure

        Returns:
            LLMClient instance

        Raises:
            LLMConfigError: If no valid client can be created
        """
        provider = settings.llm.provider

        # Try primary provider
        client = cls._try_create(provider, settings)

        if client is not None:
            return client

        # Try fallback providers
        if fallback:
            fallback_providers = cls._get_fallback_providers(provider)

            for fallback_provider in fallback_providers:
                client = cls._try_create(fallback_provider, settings)
                if client is not None:
                    return client

        # No client could be created
        raise LLMConfigError(
            f"Cannot create LLM client for provider '{provider}'. "
            f"Check configuration and dependencies."
        )

    @classmethod
    def _try_create(
        cls,
        provider: str,
        settings: Settings,
    ) -> Optional[LLMClient]:
        """
        Try to create a client for the given provider.

        Args:
            provider: Provider identifier
            settings: Settings instance

        Returns:
            LLMClient instance or None if creation failed
        """
        if provider not in cls._client_types:
            return None

        client_class = cls._client_types[provider]

        try:
            client = client_class(settings)
            if client.validate_config():
                return client
        except Exception:
            # Creation or validation failed
            return None

        return None

    @classmethod
    def _get_fallback_providers(cls, primary: str) -> list:
        """
        Get fallback providers in priority order.

        Args:
            primary: Primary provider that failed

        Returns:
            List of fallback provider identifiers
        """
        # Define fallback order
        fallback_order: Dict[str, list] = {
            "openai": ["requests"],
            "requests": ["openai"],
        }

        return fallback_order.get(primary, [])

    @classmethod
    def get_available_providers(cls) -> list:
        """
        Get list of registered provider identifiers.

        Returns:
            List of provider names
        """
        return list(cls._client_types.keys())


def create_llm_client(
    settings: Settings,
    fallback: bool = True,
) -> LLMClient:
    """
    Convenience function to create LLM client.

    Args:
        settings: Settings instance with LLM configuration
        fallback: Whether to try fallback providers

    Returns:
        LLMClient instance
    """
    return LLMClientFactory.create(settings, fallback=fallback)
