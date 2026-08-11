# 流式聊天路由
import json
import traceback
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from auth.deps import get_principal
from auth.tokens import Principal
from config import API_KEY
from db import SessionLocal, get_db
from llm import APIError, build_system_prompt, create_chat_stream
from schemas import ChatRequest
from session_service import assert_session_owner, save_session_turn

router = APIRouter(tags=["chat"])


@router.post("/chat")
def chat(
    payload: ChatRequest,
    principal: Annotated[Principal, Depends(get_principal)],
    db: Annotated[Session, Depends(get_db)],
):
    """流式聊天：SSE 推送后落库；先做归属校验。"""
    if not API_KEY:
        raise HTTPException(
            status_code=500,
            detail="未配置 DEEPSEEK_API_KEY，请在 back/.env 中设置或 export 后再启动",
        )

    assert_session_owner(db, principal, payload.session_id)

    messages = [
        {
            "role": "system",
            "content": build_system_prompt(payload.name, payload.personality),
        },
        *[item.model_dump() for item in payload.history],
        {"role": "user", "content": payload.message},
    ]

    try:
        stream = create_chat_stream(messages)
    except APIError as exc:
        raise HTTPException(
            status_code=500, detail=f"大模型调用失败: {exc.message}"
        ) from exc
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"服务异常: {exc}") from exc

    def event_generator():
        full_parts = []
        try:
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                content = getattr(delta, "content", None) or ""
                if not content:
                    continue
                full_parts.append(content)
                yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"

            answer = "".join(full_parts)
            # 流结束后使用独立 Session 落库，避免请求 Session 已关闭
            save_db = SessionLocal()
            try:
                save_session_turn(
                    db=save_db,
                    session_id=payload.session_id,
                    name=payload.name,
                    personality=payload.personality,
                    question=payload.message,
                    answer=answer,
                )
            finally:
                save_db.close()
            yield "data: [DONE]\n\n"
        except Exception as exc:
            traceback.print_exc()
            yield f"data: {json.dumps({'error': str(exc)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
