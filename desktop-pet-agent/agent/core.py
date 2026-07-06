"""Agent 调度层：ReAct 模式，串联 llm / stm / ltm。"""

from config.settings import SYSTEM_PROMPT
from llm.client import LLMClient
from ltm.store import MemoryStore
from stm.context import SessionContext


class Agent:
    """Agent 调度层。

    TODO: 你写 process() 核心逻辑
    步骤：
      1. 把 user_input 写入 stm（调用 stm.add_message）
      2. 从 stm 取历史消息（调用 stm.get_messages()）
      3. 调 llm.chat(历史消息)
      4. 把助手回复写入 stm（调用 stm.add_message）
      5. 调 ltm.try_summarize() 检查是否该总结
      6. return 助手回复文本
    """

    def __init__(self, llm: LLMClient, stm: SessionContext, ltm: MemoryStore):
        self._llm = llm
        self._stm = stm
        self._ltm = ltm
        self._setup_system_prompt()

    def _setup_system_prompt(self):
        memories = self._ltm.load()
        full_prompt = SYSTEM_PROMPT

        # TODO: 你写 — 加载 soul.md 拼入 system prompt
        # 提示: from config.settings import get_soul
        #       如果有 soul 内容，拼在前面:
        #       full_prompt = soul + "\n\n" + full_prompt
        from config.settings import get_soul

        soul = get_soul()
        if soul:
            full_prompt += f"\n\n## 桌宠灵魂\n{soul}"


        if memories:
            full_prompt += f"\n\n## 长期记忆\n{memories}"

        self._stm.add_system(full_prompt)

    def process(self, user_input: str) -> str:
        """接收用户输入，返回助手回复。"""
        self._stm.add_message("user", user_input)
        history = self._stm.get_messages()
        reply = self._llm.chat(history)
        self._stm.add_message("assistant", reply)
        self._ltm.try_summarize(
            self._llm,
            [{"role": "user", "content": user_input},
             {"role": "assistant", "content": reply}],
        )
        return reply

    def process_stream(self, user_input: str):
        """流式版 process，逐个 yield token。流结束自动保存到 stm/ltm。"""
        self._stm.add_message("user", user_input)
        history = self._stm.get_messages()

        full_parts = []
        for token in self._llm.chat_stream(history):
            full_parts.append(token)
            yield token

        reply = "".join(full_parts)
        self._stm.add_message("assistant", reply)
        self._ltm.try_summarize(
            self._llm,
            [{"role": "user", "content": user_input},
             {"role": "assistant", "content": reply}],
        )

    def reset(self):
        self._stm.clear()
        self._ltm.reset_counter()
        self._setup_system_prompt()
