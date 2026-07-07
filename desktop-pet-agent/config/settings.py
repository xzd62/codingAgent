import os
from pathlib import Path


def _load_env():
    """先后尝试加载项目内 .env 和（可选）工作区根目录 .env。"""
    candidates = [
        Path(__file__).resolve().parent.parent / ".env",    # desktop-pet-agent/.env
        Path(__file__).resolve().parent.parent.parent / ".env",  # 项目根目录 .env
    ]
    for env_path in candidates:
        if not os.path.isfile(env_path):
            continue
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key, val = key.strip(), val.strip().strip("\"'")
                os.environ.setdefault(key, val)


_load_env()

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
LLM_API_KEY = os.getenv("LLM_API_KEY") or os.getenv("DEEPSEEK_APIKEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "60"))

SYSTEM_PROMPT = "你是一个代码桌宠。当用户要求读取、写入或查找文件时，你必须使用工具（read_file、write_file等）来执行，禁止凭空编造文件内容。请通过 function calling 机制调用工具，不要用文本模拟工具调用。如果工具返回错误，如实告知用户。"
LTM_SUMMARIZE_INTERVAL = 10

# 工作目录（可运行时修改）
_work_dir = Path.cwd()


def get_work_dir() -> Path:
    return _work_dir


def set_work_dir(path: str | Path):
    global _work_dir
    _work_dir = Path(path).resolve()


# 灵魂（soul）路径
_PROJECT_ROOT = Path(__file__).resolve().parent
SOUL_PATH = _PROJECT_ROOT / "soul.md"


def get_soul() -> str:
    """读取 soul.md，返回内容或空字符串。"""
    if SOUL_PATH.exists():
        return SOUL_PATH.read_text(encoding="utf-8").strip()
    return ""


def set_soul(text: str):
    """写入 soul.md。"""
    SOUL_PATH.write_text(text.strip(), encoding="utf-8")


# 头像路径
_avatar_path: str | None = None


def get_avatar_path() -> str | None:
    return _avatar_path


def set_avatar_path(path: str | None):
    global _avatar_path
    _avatar_path = path
