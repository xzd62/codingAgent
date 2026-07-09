import threading
import json
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

    def _init_engine(self):
        self._llm = LLMClient()
        self._stm = SessionContext(llm_client=self._llm)
        self._ltm = MemoryStore()
        self._agent = Agent(llm=self._llm, stm=self._stm, ltm=self._ltm)
        self._session_mgr = SessionManager()
        self._session_mgr.ensure_session(self._stm)

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
        msgs = self._stm.get_messages()
        return json.dumps(msgs, ensure_ascii=False)

    # ---- 对话 ----

    def send(self, text: str) -> str:
        try:
            reply = self._agent.process(text)
            conv_id = self._session_mgr.get_current_id()
            if conv_id:
                self._session_mgr.save_messages(conv_id, self._stm.get_messages())
            return reply
        except Exception as e:
            return f"（出错了：{e}）"

    # ---- 设置 ----

    def get_soul(self) -> str:
        return get_soul()

    def save_soul(self, text: str):
        set_soul(text)

    def get_avatar(self) -> str:
        return get_avatar_path() or ""

    def pick_avatar(self) -> str:
        for win in webview.windows:
            file_types = ("图片文件", "*.png;*.jpg;*.jpeg;*.gif;*.bmp")
            result = win.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=False, file_types=[file_types])
            if result:
                path = result[0]
                set_avatar_path(path)
                return path
        return ""

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
