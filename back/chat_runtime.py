# 进行中聊天请求的内存登记（取消信号 / 会话互斥）
from __future__ import annotations

import threading
from dataclasses import dataclass, field


@dataclass
class ActiveChatJob:
    client_request_id: str
    session_id: str
    owner_type: str
    owner_id: str
    cancel_event: threading.Event = field(default_factory=threading.Event)


_lock = threading.Lock()
_by_request: dict[str, ActiveChatJob] = {}
_by_session: dict[str, str] = {}  # session_id -> client_request_id


def register_job(job: ActiveChatJob) -> None:
    with _lock:
        _by_request[job.client_request_id] = job
        _by_session[job.session_id] = job.client_request_id


def unregister_job(client_request_id: str) -> None:
    with _lock:
        job = _by_request.pop(client_request_id, None)
        if job and _by_session.get(job.session_id) == client_request_id:
            _by_session.pop(job.session_id, None)


def get_job(client_request_id: str) -> ActiveChatJob | None:
    with _lock:
        return _by_request.get(client_request_id)


def get_session_job_id(session_id: str) -> str | None:
    with _lock:
        return _by_session.get(session_id)


def request_cancel(client_request_id: str) -> bool:
    """标记取消，并立即释放会话互斥，便于用户马上重试。

    任务本身仍留在 _by_request，直到生成协程 finally 里 unregister。
    """
    with _lock:
        job = _by_request.get(client_request_id)
        if job is None:
            return False
        job.cancel_event.set()
        if _by_session.get(job.session_id) == client_request_id:
            _by_session.pop(job.session_id, None)
        return True


def is_session_busy(session_id: str, exclude_request_id: str | None = None) -> bool:
    """会话是否仍有未取消的进行中生成。"""
    with _lock:
        busy_id = _by_session.get(session_id)
        if busy_id is None:
            return False
        if exclude_request_id and busy_id == exclude_request_id:
            return False
        job = _by_request.get(busy_id)
        if job is None:
            _by_session.pop(session_id, None)
            return False
        if job.cancel_event.is_set():
            # 已取消但尚未 unregister：不算占用
            if _by_session.get(session_id) == busy_id:
                _by_session.pop(session_id, None)
            return False
        return True
