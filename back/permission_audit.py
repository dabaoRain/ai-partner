# 权限审计写入
from __future__ import annotations

import traceback

from sqlalchemy.orm import Session

from models import PermissionLog


def log_permission(
    db: Session,
    *,
    owner_type: str,
    owner_id: str,
    purpose: str,
    action: str,
    detail: str = "",
    commit: bool = True,
) -> None:
    """记录权限/同意操作；异常不影响主流程。"""
    try:
        db.add(
            PermissionLog(
                owner_type=owner_type,
                owner_id=owner_id,
                purpose=purpose,
                action=action,
                detail=detail,
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
