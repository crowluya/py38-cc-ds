"""
OpenAI Client tests - OpenAI-compatible implementation

TDD: 测试先行
"""

from typing import Any, Dict, List
from unittest.mock import Mock, patch

import pytest

from claude_code.config.settings import LLMSettings, Settings
from claude_code.llm.openai_client import OpenAIClient


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    return Settings(
        llm=LLMSettings(
            api_key="test-key",
            api_base="http://localhost:8000",
            model="deepseek-chat",
        )
    )


def test_client_create(mock_settings: Settings) -> None:
    """验证创建 OpenAI 客户端"""
    with patch("claude_code.llm.openai_client.openai"):
        client = OpenAIClient(mock_settings)
        assert client is not None


def test_get_model(mock_settings: Settings) -> None:
    """验证获取模型名称"""
    with patch("claude_code.llm.openai_client.openai"):
        client = OpenAIClient(mock_settings)
        assert client.get_model() == "deepseek-chat"


def test_validate_config_valid(mock_settings: Settings) -> None:
    """验证有效配置"""
    with patch("claude_code.llm.openai_client.openai"):
        client = OpenAIClient(mock_settings)
        assert client.validate_config() is True


def test_validate_config_invalid() -> None:
    """验证无效配置（缺少 API key）"""
    settings = Settings(llm=LLMSettings(api_key=None))

    with patch("claude_code.llm.openai_client.openai"):
        client = OpenAIClient(settings)
        assert client.validate_config() is False


def test_supports_streaming(mock_settings: Settings) -> None:
    """验证支持流式响应"""
    with patch("claude_code.llm.openai_client.openai"):
        client = OpenAIClient(mock_settings)
        assert client.supports_streaming() is True


def test_supports_tools(mock_settings: Settings) -> None:
    """验证支持工具调用"""
    with patch("claude_code.llm.openai_client.openai"):
        client = OpenAIClient(mock_settings)
        assert client.supports_tools() is True


@patch("claude_code.llm.openai_client.openai")
def test_chat_completion(mock_openai: Mock, mock_settings: Settings) -> None:
    """验证 chat_completion 方法"""
    # Mock the response
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message = {"content": "Test response"}
    mock_response.model = "deepseek-chat"
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 20
    mock_response.usage.total_tokens = 30

    mock_openai.ChatCompletion.create.return_value = mock_response

    client = OpenAIClient(mock_settings)
    messages = [{"role": "user", "content": "Hello"}]

    response = client.chat_completion(messages)

    assert response["content"] == "Test response"
    assert response["model"] == "deepseek-chat"
    assert response["usage"]["total_tokens"] == 30


@patch("claude_code.llm.openai_client.openai")
def test_chat_completion_stream(mock_openai: Mock, mock_settings: Settings) -> None:
    """验证 chat_completion_stream 方法"""
    # Mock streaming response
    mock_chunk1 = Mock()
    mock_chunk1.choices = [Mock()]
    mock_chunk1.choices[0].delta = {"content": "Hello "}

    mock_chunk2 = Mock()
    mock_chunk2.choices = [Mock()]
    mock_chunk2.choices[0].delta = {"content": "world"}

    mock_openai.ChatCompletion.create.return_value = [mock_chunk1, mock_chunk2]

    client = OpenAIClient(mock_settings)
    messages = [{"role": "user", "content": "Say hello"}]

    chunks = list(client.chat_completion_stream(messages))

    assert len(chunks) == 2
    assert chunks[0]["delta"] == "Hello "
    assert chunks[1]["delta"] == "world"


def test_format_messages(mock_settings: Settings) -> None:
    """验证格式化消息"""
    with patch("claude_code.llm.openai_client.openai"):
        client = OpenAIClient(mock_settings)
        messages = [{"role": "user", "content": "Hello"}]

        formatted = client.format_messages(messages)
        assert formatted == messages
