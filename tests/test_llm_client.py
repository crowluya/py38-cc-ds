"""
LLM Client ABC tests - Abstract interface definition

TDD: 测试先行
"""

from typing import Any, Dict, List

import pytest

from deep_code.llm.client import (
    LLMClient,
    LLMClientError,
    LLMConfigError,
    LLMAPIError,
    LLMTimeoutError,
)


class MockLLMClient(LLMClient):
    """Mock implementation for testing ABC."""

    def __init__(self, model: str = "test-model"):
        self._model = model
        self._config_valid = True

    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        model: str = None,
        temperature: float = None,
        max_tokens: int = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        return {"content": "Test response", "model": model or self._model}

    def chat_completion_stream(
        self,
        messages: List[Dict[str, Any]],
        model: str = None,
        temperature: float = None,
        max_tokens: int = None,
        **kwargs: Any,
    ):
        yield {"delta": "Test "}
        yield {"delta": "response"}

    def get_model(self) -> str:
        return self._model

    def validate_config(self) -> bool:
        return self._config_valid


def test_mock_client_instantiable() -> None:
    """验证 Mock 实现可实例化"""
    client = MockLLMClient()
    assert client is not None


def test_chat_completion() -> None:
    """验证 chat_completion 方法"""
    client = MockLLMClient()
    messages = [{"role": "user", "content": "Hello"}]

    response = client.chat_completion(messages)

    assert "content" in response
    assert response["content"] == "Test response"


def test_chat_completion_with_params() -> None:
    """验证带参数的 chat_completion"""
    client = MockLLMClient()
    messages = [{"role": "user", "content": "Hello"}]

    response = client.chat_completion(
        messages,
        model="gpt-4",
        temperature=0.5,
        max_tokens=1000,
    )

    assert response["model"] == "gpt-4"


def test_chat_completion_stream() -> None:
    """验证 chat_completion_stream 方法"""
    client = MockLLMClient()
    messages = [{"role": "user", "content": "Hello"}]

    chunks = list(client.chat_completion_stream(messages))

    assert len(chunks) == 2
    assert chunks[0]["delta"] == "Test "
    assert chunks[1]["delta"] == "response"


def test_get_model() -> None:
    """验证 get_model 方法"""
    client = MockLLMClient(model="custom-model")
    assert client.get_model() == "custom-model"


def test_supports_streaming() -> None:
    """验证 supports_streaming 默认实现"""
    client = MockLLMClient()
    assert client.supports_streaming() is True


def test_supports_tools() -> None:
    """验证 supports_tools 默认实现"""
    client = MockLLMClient()
    assert client.supports_tools() is True


def test_validate_config() -> None:
    """验证 validate_config 方法"""
    client = MockLLMClient()
    assert client.validate_config() is True


def test_format_messages_default() -> None:
    """验证 format_messages 默认实现"""
    client = MockLLMClient()
    messages = [{"role": "user", "content": "Hello"}]

    formatted = client.format_messages(messages)

    assert formatted == messages


def test_llm_client_error() -> None:
    """验证 LLMClientError 异常"""
    with pytest.raises(LLMClientError):
        raise LLMClientError("Test error")


def test_llm_config_error() -> None:
    """验证 LLMConfigError 异常"""
    with pytest.raises(LLMConfigError):
        raise LLMConfigError("Config error")


def test_llm_api_error() -> None:
    """验证 LLMAPIError 异常"""
    with pytest.raises(LLMAPIError):
        raise LLMAPIError("API error")


def test_llm_timeout_error() -> None:
    """验证 LLMTimeoutError 异常"""
    with pytest.raises(LLMTimeoutError):
        raise LLMTimeoutError("Timeout error")


def test_exception_hierarchy() -> None:
    """验证异常继承层次"""
    assert issubclass(LLMConfigError, LLMClientError)
    assert issubclass(LLMAPIError, LLMClientError)
    assert issubclass(LLMTimeoutError, LLMClientError)


def test_abstract_cannot_instantiate() -> None:
    """验证抽象类不能直接实例化"""
    with pytest.raises(TypeError):
        LLMClient()  # type: ignore
