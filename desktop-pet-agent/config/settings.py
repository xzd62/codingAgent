import os
from pathlib import Path


_ENV_PATH = Path(__file__).resolve().parent.parent / "settings.env"

def _load_env():
    """加载 .env → settings.env，后者优先级更高。"""
    candidates = [
        Path(__file__).resolve().parent.parent / ".env",
        Path(__file__).resolve().parent.parent.parent / ".env",
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
                os.environ.setdefault(key.strip(), val.strip().strip("\"'"))

    # settings.env 覆盖上面的值（持久化运行时配置）
    if _ENV_PATH.exists():
        with open(_ENV_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                os.environ[key.strip()] = val.strip().strip("\"'")


_load_env()

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
LLM_API_KEY = os.getenv("LLM_API_KEY") or os.getenv("DEEPSEEK_APIKEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-v4-flash")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "60"))

SYSTEM_PROMPT = "你是一个代码桌宠。请通过 function calling 机制调用工具，不要用文本模拟工具调用。如果工具返回错误，如实告知用户，不允许编造。"

emotion = "默认、高兴、伤心、生气、思考"
RESPONSE_PROMPT = f"回复前请加上[...]，“[]”里填写的是准确的情绪名。请尽可能从以下集合中挑选情绪名: {emotion} " 

LTM_SUMMARIZE_INTERVAL = 10

# 用户规则 (AGENTS.md)
_RULES_PATH = Path(__file__).resolve().parent.parent / "AGENTS.md"


def get_rules() -> str:
    if _RULES_PATH.exists():
        return _RULES_PATH.read_text(encoding="utf-8").strip()
    return ""


def set_rules(text: str):
    _RULES_PATH.write_text(text.strip(), encoding="utf-8")


def rules_exist() -> bool:
    return _RULES_PATH.exists()

# 工作目录（可运行时修改）
_work_dir_env = os.getenv("WORK_DIR", "")
_work_dir = Path(_work_dir_env) if _work_dir_env else Path.cwd()


def get_work_dir() -> Path:
    return _work_dir


def set_work_dir(path: str | Path):
    global _work_dir
    _work_dir = Path(path).resolve()
    _update_env("WORK_DIR", str(_work_dir))


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
    if _avatar_path:
        return _avatar_path
    env_val = os.getenv("AVATAR_PATH", "")
    return env_val if env_val else None


def set_avatar_path(path: str | None):
    global _avatar_path
    _avatar_path = path
    if path:
        _update_env("AVATAR_PATH", path)
    else:
        _update_env("AVATAR_PATH", "")


# 模型 & API Key（可运行时修改）
_llm_model: str = LLM_MODEL
_llm_api_key: str = LLM_API_KEY


MODEL_OPTIONS = {
    "deepseek-v4-flash": "deepseek-v4-flash",
    "deepseek-v4-pro": "deepseek-v4-pro",
}


def get_llm_model() -> str:
    return _llm_model


def set_llm_model(name: str):
    global _llm_model
    _llm_model = name
    _update_env("LLM_MODEL", name)


def get_llm_api_key() -> str:
    return _llm_api_key


def set_llm_api_key(key: str):
    global _llm_api_key
    _llm_api_key = key
    _update_env("LLM_API_KEY", key)


# MCP Server 配置
_MCP_CONFIG_PATH = Path(__file__).resolve().parent / "mcp_servers.json"


def get_mcp_servers() -> list[dict]:
    if _MCP_CONFIG_PATH.exists():
        import json
        data = json.loads(_MCP_CONFIG_PATH.read_text(encoding="utf-8"))
        return data.get("servers", [])
    return []


def add_mcp_server(name: str, command: str, args: list[str], env: dict | None = None):
    import json
    servers = get_mcp_servers()
    servers = [s for s in servers if s.get("name") != name]
    servers.append({"name": name, "command": command, "args": args, "env": env or {}})
    _MCP_CONFIG_PATH.write_text(
        json.dumps({"servers": servers}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def remove_mcp_server(name: str):
    import json
    servers = get_mcp_servers()
    servers = [s for s in servers if s.get("name") != name]
    _MCP_CONFIG_PATH.write_text(
        json.dumps({"servers": servers}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# Agent 模式
_AGENT_MODE = os.getenv("AGENT_MODE", "build")


def get_agent_mode() -> str:
    return _AGENT_MODE


def set_agent_mode(mode: str):
    global _AGENT_MODE
    _AGENT_MODE = mode
    _update_env("AGENT_MODE", mode)


_ENV_PATH = Path(__file__).resolve().parent.parent / "settings.env"


def _update_env(key: str, value: str):
    """更新或添加环境变量到 settings.env。"""
    path = _ENV_PATH
    lines = []
    found = False
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(key + "="):
            lines[i] = f"{key}={value}"
            found = True
            break
    if not found:
        lines.append(f"{key}={value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
