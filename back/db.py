# 数据库引擎与会话
from collections.abc import Generator

from sqlalchemy import create_engine, text
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


def reset_db() -> None:
    """清空全部表并重建（开发初始化用）。"""
    import models  # noqa: F401

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _sqlite_persona_schema_outdated() -> bool:
    """旧 personas 表缺官方人设核心列时需整库重建。"""
    if not DATABASE_URL.startswith("sqlite"):
        return False
    required = {
        "region",
        "metaphor",
        "catchphrases",
        "intimacy_stages",
        "openings",
        "easter_eggs",
        "sort_order",
        "status",
    }
    with engine.connect() as conn:
        rows = conn.execute(text("PRAGMA table_info(personas)")).fetchall()
        if not rows:
            return False
        cols = {row[1] for row in rows}
        return not required.issubset(cols)


def _migrate_sqlite_columns() -> None:
    """为已有 SQLite 库增量补列（如 age），避免无谓整库清空。"""
    if not DATABASE_URL.startswith("sqlite"):
        return

    def _add_missing(table: str, columns: dict[str, str]) -> None:
        rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
        if not rows:
            return
        existing = {row[1] for row in rows}
        for col, ddl in columns.items():
            if col not in existing:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}"))

    with engine.begin() as conn:
        _add_missing(
            "personas",
            {
                "age": "INTEGER DEFAULT 0",
                "avatar_url": "VARCHAR(255) DEFAULT ''",
                "motto": "VARCHAR(255) DEFAULT ''",
            },
        )
        _add_missing(
            "chat_sessions",
            {
                "age": "INTEGER DEFAULT 0",
                "avatar_url": "VARCHAR(255) DEFAULT ''",
                "motto": "VARCHAR(255) DEFAULT ''",
            },
        )


def init_db(*, reset: bool = False) -> None:
    """创建表；结构过旧或 reset=True 时整库清空；并 upsert 官方人设。"""
    import models  # noqa: F401
    from persona_seed import seed_official_personas

    if reset or _sqlite_persona_schema_outdated():
        reset_db()
    else:
        Base.metadata.create_all(bind=engine)
        _migrate_sqlite_columns()

    db = SessionLocal()
    try:
        seed_official_personas(db, replace=False)
    finally:
        db.close()
