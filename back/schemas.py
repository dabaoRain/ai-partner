# 请求/响应数据模型
from pydantic import BaseModel, Field, field_validator
import re


class ChatMessage(BaseModel):
    """单条对话消息。"""

    role: str
    content: str
    # 点赞/点踩：up | down | 空
    feedback: str | None = None


class PersonaFields(BaseModel):
    """结构化人设字段（会话快照 / 聊天锁比较）。"""

    name: str = Field(..., min_length=1, max_length=100)
    age: int = Field(default=0, ge=0, le=120)
    avatar_url: str = Field(default="", max_length=255)
    region: str = Field(default="", max_length=64)
    metaphor: str = Field(default="", max_length=64)
    identity: str = Field(default="", max_length=1000)
    motto: str = Field(default="", max_length=255)
    tone: str = Field(default="", max_length=1000)
    # 口头禅：接口可为 list，入库快照时序列化为 JSON 字符串
    catchphrases: list[str] | str = Field(default_factory=list)
    interests: str = Field(default="", max_length=2000)
    intimacy_stages: list[dict] | str = Field(default_factory=list)
    relationship_boundary: str = Field(default="", max_length=1000)
    taboos: str = Field(default="", max_length=1000)
    personality: str = Field(default="", max_length=2000)
    openings: list[str] | str = Field(default_factory=list)
    easter_eggs: list[dict] | str = Field(default_factory=list)


class ChatRequest(PersonaFields):
    """前端「发送消息」接口入参。"""

    message: str = Field(..., min_length=1)
    session_id: str = Field(..., min_length=1)
    history: list[ChatMessage] = Field(default_factory=list)
    # 客户端幂等键：同一请求重放/防重复提交
    client_request_id: str = Field(..., min_length=8, max_length=64)

    @field_validator("client_request_id")
    @classmethod
    def validate_client_request_id(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
            raise ValueError("client_request_id 格式非法")
        return value


class StopChatRequest(BaseModel):
    """停止生成入参。"""

    client_request_id: str = Field(..., min_length=8, max_length=64)

    @field_validator("client_request_id")
    @classmethod
    def validate_client_request_id(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
            raise ValueError("client_request_id 格式非法")
        return value


class CreateSessionRequest(BaseModel):
    """开始/重置与某人设的对话线（一人设一线）。"""

    persona_id: str | None = Field(default=None, max_length=64)
    # True：删除已有同人设会话后重建；False：已有则直接复用
    reset: bool = False


class UpdateSessionPersonaRequest(BaseModel):
    """空会话更换人设：指定官方人设 id。"""

    persona_id: str = Field(..., min_length=1, max_length=64)


class CreateSessionResponse(BaseModel):
    """开始对话出参。"""

    session_id: str
    reused: bool = False


class SessionListItem(BaseModel):
    """历史会话列表项。"""

    session_id: str
    name: str
    personality: str = ""
    identity: str = ""
    motto: str = ""
    tone: str = ""
    region: str = ""
    avatar_url: str = ""
    persona_id: str | None = None
    created_at: str = ""
    updated_at: str = ""


class SessionDetailResponse(PersonaFields):
    """会话详情。"""

    session_id: str
    persona_id: str | None = None
    created_at: str = ""
    updated_at: str = ""
    messages: list[ChatMessage] = Field(default_factory=list)


class PersonaItemResponse(PersonaFields):
    """官方人设条目出参。"""

    id: str
    status: str = "active"
    sort_order: int = 0
    created_at: str = ""
    updated_at: str = ""


class ChatResponse(BaseModel):
    """非流式聊天出参（预留）。"""

    content: str


class RegisterRequest(BaseModel):
    """注册入参。"""

    username: str = Field(..., min_length=3, max_length=32)
    password: str = Field(..., min_length=8, max_length=128)
    # 明示同意隐私说明
    privacy_accepted: bool = False

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


class DeleteAccountRequest(BaseModel):
    """注销账号：需确认密码。"""

    password: str = Field(..., min_length=1, max_length=128)


class PreferencesResponse(BaseModel):
    memory_enabled: bool


class PreferencesUpdateRequest(BaseModel):
    memory_enabled: bool


class PrivacyPolicyResponse(BaseModel):
    version: str
    title: str
    collection_purposes: list[str]
    retention: dict[str, str]
    user_controls: list[str]
    updated_at: str


class EventItem(BaseModel):
    event_name: str = Field(..., min_length=1, max_length=64)
    session_id: str = ""
    props: dict = Field(default_factory=dict)


class EventBatchRequest(BaseModel):
    events: list[EventItem] = Field(..., min_length=1, max_length=50)


class FeedbackRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    message_key: str = Field(..., min_length=1, max_length=64)
    rating: str = Field(..., pattern="^(up|down)$")
    reason: str = Field(default="", max_length=500)


class FeedbackResponse(BaseModel):
    ok: bool = True


class PersonaRatingRequest(BaseModel):
    score: int = Field(..., ge=1, le=5)
    remark: str = Field(default="", max_length=500)


class PersonaRatingResponse(BaseModel):
    persona_id: str
    score: int | None = None
    remark: str = ""
    updated_at: str = ""


class PersonaRatingSubmitResponse(BaseModel):
    ok: bool = True
    rating: PersonaRatingResponse


class AnalyticsSummaryResponse(BaseModel):
    days: int
    totals: dict[str, int]
    my_totals: dict[str, int]
    retention_hint: str
