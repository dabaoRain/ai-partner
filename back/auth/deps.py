# FastAPI 鉴权依赖
from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from auth.tokens import Principal, decode_token
from db import get_db
from models import ChatSession, Guest, User

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class TokenPairContext:
    """可选 Bearer，供 guest 续期等场景。"""

    credentials: HTTPAuthorizationCredentials | None


def get_optional_bearer(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
) -> HTTPAuthorizationCredentials | None:
    return credentials


def get_principal(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
    db: Annotated[Session, Depends(get_db)],
) -> Principal:
    """解析并校验 Access/Guest Token，返回主体。"""
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail="未提供认证凭证")

    payload = decode_token(credentials.credentials)
    typ = payload.get("typ")
    sub = payload.get("sub")
    if typ not in ("user", "guest") or not sub:
        raise HTTPException(status_code=401, detail="无效或过期的凭证")

    if typ == "user":
        user = db.get(User, sub)
        if user is None or user.status != "active":
            raise HTTPException(status_code=401, detail="无效或过期的凭证")
        return Principal(typ="user", id=sub)

    guest = db.get(Guest, sub)
    if guest is None or guest.claimed_at is not None:
        raise HTTPException(status_code=401, detail="无效或过期的凭证")
    return Principal(typ="guest", id=sub)


def require_user_principal(
    principal: Annotated[Principal, Depends(get_principal)],
) -> Principal:
    """要求正式用户 Access。"""
    if principal.typ != "user":
        raise HTTPException(status_code=401, detail="需要登录账号")
    return principal


def get_owned_session(
    session_id: str,
    principal: Principal,
    db: Session,
) -> ChatSession:
    """加载会话并校验归属；不存在或无权统一 404。"""
    row = db.get(ChatSession, session_id)
    if (
        row is None
        or row.owner_type != principal.typ
        or row.owner_id != principal.id
    ):
        raise HTTPException(status_code=404, detail="会话不存在")
    return row
