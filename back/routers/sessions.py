# 会话 CRUD 路由（按主体隔离）
import traceback
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from analytics import track_event
from auth.deps import get_principal
from auth.tokens import Principal
from db import get_db
from schemas import (
    CreateSessionRequest,
    CreateSessionResponse,
    SessionDetailResponse,
    SessionListItem,
    UpdateSessionPersonaRequest,
)
from session_service import (
    create_session,
    delete_session,
    get_session_detail,
    list_sessions,
    update_session_persona,
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
    track_event(
        db,
        "session_deleted",
        owner_type=principal.typ,
        owner_id=principal.id,
        session_id=session_id,
    )
    return {"ok": True}


@router.put("/sessions/{session_id}/persona", response_model=SessionDetailResponse)
def api_update_session_persona(
    session_id: str,
    payload: UpdateSessionPersonaRequest,
    principal: Annotated[Principal, Depends(get_principal)],
    db: Annotated[Session, Depends(get_db)],
):
    """空会话更换人设；已有问答则 409。"""
    return update_session_persona(
        db,
        principal,
        session_id,
        persona_id=payload.persona_id,
    )


@router.post("/sessions", response_model=CreateSessionResponse)
def api_create_session(
    payload: CreateSessionRequest,
    principal: Annotated[Principal, Depends(get_principal)],
    db: Annotated[Session, Depends(get_db)],
):
    """开始与某人设的对话线；默认幂等复用，reset=True 时重建。"""
    try:
        session_id, reused = create_session(
            db,
            principal,
            persona_id=payload.persona_id,
            reset=payload.reset,
        )
    except HTTPException:
        raise
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"创建会话失败: {exc}") from exc
    if not reused:
        track_event(
            db,
            "session_created",
            owner_type=principal.typ,
            owner_id=principal.id,
            session_id=session_id,
        )
    return CreateSessionResponse(session_id=session_id, reused=reused)
