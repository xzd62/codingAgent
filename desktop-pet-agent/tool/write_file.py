"""写入文件工具。"""

from tool.registry import registry

WRITE_FILE_SCHEMA = {
    "name": "write_file",
    "description": "写入内容到指定文件（会覆盖已有内容）",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "文件路径（相对于工作目录，或绝对路径）",
            },
            "content": {
                "type": "string",
                "description": "要写入的文件内容",
            },
        },
        "required": ["path", "content"],
    },
}


def write_file_handler(args):
    from pathlib import Path
    from config.settings import get_work_dir

    path = Path(args["path"])
    content = args["content"]

    if not path.is_absolute():
        path = get_work_dir() / path

    resolved = path.resolve()

    from config.permission import check as perm_check
    allowed, reason = perm_check("write_file", str(resolved))
    if not allowed:
        return {"success": False, "error": reason}

    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content, encoding="utf-8")

    return {"success": True} 


registry.register(
    name="write_file",
    handler=write_file_handler,
    schema=WRITE_FILE_SCHEMA,
)
