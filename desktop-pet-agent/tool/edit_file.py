"""编辑文件工具（查找替换）。"""

from tool.registry import registry

EDIT_FILE_SCHEMA = {
    "name": "edit_file",
    "description": "在文件中查找并替换文本",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "文件路径（相对于工作目录，或绝对路径）",
            },
            "old": {
                "type": "string",
                "description": "被替换的旧文本",
            },
            "new": {
                "type": "string",
                "description": "替换后的新文本",
            },
        },
        "required": ["path", "old", "new"],
    },
}


def edit_file_handler(args):
    from pathlib import Path
    from config.settings import get_work_dir

    raw = args["path"]
    old = args["old"]
    new = args["new"]

    path = Path(raw)
    if not path.is_absolute():
        path = get_work_dir() / path
    resolved = path.resolve()

    work_dir = get_work_dir().resolve()
    if work_dir not in resolved.parents and resolved != work_dir:
        return {"success": False, "error": "不允许编辑工作目录之外的文件"}

    if not resolved.exists():
        return {"success": False, "error": f"文件不存在: {resolved}"}

    if resolved.stat().st_size > 1024 * 1024:
        return {"success": False, "error": "文件超过 1MB，不支持编辑"}

    try:
        content = resolved.read_text(encoding="utf-8")
    except Exception as e:
        return {"success": False, "error": f"读取失败: {e}"}

    if old not in content:
        return {"success": False, "error": "未找到匹配的旧文本"}

    new_content = content.replace(old, new, 1)
    resolved.write_text(new_content, encoding="utf-8")

    return {"success": True, "preview": new_content[:200]}


registry.register(
    name="edit_file",
    handler=edit_file_handler,
    schema=EDIT_FILE_SCHEMA,
)
