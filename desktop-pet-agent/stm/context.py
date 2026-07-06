from __future__ import annotations

from llm.client import LLMClient


class SessionContext:
    """短期记忆：当前会话的消息列表 + 自动裁剪。
    不关心消息内容，只做容器和边界管理。
    """

    def __init__(self, llm_client: LLMClient | None = None, max_tokens: int = 4096):
        self._messages: list[dict] = []
        self._max_tokens = max_tokens
        self._tokenizer = llm_client.count_tokens if llm_client else None

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    def add_message(self, role: str, content: str):
        self._messages.append({"role": role, "content": content})
        self._trim()

    def add_system(self, content: str):
        self._messages.insert(0, {"role": "system", "content": content})
        self._trim()

    def get_messages(self) -> list[dict]:
        return list(self._messages)

    def pop_message(self, index: int = -1) -> dict | None:
        if self._messages:
            return self._messages.pop(index)
        return None

    def clear(self):
        self._messages.clear()

    def count_messages(self) -> int:
        return len(self._messages)

    def count_tokens(self) -> int:
        if not self._tokenizer:
            return 0
        total = 0
        for msg in self._messages:
            total += self._tokenizer(msg.get("content", ""))
        return total

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    def _trim(self):
        if not self._tokenizer:
            return
        while self._messages and self.count_tokens() > self._max_tokens:
            # 跳过索引 0 的 system prompt，优先丢弃最旧的对话
            if len(self._messages) > 1 and self._messages[0].get("role") == "system":
                self._messages.pop(1)
            else:
                self._messages.pop(0)

    def __repr__(self) -> str:
        return (
            f"SessionContext(messages={self.count_messages()}, "
            f"tokens={self.count_tokens()}/{self._max_tokens})"
        )
