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

    def add_message(self, role: str, content: str, **kwargs):
        msg = {"role": role, "content": content}
        msg.update(kwargs)
        self._messages.append(msg)
        self._trim()

    def add_system(self, content: str):
        self._messages.insert(0, {"role": "system", "content": content})
        self._trim()

    def get_messages(self, include_status: bool = False) -> list[dict]:
        if include_status:
            return list(self._messages)
        return [m for m in self._messages if m.get("role") != "status"]

    def pop_message(self, index: int = -1) -> dict | None:
        if self._messages:
            return self._messages.pop(index)
        return None

    def clear(self):
        self._messages.clear()

    def load_messages(self, messages: list[dict]):
        self._messages = list(messages)
        self._clean_orphaned_tools()
        self._trim()

    def _clean_orphaned_tools(self):
        """移除没有对应 assistant(tool_calls) 的孤儿 tool 消息。"""
        clean = []
        expect_tool = 0
        for m in self._messages:
            if m.get("role") == "assistant" and m.get("tool_calls"):
                clean.append(m)
                expect_tool = len(m["tool_calls"])
            elif m.get("role") == "tool" and expect_tool > 0:
                clean.append(m)
                expect_tool -= 1
            elif m.get("role") != "tool":
                clean.append(m)
                expect_tool = 0
        self._messages = clean

    def count_messages(self) -> int:
        return len(self._messages)

    def count_tokens(self) -> int:
        if not self._tokenizer:
            return 0
        total = 0
        for msg in self._messages:
            c = msg.get("content")
            total += self._tokenizer(c if isinstance(c, str) else "")
        return total

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    def get_token_info(self) -> dict:
        """返回 token 统计信息。"""
        total = self.count_tokens()
        return {"tokens": total, "max": 1000000, "pct": round(total / 10000, 1)}

    def _trim(self):
        if not self._tokenizer:
            return
        while self._messages and self.count_tokens() > self._max_tokens:
            idx = 1 if (len(self._messages) > 1 and self._messages[0].get("role") == "system") else 0
            removed = self._messages.pop(idx)
            # 如果删掉的是 assistant(tool_calls)，连带删掉后续的 tool 消息
            if removed.get("role") == "assistant" and removed.get("tool_calls"):
                while idx < len(self._messages) and self._messages[idx].get("role") == "tool":
                    self._messages.pop(idx)

    def __repr__(self) -> str:
        return (
            f"SessionContext(messages={self.count_messages()}, "
            f"tokens={self.count_tokens()}/{self._max_tokens})"
        )
