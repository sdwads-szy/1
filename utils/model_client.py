# utils/model_client.py
"""
共享 model_client 单例 — 避免多处重复创建 OpenAIChatCompletionClient。

用法:
    from utils.model_client import get_model_client
    client = get_model_client()
"""

import os
import httpx
from dotenv import load_dotenv
from picoagents import OpenAIChatCompletionClient

load_dotenv("./.env.example")

_client = None

# HTTP 层超时（不依赖 asyncio cancellation，直接切断 socket）
_HTTP_TIMEOUT = httpx.Timeout(
    connect=float(os.getenv("HTTP_CONNECT_TIMEOUT", "10")),
    read=float(os.getenv("HTTP_READ_TIMEOUT", "120")),    # 流式关键：120s 无 chunk → 断连
    write=float(os.getenv("HTTP_WRITE_TIMEOUT", "30")),
    pool=float(os.getenv("HTTP_POOL_TIMEOUT", "10")),
)
_MAX_RETRIES = int(os.getenv("HTTP_MAX_RETRIES", "1"))


def get_model_client():
    """返回共享的 model_client 单例，延迟初始化。"""
    global _client
    if _client is None:
        _client = OpenAIChatCompletionClient(
            model=os.getenv("OPENAI_MODEL", "deepseek-v4-pro"),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com"),
            api_key=os.getenv("OPENAI_API_KEY", ""),
            timeout=_HTTP_TIMEOUT,
            max_retries=_MAX_RETRIES,
        )
    return _client


def reset_model_client():
    """重置单例（测试用）。"""
    global _client
    _client = None


def create_model_client():
    """创建新的 model_client 实例（非单例）。
    用于并发场景，每个 task 持有独立 client，避免共享 AsyncOpenAI 导致
    httpx 连接池竞争引发的请求永久阻塞。
    """
    return OpenAIChatCompletionClient(
        model=os.getenv("OPENAI_MODEL", "deepseek-v4-pro"),
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com"),
        api_key=os.getenv("OPENAI_API_KEY", ""),
        timeout=_HTTP_TIMEOUT,
        max_retries=_MAX_RETRIES,
    )
