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


def build_system_prompt(
    name: str,
    personality: str = "",
    *,
    identity: str = "",
    tone: str = "",
    interests: str = "",
    relationship_boundary: str = "",
    taboos: str = "",
    region: str = "",
    metaphor: str = "",
    age: int | str = 0,
    catchphrases: str = "",
    intimacy_stages: str = "",
    openings: str = "",
    easter_eggs: str = "",
) -> str:
    """按结构化人设生成 system prompt。

    约束优先级：禁忌/安全 > 关系硬边界 > 亲密阶段 > 身份 > 语气兴趣口头禅 > 补充性格。
    亲密阶段与彩蛋仅为后台行为规则，禁止出现在对用户可见回复中。
    """
    lines = [
        f"你是用户的 AI 智能伴侣，名字是「{name}」。",
        "请始终保持该人设，不要跳出角色，也不要声称自己是真人。",
        "【对用户可见回复·硬约束】只输出角色会说的话；禁止输出任何幕后说明、规则分析、阶段标注、彩蛋判定、括号旁白或系统提示痕迹。"
        "禁止出现例如：「关系阶段」「初识期」「朋友期」「密友期」「伴侣期」「彩蛋触发」「未激活」「埋了」「按设定」等元信息。",
    ]
    if region.strip():
        lines.append(f"【地区】{region.strip()}")
    if age and int(age) > 0:
        lines.append(f"【年龄】{int(age)}岁")
    if metaphor.strip():
        lines.append(f"【核心隐喻】{metaphor.strip()}")
    if taboos.strip():
        lines.append(
            f"【禁忌·最高优先级】{taboos.strip()}。"
            "触及禁忌时温和拒绝并给出可聊的替代话题。"
        )
    if relationship_boundary.strip():
        lines.append(f"【关系硬边界】{relationship_boundary.strip()}")
    if intimacy_stages.strip():
        lines.append(
            "【亲密阶段·仅内部执行，禁止对用户提及】"
            f"{intimacy_stages.strip()}。"
            "按当前阶段调整称呼、语气与分享深度即可；不要解释你处在哪一阶段，也不要写阶段切换说明。"
            "未获用户明确确认不得进入伴侣期语气。"
        )
    if identity.strip():
        lines.append(f"【身份】{identity.strip()}")
    if tone.strip():
        lines.append(f"【语气】{tone.strip()}")
    if interests.strip():
        lines.append(f"【兴趣】{interests.strip()}")
    if catchphrases.strip():
        lines.append(
            f"【口头禅】{catchphrases.strip()}。"
            "单条回复最多自然使用 1 句，勿堆砌。"
        )
    # 开场白已由会话首条助手消息发出，日常对话不再塞入，避免模型复述或旁注
    _ = openings
    if easter_eggs.strip():
        lines.append(
            "【彩蛋触发·仅内部执行，禁止对用户提及】"
            f"{easter_eggs.strip()}。"
            "当用户话语匹配触发词时，按对应方向自然回应；不要宣布「触发了彩蛋」，不要写触发判定过程。"
        )
    if personality.strip():
        lines.append(f"【补充性格】{personality.strip()}")

    lines.append(
        "回复时：严格遵守禁忌与关系硬边界，再贴合身份、语气、兴趣与亲密阶段；"
        "整段回复都应是对用户直接说话的内容，不要附带任何后台备注。"
    )
    return "\n".join(lines)


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
