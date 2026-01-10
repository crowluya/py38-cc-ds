"""
Requests Client tests - OpenAI-compatible HTTP client

TDD: 测试先行
"""

from typing import Any, Dict, List
from unittest.mock import Mock, patch

import pytest
import requests

from deep_code.config.settings import LLMSettings, Settings
from deep_code.llm.requests_client import RequestsClient


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    return Settings(
        llm=LLMSettings(
            api_key="test-key",
            api_base="http://localhost:8000/v1",
            model="deepseek-chat",
        )
    )


def test_client_create(mock_settings: Settings) -> None:
    """验证创建 Requests 客户端"""
    client = RequestsClient(mock_settings)
    assert client is not None
    assert client.get_model() == "deepseek-chat"


def test_get_model(mock_settings: Settings) -> None:
    """验证获取模型名称"""
    client = RequestsClient(mock_settings)
    assert client.get_model() == "deepseek-chat"


def test_validate_config_valid(mock_settings: Settings) -> None:
    """验证有效配置"""
    client = RequestsClient(mock_settings)
    assert client.validate_config() is True


def test_validate_config_invalid_no_key() -> None:
    """验证无效配置（缺少 API key）"""
    settings = Settings(
        llm=LLMSettings(
            api_key=None,
            api_base="http://localhost:8000/v1",
        )
    )
    client = RequestsClient(settings)
    assert client.validate_config() is False


def test_validate_config_invalid_no_base() -> None:
    """验证无效配置（缺少 base URL）"""
    settings = Settings(
        llm=LLMSettings(
            api_key="test-key",
            api_base=None,
        )
    )
    client = RequestsClient(settings)
    assert client.validate_config() is False


def test_supports_streaming(mock_settings: Settings) -> None:
    """验证支持流式响应"""
    client = RequestsClient(mock_settings)
    assert client.supports_streaming() is True


def test_supports_tools(mock_settings: Settings) -> None:
    """验证支持工具调用"""
    client = RequestsClient(mock_settings)
    assert client.supports_tools() is True


def test_get_api_url(mock_settings: Settings) -> None:
    """验证获取 API URL"""
    client = RequestsClient(mock_settings)
    assert client._get_api_url() == "http://localhost:8000/v1/chat/completions"


def test_get_api_url_default() -> None:
    """验证默认 API URL"""
    settings = Settings(
        llm=LLMSettings(
            api_key="test-key",
            api_base=None,
        )
    )
    client = RequestsClient(settings)
    assert "api.openai.com" in client._get_api_url()


@patch("deep_code.llm.requests_client.requests.Session")
def test_chat_completion(mock_session_class: Mock, mock_settings: Settings) -> None:
    """验证 chat_completion 方法"""
    # Mock response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Test response"}}],
        "model": "deepseek-chat",
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
    }

    mock_session = Mock()
    mock_session.post.return_value = mock_response
    mock_session_class.return_value = mock_session

    client = RequestsClient(mock_settings)
    messages = [{"role": "user", "content": "Hello"}]

    response = client.chat_completion(messages)

    assert response["content"] == "Test response"
    assert response["usage"]["total_tokens"] == 30


@patch("deep_code.llm.requests_client.requests.Session")
def test_chat_completion_stream(mock_session_class: Mock, mock_settings: Settings) -> None:
    """验证 chat_completion_stream 方法"""
    # Mock streaming response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.iter_lines.return_value = [
        b"data: {\"choices\": [{\"delta\": {\"content\": \"Hello \"}}]}\n",
        b"data: {\"choices\": [{\"delta\": {\"content\": \"world\"}}]}\n",
        b"data: [DONE]\n",
    ]

    mock_session = Mock()
    mock_session.post.return_value = mock_response
    mock_session_class.return_value = mock_session

    client = RequestsClient(mock_settings)
    messages = [{"role": "user", "content": "Say hello"}]

    chunks = list(client.chat_completion_stream(messages))

    assert len(chunks) == 2
    assert chunks[0]["delta"] == "Hello "
    assert chunks[1]["delta"] == "world"


def test_close(mock_settings: Settings) -> None:
    """验证关闭 session"""
    client = RequestsClient(mock_settings)
    client.close()
    # Should not raise any exception
