"""MCP Client — 连接外部 MCP Server，动态注册工具到 ToolRegistry。"""

from tool.registry import registry


def init():
    """读取配置，连接所有 MCP Server，注册工具。"""
    from config.settings import get_mcp_servers

    servers = get_mcp_servers()
    for cfg in servers:
        name = cfg.get("name", "unknown")
        command = cfg.get("command", "")
        args = cfg.get("args", [])
        env = cfg.get("env", {})

        try:
            session, tools = _connect_to_server(name, command, args, env)
            _register_tools(name, session, tools)
        except Exception as e:
            print(f"[MCP] 连接 '{name}' 失败: {e}")


# ============================================================
#  ★ 你来实现这部分 ★
#  用 mcp SDK 建立 stdio 连接，返回 (session, tools)
# ============================================================
def _connect_to_server(name: str, command: str, args: list[str],
                       env: dict[str, str]):
    """连接到 MCP Server，发现工具列表。

    你需要用 mcp SDK 完成：
      1. 创建 StdioServerParameters(command, args, env)
      2. 用 stdio_client() 拿到 read_stream, write_stream
      3. 用 ClientSession(read, write) 创建 session
      4. 调用 await session.initialize()
      5. 调用 await session.list_tools()
      6. 返回 (session, tools) — tools 是 list[Tool] 对象

    MCP SDK 的 Tool 有 .name, .description, .input_schema 三个属性。
    """
    # ── 你的代码写在这里 ──
    raise NotImplementedError("请实现 _connect_to_server()")


# ============================================================
#  以下由我（AI）写完，你不用动
# ============================================================
def _mcp_schema_to_our_schema(tool) -> dict:
    """把 MCP SDK 的 Tool 对象转成我们 registry 的 schema 格式。"""
    return {
        "name": tool.name,
        "description": tool.description,
        "parameters": tool.input_schema,
    }


def _register_tools(server_name: str, session, tools):
    """把 MCP Server 的工具注册到全局 ToolRegistry。"""
    for tool in tools:
        prefixed = f"{server_name}_{tool.name}"
        schema = _mcp_schema_to_our_schema(tool)
        schema["name"] = prefixed

        def make_handler(session=session, tool_name=tool.name):
            def handler(args):
                import anyio
                try:
                    result = anyio.run(session.call_tool, tool_name, args)
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
    """断开所有 MCP Server 连接（预留）。"""
    print("[MCP] 清理连接…")
