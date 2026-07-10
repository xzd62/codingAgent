import json
import httpx

from config.settings import (
    LLM_BASE_URL,
    LLM_TEMPERATURE,
    LLM_TIMEOUT,
    get_llm_model,
    get_llm_api_key,
)

from tool.registry import registry


class LLMClient:
    """LLM 通信客户端，只负责收发消息，不存历史、不决策。"""

    def __init__(self, base_url: str = LLM_BASE_URL, api_key: str = ""):
        self.base_url = base_url
        self.api_key = api_key or get_llm_api_key()
        self.model = get_llm_model()
        self.temperature = LLM_TEMPERATURE

        self.client = httpx.Client(base_url=self.base_url, headers={"Authorization": f"Bearer {self.api_key}"}, timeout=LLM_TIMEOUT)

    def refresh(self):
        """刷新运行时配置（模型名、API Key 变更后调用）。"""
        self.api_key = get_llm_api_key()
        self.model = get_llm_model()
        self.client.headers.update({"Authorization": f"Bearer {self.api_key}"})



    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
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
