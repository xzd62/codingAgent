import json

from tool.registry import registry

SCHEMA = {
    "name": "search_notes",
    "description": "搜索已记录的笔记，按关键词匹配标题或正文，返回匹配的笔记列表",
    "parameters": {
        "type": "object",
        "properties": {
            "keyword": {
                "type": "string",
                "description": "搜索关键词",
            },
        },
        "required": ["keyword"],
    },
}


def handler(args):
    from note.store import NoteStore
    store = NoteStore()
    results = store.search(keyword=args["keyword"])
    return {
        "success": True,
        "count": len(results),
        "notes": results,
    }


registry.register(name="search_notes", handler=handler, schema=SCHEMA)
