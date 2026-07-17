"""读取文件工具。"""

from tool.registry import registry

READ_FILE_SCHEMA = {
    "name": "read_file",
    "description": "读取指定文件的内容",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "文件路径（相对于工作目录，或绝对路径）",
            },
        },
        "required": ["path"],
    },
}


def read_file_handler(args):
    from pathlib import Path
    from config.settings import get_work_dir

    raw = args["path"]
    path = Path(raw)

    if not path.is_absolute():
        path = get_work_dir() / path

    resolved = path.resolve()

    from config.permission import check as perm_check
    allowed, reason = perm_check("read_file", str(resolved))
    if not allowed:
        return {"success": False, "error": reason}

    # 检查是否是目录
    if resolved.is_dir():
        return {"success": False, "error": f"'{raw}' 是目录，不是文件"}

    # 安全校验：限制最大 500KB
    if resolved.stat().st_size > 500 * 1024:
        return {"success": False, "error": "文件超过 500KB，不支持读取"}

    # 尝试 UTF-8，失败则回退系统编码
    try:
        content = resolved.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        import locale
        encoding = locale.getpreferredencoding()
        content = resolved.read_text(encoding=encoding)

    # 结果截断，避免撑爆 LLM 上下文
    if len(content) > 30000:
        content = content[:30000] + "\n\n...（内容过长已截断）"

    return {"success": True, "content": content}


registry.register(
    name="read_file",
    handler=read_file_handler,
    schema=READ_FILE_SCHEMA,
)
