# 会话 CRUD 路由
import traceback

from fastapi import APIRouter, HTTPException

from schemas import (
    CreateSessionRequest,
    CreateSessionResponse,
    SessionDetailResponse,
    SessionListItem,
)
from session_store import (
    create_session_file,
    delete_session_file,
    generate_session_id,
    list_sessions_from_disk,
    read_session_file,
    turns_to_messages,
)

router = APIRouter(tags=["sessions"])


@router.get("/sessions", response_model=list[SessionListItem])
def list_sessions():
    """历史会话列表：读取 sessions 目录下全部 JSON，最新在前。"""
    return list_sessions_from_disk()


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
def get_session(session_id: str):
    """会话详情：用于切换历史会话时回填人设与聊天记录。"""
    data = read_session_file(session_id)
    return {
        "session_id": data.get("session_id") or session_id,
        "name": data.get("name") or "",
        "personality": data.get("personality") or "",
        "created_at": data.get("created_at") or "",
        "updated_at": data.get("updated_at") or "",
        "messages": turns_to_messages(data.get("turns") or []),
    }


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    """删除会话文件，与前端历史列表保持一致。"""
    delete_session_file(session_id)
    return {"ok": True}


@router.post("/sessions", response_model=CreateSessionResponse)
def create_session(payload: CreateSessionRequest):
    """新建会话：后端生成 session_id，并创建空的 sessions/{id}.json。"""
    session_id = generate_session_id()
    try:
        create_session_file(session_id, payload.name, payload.personality)
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"创建会话失败: {exc}") from exc
    return CreateSessionResponse(session_id=session_id)
