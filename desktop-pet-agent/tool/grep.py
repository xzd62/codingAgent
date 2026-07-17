"""内容搜索工具。"""

from tool.registry import registry

GREP_SCHEMA = {
    "name": "grep",
    "description": "在文件中搜索匹配的文本，返回文件名和行号",
    "parameters": {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "搜索的正则表达式",
            },
            "path": {
                "type": "string",
                "description": "搜索路径（文件或目录），默认为工作目录",
            },
        },
        "required": ["pattern"],
    },
}


def grep_handler(args):
    import re
    from pathlib import Path
    from config.settings import get_work_dir

    pattern = args["pattern"]
    raw_path = args.get("path", "")
    work_dir = get_work_dir()

    if raw_path:
        search_path = Path(raw_path)
        if not search_path.is_absolute():
            search_path = work_dir / search_path
        search_path = search_path.resolve()
        from config.permission import check as perm_check
        allowed, reason = perm_check("grep", str(search_path))
        if not allowed:
            return {"success": False, "error": reason}
    else:
        search_path = work_dir

    if not search_path.exists():
        return {"success": False, "error": f"路径不存在: {search_path}"}

    files_to_search = []
    if search_path.is_file():
        files_to_search = [search_path]
    else:
        files_to_search = list(search_path.rglob("*"))

    results = []
    compiled = re.compile(pattern)

    for fp in files_to_search:
        if not fp.is_file():
            continue
        if fp.stat().st_size > 1024 * 512:
            continue
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        base = work_dir if work_dir.is_dir() else work_dir.parent
        for lineno, line in enumerate(text.splitlines(), 1):
            if compiled.search(line):
                try:
                    rel = fp.relative_to(base)
                except ValueError:
                    rel = fp.name
                results.append(f"{rel}:{lineno}: {line.strip()[:120]}")

    return {"success": True, "matches": results, "count": len(results)}


registry.register(
    name="grep",
    handler=grep_handler,
    schema=GREP_SCHEMA,
)
