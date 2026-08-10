# DeepSeek 大模型客户端与提示词
from openai import APIError, OpenAI

from config import API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

client = OpenAI(
    api_key=API_KEY,
    base_url=DEEPSEEK_BASE_URL,
)


def build_system_prompt(name: str, personality: str) -> str:
    # 用人设动态生成 system，随前端每次请求变化
    return (
        f"你的名字是{name}。你的性格设定是：{personality}。"
        f"请始终以该身份与口吻回复用户，不要跳出人设。"
    )


def create_chat_stream(messages: list[dict]):
    """创建流式聊天补全；调用失败时抛出 APIError / Exception。"""
    return client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=messages,
        stream=True,
        reasoning_effort="high",
        extra_body={"thinking": {"type": "enabled"}},
    )


__all__ = ["APIError", "build_system_prompt", "create_chat_stream", "client"]
