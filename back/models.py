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


class ChatSession(Base):
    """聊天会话，归属 guest 或 user。"""

    __tablename__ = "chat_sessions"
    __table_args__ = (
        UniqueConstraint("id", name="uq_chat_sessions_id"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    owner_type: Mapped[str] = mapped_column(String(10), index=True)  # guest | user
    owner_id: Mapped[str] = mapped_column(String(36), index=True)
    name: Mapped[str] = mapped_column(String(100))
    personality: Mapped[str] = mapped_column(Text)
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
