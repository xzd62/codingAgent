"""Agent 调度层：ReAct 模式，串联 llm / stm / ltm。"""

import json

from config.settings import SYSTEM_PROMPT, RESPONSE_PROMPT
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
        full_prompt = SYSTEM_PROMPT + "\n\n" + RESPONSE_PROMPT

        from config.settings import get_soul, get_rules

        rules = get_rules()
        if rules:
            full_prompt += f"\n\n## 用户规则\n{rules}"

        soul = get_soul()
        if soul:
            full_prompt += f"\n\n## 桌宠灵魂\n{soul}"

        from skill.registry import get_registry
        reg = get_registry()
        skill_list = reg.list_skills()
        if skill_list:
            lines = [f"- {s['name']}: {s['description']}" for s in skill_list]
            full_prompt += "\n\n### 可用技能\n" + "\n".join(lines)
            full_prompt += "\n\n如需使用某个技能，调用 `load_skill(name=\"技能名\")` 加载详细指引。"

        if memories:
            full_prompt += f"\n\n## 长期记忆\n{memories}"

        self._stm.add_system(full_prompt)
    def process(self, user_input: str) -> str:
        self._stm.add_message(role="user",content=user_input)
        tools = registry.get_schemas()
        first = True

        while True:
            if first:
                self._on_status("思考中…")
                self._stm.add_message("status", "思考中…")
                first = False
            history = self._stm.get_messages()
            reply = self._llm.chat(history, tools)

            if reply.get("tool_calls"):
                content = reply.get("content")
                content_str = content if content else ""
                self._stm.add_message("assistant", content if content else None,
                                      tool_calls=reply["tool_calls"])
                if content_str:
                    self._on_status(f"__TEXT__:{content_str}")
                    self._stm.add_message("status", f"__TEXT__:{content_str}")
                for tc in reply["tool_calls"]:
                    name = tc["function"]["name"]
                    args = json.loads(tc["function"]["arguments"])
                    label = f"-> 调用工具: {name}"
                    if name == "read_file":
                        label += f" {args.get('path', '')}"
                    elif name == "glob":
                        label += f" {args.get('pattern', '')}"
                    elif name == "edit_file":
                        label += f" {args.get('path', '')}"
                    elif name == "grep":
                        gp = args.get('pattern', '')
                        gpath = args.get('path', '')
                        label += f" {gp} in {gpath}" if gpath else f" {gp}"
                    self._on_status(label)
                    self._stm.add_message("status", label)

                    if name == "bash":
                        cmd = f"运行: {args.get('command', '')}"
                        self._on_status(cmd)
                        self._stm.add_message("status", cmd)

                    try:
                        obs = registry.dispatch(name, args)
                    except Exception as e:
                        obs = {"success": False, "error": f"工具执行异常: {e}"}

                    if not obs.get("success", True):
                        self._on_status(f"工具执行失败: {obs.get('error', '未知错误')}")
                        self._stm.add_message("status", f"工具执行失败: {obs.get('error', '未知错误')}")

                    if name == "bash":
                        out = obs.get("output", "")
                        if out:
                            self._on_status(out)
                            self._stm.add_message("status", out)
                    elif name == "write_file":
                        wp = f"写入: {args.get('path', '')}"
                        self._on_status(wp)
                        self._stm.add_message("status", wp)
                        wc = args.get("content", "")
                        if wc:
                            self._on_status(wc)
                            self._stm.add_message("status", wc)
                        if args["path"].endswith(".py"):
                            vr = registry.dispatch('verify', {'path': args['path']})
                            if vr.get("valid") == False:
                                obs["verify_error"] = vr.get("error", "")
                                self._on_status(f"语法错误: {vr.get('error', '')}")
                                self._stm.add_message("status", f"语法错误: {vr.get('error', '')}")


                    elif name == "glob":
                        cnt = len(obs.get("files", []))
                        self._on_status(f"({cnt}个匹配)")
                        self._stm.add_message("status", f"({cnt}个匹配)")
                    elif name == "grep":
                        cnt = len(obs.get("matches", []))
                        self._on_status(f"（{cnt}个匹配）")
                        self._stm.add_message("status", f"（{cnt}个匹配）")

                    self._stm.add_message("tool", json.dumps(obs, ensure_ascii=False),
                                          tool_call_id=tc["id"])
                continue 

            text = reply["content"] or ""

            import re
            parsed = False
            for tname in ("read_file", "write_file", "glob", "grep", "edit_file", "bash", "verify"):
                pattern = rf"<{tname}>(.*?)</{tname}>"
                match = re.search(pattern, text, re.DOTALL)
                if match:
                    args_raw = match.group(1).strip()
                    try:
                        args = json.loads(args_raw) if args_raw.startswith("{") else {"path": args_raw}
                    except json.JSONDecodeError:
                        args = {"path": args_raw}
                    label = f"-> 调用工具: {tname}"
                    if tname == "read_file":
                        label += f" {args.get('path', '')}"
                    elif tname == "glob":
                        label += f" {args.get('pattern', '')}"
                    self._on_status(label)
                    self._stm.add_message("status", label)
                    if tname == "bash":
                        cmd = f"运行: {args.get('command', '')}"
                        self._on_status(cmd)
                        self._stm.add_message("status", cmd)
                    obs = registry.dispatch(tname, args)
                    if tname == "bash":
                        out = obs.get("output", "")
                        if out:
                            self._on_status(out)
                            self._stm.add_message("status", out)
                    elif tname == "write_file":
                        wp = f"写入: {args.get('path', '')}"
                        self._on_status(wp)
                        self._stm.add_message("status", wp)
                        wc = args.get("content", "")
                        if wc:
                            self._on_status(wc)
                    elif tname == "glob":
                        cnt = len(obs.get("files", []))
                        self._on_status(f"({cnt}个匹配)")
                        self._stm.add_message("status", f"({cnt}个匹配)")
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
