# 聊天链路统一错误码
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChatError:
    """SSE / HTTP 共用错误描述。"""

    code: str
    message: str
    retryable: bool

    def as_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
        }


FIRST_TOKEN_TIMEOUT = ChatError(
    "FIRST_TOKEN_TIMEOUT",
    "等待首字超时，请重试",
    True,
)
STREAM_TIMEOUT = ChatError(
    "STREAM_TIMEOUT",
    "生成超时，请重试",
    True,
)
UPSTREAM_ERROR = ChatError(
    "UPSTREAM_ERROR",
    "模型服务异常，请重试",
    True,
)
STREAM_INTERRUPTED = ChatError(
    "STREAM_INTERRUPTED",
    "连接中断，请重试",
    True,
)
CLIENT_CANCELLED = ChatError(
    "CLIENT_CANCELLED",
    "已停止生成",
    False,
)
SESSION_BUSY = ChatError(
    "SESSION_BUSY",
    "当前会话正在生成，请稍后再试或先停止",
    False,
)
DUPLICATE_IN_FLIGHT = ChatError(
    "DUPLICATE_IN_FLIGHT",
    "相同请求正在处理中",
    False,
)
