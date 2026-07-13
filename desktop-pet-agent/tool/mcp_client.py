"""MCP Client — 连接外部 MCP Server，动态注册工具到 ToolRegistry。"""

import asyncio
import threading
import anyio
from mcp import ClientSession, StdioServerParameters, stdio_client

from tool.registry import registry

# 持久事件循环 + 后台线程（所有 anyio 操作共享同一个循环）
_loop: asyncio.AbstractEventLoop | None = None
_loop_lock = threading.Lock()


def _run_async(coro):
    global _loop
    with _loop_lock:
        if _loop is None:
            _loop = asyncio.new_event_loop()
            t = threading.Thread(target=_loop.run_forever, daemon=True)
            t.start()
    future = asyncio.run_coroutine_threadsafe(coro, _loop)
    return future.result()


class _Connection:
    def __init__(self, streams_cm, session_cm, session):
        self._streams_cm = streams_cm
        self._session_cm = session_cm
        self.session = session


_connections: list = []


def init():
    from config.settings import get_mcp_servers

    servers = get_mcp_servers()
    for cfg in servers:
        name = cfg.get("name", "unknown")
        command = cfg.get("command", "")
        args = cfg.get("args", [])
        env = cfg.get("env", {})

        try:
            conn, tools = _connect_to_server(name, command, args, env)
            _connections.append(conn)
            _register_tools(name, conn.session, tools)
        except Exception as e:
            print(f"[MCP] 连接 '{name}' 失败: {e}")


def _connect_to_server(name: str, command: str, args: list[str],
                       env: dict[str, str]):
    async def _connect_inner():
        params = StdioServerParameters(
            command=command,
            args=args,
            env=env or None,
        )

        streams_cm = stdio_client(params)
        read, write = await streams_cm.__aenter__()

        session_cm = ClientSession(read, write)
        session = await session_cm.__aenter__()

        await session.initialize()

        result = await session.list_tools()

        return _Connection(streams_cm, session_cm, session), result.tools

    return _run_async(_connect_inner())


def _mcp_schema_to_our_schema(tool) -> dict:
    return {
        "name": tool.name,
        "description": tool.description,
        "parameters": tool.inputSchema,
    }


def _register_tools(server_name: str, session, tools):
    """把 MCP Server 的工具注册到全局 ToolRegistry。"""
    for tool in tools:
        prefixed = f"{server_name}_{tool.name}"
        schema = _mcp_schema_to_our_schema(tool)
        schema["name"] = prefixed

        def make_handler(session=session, tool_name=tool.name):
            def handler(args):
                try:
                    result = _run_async(session.call_tool(tool_name, args))
                    if hasattr(result, "content") and result.content:
                        texts = [
                            c.text for c in result.content
                            if hasattr(c, "text") and c.text
                        ]
                        return {"success": True, "content": "\n".join(texts)}
                    return {"success": True, "content": str(result)}
                except Exception as e:
                    return {"success": False, "error": str(e)}
            return handler

        registry.register(
            name=prefixed,
            handler=make_handler(),
            schema=schema,
        )
        print(f"[MCP] 注册工具: {prefixed} (来自 {server_name})")


def shutdown():
    for conn in _connections:
        anyio.run(conn.close)
    _connections.clear()
    print("[MCP] 所有连接已关闭")
