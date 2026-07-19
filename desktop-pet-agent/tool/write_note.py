from tool.registry import registry

SCHEMA = {
    "name": "write_note",
    "description": "记录笔记。当用户提到想记住什么、待办事项、重要信息时使用，可将内容保存为笔记供日后查阅",
    "parameters": {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "笔记正文，建议整理为清晰简洁的文本",
            },
            "title": {
                "type": "string",
                "description": "笔记标题（可选，留空自动取第一行前30字）",
            },
        },
        "required": ["content"],
    },
}


def handler(args):
    from note.store import NoteStore
    store = NoteStore()
    note_id = store.create(content=args["content"], title=args.get("title", ""))
    return {"success": True, "note_id": note_id, "message": f"笔记已保存（#{note_id}）"}


registry.register(name="write_note", handler=handler, schema=SCHEMA)
