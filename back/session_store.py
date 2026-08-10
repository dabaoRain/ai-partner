# 会话文件读写（sessions 目录）
import json
from datetime import datetime, timedelta

from fastapi import HTTPException

from config import SESSION_ID_PATTERN, SESSIONS_DIR


def generate_session_id() -> str:
    """由后端生成唯一会话 ID：年月日_时分秒；同秒冲突则顺延 1 秒。"""
    now = datetime.now()
    while True:
        session_id = now.strftime("%Y%m%d_%H%M%S")
        if not (SESSIONS_DIR / f"{session_id}.json").exists():
            return session_id
        now += timedelta(seconds=1)


def create_session_file(session_id: str, name: str, personality: str) -> None:
    """创建空会话 JSON（一次会话一个文件）。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data = {
        "session_id": session_id,
        "name": name,
        "personality": personality,
        "created_at": now,
        "updated_at": now,
        "turns": [],
    }
    with (SESSIONS_DIR / f"{session_id}.json").open("w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)


def read_session_file(session_id: str) -> dict:
    """读取单个会话 JSON；不存在或格式非法则抛出 HTTP 异常。"""
    if not SESSION_ID_PATTERN.match(session_id):
        raise HTTPException(
            status_code=400,
            detail="session_id 格式须为 年月日_时分秒，例如 20260310_223415",
        )

    file_path = SESSIONS_DIR / f"{session_id}.json"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="会话不存在")

    with file_path.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def delete_session_file(session_id: str) -> None:
    """删除会话 JSON 文件。"""
    if not SESSION_ID_PATTERN.match(session_id):
        raise HTTPException(
            status_code=400,
            detail="session_id 格式须为 年月日_时分秒，例如 20260310_223415",
        )
    file_path = SESSIONS_DIR / f"{session_id}.json"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="会话不存在")
    file_path.unlink()


def turns_to_messages(turns: list) -> list[dict]:
    """将落盘的 turns 转成前端可用的 user/assistant messages。"""
    messages = []
    for turn in turns or []:
        question = turn.get("question")
        answer = turn.get("answer")
        if question:
            messages.append({"role": "user", "content": question})
        if answer:
            messages.append({"role": "assistant", "content": answer})
    return messages


def list_sessions_from_disk() -> list[dict]:
    """扫描 sessions 目录，按 session_id 倒序（最新在前）。"""
    items = []
    for path in SESSIONS_DIR.glob("*.json"):
        session_id = path.stem
        if not SESSION_ID_PATTERN.match(session_id):
            continue
        try:
            with path.open("r", encoding="utf-8") as fp:
                data = json.load(fp)
        except (OSError, json.JSONDecodeError):
            continue
        items.append(
            {
                "session_id": data.get("session_id") or session_id,
                "name": data.get("name") or "",
                "personality": data.get("personality") or "",
                "created_at": data.get("created_at") or "",
                "updated_at": data.get("updated_at") or "",
            }
        )

    # session_id 即 年月日_时分秒，字符串倒序等于时间倒序
    items.sort(key=lambda item: item["session_id"], reverse=True)
    return items


def save_session_turn(
    session_id: str,
    name: str,
    personality: str,
    question: str,
    answer: str,
) -> None:
    """将一轮交互追加写入 sessions/{session_id}.json。

    会话文件必须已由 POST /sessions 创建；此处只追加 turns。
    会话级字段（session_id/name/personality）只写在文件顶层；
    turns 内仅记录本轮 question、answer、saved_at。
    """
    data = read_session_file(session_id)
    file_path = SESSIONS_DIR / f"{session_id}.json"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    turn = {
        "question": question,
        "answer": answer,
        "saved_at": now,
    }

    data["name"] = name
    data["personality"] = personality
    data.setdefault("turns", []).append(turn)
    data["updated_at"] = now

    with file_path.open("w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)
