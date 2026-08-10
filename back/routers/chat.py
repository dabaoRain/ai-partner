# 流式聊天路由
import json
import traceback

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from config import API_KEY
from llm import APIError, build_system_prompt, create_chat_stream
from schemas import ChatRequest
from session_store import read_session_file, save_session_turn

router = APIRouter(tags=["chat"])


@router.post("/chat")
def chat(payload: ChatRequest):
    """流式聊天：SSE 逐块推送大模型输出，结束后落盘。"""
    if not API_KEY:
        raise HTTPException(
            status_code=500,
            detail="未配置 DEEPSEEK_API_KEY，请在 back/.env 中设置或 export 后再启动",
        )

    # 提前校验会话存在，避免流中途才报错
    read_session_file(payload.session_id)

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
            save_session_turn(
                session_id=payload.session_id,
                name=payload.name,
                personality=payload.personality,
                question=payload.message,
                answer=answer,
            )
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
