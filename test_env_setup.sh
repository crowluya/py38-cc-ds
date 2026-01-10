#!/bin/bash
# 测试环境变量配置的脚本

echo "=== 测试环境变量配置 ==="
echo ""

# 设置测试环境变量
export DEEPSEEK_API_KEY="sk-test-key-123456"
export DEEPSEEK_BASE_URL="https://api.deepseek.com/v1"
export DEEPSEEK_MODEL="deepseek-chat"

echo "环境变量已设置:"
echo "  DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY:0:10}..."
echo "  DEEPSEEK_BASE_URL=$DEEPSEEK_BASE_URL"
echo "  DEEPSEEK_MODEL=$DEEPSEEK_MODEL"
echo ""

# 测试 Python 加载
python3 << 'PYTHON_SCRIPT'
import os
print("Python 环境变量:")
print(f"  DEEPSEEK_API_KEY: {os.environ.get('DEEPSEEK_API_KEY', '(not set)')}")
print(f"  DEEPSEEK_BASE_URL: {os.environ.get('DEEPSEEK_BASE_URL', '(not set)')}")
print(f"  DEEPSEEK_MODEL: {os.environ.get('DEEPSEEK_MODEL', '(not set)')}")
print()

from deep_code.config.loader import load_settings

settings = load_settings()
print("加载的配置:")
print(f"  API Key: {'*' * 10 if settings.llm.api_key else '(not set)'}")
print(f"  API Base: {settings.llm.api_base or '(not set)'}")
print(f"  Model: {settings.llm.model}")
PYTHON_SCRIPT

echo ""
echo "=== 测试完成 ==="
echo ""
echo "要实际测试模型连接，请设置真实的 API_KEY 后运行此脚本。"
