# SQLAlchemy 数据模型
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.utcnow()


class User(Base):
    """正式用户账号。"""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    # 存小写，保证大小写不敏感唯一
    username: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    auth_sessions: Mapped[list[AuthSession]] = relationship(back_populates="user")


class Guest(Base):
    """匿名访客；claim 后标记失效。"""

    __tablename__ = "guests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    claimed_by_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )


class AuthSession(Base):
    """Refresh Token 服务端记录，用于吊销。"""

    __tablename__ = "auth_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    refresh_jti: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    user: Mapped[User] = relationship(back_populates="auth_sessions")


class Persona(Base):
    """官方人设库（只读）：由 persona/index.md 种子写入。"""

    __tablename__ = "personas"

    # 官方稳定 id，如 official_ne_zhaoyining
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    region: Mapped[str] = mapped_column(String(64), default="")
    metaphor: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, index=True)
    name: Mapped[str] = mapped_column(String(100))
    # 人设年龄（岁），官方库约定 25～28
    age: Mapped[int] = mapped_column(Integer, default=0)
    # 人设美图：相对站点路径，如 /static/personas/1.jpg
    avatar_url: Mapped[str] = mapped_column(String(255), default="")
    identity: Mapped[str] = mapped_column(Text, default="")
    tone: Mapped[str] = mapped_column(Text, default="")
    # JSON 数组字符串
    catchphrases: Mapped[str] = mapped_column(Text, default="[]")
    interests: Mapped[str] = mapped_column(Text, default="")
    # JSON 数组：[{title, period, description}]
    intimacy_stages: Mapped[str] = mapped_column(Text, default="[]")
    relationship_boundary: Mapped[str] = mapped_column(Text, default="")
    taboos: Mapped[str] = mapped_column(Text, default="")
    personality: Mapped[str] = mapped_column(Text, default="")
    # JSON 数组字符串
    openings: Mapped[str] = mapped_column(Text, default="[]")
    # JSON 数组：[{trigger, response}]
    easter_eggs: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class ChatSession(Base):
    """聊天会话，归属 guest 或 user。"""

    __tablename__ = "chat_sessions"
    __table_args__ = (
        UniqueConstraint("id", name="uq_chat_sessions_id"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    owner_type: Mapped[str] = mapped_column(String(10), index=True)  # guest | user
    owner_id: Mapped[str] = mapped_column(String(36), index=True)
    # 选用的官方人设 id；会话内快照不可改
    persona_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(100))
    personality: Mapped[str] = mapped_column(Text)
    # 结构化人设（会话锁定快照，与官方库字段对齐）
    region: Mapped[str] = mapped_column(String(64), default="")
    metaphor: Mapped[str] = mapped_column(String(64), default="")
    age: Mapped[int] = mapped_column(Integer, default=0)
    avatar_url: Mapped[str] = mapped_column(String(255), default="")
    identity: Mapped[str] = mapped_column(Text, default="")
    tone: Mapped[str] = mapped_column(Text, default="")
    catchphrases: Mapped[str] = mapped_column(Text, default="[]")
    interests: Mapped[str] = mapped_column(Text, default="")
    intimacy_stages: Mapped[str] = mapped_column(Text, default="[]")
    relationship_boundary: Mapped[str] = mapped_column(Text, default="")
    taboos: Mapped[str] = mapped_column(Text, default="")
    openings: Mapped[str] = mapped_column(Text, default="[]")
    easter_eggs: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    messages: Mapped[list[Message]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Message.id",
    )


class Message(Base):
    """会话内单条消息。"""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20))  # user | assistant
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    session: Mapped[ChatSession] = relationship(back_populates="messages")


class ConsentLog(Base):
    """匿名数据升级授权审计。"""

    __tablename__ = "consent_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    guest_id: Mapped[str] = mapped_column(String(36), index=True)
    consented_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    session_count: Mapped[int] = mapped_column(Integer, default=0)
    client_meta: Mapped[str] = mapped_column(Text, default="")


class ChatRequestLog(Base):
    """聊天请求幂等与状态记录。"""

    __tablename__ = "chat_request_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    client_request_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    owner_type: Mapped[str] = mapped_column(String(10), index=True)
    owner_id: Mapped[str] = mapped_column(String(36), index=True)
    session_id: Mapped[str] = mapped_column(String(32), index=True)
    # pending | streaming | completed | failed | cancelled
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    user_message: Mapped[str] = mapped_column(Text, default="")
    answer: Mapped[str] = mapped_column(Text, default="")
    error_code: Mapped[str] = mapped_column(String(64), default="")
    error_message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class UserPreference(Base):
    """用户偏好；记忆开关仅预留存储。"""

    __tablename__ = "user_preferences"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    memory_enabled: Mapped[int] = mapped_column(Integer, default=0)  # 0/1
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class PermissionLog(Base):
    """权限/同意操作审计。"""

    __tablename__ = "permission_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_type: Mapped[str] = mapped_column(String(10), index=True)  # user | guest | system
    owner_id: Mapped[str] = mapped_column(String(36), index=True)
    # privacy_policy | memory_toggle | account_delete | analytics_opt_in | claim_guest
    purpose: Mapped[str] = mapped_column(String(64), index=True)
    action: Mapped[str] = mapped_column(String(32))  # grant | revoke | view
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class AnalyticsEvent(Base):
    """产品埋点事件。"""

    __tablename__ = "analytics_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    event_name: Mapped[str] = mapped_column(String(64), index=True)
    owner_type: Mapped[str] = mapped_column(String(10), default="", index=True)
    owner_id: Mapped[str] = mapped_column(String(36), default="", index=True)
    session_id: Mapped[str] = mapped_column(String(32), default="", index=True)
    props_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)


class MessageFeedback(Base):
    """消息反馈（点赞/点踩）。"""

    __tablename__ = "message_feedbacks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_type: Mapped[str] = mapped_column(String(10), index=True)
    owner_id: Mapped[str] = mapped_column(String(36), index=True)
    session_id: Mapped[str] = mapped_column(String(32), index=True)
    # 助手消息在会话中的序号（0-based messages 列表下标）或其他客户端键
    message_key: Mapped[str] = mapped_column(String(64), index=True)
    rating: Mapped[str] = mapped_column(String(16))  # up | down
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
