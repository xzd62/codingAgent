import json
import httpx

from config.settings import (
    LLM_BASE_URL,
    LLM_API_KEY,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_TIMEOUT,
)

from tool.registry import registry


class LLMClient:
    """LLM 通信客户端，只负责收发消息，不存历史、不决策。"""

    def __init__(self, base_url: str = LLM_BASE_URL, api_key: str = LLM_API_KEY):
        self.base_url = base_url
        self.api_key = api_key
        self.model = LLM_MODEL
        self.temperature = LLM_TEMPERATURE

        self.client = httpx.Client(base_url=self.base_url, headers={"Authorization": f"Bearer {self.api_key}"}, timeout=LLM_TIMEOUT)



    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        """发送对话消息，返回助手回复消息（含 content 和/或 tool_calls）。

        返回格式：
          - 纯文本: {"role": "assistant", "content": "你好"}
          - 调工具: {"role": "assistant", "content": None, "tool_calls": [...]}
        """
        request_body = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }
        if tools:
            request_body["tools"] = tools
        response = self.client.post("/chat/completions", json=request_body)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]

    def chat_stream(self, messages: list[dict]):
        """流式对话，逐个 yield 文本 token。"""
        request_body = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "stream": True,
        }
        with self.client.stream("POST", "/chat/completions", json=request_body) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line or not line.startswith("data: "):
                    continue
                payload = line[6:]
                if payload == "[DONE]":
                    break
                chunk = json.loads(payload)
                delta = chunk["choices"][0]["delta"]
                if "content" in delta and delta["content"]:
                    yield delta["content"]

    # ------------------------------------------------------------------
    # 以下是工具方法（可选）
    # ------------------------------------------------------------------

    def count_tokens(self, text: str) -> int:
        import re
        zh_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
        en_words = len(re.findall(r"[a-zA-Z]+", text))
        return int(zh_chars / 1.5 + en_words * 1.5 + 1)
