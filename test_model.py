#!/usr/bin/env python3
"""
测试 DeepSeek 模型连接

使用方法:
1. 设置环境变量:
   export DEEPSEEK_API_KEY="your_api_key"
   export DEEPSEEK_BASE_URL="https://api.deepseek.com/v1"
   export DEEPSEEK_MODEL="deepseek-chat"

2. 运行此脚本:
   python test_model.py
"""

import os
import sys

def main():
    # 检查环境变量
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    api_base = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

    print("=== DeepSeek 模型连接测试 ===")
    print()
    print("环境变量:")
    print(f"  DEEPSEEK_API_KEY: {'*' * 10 if api_key else '(未设置)'}")
    print(f"  DEEPSEEK_BASE_URL: {api_base}")
    print(f"  DEEPSEEK_MODEL: {model}")
    print()

    if not api_key:
        print("❌ 错误: DEEPSEEK_API_KEY 环境变量未设置")
        print()
        print("请设置环境变量:")
        print("  export DEEPSEEK_API_KEY='your_api_key'")
        print("  export DEEPSEEK_BASE_URL='https://api.deepseek.com/v1'")
        print("  export DEEPSEEK_MODEL='deepseek-chat'")
        print()
        return 1

    try:
        from deep_code.config.loader import load_settings
        from deep_code.llm.factory import create_llm_client
        from deep_code.config.settings import Settings, LLMSettings

        # 加载配置
        settings = load_settings()
        llm = settings.llm

        print("加载的配置:")
        print(f"  Provider: {llm.provider}")
        print(f"  API Key: {'*' * 10 if llm.api_key else '(未设置)'}")
        print(f"  API Base: {llm.api_base or '(默认)'}")
        print(f"  Model: {llm.model}")
        print()

        # 如果环境变量覆盖了，用 requests 客户端
        if llm.api_key and llm.api_base:
            # 使用 requests 客户端
            print("使用 Requests 客户端...")
            client = create_llm_client(settings)
        else:
            print("❌ 配置不完整，请检查环境变量")
            return 1

        print(f"  客户端类型: {type(client).__name__}")
        print()

        # 测试聊天
        print("发送测试请求...")
        response = client.chat_completion(
            messages=[{'role': 'user', 'content': '用5个字说你好'}],
            max_tokens=20,
            temperature=0.7,
        )

        print()
        print(f"✅ 连接成功!")
        print(f"   回复: {response.content}")
        print(f"   完成原因: {response.finish_reason}")
        print()
        return 0

    except Exception as e:
        import traceback
        print()
        print(f"❌ 连接失败: {type(e).__name__}")
        print(f"   错误信息: {e}")
        print()
        print("详细错误:")
        traceback.print_exc()
        print()
        
        # 给出常见错误的提示
        error_str = str(e).lower()
        if "timeout" in error_str or "timed out" in error_str:
            print("提示: 连接超时，请检查网络或 API 地址")
        elif "401" in error_str or "unauthorized" in error_str or "api key" in error_str or "auth" in error_str:
            print("提示: API 密钥无效，请检查 DEEPSEEK_API_KEY")
        elif "connection" in error_str or "network" in error_str:
            print("提示: 网络连接失败，请检查 DEEPSEEK_BASE_URL")
        elif "ssl" in error_str or "certificate" in error_str:
            print("提示: SSL 证书错误，内网环境可设置 VERIFY_SSL=false")
        print()
        return 1

if __name__ == "__main__":
    sys.exit(main())
