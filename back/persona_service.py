# 官方人设库：只读列表与快照工具
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Persona
from persona_seed import default_persona_id

# 参与会话快照 / 锁比较 / Prompt 的内容字段
PERSONA_FIELD_KEYS = (
    "name",
    "age",
    "region",
    "metaphor",
    "identity",
    "tone",
    "catchphrases",
    "interests",
    "intimacy_stages",
    "relationship_boundary",
    "taboos",
    "personality",
    "openings",
    "easter_eggs",
)


def _fmt(dt: datetime | None) -> str:
    if dt is None:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _loads_list(raw: Any) -> list:
    if isinstance(raw, list):
        return raw
    text = (raw or "").strip()
    if not text:
        return []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def _dumps_list(value: Any) -> str:
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return "[]"
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return json.dumps(parsed, ensure_ascii=False)
        except json.JSONDecodeError:
            # 按行拆成列表
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            return json.dumps(lines, ensure_ascii=False)
        return json.dumps([text], ensure_ascii=False)
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=False)
    return "[]"


def _as_age(value: Any) -> int:
    try:
        age = int(value or 0)
    except (TypeError, ValueError):
        return 0
    return age if age > 0 else 0


def normalize_persona(data: dict[str, Any]) -> dict[str, str]:
    """规范化人设字段（字符串形态，便于落库与比较）。"""
    name = (data.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="人设名字不能为空")
    return {
        "name": name,
        "age": str(_as_age(data.get("age"))),
        "region": (data.get("region") or "").strip(),
        "metaphor": (data.get("metaphor") or "").strip(),
        "identity": (data.get("identity") or "").strip(),
        "tone": (data.get("tone") or "").strip(),
        "catchphrases": _dumps_list(data.get("catchphrases")),
        "interests": (data.get("interests") or "").strip(),
        "intimacy_stages": _dumps_list(data.get("intimacy_stages")),
        "relationship_boundary": (data.get("relationship_boundary") or "").strip(),
        "taboos": (data.get("taboos") or "").strip(),
        "personality": (data.get("personality") or "").strip(),
        "openings": _dumps_list(data.get("openings")),
        "easter_eggs": _dumps_list(data.get("easter_eggs")),
    }


def persona_snapshot(row: Persona | Any) -> dict[str, str]:
    """从 ORM / 会话行提取可比较快照（一律为字符串）。"""
    return {
        "name": (getattr(row, "name", None) or "").strip(),
        "age": str(_as_age(getattr(row, "age", None))),
        "region": (getattr(row, "region", None) or "").strip(),
        "metaphor": (getattr(row, "metaphor", None) or "").strip(),
        "identity": (getattr(row, "identity", None) or "").strip(),
        "tone": (getattr(row, "tone", None) or "").strip(),
        "catchphrases": _dumps_list(getattr(row, "catchphrases", None)),
        "interests": (getattr(row, "interests", None) or "").strip(),
        "intimacy_stages": _dumps_list(getattr(row, "intimacy_stages", None)),
        "relationship_boundary": (
            getattr(row, "relationship_boundary", None) or ""
        ).strip(),
        "taboos": (getattr(row, "taboos", None) or "").strip(),
        "personality": (getattr(row, "personality", None) or "").strip(),
        "openings": _dumps_list(getattr(row, "openings", None)),
        "easter_eggs": _dumps_list(getattr(row, "easter_eggs", None)),
    }


def personas_equal(a: dict[str, Any], b: dict[str, Any]) -> bool:
    """比较两份人设内容是否一致。"""
    left = normalize_persona(a)
    right = normalize_persona(b)
    return left == right


def snapshot_to_api(fields: dict[str, str]) -> dict[str, Any]:
    """将字符串快照转为接口形态（列表字段解析）。"""
    return {
        "name": fields.get("name") or "",
        "age": _as_age(fields.get("age")),
        "region": fields.get("region") or "",
        "metaphor": fields.get("metaphor") or "",
        "identity": fields.get("identity") or "",
        "tone": fields.get("tone") or "",
        "catchphrases": _loads_list(fields.get("catchphrases")),
        "interests": fields.get("interests") or "",
        "intimacy_stages": _loads_list(fields.get("intimacy_stages")),
        "relationship_boundary": fields.get("relationship_boundary") or "",
        "taboos": fields.get("taboos") or "",
        "personality": fields.get("personality") or "",
        "openings": _loads_list(fields.get("openings")),
        "easter_eggs": _loads_list(fields.get("easter_eggs")),
    }


def persona_to_dict(row: Persona) -> dict:
    snap = persona_snapshot(row)
    return {
        "id": row.id,
        "region": snap["region"],
        "metaphor": snap["metaphor"],
        "status": row.status or "active",
        "sort_order": int(row.sort_order or 0),
        "name": snap["name"],
        "age": _as_age(snap["age"]),
        "identity": snap["identity"],
        "tone": snap["tone"],
        "catchphrases": _loads_list(snap["catchphrases"]),
        "interests": snap["interests"],
        "intimacy_stages": _loads_list(snap["intimacy_stages"]),
        "relationship_boundary": snap["relationship_boundary"],
        "taboos": snap["taboos"],
        "personality": snap["personality"],
        "openings": _loads_list(snap["openings"]),
        "easter_eggs": _loads_list(snap["easter_eggs"]),
        "created_at": _fmt(row.created_at),
        "updated_at": _fmt(row.updated_at),
    }


def list_personas(db: Session) -> list[dict]:
    """官方人设列表，按 sort_order 升序。"""
    stmt = (
        select(Persona)
        .where(Persona.status == "active")
        .order_by(Persona.sort_order.asc(), Persona.id.asc())
    )
    return [persona_to_dict(row) for row in db.scalars(stmt).all()]


def get_persona(db: Session, persona_id: str) -> Persona:
    """读取官方人设；不存在 → 404。"""
    row = db.get(Persona, persona_id)
    if row is None or (row.status or "") != "active":
        raise HTTPException(status_code=404, detail="人设不存在")
    return row


def get_default_persona(db: Session) -> dict:
    """默认人设（第一个）。"""
    pid = default_persona_id(db)
    if not pid:
        raise HTTPException(status_code=500, detail="官方人设尚未初始化")
    return persona_to_dict(get_persona(db, pid))
