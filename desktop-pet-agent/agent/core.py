"""Agent 调度层：ReAct 模式，串联 llm / stm / ltm。"""

import json

from config.settings import SYSTEM_PROMPT
from llm.client import LLMClient
from ltm.store import MemoryStore
from stm.context import SessionContext
from tool.registry import registry


class Agent:
    """Agent 调度层。 """

    def __init__(self, llm: LLMClient, stm: SessionContext, ltm: MemoryStore,
                 on_status: callable | None = None):
        self._llm = llm
        self._stm = stm
        self._ltm = ltm
        self._on_status = on_status or (lambda msg: None)
        self._setup_system_prompt()

    def _setup_system_prompt(self):
        memories = self._ltm.load()
        full_prompt = SYSTEM_PROMPT

        from config.settings import get_soul

        soul = get_soul()
        if soul:
            full_prompt += f"\n\n## 桌宠灵魂\n{soul}"


        if memories:
            full_prompt += f"\n\n## 长期记忆\n{memories}"

        self._stm.add_system(full_prompt)

    def process(self, user_input: str) -> str:
        self._stm.add_message(role="user",content=user_input)
        tools = registry.get_schemas()
        
        while True:
            self._on_status("思考中…")
            history = self._stm.get_messages()
            reply = self._llm.chat(history, tools)

            if reply.get("tool_calls"):
                self._stm.add_message("assistant", reply.get("content") or "",
                                      tool_calls=reply["tool_calls"])
                for tc in reply["tool_calls"]:
                    name = tc["function"]["name"]
                    args = json.loads(tc["function"]["arguments"])
                    self._on_status(f"调用工具 {name}…")
                    obs = registry.dispatch(name, args)
                    got = str(obs.get("content", ""))[:80] if obs.get("success") else str(obs)
                    self._on_status(f"工具返回: {got}")
                    self._stm.add_message("tool", json.dumps(obs, ensure_ascii=False),
                                          tool_call_id=tc["id"])
                continue 

            text = reply["content"] or ""

            # 兼容处理：LLM 用 <tool_name>...</tool_name> 文字模拟调工具时，手动解析执行
            import re
            parsed = False
            for tname in ("read_file", "write_file", "glob"):
                pattern = rf"<{tname}>(.*?)</{tname}>"
                match = re.search(pattern, text, re.DOTALL)
                if match:
                    args_raw = match.group(1).strip()
                    try:
                        args = json.loads(args_raw) if args_raw.startswith("{") else {"path": args_raw}
                    except json.JSONDecodeError:
                        args = {"path": args_raw}
                    self._on_status(f"调用工具 {tname}…")
                    obs = registry.dispatch(tname, args)
                    got = str(obs.get("content", ""))[:80] if obs.get("success") else str(obs)
                    self._on_status(f"工具返回: {got}")
                    self._stm.add_message("assistant", text)
                    self._stm.add_message("tool", json.dumps(obs, ensure_ascii=False),
                                          tool_call_id=tname)
                    parsed = True
                    break
            if parsed:
                continue

            self._stm.add_message("assistant", text)
            self._ltm.try_summarize(
                self._llm,
                [{"role": "user", "content": user_input},
                 {"role": "assistant", "content": text}],
                )       
            return text

    def process_stream(self, user_input: str):
        self._on_status("思考中…")
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
