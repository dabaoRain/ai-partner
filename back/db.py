# 数据库引擎与会话
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config import DATABASE_URL

# SQLite 需关闭同线程检查，便于 FastAPI 同步路由使用
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    """ORM 基类。"""


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖：请求级 DB Session。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """创建全部表（Alpha 用 create_all，不做 Alembic）。"""
    # 延迟导入，避免循环依赖
    import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
