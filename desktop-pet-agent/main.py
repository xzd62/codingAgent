"""入口：初始化各模块，启动系统托盘 + 控制台。"""

import threading
from pathlib import Path

from config.settings import set_work_dir

# 默认工作目录设为 main.py 所在目录
set_work_dir(Path(__file__).resolve().parent)

from agent.core import Agent
from llm.client import LLMClient
from ltm.store import MemoryStore
from stm.context import SessionContext
from ui.console import ConsoleWindow
from ui.settings_window import SettingsWindow
from ui.tray import TrayApp

# 加载并注册所有工具
import tool.read_file
import tool.write_file
import tool.glob
import tool.grep
import tool.edit_file
import tool.bash


def main():
    llm = LLMClient()
    stm = SessionContext(llm_client=llm)
    ltm = MemoryStore()
    agent = Agent(llm=llm, stm=stm, ltm=ltm)

    console = ConsoleWindow(agent)
    settings = SettingsWindow(console._root)

    def on_open():
        console.show()

    def on_settings():
        settings.show()

    def on_exit():
        console.quit()
        tray.stop()

    tray = TrayApp(on_open=on_open, on_settings=on_settings, on_exit=on_exit)

    threading.Thread(target=tray.run, daemon=True).start()

    console.run()


if __name__ == "__main__":
    main()
