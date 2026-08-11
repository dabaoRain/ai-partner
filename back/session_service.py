# 会话业务：基于数据库的归属读写
from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from auth.tokens import Principal
from config import SESSION_ID_PATTERN
from models import ChatSession, Message, MessageFeedback
from persona_seed import default_persona_id
from persona_service import (
    get_persona,
    persona_snapshot,
    snapshot_to_api,
)


def _fmt(dt: datetime | None) -> str:
    if dt is None:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _loads_list(raw: Any) -> list:
    if isinstance(raw, list):
        return raw
    text = (raw or "").strip()
    if not text:
        return []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def _pick_opening(fields: dict[str, str]) -> str:
    """从人设开场白中选一条（随机，缺省空）。"""
    openings = [
        str(item).strip()
        for item in _loads_list(fields.get("openings"))
        if str(item).strip()
    ]
    if not openings:
        return ""
    return random.choice(openings)


def _user_message_count(db: Session, session_id: str) -> int:
    """用户消息数；开场白不算锁定条件。"""
    return int(
        db.scalar(
            select(func.count())
            .select_from(Message)
            .where(Message.session_id == session_id, Message.role == "user")
        )
        or 0
    )


def _replace_opening_message(
    db: Session,
    session_id: str,
    opening: str,
    *,
    now: datetime | None = None,
) -> None:
    """空会话（无用户消息）时写入/替换助手开场白。"""
    stamp = now or datetime.utcnow()
    existing = db.scalars(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.id.asc())
    ).all()
    # 尚无用户发言：清掉旧助手消息，写入新开场白
    if any(msg.role == "user" for msg in existing):
        return
    for msg in existing:
        db.delete(msg)
    if opening:
        db.add(
            Message(
                session_id=session_id,
                role="assistant",
                content=opening,
                created_at=stamp,
            )
        )


def _apply_snapshot(row: ChatSession, fields: dict[str, str], persona_id: str | None) -> None:
    """将会话人设快照写到行上。"""
    row.persona_id = persona_id
    row.name = fields["name"]
    row.personality = fields["personality"]
    row.region = fields["region"]
    row.metaphor = fields["metaphor"]
    try:
        row.age = int(fields.get("age") or 0)
    except (TypeError, ValueError):
        row.age = 0
    row.identity = fields["identity"]
    row.tone = fields["tone"]
    row.catchphrases = fields["catchphrases"]
    row.interests = fields["interests"]
    row.intimacy_stages = fields["intimacy_stages"]
    row.relationship_boundary = fields["relationship_boundary"]
    row.taboos = fields["taboos"]
    row.openings = fields["openings"]
    row.easter_eggs = fields["easter_eggs"]


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
    *,
    persona_id: str | None = None,
) -> str:
    """创建会话：写入官方人设快照，并主动发送一条开场白。"""
    resolved = persona_id or default_persona_id(db)
    if not resolved:
        raise HTTPException(status_code=500, detail="官方人设尚未初始化")
    lib = get_persona(db, resolved)
    fields = persona_snapshot(lib)

    session_id = generate_session_id(db)
    now = datetime.utcnow()
    row = ChatSession(
        id=session_id,
        owner_type=principal.typ,
        owner_id=principal.id,
        created_at=now,
        updated_at=now,
        name=fields["name"],
        personality=fields["personality"],
    )
    _apply_snapshot(row, fields, resolved)
    db.add(row)
    db.flush()
    opening = _pick_opening(fields)
    if opening:
        db.add(
            Message(
                session_id=session_id,
                role="assistant",
                content=opening,
                created_at=now,
            )
        )
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
            "identity": getattr(row, "identity", None) or "",
            "tone": getattr(row, "tone", None) or "",
            "region": getattr(row, "region", None) or "",
            "persona_id": getattr(row, "persona_id", None),
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

    # 旧空会话：打开时补一条开场白（无用户消息时）
    if _user_message_count(db, session_id) == 0:
        has_assistant = any(msg.role == "assistant" for msg in row.messages)
        if not has_assistant:
            opening = _pick_opening(persona_snapshot(row))
            if opening:
                db.add(
                    Message(
                        session_id=session_id,
                        role="assistant",
                        content=opening,
                        created_at=datetime.utcnow(),
                    )
                )
                db.commit()
                db.refresh(row)
                # 重新加载 messages 关系
                stmt = (
                    select(ChatSession)
                    .options(selectinload(ChatSession.messages))
                    .where(ChatSession.id == session_id)
                )
                row = db.scalars(stmt).first()

    messages = [
        {"role": msg.role, "content": msg.content} for msg in row.messages
    ]

    feedback_rows = db.scalars(
        select(MessageFeedback)
        .where(
            MessageFeedback.session_id == session_id,
            MessageFeedback.owner_type == principal.typ,
            MessageFeedback.owner_id == principal.id,
        )
        .order_by(MessageFeedback.created_at.asc())
    ).all()
    latest_feedback: dict[str, str] = {}
    for fb in feedback_rows:
        latest_feedback[fb.message_key] = fb.rating

    for index, item in enumerate(messages):
        rating = latest_feedback.get(f"{session_id}:{index}")
        if rating in ("up", "down"):
            item["feedback"] = rating

    return {
        "session_id": row.id,
        "persona_id": getattr(row, "persona_id", None),
        **snapshot_to_api(persona_snapshot(row)),
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


def update_session_persona(
    db: Session,
    principal: Principal,
    session_id: str,
    *,
    persona_id: str,
) -> dict:
    """仅允许在尚无用户发言时更换人设快照，并刷新开场白。"""
    row = assert_session_owner(db, principal, session_id)
    if _user_message_count(db, session_id) > 0:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "PERSONA_LOCKED",
                "message": "当前会话已有问答，更换人设请新建会话",
                "retryable": False,
            },
        )

    lib = get_persona(db, persona_id)
    fields = persona_snapshot(lib)
    now = datetime.utcnow()
    _apply_snapshot(row, fields, persona_id)
    row.updated_at = now
    _replace_opening_message(db, session_id, _pick_opening(fields), now=now)
    db.commit()
    return get_session_detail(db, principal, session_id)


def save_session_turn(
    db: Session,
    session_id: str,
    question: str,
    answer: str,
) -> None:
    """追加一轮问答；不修改会话人设快照。"""
    row = db.get(ChatSession, session_id)
    if row is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    now = datetime.utcnow()
    row.updated_at = now
    db.add(Message(session_id=session_id, role="user", content=question, created_at=now))
    db.add(
        Message(session_id=session_id, role="assistant", content=answer, created_at=now)
    )
    db.commit()
