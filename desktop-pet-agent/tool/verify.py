"""Python 语法验证工具。"""

import ast

from tool.registry import registry

VERIFY_SCHEMA = {
    "name": "verify",
    "description": "检查 Python 文件语法是否正确",
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


def verify_handler(args):
    from pathlib import Path
    from config.settings import get_work_dir

    raw = args["path"]
    path = Path(raw) 
    if not path.is_absolute():
        path = get_work_dir() / path
    resolved = path.resolve()

    if not resolved.exists():
        return {"success": False, "error": f"文件不存在: {resolved}"}
    
    code = resolved.read_text(encoding="utf-8")
    try:
        ast.parse(code)
        return {"success": True, "valid": True, "message": "语法校验通过"}
    except SyntaxError as e:
        return {"success": True, "valid": False, "error": f"第 {e.lineno} 行: {e.msg}", "lineno": e.lineno}



registry.register(
    name="verify",
    handler=verify_handler,
    schema=VERIFY_SCHEMA,
)
