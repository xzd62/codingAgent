"""入口：初始化各模块，启动系统托盘 + 控制台。"""

import threading

from agent.core import Agent
from llm.client import LLMClient
from ltm.store import MemoryStore
from stm.context import SessionContext
from ui.console import ConsoleWindow
from ui.settings_window import SettingsWindow
from ui.tray import TrayApp


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
