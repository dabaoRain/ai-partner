# 官方人设只读接口
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from auth.deps import get_principal
from auth.tokens import Principal
from db import get_db
from persona_service import get_default_persona, get_persona, list_personas, persona_to_dict
from schemas import PersonaItemResponse

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
