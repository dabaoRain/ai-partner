# 健康检查路由
from fastapi import APIRouter

from config import API_KEY

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return {"status": "ok", "has_api_key": bool(API_KEY)}
