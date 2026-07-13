"""网页抓取工具。"""

from tool.registry import registry
import html2text
import httpx

WEB_FETCH_SCHEMA = {
    "name": "web_fetch",
    "description": "抓取网页内容，支持转 Markdown",
    "parameters": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "要抓取的网页 URL",
            },
            "timeout": {
                "type": "integer",
                "description": "超时秒数，默认 30",
            },
            "format": {
                "type": "string",
                "enum": ["markdown", "raw"],
                "description": "返回格式：markdown（默认，HTML→Markdown）或 raw（原始响应文本）",
            },
        },
        "required": ["url"],
    },
}

MAX_SIZE = 2 * 1024 * 1024  # 2MB


def web_fetch_handler(args):
    url = args.get("url")
    if not url:
        return {"success": False, "error": "缺少 url 参数"}
    timeout = args.get("timeout", 30)
    fmt = args.get("format", "markdown")

    if not url.startswith(("http://", "https://")):
        return {"success": False, "error": "只支持 http/https 协议"}

    try:
        response = httpx.get(url, timeout=timeout, follow_redirects=True)
        response.raise_for_status()
    except Exception as e:
        return {"success": False, "error": f"请求失败: {e}"}

    if fmt == "markdown":
        converter = html2text.HTML2Text()
        converter.body_width = 0
        content = converter.handle(response.text)
    else:
        content = response.text

    if len(content) > 30000:
        content = content[:30000] + "\n\n...（内容过长已截断）"

    return {"success": True, "content": content}


registry.register(
    name="web_fetch",
    handler=web_fetch_handler,
    schema=WEB_FETCH_SCHEMA,
)
