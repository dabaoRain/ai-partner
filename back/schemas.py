# 请求/响应数据模型
from pydantic import BaseModel, Field, field_validator
import re


class ChatMessage(BaseModel):
    """单条对话消息。"""

    role: str
    content: str


class ChatRequest(BaseModel):
    """前端「发送消息」接口入参。"""

    message: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    personality: str = Field(..., min_length=1)
    session_id: str = Field(..., min_length=1)
    history: list[ChatMessage] = Field(default_factory=list)


class CreateSessionRequest(BaseModel):
    """新建会话入参。"""

    name: str = Field(..., min_length=1)
    personality: str = Field(..., min_length=1)


class CreateSessionResponse(BaseModel):
    """新建会话出参。"""

    session_id: str


class SessionListItem(BaseModel):
    """历史会话列表项。"""

    session_id: str
    name: str
    personality: str
    created_at: str = ""
    updated_at: str = ""


class SessionDetailResponse(BaseModel):
    """会话详情。"""

    session_id: str
    name: str
    personality: str
    created_at: str = ""
    updated_at: str = ""
    messages: list[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    """非流式聊天出参（预留）。"""

    content: str


class RegisterRequest(BaseModel):
    """注册入参。"""

    username: str = Field(..., min_length=3, max_length=32)
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_]+", value):
            raise ValueError("用户名仅允许字母、数字和下划线")
        return value


class LoginRequest(BaseModel):
    """登录入参。"""

    username: str = Field(..., min_length=1, max_length=32)
    password: str = Field(..., min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    """刷新 Access。"""

    refresh_token: str = Field(..., min_length=1)


class LogoutRequest(BaseModel):
    """登出：可只传 refresh_token。"""

    refresh_token: str | None = None


class ClaimGuestRequest(BaseModel):
    """匿名数据升级授权。"""

    guest_token: str = Field(..., min_length=1)
    consent: bool


class GuestTokenResponse(BaseModel):
    guest_token: str
    guest_id: str


class UserPublic(BaseModel):
    id: str
    username: str


class AuthTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserPublic


class MeResponse(BaseModel):
    typ: str
    id: str
    username: str | None = None


class ClaimGuestResponse(BaseModel):
    claimed_session_count: int
