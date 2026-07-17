"""权限管理 — 工作目录外路径的授权检查与持久化。"""

import json
from pathlib import Path

_PERMISSIONS_FILE = Path(__file__).resolve().parent.parent / "data" / "permissions.json"

# 临时跳过（一次性授权），path → True
_skip_once: dict[str, bool] = {}


def _load() -> list[dict]:
    if not _PERMISSIONS_FILE.exists():
        return []
    try:
        data = json.loads(_PERMISSIONS_FILE.read_text(encoding="utf-8"))
        return data.get("permissions", [])
    except (json.JSONDecodeError, Exception):
        return []


def _save(perms: list[dict]):
    _PERMISSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _PERMISSIONS_FILE.write_text(
        json.dumps({"permissions": perms}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _path_matches(permission_path: str, target_path: str) -> bool:
    """判断 target_path 是否在 permission_path 的授权范围内。"""
    pp = Path(permission_path).resolve()
    tp = Path(target_path).resolve()
    if pp == tp:
        return True
    if pp.is_dir() or not pp.suffix:
        try:
            tp.relative_to(pp)
            return True
        except ValueError:
            pass
    return False


def check(tool_name: str, resolved_path: str) -> tuple[bool, str]:
    """检查是否允许操作该路径。

    返回 (allowed, reason)
    拒绝时 reason 包含 __PERMISSION_REQUIRED__:path 供 agent 识别。
    """
    from config.settings import get_work_dir
    work_dir = get_work_dir().resolve()
    tp = Path(resolved_path).resolve()

    # 工作目录内 → 允许
    try:
        tp.relative_to(work_dir)
        return True, ""
    except ValueError:
        pass

    # 临时跳过（一次性授权）
    if _skip_once.pop(str(tp), False):
        return True, ""

    # 永久授权
    for perm in _load():
        if _path_matches(perm["path"], str(tp)):
            return True, ""

    return False, f"__PERMISSION_REQUIRED__:{resolved_path}"


def grant(path: str):
    """添加永久路径授权。"""
    perms = _load()
    resolved = str(Path(path).resolve())
    if not any(p["path"] == resolved for p in perms):
        perms.append({"path": resolved})
        _save(perms)


def list_all() -> list[dict]:
    """列出所有永久授权路径。"""
    return _load()


def revoke(path: str):
    """移除指定路径的永久授权。"""
    perms = _load()
    resolved = str(Path(path).resolve())
    perms = [p for p in perms if p["path"] != resolved]
    _save(perms)


def skip_once(path: str):
    """添加一次性临时授权（用于"允许一次"）。"""
    _skip_once[str(Path(path).resolve())] = True


def clear_temporary():
    """清空所有一次性授权。"""
    _skip_once.clear()
