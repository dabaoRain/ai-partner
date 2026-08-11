# DeepSeek 大模型客户端与提示词
from __future__ import annotations

import time

from openai import APIConnectionError, APIError, APITimeoutError, OpenAI

from config import (
    API_KEY,
    CHAT_UPSTREAM_MAX_RETRIES,
    CHAT_UPSTREAM_TIMEOUT_SEC,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
)

client = OpenAI(
    api_key=API_KEY,
    base_url=DEEPSEEK_BASE_URL,
    timeout=CHAT_UPSTREAM_TIMEOUT_SEC,
    max_retries=0,  # 连接失败由下方业务重试控制
)


def build_system_prompt(name: str, personality: str) -> str:
    # 用人设动态生成 system，随前端每次请求变化
    return (
        f"你的名字是{name}。你的性格设定是：{personality}。"
        f"请始终以该身份与口吻回复用户，不要跳出人设。"
    )


def _is_retryable_upstream(exc: Exception) -> bool:
    if isinstance(exc, (APIConnectionError, APITimeoutError)):
        return True
    text = str(exc).lower()
    return "connection error" in text or "timeout" in text or "temporarily" in text


def create_chat_stream(messages: list[dict]):
    """创建流式聊天补全；连接类错误自动有限次重试。"""
    last_exc: Exception | None = None
    attempts = max(1, CHAT_UPSTREAM_MAX_RETRIES)
    for i in range(attempts):
        try:
            return client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=messages,
                stream=True,
                reasoning_effort="high",
                extra_body={"thinking": {"type": "enabled"}},
            )
        except Exception as exc:
            last_exc = exc
            if i + 1 >= attempts or not _is_retryable_upstream(exc):
                raise
            # 短暂退避后重试
            time.sleep(0.6 * (i + 1))
    assert last_exc is not None
    raise last_exc


__all__ = [
    "APIError",
    "APIConnectionError",
    "APITimeoutError",
    "build_system_prompt",
    "create_chat_stream",
    "client",
]
