import base64
import json
import threading
from pathlib import Path

import webview

from agent.core import Agent, INTERRUPTED_MARK
from ui.tray import TrayApp
from config.settings import get_soul, set_soul, get_avatar_path, set_avatar_path, get_llm_model, set_llm_model, get_llm_api_key, set_llm_api_key, get_work_dir, set_work_dir, get_rules, set_rules, rules_exist, add_mcp_server
from llm.client import LLMClient
from ltm.store import MemoryStore
from stm.context import SessionContext
from stm.manager import SessionManager

import tool.read_file
import tool.write_file
import tool.glob
import tool.grep
import tool.edit_file
import tool.bash


class Api:
    def __init__(self):
        self._init_engine()
        self._status_queue: list[str] = []
        self._pending_mood: str = ""

    def _init_engine(self):
        self._llm = LLMClient()
        self._stm = SessionContext(llm_client=self._llm)
        self._ltm = MemoryStore()
        self._agent = Agent(llm=self._llm, stm=self._stm, ltm=self._ltm,
                            on_status=self._push_status)
        self._session_mgr = SessionManager()
        self._session_mgr.ensure_session(self._stm)

    def _push_status(self, text: str):
        if text.startswith("__MOOD__:"):
            self._pending_mood = text[9:]
        else:
            self._status_queue.append(text)

    def get_status_updates(self) -> str:
        items = list(self._status_queue)
        self._status_queue[:] = [x for x in items if x.startswith("__") and not x.startswith("__TEXT__:") and not x.startswith("__TOKEN__:") and not x.startswith("__PLAN__:") and not x.startswith("__ASK_USER__:") and not x.startswith("__USER_ANSWER__:")]
        plain = [x for x in items if not x.startswith("__") or x.startswith("__TEXT__:") or x.startswith("__TOKEN__:") or x.startswith("__PLAN__:") or x.startswith("__ASK_USER__:") or x.startswith("__USER_ANSWER__:")]
        return json.dumps(plain, ensure_ascii=False)

    def check_reply(self) -> str:
        for i, item in enumerate(self._status_queue):
            if item.startswith("__REPLY__:"):
                self._status_queue.pop(i)
                return item[10:]
            if item == "__INTERRUPTED__":
                self._status_queue.pop(i)
                return item
            if item.startswith("__ERROR__:"):
                self._status_queue.pop(i)
                return f"__ERROR__:{item[10:]}"
        return ""

    def check_mood(self) -> str:
        m = self._pending_mood
        self._pending_mood = ""
        return m

    def get_mood_image(self, mood: str) -> str:
        """返回表情图片的 data URL。"""
        char_dir = Path(__file__).resolve().parent.parent / "character"
        for name in (mood, "默认"):
            for ext in ("svg", "png", "jpg", "jpeg"):
                p = char_dir / f"{name}.{ext}"
                if p.exists():
                    raw = p.read_bytes()
                    mime = "image/svg+xml" if ext == "svg" else f"image/{ext}"
                    return f"data:{mime};base64,{base64.b64encode(raw).decode()}"
        return ""

    def get_convs(self) -> str:
        convs = self._session_mgr.list_conversations()
        return json.dumps(convs, ensure_ascii=False)

    def switch_conv(self, conv_id: int):
        self._session_mgr.switch_to(conv_id, self._stm)
        self._agent._setup_system_prompt()

    def new_conv(self):
        self._session_mgr.new_session(self._stm)
        self._agent._setup_system_prompt()

    def delete_conv(self, conv_id: int):
        self._session_mgr.delete_conversation(conv_id)
        if self._session_mgr.get_current_id() == conv_id:
            remaining = self._session_mgr.list_conversations()
            if remaining:
                self._session_mgr.switch_to(remaining[0]["id"], self._stm)
            else:
                self._session_mgr.new_session(self._stm)
            self._agent._setup_system_prompt()

    def get_history(self) -> str:
        msgs = self._stm.get_messages(include_status=True)
        if msgs:
            return json.dumps(msgs, ensure_ascii=False)
        conv_id = self._session_mgr.get_current_id()
        if conv_id:
            msgs = self._session_mgr.load_messages(conv_id)
            self._stm.load_messages(msgs)
            return json.dumps(msgs, ensure_ascii=False)
        return "[]"

    def send(self, text: str) -> str:
        try:
            reply = self._agent.process(text)
            self._save_conv()
            return reply
        except Exception as e:
            return f"（出错了：{e}）"

    def start_stream(self, text: str):
        self._status_queue.clear()
        threading.Thread(target=self._stream_worker, args=(text,), daemon=True).start()

    def _stream_worker(self, text: str):
        saved_conv_id = self._session_mgr.get_current_id()
        try:
            reply = self._agent.process(text)
            self._save_conv(conv_id=saved_conv_id)
            if reply == INTERRUPTED_MARK:
                self._stm.add_message("status", "已中断")
                self._status_queue.append("__INTERRUPTED__")
                return
            tu = self._llm.turn_usage
            turn_total = tu["prompt"] + tu["completion"]
            self._session_mgr.add_tokens(saved_conv_id, turn_total)
            self._status_queue.append(f"__TOKEN__:{json.dumps(tu)}")
            reply = reply.lstrip("：:　 \t\n\r")
            import re
            mm = re.search(r"\[(.+?)\]", reply)
            if mm:
                self._pending_mood = mm.group(1).strip("：:")
            self._status_queue.append(f"__REPLY__:{reply}")
        except Exception as e:
            self._status_queue.append(f"__ERROR__:{e}")

    def interrupt(self):
        self._agent.cancel()

    def _save_conv(self, conv_id: int = 0):
        cid = conv_id or self._session_mgr.get_current_id()
        if cid:
            msgs = self._stm.get_messages(include_status=True)
            self._session_mgr.save_messages(cid, msgs)


    def save_pet_size(self, size: int):
        from config.settings import _update_env
        _update_env("PET_SIZE", str(size))

    def get_pet_size(self) -> int:
        import os
        return int(os.getenv("PET_SIZE", "180"))

    def get_workdir(self) -> str:
        return str(get_work_dir())

    def pick_workdir(self) -> str:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        path = filedialog.askdirectory(title="选择工作目录", initialdir=str(get_work_dir()))
        root.destroy()
        if path:
            set_work_dir(path)
            self._agent._setup_system_prompt()
        return str(get_work_dir())

    def rename_conv(self, conv_id: int, name: str):
        self._session_mgr.rename_conversation(conv_id, name)

    def get_soul(self) -> str:
        return get_soul()

    def save_soul(self, text: str):
        set_soul(text)
        self._agent._setup_system_prompt()

    def get_rules(self) -> str:
        return get_rules()

    def save_rules(self, text: str):
        set_rules(text)
        self._agent._setup_system_prompt()

    def rules_exist(self) -> bool:
        return rules_exist()

    def create_rules(self):
        """创建默认规则文件。"""
        default = ""
        set_rules(default)

    def get_avatar(self) -> str:
        return get_avatar_path() or ""

    def pick_avatar(self, path: str):
        set_avatar_path(path)

    def save_avatar_data(self, data_url: str):
        import re
        match = re.match(r"data:image/(\w+);base64,(.+)", data_url)
        if not match:
            return ""
        ext = match.group(1)
        raw = base64.b64decode(match.group(2))
        save_dir = Path(__file__).resolve().parent.parent / "character"
        save_dir.mkdir(parents=True, exist_ok=True)
        save_path = save_dir / f"default.{ext}"
        save_path.write_bytes(raw)
        set_avatar_path(str(save_path))

    def get_avatar_data(self) -> str:
        path = get_avatar_path()
        if not path or not Path(path).exists():
            return ""
        raw = Path(path).read_bytes()
        ext = Path(path).suffix.lstrip(".") or "png"
        return f"data:image/{ext};base64,{base64.b64encode(raw).decode()}"

    def clear_avatar(self):
        set_avatar_path(None)

    def get_model(self) -> str:
        return get_llm_model()

    def set_model(self, name: str):
        set_llm_model(name)
        for win in webview.windows:
            if win:
                api = win._js_api
                if api and api._llm:
                    api._llm.refresh()
                break

    def get_apikey(self) -> str:
        k = get_llm_api_key()
        return k[:8] + "••••" + k[-4:] if len(k) > 12 else ""

    def save_apikey(self, key: str):
        set_llm_api_key(key)
        for win in webview.windows:
            if win:
                api = win._js_api
                if api and api._llm:
                    api._llm.refresh()
                break

    def get_mcp_status(self) -> str:
        import tool.mcp_client
        return json.dumps(tool.mcp_client.get_status(), ensure_ascii=False)

    def remove_mcp_server(self, name: str):
        import tool.mcp_client
        tool.mcp_client.remove(name)

    def reconnect_mcp_server(self, name: str) -> bool:
        import tool.mcp_client
        return tool.mcp_client.reconnect(name)

    def add_mcp_server(self, name: str, command: str, args: str):
        import json
        args_list = json.loads(args) if args else []
        add_mcp_server(name, command, args_list)
        import tool.mcp_client
        tool.mcp_client.init()

    def get_skills(self) -> str:
        from skill.registry import get_registry
        return json.dumps(get_registry().list_skills(), ensure_ascii=False)

    def toggle_skill(self, name: str, enabled: bool):
        from skill.registry import get_registry
        reg = get_registry()
        if enabled:
            reg.enable(name)
        else:
            reg.disable(name)
        self._agent._setup_system_prompt()

    def get_skill_detail(self, name: str) -> str:
        from skill.registry import get_registry
        skill = get_registry().get_skill(name)
        if skill:
            return skill.prompt
        return ""

    def create_skill(self, name: str, description: str):
        from skill.registry import get_registry
        get_registry().create_skill(name, description)
        self._agent._setup_system_prompt()

    def delete_skill(self, name: str):
        from skill.registry import get_registry
        get_registry().delete_skill(name)
        self._agent._setup_system_prompt()

    def save_skill(self, name: str, content: str):
        from skill.registry import get_registry
        get_registry().save_skill(name, content)
        self._agent._setup_system_prompt()

    def get_mode(self) -> str:
        return self._agent._mode

    def set_mode(self, mode: str):
        self._agent.set_mode(mode)

    def get_conv_total_tokens(self, conv_id: int) -> int:
        return self._session_mgr.get_tokens(conv_id)

    def answer_question(self, text: str):
        from agent import question
        question.answer(text)


def _start_tray(window):
    def on_open():
        window.show()
        window.restore()

    def on_exit():
        import os
        os._exit(0)

    tray = TrayApp(on_open=on_open, on_exit=on_exit)
    tray.run()


def run():
    srcdir = Path(__file__).resolve().parent.parent / "web"
    set_work_dir(srcdir.parent)

    api = Api()
    window = webview.create_window(
        "CodePet",
        str(srcdir / "index.html"),
        width=1280,
        height=800,
        resizable=True,
        js_api=api,
        confirm_close=True,
    )

    window.events.closing += api._save_conv

    threading.Thread(target=_start_tray, args=(window,), daemon=True).start()
    webview.start(debug=False)


if __name__ == "__main__":
    run()
