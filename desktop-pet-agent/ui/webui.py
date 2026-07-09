import base64
import json
import threading
from pathlib import Path

import webview

from agent.core import Agent
from config.settings import (
    get_soul, set_soul,
    get_avatar_path, set_avatar_path,
    get_llm_model, set_llm_model,
    get_llm_api_key, set_llm_api_key,
    set_work_dir,
)
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
        """JS 轮询：获取新状态消息。"""
        if not self._status_queue:
            return "[]"
        result = json.dumps(list(self._status_queue), ensure_ascii=False)
        self._status_queue.clear()
        return result

    # ---- 会话 ----

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
        return json.dumps(msgs, ensure_ascii=False)

    # ---- 对话 ----

    def send(self, text: str) -> str:
        """同步发送（备用）。"""
        return self._do_send(text)

    def start_stream(self, text: str):
        """非阻塞对话：后台跑 process()，前端轮询状态和最终结果。"""
        self._status_queue.clear()
        threading.Thread(target=self._stream_worker, args=(text,), daemon=True).start()

    def _stream_worker(self, text: str):
        try:
            reply = self._agent.process(text)
            self._save_conv()
            self._status_queue.append(f"__REPLY__:{reply}")
        except Exception as e:
            self._status_queue.append(f"__ERROR__:{e}")

    def _do_send(self, text: str) -> str:
        try:
            reply = self._agent.process(text)
            self._save_conv()
            return reply
        except Exception as e:
            return f"（出错了：{e}）"

    def _stream_worker(self, text: str):
        """后台线程：调 process()，结果通过 status_queue 返回（__REPLY__ / __ERROR__）。"""
        try:
            reply = self._agent.process(text)
            self._save_conv()
            self._status_queue.append(f"__REPLY__:{reply}")
        except Exception as e:
            self._status_queue.append(f"__ERROR__:{e}")

    def _save_conv(self):
        conv_id = self._session_mgr.get_current_id()
        if conv_id:
            self._session_mgr.save_messages(conv_id, self._stm.get_messages())

    # ---- 设置 ----

    def get_soul(self) -> str:
        return get_soul()

    def save_soul(self, text: str):
        set_soul(text)

    def get_avatar(self) -> str:
        return get_avatar_path() or ""

    def pick_avatar(self, path: str):
        set_avatar_path(path)

    def save_avatar_data(self, data_url: str):
        """保存 base64 图片数据到本地文件，返回保存后的路径。"""
        import re
        match = re.match(r"data:image/(\w+);base64,(.+)", data_url)
        if not match:
            return ""
        ext = match.group(1)
        raw = base64.b64decode(match.group(2))
        save_dir = Path(__file__).resolve().parent.parent / "data"
        save_dir.mkdir(parents=True, exist_ok=True)
        save_path = save_dir / f"avatar.{ext}"
        save_path.write_bytes(raw)
        set_avatar_path(str(save_path))
        return str(save_path)

    def get_avatar_data(self) -> str:
        """返回头像图片的 base64 data URL。"""
        path = get_avatar_path()
        if not path or not Path(path).exists():
            return ""
        raw = Path(path).read_bytes()
        ext = Path(path).suffix.lstrip(".") or "png"
        return f"data:image/{ext};base64,{base64.b64encode(raw).decode()}"

    def clear_avatar(self):
        set_avatar_path(None)

    # ---- 模型 ----

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
        on_settings=lambda: None,
        on_exit=lambda: _quit(),
    )
    tray.run()


def _quit():
    import os
    os._exit(0)


def run():
    srcdir = Path(__file__).resolve().parent.parent / "web"
    set_work_dir(srcdir.parent)

    threading.Thread(target=_start_tray, daemon=True).start()

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
