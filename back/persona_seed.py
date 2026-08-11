# 从 persona/index.md 解析并写入官方人设
from __future__ import annotations

import json
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Persona

PERSONA_MD = Path(__file__).resolve().parent.parent / "persona" / "index.md"

_OVERVIEW_ROW = re.compile(
    r"\|\s*`([^`]+)`\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*(\w+)\s*\|"
)
_CARD_HEAD = re.compile(r"^###\s+(\d+)\.\s+(.+?)\s*$", re.M)
_SIMPLE_FIELD = re.compile(r"^- \*\*(\w+)\*\*：(.+)\s*$", re.M)
_LIST_FIELD = re.compile(
    r"^- \*\*(catchphrases|interests|intimacy_stages|开场白|彩蛋触发)\*\*：\s*$",
    re.M,
)


def _dumps(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def _parse_overview(text: str) -> dict[str, dict[str, str]]:
    """总览表：id → region / age / metaphor / status。"""
    result: dict[str, dict[str, str]] = {}
    for match in _OVERVIEW_ROW.finditer(text):
        pid, region, _name, age, metaphor, status = match.groups()
        result[pid.strip()] = {
            "region": region.strip(),
            "age": age.strip(),
            "metaphor": metaphor.strip(),
            "status": status.strip(),
        }
    return result


def _take_block_lines(lines: list[str], start: int) -> tuple[list[str], int]:
    """从 start 起读取缩进子项，直到下一条顶层字段或分隔线。"""
    block: list[str] = []
    i = start
    while i < len(lines):
        line = lines[i]
        if line.startswith("---"):
            break
        if line.startswith("- **") and not line.startswith("  "):
            break
        if line.startswith("### "):
            break
        if line.strip():
            block.append(line.rstrip())
        i += 1
    return block, i


def _parse_catchphrases(block: list[str]) -> list[str]:
    items: list[str] = []
    for line in block:
        m = re.match(r"^\s*\d+\.\s*(.+)$", line)
        if m:
            items.append(m.group(1).strip())
    return items


def _parse_interests(block: list[str]) -> str:
    """兴趣爱好落库为多行文本，便于 Prompt 与展示。"""
    parts: list[str] = []
    for line in block:
        m = re.match(r"^\s*-\s*(.+)$", line)
        if m:
            parts.append(m.group(1).strip())
    return "\n".join(parts)


def _parse_intimacy(block: list[str]) -> list[dict[str, str]]:
    stages: list[dict[str, str]] = []
    for line in block:
        m = re.match(
            r"^\s*-\s*\*\*(.+?)（(.+?)）\*\*：\s*(.+)$",
            line,
        )
        if m:
            stages.append(
                {
                    "title": m.group(1).strip(),
                    "period": m.group(2).strip(),
                    "description": m.group(3).strip(),
                }
            )
    return stages


def _parse_openings(block: list[str]) -> list[str]:
    return _parse_catchphrases(block)


def _parse_easter(block: list[str]) -> list[dict[str, str]]:
    eggs: list[dict[str, str]] = []
    for line in block:
        m = re.match(r"^\s*-\s*(.+?)\s*→\s*(.+)$", line)
        if m:
            eggs.append(
                {
                    "trigger": m.group(1).strip(),
                    "response": m.group(2).strip(),
                }
            )
    return eggs


def parse_persona_markdown(md_path: Path | None = None) -> list[dict]:
    """解析官方人设 Markdown，返回可入库字典列表。"""
    path = md_path or PERSONA_MD
    text = path.read_text(encoding="utf-8")
    overview = _parse_overview(text)

    heads = list(_CARD_HEAD.finditer(text))
    cards: list[dict] = []
    for idx, head in enumerate(heads):
        start = head.end()
        end = heads[idx + 1].start() if idx + 1 < len(heads) else len(text)
        # 卡片正文截到使用指南之前
        body = text[start:end]
        if "## 使用指南" in body:
            body = body.split("## 使用指南", 1)[0]
        body = body.strip()
        lines = body.splitlines()

        fields: dict[str, object] = {
            "sort_order": int(head.group(1)),
            "card_title": head.group(2).strip(),
        }
        i = 0
        while i < len(lines):
            line = lines[i]
            simple = re.match(r"^- \*\*(\w+)\*\*：(.+)$", line)
            if simple:
                key, value = simple.group(1), simple.group(2).strip()
                if value.startswith("`") and value.endswith("`") and len(value) >= 2:
                    value = value[1:-1].strip()
                fields[key] = value
                i += 1
                continue

            list_head = re.match(
                r"^- \*\*(catchphrases|interests|intimacy_stages|开场白|彩蛋触发)\*\*：\s*$",
                line,
            )
            if list_head:
                key = list_head.group(1)
                block, i = _take_block_lines(lines, i + 1)
                if key == "catchphrases":
                    fields["catchphrases"] = _parse_catchphrases(block)
                elif key == "interests":
                    fields["interests"] = _parse_interests(block)
                elif key == "intimacy_stages":
                    fields["intimacy_stages"] = _parse_intimacy(block)
                elif key == "开场白":
                    fields["openings"] = _parse_openings(block)
                elif key == "彩蛋触发":
                    fields["easter_eggs"] = _parse_easter(block)
                continue
            i += 1

        pid = str(fields.get("id") or "").strip()
        if not pid:
            continue
        meta = overview.get(pid, {})
        age_raw = str(fields.get("age") or meta.get("age") or "0").strip()
        try:
            age = int(age_raw)
        except ValueError:
            age = 0
        cards.append(
            {
                "id": pid,
                "region": meta.get("region") or "",
                "metaphor": meta.get("metaphor") or "",
                "status": meta.get("status") or "active",
                "sort_order": int(fields["sort_order"]),
                "name": str(fields.get("name") or "").strip(),
                "age": age,
                "identity": str(fields.get("identity") or "").strip(),
                "tone": str(fields.get("tone") or "").strip(),
                "catchphrases": _dumps(fields.get("catchphrases") or []),
                "interests": str(fields.get("interests") or "").strip(),
                "intimacy_stages": _dumps(fields.get("intimacy_stages") or []),
                "relationship_boundary": str(
                    fields.get("relationship_boundary") or ""
                ).strip(),
                "taboos": str(fields.get("taboos") or "").strip(),
                "personality": str(fields.get("personality") or "").strip(),
                "openings": _dumps(fields.get("openings") or []),
                "easter_eggs": _dumps(fields.get("easter_eggs") or []),
            }
        )
    return cards


def seed_official_personas(db: Session, *, replace: bool = True) -> int:
    """将官方人设写入数据库；replace=True 时先清空人设表再全量写入。"""
    cards = parse_persona_markdown()
    if not cards:
        raise RuntimeError(f"未能从 {PERSONA_MD} 解析到任何人设")

    if replace:
        for row in db.scalars(select(Persona)).all():
            db.delete(row)
        db.flush()

    for card in cards:
        existing = db.get(Persona, card["id"])
        if existing is None:
            db.add(Persona(**card))
        else:
            for key, value in card.items():
                if key == "id":
                    continue
                setattr(existing, key, value)
    db.commit()
    return len(cards)


def default_persona_id(db: Session) -> str | None:
    """默认人设：按 sort_order 第一个 active。"""
    row = db.scalars(
        select(Persona)
        .where(Persona.status == "active")
        .order_by(Persona.sort_order.asc(), Persona.id.asc())
        .limit(1)
    ).first()
    return row.id if row else None
