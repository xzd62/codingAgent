"""文件搜索工具。"""

import os
from pathlib import Path

from tool.registry import registry

GLOB_SCHEMA = {
    "name": "glob",
    "description": "搜索匹配指定模式的文件路径，支持 ** 递归匹配",
    "parameters": {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "文件匹配模式，例如 *.py 或 **/*.md 或 D:\\path\\**\\*.py",
            },
        },
        "required": ["pattern"],
    },
}


def glob_handler(args):
    from config.settings import get_work_dir

    pattern = args["pattern"]
    work_dir = get_work_dir()
    p = Path(pattern)

    if p.is_absolute():
        from config.permission import check as perm_check
        allowed, reason = perm_check("glob", str(p))
        if not allowed:
            return {"success": False, "error": reason}
        import glob as pyglob
        matched_files = pyglob.glob(pattern, recursive=True)
        paths = [str(f) for f in matched_files if os.path.isfile(f)]
    else:
        matched = list(work_dir.rglob(pattern))
        paths = [str(m.relative_to(work_dir)) for m in matched if m.is_file()]

    return {"success": True, "files": paths}


registry.register(
    name="glob",
    handler=glob_handler,
    schema=GLOB_SCHEMA,
)
