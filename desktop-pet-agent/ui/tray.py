import tkinter as tk
from tkinter import filedialog
from pathlib import Path

import pystray
from PIL import Image, ImageDraw

from config.settings import get_work_dir, set_work_dir


def _create_icon_image(size: int = 64):
    """画一个简化版猫脸作为托盘图标。"""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx = cy = size // 2
    r = size // 3

    # 脸（圆形）
    draw.ellipse([cx - r, cy - r + 4, cx + r, cy + r + 4], fill=(255, 179, 71))

    # 耳朵（两个三角形）
    ear_color = (255, 159, 67)
    draw.polygon([(cx - r + 4, cy - r + 4), (cx - r - 4, cy - r - 8), (cx - r + 16, cy - r + 4)], fill=ear_color)
    draw.polygon([(cx + r - 4, cy - r + 4), (cx + r + 4, cy - r - 8), (cx + r - 16, cy - r + 4)], fill=ear_color)

    # 眼睛
    eye_color = (51, 51, 51)
    draw.ellipse([cx - 8, cy - 2, cx - 3, cy + 4], fill=eye_color)
    draw.ellipse([cx + 3, cy - 2, cx + 8, cy + 4], fill=eye_color)

    # 鼻子
    draw.polygon([(cx - 2, cy + 6), (cx + 2, cy + 6), (cx, cy + 9)], fill=(255, 107, 107))

    # 嘴巴
    draw.arc([cx - 6, cy + 8, cx, cy + 14], start=0, end=180, fill=(85, 85, 85), width=1)
    draw.arc([cx, cy + 8, cx + 6, cy + 14], start=0, end=180, fill=(85, 85, 85), width=1)

    return img


class TrayApp:
    """系统托盘图标（负责生命周期，不负责 UI 逻辑）。"""

    def __init__(self, on_open: callable, on_settings: callable, on_exit: callable, on_select_workdir: callable | None = None):
        self._on_open = on_open
        self._on_settings = on_settings
        self._on_exit = on_exit
        self._on_select_workdir = on_select_workdir or self._choose_workdir
        self._icon: pystray.Icon | None = None

    @staticmethod
    def _choose_workdir():
        root = tk.Tk()
        root.withdraw()
        path = filedialog.askdirectory(
            title="选择工作目录",
            initialdir=str(get_work_dir()),
        )
        root.destroy()
        if path:
            set_work_dir(Path(path))

    def run(self):
        menu = pystray.Menu(
            pystray.MenuItem("打开控制台", self._on_open),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("设置", self._on_settings),
            pystray.MenuItem("选择工作目录", self._on_select_workdir),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", self._on_exit),
        )
        image = _create_icon_image(64)
        self._icon = pystray.Icon("codepet", image, "CodePet", menu)
        self._icon.run()

    def stop(self):
        if self._icon:
            self._icon.stop()
