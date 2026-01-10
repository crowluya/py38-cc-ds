"""
LLM Factory tests - Client creation and fallback

TDD: 测试先行
"""

from typing import Any, Dict, List

import pytest

from deep_code.config.settings import LLMSettings, Settings
from deep_code.llm.client import LLMClient, LLMConfigError
from deep_code.llm.factory import (
    LLMClientFactory,
    create_llm_client,
)


class MockLLMClient(LLMClient):
    """Mock LLM client for testing."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._valid = True

    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        model: str = None,
        temperature: float = None,
        max_tokens: int = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        return {"content": "Mock response"}

    def chat_completion_stream(
        self,
        messages: List[Dict[str, Any]],
        model: str = None,
        temperature: float = None,
        max_tokens: int = None,
        **kwargs: Any,
    ):
        yield {"delta": "Mock"}

    def get_model(self) -> str:
        return self._settings.llm.model

    def validate_config(self) -> bool:
        return self._valid


class InvalidMockLLMClient(LLMClient):
    """Mock LLM client that always fails validation."""

    def __init__(self, settings: Settings):
        self._settings = settings

    def chat_completion(self, messages, model=None, temperature=None, max_tokens=None, **kwargs):
        return {"content": "Invalid"}

    def chat_completion_stream(self, messages, model=None, temperature=None, max_tokens=None, **kwargs):
        yield {"delta": "Invalid"}

    def get_model(self) -> str:
        return "invalid"

    def validate_config(self) -> bool:
        return False  # Always invalid


def test_register_client() -> None:
    """验证注册客户端类型"""
    LLMClientFactory.register_client("mock", MockLLMClient)

    assert "mock" in LLMClientFactory.get_available_providers()

    # Cleanup
    LLMClientFactory.unregister_client("mock")


def test_unregister_client() -> None:
    """验证注销客户端类型"""
    LLMClientFactory.register_client("mock", MockLLMClient)
    LLMClientFactory.unregister_client("mock")

    assert "mock" not in LLMClientFactory.get_available_providers()


def test_create_client() -> None:
    """验证创建客户端"""
    LLMClientFactory.register_client("mock", MockLLMClient)

    settings = Settings(llm=LLMSettings(provider="mock"))
    client = LLMClientFactory.create(settings)

    assert client is not None
    assert isinstance(client, MockLLMClient)

    # Cleanup
    LLMClientFactory.unregister_client("mock")


def test_create_client_with_fallback() -> None:
    """验证创建客户端（带回退）"""
    # Register openai (invalid) and requests (mock) as fallback
    LLMClientFactory.register_client("openai", InvalidMockLLMClient)
    LLMClientFactory.register_client("requests", MockLLMClient)

    settings = Settings(llm=LLMSettings(provider="openai"))
    client = LLMClientFactory.create(settings, fallback=True)

    # Should fall back to requests (mock)
    assert isinstance(client, MockLLMClient)

    # Cleanup
    LLMClientFactory.unregister_client("openai")
    LLMClientFactory.unregister_client("requests")


def test_create_client_no_fallback() -> None:
    """验证创建客户端（无回退）"""
    LLMClientFactory.register_client("invalid", InvalidMockLLMClient)

    settings = Settings(llm=LLMSettings(provider="invalid"))

    with pytest.raises(LLMConfigError):
        LLMClientFactory.create(settings, fallback=False)

    # Cleanup
    LLMClientFactory.unregister_client("invalid")


def test_create_client_unknown_provider() -> None:
    """验证创建未知提供商会报错"""
    settings = Settings(llm=LLMSettings(provider="unknown"))

    with pytest.raises(LLMConfigError):
        LLMClientFactory.create(settings)


def test_get_available_providers() -> None:
    """验证获取可用提供者列表"""
    # Clear any existing registrations
    for provider in list(LLMClientFactory.get_available_providers()):
        LLMClientFactory.unregister_client(provider)

    LLMClientFactory.register_client("mock1", MockLLMClient)
    LLMClientFactory.register_client("mock2", MockLLMClient)

    providers = LLMClientFactory.get_available_providers()

    assert "mock1" in providers
    assert "mock2" in providers

    # Cleanup
    LLMClientFactory.unregister_client("mock1")
    LLMClientFactory.unregister_client("mock2")


def test_create_llm_client_convenience() -> None:
    """验证便捷函数 create_llm_client"""
    LLMClientFactory.register_client("mock", MockLLMClient)

    settings = Settings(llm=LLMSettings(provider="mock"))
    client = create_llm_client(settings)

    assert isinstance(client, MockLLMClient)

    # Cleanup
    LLMClientFactory.unregister_client("mock")


def test_fallback_order() -> None:
    """验证回退顺序"""
    # Test openai -> requests fallback
    fallback = LLMClientFactory._get_fallback_providers("openai")
    assert fallback == ["requests"]

    # Test requests -> openai fallback
    fallback = LLMClientFactory._get_fallback_providers("requests")
    assert fallback == ["openai"]

    # Test unknown provider
    fallback = LLMClientFactory._get_fallback_providers("unknown")
    assert fallback == []
