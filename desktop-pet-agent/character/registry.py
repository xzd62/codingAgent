"""角色包注册中心 — 扫描、管理角色包。"""

import base64
from pathlib import Path


_BASE_DIR = Path(__file__).resolve().parent
_SOUL_FILE = "soul.md"
MOODS = ["默认", "高兴", "伤心", "生气", "思考"]


def list_characters() -> list[dict]:
    result = []
    for entry in sorted(_BASE_DIR.iterdir()):
        if not entry.is_dir() or entry.name.startswith("__"):
            continue
        if not (entry / _SOUL_FILE).exists():
            continue
        preview = _get_preview(entry.name)
        result.append({
            "name": entry.name,
            "preview": preview,
        })
    return result


def _get_preview(name: str) -> str:
    for mood in MOODS:
        for ext in ("png", "jpg", "jpeg", "gif", "svg"):
            p = _BASE_DIR / name / f"{mood}.{ext}"
            if p.exists():
                raw = p.read_bytes()
                mime = "image/svg+xml" if ext == "svg" else f"image/{ext}"
                return f"data:{mime};base64,{base64.b64encode(raw).decode()}"
    return ""


def create_character(name: str):
    dir = _BASE_DIR / name
    dir.mkdir(parents=True, exist_ok=True)
    (dir / _SOUL_FILE).write_text("", encoding="utf-8")


def rename_character(old_name: str, new_name: str):
    (_BASE_DIR / old_name).rename(_BASE_DIR / new_name)


def delete_character(name: str):
    import shutil
    dir = _BASE_DIR / name
    if dir.is_dir():
        shutil.rmtree(dir)


def get_soul(name: str) -> str:
    p = _BASE_DIR / name / _SOUL_FILE
    if p.exists():
        return p.read_text(encoding="utf-8").strip()
    return ""


def save_soul(name: str, text: str):
    p = _BASE_DIR / name / _SOUL_FILE
    p.write_text(text.strip() + "\n", encoding="utf-8")


def get_moods(name: str) -> list[dict]:
    seen = set()
    result = []
    # 先加预定义的 5 个，保证顺序
    for mood in MOODS:
        data_url = _get_mood_data(name, mood)
        seen.add(mood)
        result.append({"mood": mood, "hasImage": bool(data_url), "dataUrl": data_url or ""})
    # 再加目录里自定义的
    dir = _BASE_DIR / name
    if dir.is_dir():
        for f in sorted(dir.iterdir()):
            stem = f.stem
            if stem not in seen and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif", ".svg"):
                seen.add(stem)
                raw = f.read_bytes()
                mime = "image/svg+xml" if f.suffix.lower() == ".svg" else f"image/{f.suffix[1:].lower()}"
                result.append({"mood": stem, "hasImage": True, "dataUrl": f"data:{mime};base64,{base64.b64encode(raw).decode()}"})
    return result


def delete_mood_image(name: str, mood: str):
    dir = _BASE_DIR / name
    for ext in ("png", "jpg", "jpeg", "gif", "svg"):
        p = dir / f"{mood}.{ext}"
        if p.exists():
            p.unlink()
            return


def rename_mood_image(name: str, old_mood: str, new_mood: str):
    dir = _BASE_DIR / name
    for ext in ("png", "jpg", "jpeg", "gif", "svg"):
        src = dir / f"{old_mood}.{ext}"
        if src.exists():
            src.rename(dir / f"{new_mood}.{ext}")
            return


def _get_mood_data(name: str, mood: str) -> str:
    for ext in ("png", "jpg", "jpeg", "gif", "svg"):
        p = _BASE_DIR / name / f"{mood}.{ext}"
        if p.exists():
            raw = p.read_bytes()
            mime = "image/svg+xml" if ext == "svg" else f"image/{ext}"
            return f"data:{mime};base64,{base64.b64encode(raw).decode()}"
    return ""


def save_mood_image(name: str, mood: str, data_url: str):
    import re
    match = re.match(r"data:image/(\w+);base64,(.+)", data_url)
    if not match:
        return
    ext = match.group(1)
    raw = base64.b64decode(match.group(2))
    # 删除旧的同情绪图片
    dir = _BASE_DIR / name
    for old_ext in ("png", "jpg", "jpeg", "gif", "svg"):
        old = dir / f"{mood}.{old_ext}"
        if old.exists():
            old.unlink()
    (dir / f"{mood}.{ext}").write_bytes(raw)
