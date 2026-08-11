# 会话业务：基于数据库的归属读写
from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from auth.tokens import Principal
from config import SESSION_ID_PATTERN
from models import ChatSession, Message


def _fmt(dt: datetime | None) -> str:
    if dt is None:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def generate_session_id(db: Session) -> str:
    """后端生成唯一会话 ID：年月日_时分秒；同秒冲突则顺延。"""
    now = datetime.utcnow()
    while True:
        session_id = now.strftime("%Y%m%d_%H%M%S")
        if db.get(ChatSession, session_id) is None:
            return session_id
        now += timedelta(seconds=1)


def create_session(
    db: Session,
    principal: Principal,
    name: str,
    personality: str,
) -> str:
    """创建空会话并归属当前主体。"""
    session_id = generate_session_id(db)
    now = datetime.utcnow()
    row = ChatSession(
        id=session_id,
        owner_type=principal.typ,
        owner_id=principal.id,
        name=name,
        personality=personality,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    return session_id


def list_sessions(db: Session, principal: Principal) -> list[dict]:
    """仅返回当前主体的会话，按 id 倒序。"""
    stmt = (
        select(ChatSession)
        .where(
            ChatSession.owner_type == principal.typ,
            ChatSession.owner_id == principal.id,
        )
        .order_by(ChatSession.id.desc())
    )
    rows = db.scalars(stmt).all()
    return [
        {
            "session_id": row.id,
            "name": row.name or "",
            "personality": row.personality or "",
            "created_at": _fmt(row.created_at),
            "updated_at": _fmt(row.updated_at),
        }
        for row in rows
    ]


def get_session_detail(
    db: Session,
    principal: Principal,
    session_id: str,
) -> dict:
    """会话详情；越权或不存在 → 404。"""
    if not SESSION_ID_PATTERN.match(session_id):
        raise HTTPException(
            status_code=400,
            detail="session_id 格式须为 年月日_时分秒，例如 20260310_223415",
        )
    stmt = (
        select(ChatSession)
        .options(selectinload(ChatSession.messages))
        .where(ChatSession.id == session_id)
    )
    row = db.scalars(stmt).first()
    if (
        row is None
        or row.owner_type != principal.typ
        or row.owner_id != principal.id
    ):
        raise HTTPException(status_code=404, detail="会话不存在")

    messages = [
        {"role": msg.role, "content": msg.content} for msg in row.messages
    ]
    return {
        "session_id": row.id,
        "name": row.name or "",
        "personality": row.personality or "",
        "created_at": _fmt(row.created_at),
        "updated_at": _fmt(row.updated_at),
        "messages": messages,
    }


def delete_session(db: Session, principal: Principal, session_id: str) -> None:
    """删除会话；越权或不存在 → 404。"""
    if not SESSION_ID_PATTERN.match(session_id):
        raise HTTPException(
            status_code=400,
            detail="session_id 格式须为 年月日_时分秒，例如 20260310_223415",
        )
    row = db.get(ChatSession, session_id)
    if (
        row is None
        or row.owner_type != principal.typ
        or row.owner_id != principal.id
    ):
        raise HTTPException(status_code=404, detail="会话不存在")
    db.delete(row)
    db.commit()


def assert_session_owner(
    db: Session,
    principal: Principal,
    session_id: str,
) -> ChatSession:
    """聊天前校验归属。"""
    if not SESSION_ID_PATTERN.match(session_id):
        raise HTTPException(
            status_code=400,
            detail="session_id 格式须为 年月日_时分秒，例如 20260310_223415",
        )
    row = db.get(ChatSession, session_id)
    if (
        row is None
        or row.owner_type != principal.typ
        or row.owner_id != principal.id
    ):
        raise HTTPException(status_code=404, detail="会话不存在")
    return row


def save_session_turn(
    db: Session,
    session_id: str,
    name: str,
    personality: str,
    question: str,
    answer: str,
) -> None:
    """追加一轮问答消息。"""
    row = db.get(ChatSession, session_id)
    if row is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    now = datetime.utcnow()
    row.name = name
    row.personality = personality
    row.updated_at = now
    db.add(Message(session_id=session_id, role="user", content=question, created_at=now))
    db.add(
        Message(session_id=session_id, role="assistant", content=answer, created_at=now)
    )
    db.commit()
