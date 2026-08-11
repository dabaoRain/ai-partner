# 注册登录、Guest、Refresh、Claim
from __future__ import annotations

import json
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth.deps import get_optional_bearer, get_principal, require_user_principal
from auth.passwords import hash_password, verify_password
from auth.tokens import (
    Principal,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from db import get_db
from models import AuthSession, ChatSession, ConsentLog, Guest, User
from schemas import (
    AuthTokenResponse,
    ClaimGuestRequest,
    ClaimGuestResponse,
    GuestTokenResponse,
    LoginRequest,
    LogoutRequest,
    MeResponse,
    RefreshRequest,
    RegisterRequest,
    UserPublic,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_user_tokens(db: Session, user: User) -> AuthTokenResponse:
    access = create_access_token(user.id, "user")
    refresh, jti, expires_at = create_refresh_token(user.id)
    db.add(
        AuthSession(
            user_id=user.id,
            refresh_jti=jti,
            expires_at=expires_at,
        )
    )
    db.commit()
    return AuthTokenResponse(
        access_token=access,
        refresh_token=refresh,
        user=UserPublic(id=user.id, username=user.username),
    )


@router.post("/guest", response_model=GuestTokenResponse)
def create_guest(
    db: Annotated[Session, Depends(get_db)],
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(get_optional_bearer)
    ],
):
    """签发匿名 Guest Token；已有有效 Guest 则幂等返回。"""
    if credentials and credentials.credentials:
        try:
            payload = decode_token(credentials.credentials)
            if payload.get("typ") == "guest" and payload.get("sub"):
                guest = db.get(Guest, payload["sub"])
                if guest is not None and guest.claimed_at is None:
                    return GuestTokenResponse(
                        guest_token=credentials.credentials,
                        guest_id=guest.id,
                    )
        except HTTPException:
            pass

    guest = Guest()
    db.add(guest)
    db.commit()
    db.refresh(guest)
    token = create_access_token(guest.id, "guest")
    return GuestTokenResponse(guest_token=token, guest_id=guest.id)


@router.post("/register", response_model=AuthTokenResponse)
def register(payload: RegisterRequest, db: Annotated[Session, Depends(get_db)]):
    """用户名密码注册；不自动合并匿名数据。"""
    username_key = payload.username.lower()
    exists = db.scalars(select(User).where(User.username == username_key)).first()
    if exists:
        raise HTTPException(status_code=409, detail="用户名已存在")

    user = User(
        username=username_key,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _issue_user_tokens(db, user)


@router.post("/login", response_model=AuthTokenResponse)
def login(payload: LoginRequest, db: Annotated[Session, Depends(get_db)]):
    """登录；失败信息不区分用户名/密码。"""
    username_key = payload.username.lower()
    user = db.scalars(select(User).where(User.username == username_key)).first()
    if (
        user is None
        or user.status != "active"
        or not verify_password(payload.password, user.password_hash)
    ):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return _issue_user_tokens(db, user)


@router.post("/refresh", response_model=AuthTokenResponse)
def refresh(payload: RefreshRequest, db: Annotated[Session, Depends(get_db)]):
    """用 Refresh 换发新 Access + Refresh（旧 Refresh 吊销）。"""
    data = decode_token(payload.refresh_token)
    if data.get("typ") != "refresh" or not data.get("sub") or not data.get("jti"):
        raise HTTPException(status_code=401, detail="无效或过期的凭证")

    row = db.scalars(
        select(AuthSession).where(AuthSession.refresh_jti == data["jti"])
    ).first()
    if (
        row is None
        or row.revoked_at is not None
        or row.expires_at < datetime.utcnow()
        or row.user_id != data["sub"]
    ):
        raise HTTPException(status_code=401, detail="无效或过期的凭证")

    user = db.get(User, row.user_id)
    if user is None or user.status != "active":
        raise HTTPException(status_code=401, detail="无效或过期的凭证")

    row.revoked_at = datetime.utcnow()
    db.commit()
    return _issue_user_tokens(db, user)


@router.post("/logout")
def logout(
    payload: LogoutRequest,
    db: Annotated[Session, Depends(get_db)],
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(get_optional_bearer)
    ],
):
    """吊销 Refresh；Access 依赖短过期自然失效。"""
    token = payload.refresh_token
    if not token and credentials:
        # 若误传 access，忽略；仅处理 refresh
        try:
            data = decode_token(credentials.credentials)
            if data.get("typ") == "refresh":
                token = credentials.credentials
        except HTTPException:
            token = None

    if token:
        data = decode_token(token)
        if data.get("typ") == "refresh" and data.get("jti"):
            row = db.scalars(
                select(AuthSession).where(AuthSession.refresh_jti == data["jti"])
            ).first()
            if row and row.revoked_at is None:
                row.revoked_at = datetime.utcnow()
                db.commit()
    return {"ok": True}


@router.get("/me", response_model=MeResponse)
def me(
    principal: Annotated[Principal, Depends(get_principal)],
    db: Annotated[Session, Depends(get_db)],
):
    """当前主体信息。"""
    if principal.typ == "user":
        user = db.get(User, principal.id)
        return MeResponse(typ="user", id=principal.id, username=user.username if user else None)
    return MeResponse(typ="guest", id=principal.id)


@router.post("/claim-guest", response_model=ClaimGuestResponse)
def claim_guest(
    payload: ClaimGuestRequest,
    request: Request,
    principal: Annotated[Principal, Depends(require_user_principal)],
    db: Annotated[Session, Depends(get_db)],
):
    """明确授权后将匿名会话归属到当前用户。"""
    if payload.consent is not True:
        raise HTTPException(status_code=400, detail="须明确同意授权才能合并匿名数据")

    guest_payload = decode_token(payload.guest_token)
    if guest_payload.get("typ") != "guest" or not guest_payload.get("sub"):
        raise HTTPException(status_code=401, detail="无效或过期的凭证")

    guest_id = guest_payload["sub"]
    guest = db.get(Guest, guest_id)
    if guest is None:
        raise HTTPException(status_code=401, detail="无效或过期的凭证")
    if guest.claimed_at is not None:
        raise HTTPException(status_code=409, detail="该匿名数据已被合并")

    sessions = db.scalars(
        select(ChatSession).where(
            ChatSession.owner_type == "guest",
            ChatSession.owner_id == guest_id,
        )
    ).all()
    count = 0
    for row in sessions:
        row.owner_type = "user"
        row.owner_id = principal.id
        count += 1

    now = datetime.utcnow()
    guest.claimed_at = now
    guest.claimed_by_user_id = principal.id
    meta = {
        "user_agent": request.headers.get("user-agent", ""),
        "client_host": request.client.host if request.client else "",
    }
    db.add(
        ConsentLog(
            user_id=principal.id,
            guest_id=guest_id,
            consented_at=now,
            session_count=count,
            client_meta=json.dumps(meta, ensure_ascii=False),
        )
    )
    db.commit()
    return ClaimGuestResponse(claimed_session_count=count)
