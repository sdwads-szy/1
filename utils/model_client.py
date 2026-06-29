# utils/model_client.py
"""
共享 model_client 单例 — 避免多处重复创建 OpenAIChatCompletionClient。

用法:
    from utils.model_client import get_model_client
    client = get_model_client()
"""

import os
from dotenv import load_dotenv
from picoagents import OpenAIChatCompletionClient

load_dotenv("./.env.example")

_client = None


def get_model_client():
    """返回共享的 model_client 单例，延迟初始化。"""
    global _client
    if _client is None:
        _client = OpenAIChatCompletionClient(
            model=os.getenv("OPENAI_MODEL", "deepseek-v4-pro"),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com"),
            api_key=os.getenv("OPENAI_API_KEY", ""),
        )
    return _client


def reset_model_client():
    """重置单例（测试用）。"""
    global _client
    _client = None
