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

# 会话落盘目录：back/sessions/
SESSIONS_DIR = Path(__file__).resolve().parent / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

# 会话文件名仅允许 年月日_时分秒，如 20260310_223415
SESSION_ID_PATTERN = re.compile(r"^\d{8}_\d{6}$")
