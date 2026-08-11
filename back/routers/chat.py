# 流式聊天路由：停止 / 超时 / 幂等 / 防重复 / 错误码
from __future__ import annotations

import json
import time
import traceback
from datetime import datetime
from typing import Annotated, Iterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth.deps import get_principal
from auth.tokens import Principal
from chat_errors import (
    CLIENT_CANCELLED,
    DUPLICATE_IN_FLIGHT,
    FIRST_TOKEN_TIMEOUT,
    SESSION_BUSY,
    STREAM_INTERRUPTED,
    STREAM_TIMEOUT,
    UPSTREAM_ERROR,
    ChatError,
)
from chat_runtime import (
    ActiveChatJob,
    get_job,
    is_session_busy,
    register_job,
    request_cancel,
    unregister_job,
)
from config import (
    API_KEY,
    CHAT_FIRST_TOKEN_TIMEOUT_SEC,
    CHAT_STREAM_TIMEOUT_SEC,
)
from db import SessionLocal, get_db
from llm import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    build_system_prompt,
    create_chat_stream,
)
from models import ChatRequestLog
from schemas import ChatRequest, StopChatRequest
from session_service import assert_session_owner, save_session_turn

router = APIRouter(tags=["chat"])


def _sse(payload: dict | str) -> str:
    if isinstance(payload, str):
        return f"data: {payload}\n\n"
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _sse_error(err: ChatError) -> str:
    return _sse({"error": err.as_dict()})


def _update_log(
    client_request_id: str,
    *,
    status: str | None = None,
    answer: str | None = None,
    error: ChatError | None = None,
) -> None:
    db = SessionLocal()
    try:
        row = db.scalars(
            select(ChatRequestLog).where(
                ChatRequestLog.client_request_id == client_request_id
            )
        ).first()
        if row is None:
            return
        if status is not None:
            row.status = status
        if answer is not None:
            row.answer = answer
        if error is not None:
            row.error_code = error.code
            row.error_message = error.message
        row.updated_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()


def _replay_completed(answer: str) -> Iterator[str]:
    if answer:
        yield _sse({"content": answer, "replay": True})
    yield _sse("[DONE]")


@router.post("/chat/stop")
def stop_chat(
    payload: StopChatRequest,
    principal: Annotated[Principal, Depends(get_principal)],
    db: Annotated[Session, Depends(get_db)],
):
    """停止指定幂等键对应的生成。"""
    row = db.scalars(
        select(ChatRequestLog).where(
            ChatRequestLog.client_request_id == payload.client_request_id
        )
    ).first()
    if row is None or row.owner_type != principal.typ or row.owner_id != principal.id:
        raise HTTPException(status_code=404, detail="请求不存在")

    found = request_cancel(payload.client_request_id)
    return {"ok": True, "cancelled": found}


@router.post("/chat")
def chat(
    payload: ChatRequest,
    principal: Annotated[Principal, Depends(get_principal)],
    db: Annotated[Session, Depends(get_db)],
):
    """流式聊天：SSE；支持幂等回放、会话互斥、超时与停止。"""
    if not API_KEY:
        raise HTTPException(
            status_code=500,
            detail="未配置 DEEPSEEK_API_KEY，请在 back/.env 中设置或 export 后再启动",
        )

    assert_session_owner(db, principal, payload.session_id)

    existing = db.scalars(
        select(ChatRequestLog).where(
            ChatRequestLog.client_request_id == payload.client_request_id
        )
    ).first()

    # 幂等：已完成则回放
    if existing is not None:
        if existing.owner_type != principal.typ or existing.owner_id != principal.id:
            raise HTTPException(status_code=404, detail="请求不存在")
        if existing.status == "completed":
            return StreamingResponse(
                _replay_completed(existing.answer or ""),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )
        if existing.status == "streaming":
            if get_job(payload.client_request_id) is not None:
                raise HTTPException(
                    status_code=409,
                    detail=DUPLICATE_IN_FLIGHT.as_dict(),
                )
            # 进程内无登记：视为残留，允许重试
            existing.status = "failed"
            existing.error_code = STREAM_INTERRUPTED.code
            existing.error_message = STREAM_INTERRUPTED.message
            existing.updated_at = datetime.utcnow()
            db.commit()
        elif existing.status in ("failed", "cancelled", "pending"):
            # 允许用同一幂等键重试失败/取消请求
            existing.status = "pending"
            existing.answer = ""
            existing.error_code = ""
            existing.error_message = ""
            existing.user_message = payload.message
            existing.session_id = payload.session_id
            existing.updated_at = datetime.utcnow()
            db.commit()
        log_row = existing
    else:
        log_row = ChatRequestLog(
            client_request_id=payload.client_request_id,
            owner_type=principal.typ,
            owner_id=principal.id,
            session_id=payload.session_id,
            status="pending",
            user_message=payload.message,
        )
        db.add(log_row)
        db.commit()

    # 同一会话防重复生成（已取消的任务不占坑）
    if is_session_busy(payload.session_id, payload.client_request_id):
        raise HTTPException(status_code=409, detail=SESSION_BUSY.as_dict())

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
    except (APIConnectionError, APITimeoutError) as exc:
        err = ChatError(
            UPSTREAM_ERROR.code,
            "无法连接模型服务，请检查网络后重试",
            True,
        )
        _update_log(payload.client_request_id, status="failed", error=err)
        raise HTTPException(status_code=502, detail=err.as_dict()) from exc
    except APIError as exc:
        err = ChatError(UPSTREAM_ERROR.code, f"{UPSTREAM_ERROR.message}: {exc.message}", True)
        _update_log(payload.client_request_id, status="failed", error=err)
        raise HTTPException(status_code=502, detail=err.as_dict()) from exc
    except Exception as exc:
        traceback.print_exc()
        msg = str(exc)
        if "connection error" in msg.lower():
            msg = "无法连接模型服务，请检查网络后重试"
        else:
            msg = f"{UPSTREAM_ERROR.message}: {exc}"
        err = ChatError(UPSTREAM_ERROR.code, msg, True)
        _update_log(payload.client_request_id, status="failed", error=err)
        raise HTTPException(status_code=502, detail=err.as_dict()) from exc

    job = ActiveChatJob(
        client_request_id=payload.client_request_id,
        session_id=payload.session_id,
        owner_type=principal.typ,
        owner_id=principal.id,
    )
    register_job(job)
    _update_log(payload.client_request_id, status="streaming")

    def event_generator():
        full_parts: list[str] = []
        started = time.monotonic()
        got_first_token = False
        terminal_error: ChatError | None = None
        cancelled = False

        try:
            yield _sse(
                {
                    "event": "start",
                    "client_request_id": payload.client_request_id,
                }
            )

            for chunk in stream:
                if job.cancel_event.is_set():
                    cancelled = True
                    terminal_error = CLIENT_CANCELLED
                    break

                now = time.monotonic()
                if not got_first_token and (now - started) > CHAT_FIRST_TOKEN_TIMEOUT_SEC:
                    terminal_error = FIRST_TOKEN_TIMEOUT
                    break
                if (now - started) > CHAT_STREAM_TIMEOUT_SEC:
                    terminal_error = STREAM_TIMEOUT
                    break

                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                # thinking 阶段可能只有 reasoning_content，也算上游已响应，避免误报首字超时
                reasoning = getattr(delta, "reasoning_content", None) or ""
                content = getattr(delta, "content", None) or ""
                if reasoning or content:
                    got_first_token = True
                if not content:
                    continue
                full_parts.append(content)
                yield _sse({"content": content})

            answer = "".join(full_parts)

            if terminal_error is not None:
                if cancelled and answer:
                    # 用户停止且已有内容：落库部分结果
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
                    _update_log(
                        payload.client_request_id,
                        status="cancelled",
                        answer=answer,
                        error=terminal_error,
                    )
                else:
                    _update_log(
                        payload.client_request_id,
                        status="cancelled" if cancelled else "failed",
                        answer=answer,
                        error=terminal_error,
                    )
                yield _sse_error(terminal_error)
                return

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

            _update_log(
                payload.client_request_id,
                status="completed",
                answer=answer,
            )
            yield _sse("[DONE]")
        except Exception as exc:
            traceback.print_exc()
            err = ChatError(
                STREAM_INTERRUPTED.code,
                f"{STREAM_INTERRUPTED.message}: {exc}",
                True,
            )
            _update_log(
                payload.client_request_id,
                status="failed",
                answer="".join(full_parts),
                error=err,
            )
            yield _sse_error(err)
        finally:
            try:
                close = getattr(stream, "close", None)
                if callable(close):
                    close()
            except Exception:
                pass
            unregister_job(payload.client_request_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
