# 会话 CRUD 路由（按主体隔离）
import traceback
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth.deps import get_principal
from auth.tokens import Principal
from db import get_db
from schemas import (
    CreateSessionRequest,
    CreateSessionResponse,
    SessionDetailResponse,
    SessionListItem,
)
from session_service import (
    create_session,
    delete_session,
    get_session_detail,
    list_sessions,
)

router = APIRouter(tags=["sessions"])


@router.get("/sessions", response_model=list[SessionListItem])
def api_list_sessions(
    principal: Annotated[Principal, Depends(get_principal)],
    db: Annotated[Session, Depends(get_db)],
):
    """历史会话列表：仅当前主体。"""
    return list_sessions(db, principal)


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
def api_get_session(
    session_id: str,
    principal: Annotated[Principal, Depends(get_principal)],
    db: Annotated[Session, Depends(get_db)],
):
    """会话详情：归属校验失败返回 404。"""
    return get_session_detail(db, principal, session_id)


@router.delete("/sessions/{session_id}")
def api_delete_session(
    session_id: str,
    principal: Annotated[Principal, Depends(get_principal)],
    db: Annotated[Session, Depends(get_db)],
):
    """删除会话。"""
    delete_session(db, principal, session_id)
    return {"ok": True}


@router.post("/sessions", response_model=CreateSessionResponse)
def api_create_session(
    payload: CreateSessionRequest,
    principal: Annotated[Principal, Depends(get_principal)],
    db: Annotated[Session, Depends(get_db)],
):
    """新建会话并写入归属。"""
    try:
        session_id = create_session(db, principal, payload.name, payload.personality)
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"创建会话失败: {exc}") from exc
    return CreateSessionResponse(session_id=session_id)
