# 应用配置与路径常量
import os
import re
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# DeepSeek API Key
API_KEY = os.environ.get("DEEPSEEK_API_KEY")

# 大模型配置
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-v4-pro"

# 数据目录与 SQLite
DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    f"sqlite:///{(DATA_DIR / 'ai_partner.db').as_posix()}",
)

# JWT
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-change-me-ai-partner-jwt-secret")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))
GUEST_TOKEN_EXPIRE_DAYS = int(os.environ.get("GUEST_TOKEN_EXPIRE_DAYS", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.environ.get("REFRESH_TOKEN_EXPIRE_DAYS", "14"))

# CORS 白名单，逗号分隔；开发默认本机前端
_cors = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
)
CORS_ORIGINS = [item.strip() for item in _cors.split(",") if item.strip()]

# 会话 ID 格式：年月日_时分秒
SESSION_ID_PATTERN = re.compile(r"^\d{8}_\d{6}$")

# 聊天链路超时（秒）；开启 thinking 时首包可能较久，默认放宽
CHAT_FIRST_TOKEN_TIMEOUT_SEC = int(os.environ.get("CHAT_FIRST_TOKEN_TIMEOUT_SEC", "90"))
CHAT_STREAM_TIMEOUT_SEC = int(os.environ.get("CHAT_STREAM_TIMEOUT_SEC", "180"))
# 上游 HTTP 超时与建连失败重试次数
CHAT_UPSTREAM_TIMEOUT_SEC = float(os.environ.get("CHAT_UPSTREAM_TIMEOUT_SEC", "120"))
CHAT_UPSTREAM_MAX_RETRIES = int(os.environ.get("CHAT_UPSTREAM_MAX_RETRIES", "3"))

# 数据保留（天）；0 表示不自动清理该类
DATA_RETENTION_DAYS_GUEST = int(os.environ.get("DATA_RETENTION_DAYS_GUEST", "30"))
DATA_RETENTION_DAYS_CHAT_REQUEST_LOG = int(
    os.environ.get("DATA_RETENTION_DAYS_CHAT_REQUEST_LOG", "90")
)
