# 埋点写入（失败不影响主流程）
from __future__ import annotations

import json
import traceback
from typing import Any

from sqlalchemy.orm import Session

from models import AnalyticsEvent


def track_event(
    db: Session,
    event_name: str,
    *,
    owner_type: str = "",
    owner_id: str = "",
    session_id: str = "",
    props: dict[str, Any] | None = None,
    commit: bool = True,
) -> None:
    """写入一条分析事件；异常只打日志。"""
    try:
        db.add(
            AnalyticsEvent(
                event_name=event_name,
                owner_type=owner_type or "",
                owner_id=owner_id or "",
                session_id=session_id or "",
                props_json=json.dumps(props or {}, ensure_ascii=False),
            )
        )
        if commit:
            db.commit()
    except Exception:
        traceback.print_exc()
        try:
            db.rollback()
        except Exception:
            pass
