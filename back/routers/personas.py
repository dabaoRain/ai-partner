# 官方人设只读接口
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from analytics import track_event
from auth.deps import get_principal
from auth.tokens import Principal
from db import get_db
from models import PersonaRating
from persona_service import get_default_persona, get_persona, list_personas, persona_to_dict
from schemas import (
    PersonaItemResponse,
    PersonaRatingRequest,
    PersonaRatingResponse,
    PersonaRatingSubmitResponse,
)

router = APIRouter(prefix="/personas", tags=["personas"])


@router.get("", response_model=list[PersonaItemResponse])
def api_list_personas(
    _principal: Annotated[Principal, Depends(get_principal)],
    db: Annotated[Session, Depends(get_db)],
):
    """官方人设列表（只读）。"""
    return list_personas(db)


@router.get("/default", response_model=PersonaItemResponse)
def api_default_persona(
    _principal: Annotated[Principal, Depends(get_principal)],
    db: Annotated[Session, Depends(get_db)],
):
    """默认人设（排序第一）。"""
    return get_default_persona(db)


@router.get("/{persona_id}", response_model=PersonaItemResponse)
def api_get_persona(
    persona_id: str,
    _principal: Annotated[Principal, Depends(get_principal)],
    db: Annotated[Session, Depends(get_db)],
):
    """单条官方人设详情（只读）。"""
    return persona_to_dict(get_persona(db, persona_id))


@router.get("/{persona_id}/rating", response_model=PersonaRatingResponse)
def api_get_my_persona_rating(
    persona_id: str,
    principal: Annotated[Principal, Depends(get_principal)],
    db: Annotated[Session, Depends(get_db)],
):
    """当前主体对某个人设的评价；未评价时返回空分值。"""
    get_persona(db, persona_id)
    row = db.scalars(
        select(PersonaRating).where(
            PersonaRating.owner_type == principal.typ,
            PersonaRating.owner_id == principal.id,
            PersonaRating.persona_id == persona_id,
        )
    ).first()
    if row is None:
        return PersonaRatingResponse(persona_id=persona_id)
    return PersonaRatingResponse(
        persona_id=persona_id,
        score=row.score,
        remark=row.remark or "",
        updated_at=row.updated_at.isoformat(),
    )


@router.post("/{persona_id}/rating", response_model=PersonaRatingSubmitResponse)
def api_rate_persona(
    persona_id: str,
    payload: PersonaRatingRequest,
    principal: Annotated[Principal, Depends(get_principal)],
    db: Annotated[Session, Depends(get_db)],
):
    """提交/更新人设评价：1～5 分 + 备注。"""
    get_persona(db, persona_id)
    row = db.scalars(
        select(PersonaRating).where(
            PersonaRating.owner_type == principal.typ,
            PersonaRating.owner_id == principal.id,
            PersonaRating.persona_id == persona_id,
        )
    ).first()
    if row is None:
        row = PersonaRating(
            owner_type=principal.typ,
            owner_id=principal.id,
            persona_id=persona_id,
            score=payload.score,
            remark=payload.remark or "",
        )
        db.add(row)
    else:
        row.score = payload.score
        row.remark = payload.remark or ""
        row.updated_at = datetime.utcnow()

    track_event(
        db,
        "persona_rating",
        owner_type=principal.typ,
        owner_id=principal.id,
        props={
            "persona_id": persona_id,
            "score": payload.score,
            "has_remark": bool((payload.remark or "").strip()),
        },
        commit=False,
    )
    db.commit()
    db.refresh(row)
    return PersonaRatingSubmitResponse(
        rating=PersonaRatingResponse(
            persona_id=persona_id,
            score=row.score,
            remark=row.remark or "",
            updated_at=row.updated_at.isoformat(),
        )
    )
