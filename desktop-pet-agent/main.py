"""入口：初始化各模块，启动桌面 UI。"""

from pathlib import Path

from config.settings import set_work_dir

set_work_dir(Path(__file__).resolve().parent)

import tool.read_file
import tool.write_file
import tool.glob
import tool.grep
import tool.edit_file
import tool.bash
import tool.verify
import tool.web_fetch
import tool.mcp_client

from ui.webui import run


def main():
    tool.mcp_client.init()
    run()


if __name__ == "__main__":
    main()
