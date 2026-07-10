import base64
import json
import threading
from pathlib import Path

import webview

from agent.core import Agent
from config.settings import get_soul, set_soul, get_avatar_path, set_avatar_path, get_llm_model, set_llm_model, get_llm_api_key, set_llm_api_key, get_work_dir, set_work_dir
from llm.client import LLMClient
from ltm.store import MemoryStore
from stm.context import SessionContext
from stm.manager import SessionManager
from ui.tray import TrayApp
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

    def _init_engine(self):
        self._llm = LLMClient()
        self._stm = SessionContext(llm_client=self._llm)
        self._ltm = MemoryStore()
        self._agent = Agent(llm=self._llm, stm=self._stm, ltm=self._ltm,
                            on_status=self._push_status)
        self._session_mgr = SessionManager()
        self._session_mgr.ensure_session(self._stm)

    def _push_status(self, text: str):
        self._status_queue.append(text)

    def get_status_updates(self) -> str:
        items = list(self._status_queue)
        self._status_queue[:] = [x for x in items if x.startswith("__")]
        plain = [x for x in items if not x.startswith("__")]
        return json.dumps(plain, ensure_ascii=False)

    def check_reply(self) -> str:
        for item in self._status_queue:
            if item.startswith("__REPLY__:"):
                self._status_queue.clear()
                return item[9:]
            if item.startswith("__ERROR__:"):
                self._status_queue.clear()
                return f"__ERROR__:{item[9:]}"
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
            reply = reply.lstrip("：:")
            self._status_queue.append(f"__REPLY__:{reply}")
            if reply and self._stm.get_token_info()["pct"] >= 80:
                self._auto_compress()
        except Exception as e:
            self._status_queue.append(f"__ERROR__:{e}")

    def _auto_compress(self):
        info = self._stm.get_token_info()
        self._push_status(f"上下文已达 {info['tokens']}K ({info['pct']}%)，正在压缩…")
        try:
            msgs = self._stm.get_messages(include_status=True)
            to_c = [m for m in msgs if m.get("role") != "system"]
            if not to_c:
                return
            text = "\n".join(f"[{m['role']}] {m.get('content','')}" for m in to_c)
            from ltm.prompts import COMPRESS_PROMPT
            result = self._llm.chat([
                {"role": "system", "content": COMPRESS_PROMPT},
                {"role": "user", "content": text},
            ])
            st = result.get("content") or "(压缩完成)"
            sys_m = [m for m in msgs if m.get("role") == "system"]
            self._stm.load_messages(sys_m)
            self._stm.add_message("system", f"[对话摘要] {st}")
            cid = self._session_mgr.get_current_id()
            if cid:
                self._save_conv(conv_id=cid)
            aft = self._stm.get_token_info()
            self._push_status(f"压缩完成: {info['tokens']}K -> {aft['tokens']}K")
        except Exception as e:
            self._push_status(f"压缩失败: {e}")

    def _save_conv(self, conv_id: int = 0):
        cid = conv_id or self._session_mgr.get_current_id()
        if cid:
            msgs = self._stm.get_messages(include_status=True)
            self._session_mgr.save_messages(cid, msgs)

    def get_token_info(self) -> str:
        return json.dumps(self._stm.get_token_info())

    def compress_now(self):
        self._auto_compress()

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
        return str(get_work_dir())

    def rename_conv(self, conv_id: int, name: str):
        self._session_mgr.rename_conversation(conv_id, name)

    def get_soul(self) -> str:
        return get_soul()

    def save_soul(self, text: str):
        set_soul(text)

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


def _start_tray():
    tray = TrayApp(
        on_open=lambda: None,
        on_exit=lambda: _quit(),
    )
    tray.run()


def _quit():
    import os
    os._exit(0)


def run():
    srcdir = Path(__file__).resolve().parent.parent / "web"
    set_work_dir(srcdir.parent)

    webview.create_window(
        "CodePet",
        str(srcdir / "index.html"),
        width=1280,
        height=800,
        resizable=True,
        js_api=Api(),
    )
    webview.start(debug=False)


if __name__ == "__main__":
    run()
