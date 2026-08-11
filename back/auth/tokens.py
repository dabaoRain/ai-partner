# JWT 签发与解析
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import jwt
from fastapi import HTTPException

from config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    GUEST_TOKEN_EXPIRE_DAYS,
    JWT_ALGORITHM,
    JWT_SECRET,
    REFRESH_TOKEN_EXPIRE_DAYS,
)

TokenTyp = Literal["user", "guest", "refresh"]


@dataclass
class Principal:
    """当前请求主体。"""

    typ: Literal["user", "guest"]
    id: str


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(subject: str, typ: Literal["user", "guest"]) -> str:
    """签发 Access / Guest Token。"""
    if typ == "guest":
        expire = _now() + timedelta(days=GUEST_TOKEN_EXPIRE_DAYS)
    else:
        expire = _now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": subject,
        "typ": typ,
        "jti": str(uuid.uuid4()),
        "exp": expire,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(subject: str) -> tuple[str, str, datetime]:
    """签发 Refresh Token，返回 (token, jti, expires_at)。"""
    jti = str(uuid.uuid4())
    expire = _now() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": subject,
        "typ": "refresh",
        "jti": jti,
        "exp": expire,
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, jti, expire.replace(tzinfo=None)


def decode_token(token: str) -> dict[str, Any]:
    """解析 JWT；无效则 401。"""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="无效或过期的凭证") from exc
