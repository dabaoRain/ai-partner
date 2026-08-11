# 埋点上报与质量看板
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from analytics import track_event
from auth.deps import get_principal, require_user_principal
from auth.tokens import Principal
from db import get_db
from models import AnalyticsEvent, MessageFeedback
from schemas import (
    AnalyticsSummaryResponse,
    EventBatchRequest,
    FeedbackRequest,
    FeedbackResponse,
)
from session_service import assert_session_owner

router = APIRouter(tags=["analytics"])

CORE_EVENTS = [
    "user_registered",
    "user_login",
    "first_chat",
    "chat_message",
    "chat_completed",
    "chat_failed",
    "chat_cancelled",
    "feedback",
    "persona_rating",
    "session_deleted",
    "account_deleted",
    "app_open",
]


@router.post("/events/batch")
def post_events_batch(
    payload: EventBatchRequest,
    principal: Annotated[Principal, Depends(get_principal)],
    db: Annotated[Session, Depends(get_db)],
):
    """客户端批量上报；服务端补齐主体。"""
    for item in payload.events:
        name = item.event_name.strip()
        if not name:
            continue
        track_event(
            db,
            name,
            owner_type=principal.typ,
            owner_id=principal.id,
            session_id=item.session_id or "",
            props=item.props or {},
            commit=False,
        )
    db.commit()
    return {"ok": True, "accepted": len(payload.events)}


@router.post("/feedback", response_model=FeedbackResponse)
def post_feedback(
    payload: FeedbackRequest,
    principal: Annotated[Principal, Depends(get_principal)],
    db: Annotated[Session, Depends(get_db)],
):
    """消息点赞/点踩反馈；同一 message_key 更新而非重复插入。"""
    assert_session_owner(db, principal, payload.session_id)
    existing = db.scalars(
        select(MessageFeedback)
        .where(
            MessageFeedback.owner_type == principal.typ,
            MessageFeedback.owner_id == principal.id,
            MessageFeedback.session_id == payload.session_id,
            MessageFeedback.message_key == payload.message_key,
        )
        .order_by(MessageFeedback.created_at.desc())
    ).first()
    if existing is not None:
        existing.rating = payload.rating
        existing.reason = payload.reason or ""
    else:
        db.add(
            MessageFeedback(
                owner_type=principal.typ,
                owner_id=principal.id,
                session_id=payload.session_id,
                message_key=payload.message_key,
                rating=payload.rating,
                reason=payload.reason or "",
            )
        )
    track_event(
        db,
        "feedback",
        owner_type=principal.typ,
        owner_id=principal.id,
        session_id=payload.session_id,
        props={
            "rating": payload.rating,
            "message_key": payload.message_key,
            "reason": payload.reason or "",
        },
        commit=False,
    )
    db.commit()
    return FeedbackResponse(ok=True)


@router.get("/analytics/summary", response_model=AnalyticsSummaryResponse)
def analytics_summary(
    principal: Annotated[Principal, Depends(require_user_principal)],
    db: Annotated[Session, Depends(get_db)],
    days: int = 7,
):
    """质量看板：近 N 天核心事件计数 + 当前用户计数。"""
    days = max(1, min(days, 90))
    cutoff = datetime.utcnow() - timedelta(days=days)

    def _count(owner_filter: bool) -> dict[str, int]:
        totals = {name: 0 for name in CORE_EVENTS}
        stmt = (
            select(AnalyticsEvent.event_name, func.count())
            .where(AnalyticsEvent.created_at >= cutoff)
            .group_by(AnalyticsEvent.event_name)
        )
        if owner_filter:
            stmt = stmt.where(
                AnalyticsEvent.owner_type == "user",
                AnalyticsEvent.owner_id == principal.id,
            )
        for name, cnt in db.execute(stmt).all():
            if name in totals:
                totals[name] = int(cnt)
            else:
                totals[name] = int(cnt)
        return totals

    totals = _count(False)
    my_totals = _count(True)

    # 粗留存提示：近 N 天有 chat_completed 的去重用户数 / 同期注册数
    active_users = db.scalar(
        select(func.count(func.distinct(AnalyticsEvent.owner_id))).where(
            AnalyticsEvent.created_at >= cutoff,
            AnalyticsEvent.event_name == "chat_completed",
            AnalyticsEvent.owner_type == "user",
        )
    ) or 0
    registered = totals.get("user_registered", 0)
    hint = (
        f"近{days}天完成对话的去重用户 {active_users}；"
        f"同期注册 {registered}（粗口径，非严格 D1/D7 队列）"
    )

    return AnalyticsSummaryResponse(
        days=days,
        totals=totals,
        my_totals=my_totals,
        retention_hint=hint,
    )
