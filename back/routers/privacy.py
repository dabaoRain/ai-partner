# 隐私政策、偏好、过期清理
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from auth.deps import get_principal, require_user_principal
from auth.tokens import Principal
from config import DATA_RETENTION_DAYS_CHAT_REQUEST_LOG, DATA_RETENTION_DAYS_GUEST
from db import get_db
from models import ChatRequestLog, ChatSession, Guest, UserPreference
from permission_audit import log_permission
from schemas import (
    PreferencesResponse,
    PreferencesUpdateRequest,
    PrivacyPolicyResponse,
)

router = APIRouter(prefix="/privacy", tags=["privacy"])

POLICY_VERSION = "1.0.3"
POLICY_UPDATED_AT = "2026-08-11"


@router.get("/policy", response_model=PrivacyPolicyResponse)
def get_privacy_policy():
    """公开：收集目的与数据保留策略说明。"""
    return PrivacyPolicyResponse(
        version=POLICY_VERSION,
        title="AI 智能伴侣隐私说明",
        collection_purposes=[
            "账号标识（用户名与密码哈希）：用于注册登录与跨端恢复会话",
            "会话与消息内容：用于多轮对话上下文与历史回看",
            "人设配置（名字/性格）：用于生成角色化回复",
            "操作日志与埋点（不含密码明文）：用于稳定性、质量统计与安全审计",
            "匿名 Guest 标识：用于未登录体验时的会话归属",
        ],
        retention={
            "account": "账号数据在注销前长期保留；注销后立即删除会话、消息与偏好",
            "guest": f"未认领的游客会话与标识默认保留 {DATA_RETENTION_DAYS_GUEST} 天",
            "chat_request_logs": (
                f"聊天幂等/状态日志默认保留 {DATA_RETENTION_DAYS_CHAT_REQUEST_LOG} 天"
            ),
            "analytics": "聚合质量统计保留；账号注销时删除该账号相关事件明细",
        },
        user_controls=[
            "可随时删除单个会话",
            "可注销账号并清除个人对话数据",
            "记忆功能开关已预留（当前版本不会启用长期记忆写入）",
            "匿名数据合并到账号前需明确同意",
        ],
        updated_at=POLICY_UPDATED_AT,
    )


@router.get("/preferences", response_model=PreferencesResponse)
def get_preferences(
    principal: Annotated[Principal, Depends(require_user_principal)],
    db: Annotated[Session, Depends(get_db)],
):
    """读取用户偏好（记忆开关预留）。"""
    row = db.get(UserPreference, principal.id)
    if row is None:
        row = UserPreference(user_id=principal.id, memory_enabled=0)
        db.add(row)
        db.commit()
    enabled = bool(row.memory_enabled)
    return PreferencesResponse(memory_enabled=enabled)


@router.patch("/preferences", response_model=PreferencesResponse)
def update_preferences(
    payload: PreferencesUpdateRequest,
    principal: Annotated[Principal, Depends(require_user_principal)],
    db: Annotated[Session, Depends(get_db)],
):
    """更新记忆开关预留；仅写偏好与审计，不触发记忆引擎。"""
    row = db.get(UserPreference, principal.id)
    if row is None:
        row = UserPreference(user_id=principal.id, memory_enabled=0)
        db.add(row)
    row.memory_enabled = 1 if payload.memory_enabled else 0
    row.updated_at = datetime.utcnow()
    db.commit()
    log_permission(
        db,
        owner_type="user",
        owner_id=principal.id,
        purpose="memory_toggle",
        action="grant" if payload.memory_enabled else "revoke",
        detail=f"memory_enabled={payload.memory_enabled}",
    )
    return PreferencesResponse(memory_enabled=payload.memory_enabled)


@router.post("/purge-expired")
def purge_expired(
    principal: Annotated[Principal, Depends(require_user_principal)],
    db: Annotated[Session, Depends(get_db)],
):
    """按保留策略清理过期游客与请求日志（需登录；运维/种子用户可用）。"""
    deleted_guests = 0
    deleted_sessions = 0
    deleted_logs = 0

    if DATA_RETENTION_DAYS_GUEST > 0:
        cutoff = datetime.utcnow() - timedelta(days=DATA_RETENTION_DAYS_GUEST)
        guests = db.scalars(
            select(Guest).where(
                Guest.claimed_at.is_(None),
                Guest.created_at < cutoff,
            )
        ).all()
        for guest in guests:
            sessions = db.scalars(
                select(ChatSession).where(
                    ChatSession.owner_type == "guest",
                    ChatSession.owner_id == guest.id,
                )
            ).all()
            for sess in sessions:
                db.delete(sess)
                deleted_sessions += 1
            db.delete(guest)
            deleted_guests += 1

    if DATA_RETENTION_DAYS_CHAT_REQUEST_LOG > 0:
        log_cutoff = datetime.utcnow() - timedelta(
            days=DATA_RETENTION_DAYS_CHAT_REQUEST_LOG
        )
        result = db.execute(
            delete(ChatRequestLog).where(ChatRequestLog.created_at < log_cutoff)
        )
        deleted_logs = result.rowcount or 0

    db.commit()
    log_permission(
        db,
        owner_type="user",
        owner_id=principal.id,
        purpose="data_retention_purge",
        action="grant",
        detail=(
            f"guests={deleted_guests},sessions={deleted_sessions},logs={deleted_logs}"
        ),
    )
    return {
        "ok": True,
        "deleted_guests": deleted_guests,
        "deleted_sessions": deleted_sessions,
        "deleted_chat_request_logs": deleted_logs,
    }


@router.get("/permissions")
def list_my_permissions(
    principal: Annotated[Principal, Depends(get_principal)],
    db: Annotated[Session, Depends(get_db)],
):
    """当前主体的权限审计记录（可审计）。"""
    from models import PermissionLog

    rows = db.scalars(
        select(PermissionLog)
        .where(
            PermissionLog.owner_type == principal.typ,
            PermissionLog.owner_id == principal.id,
        )
        .order_by(PermissionLog.created_at.desc())
        .limit(100)
    ).all()
    return [
        {
            "purpose": r.purpose,
            "action": r.action,
            "detail": r.detail,
            "created_at": r.created_at.isoformat() + "Z" if r.created_at else "",
        }
        for r in rows
    ]
