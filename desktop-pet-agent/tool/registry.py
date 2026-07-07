"""
工具注册中心 
工具在模块顶层调用 registry.register() 注册。
"""


class ToolEntry:
    def __init__(self, name, handler, schema, check_fn=None):
        self.name = name
        self.handler = handler
        self.schema = schema
        self.check_fn = check_fn

    def is_available(self) -> bool:
        if self.check_fn is not None:
            return self.check_fn()
        return True


class ToolRegistry:
    def __init__(self):
        self._tools = {}

    def register(self, name, handler, schema, check_fn=None):
        self._tools[name] = ToolEntry(name, handler, schema, check_fn)

    def get_tools(self):
        result = []
        for name, entry in self._tools.items():
            if entry.is_available():
                result.append((name, entry.handler, entry.schema))
        return result

    def get_schemas(self):
        result = []
        for name, entry in self._tools.items():
            if entry.is_available():
                result.append({
                    "type": "function",
                    "function": entry.schema,
                })
        return result

    def dispatch(self, name, args):
        entry = self._tools.get(name)
        if entry is None:
            return {"error": f"工具 '{name}' 不存在"}
        return entry.handler(args)


registry = ToolRegistry()
