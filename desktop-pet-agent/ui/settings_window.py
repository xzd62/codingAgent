"""可视化设置面板 — 灵魂、头像、TTS（预留）。"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

from config.settings import get_soul, set_soul, get_avatar_path, set_avatar_path


class SettingsWindow:
    WIDTH = 520
    HEIGHT = 480

    def __init__(self, parent: tk.Tk):
        self._win = tk.Toplevel(parent)
        self._win.title("CodePet 设置")
        self._win.geometry(f"{self.WIDTH}x{self.HEIGHT}")
        self._win.resizable(False, False)
        self._win.protocol("WM_DELETE_WINDOW", self._win.withdraw)

        self._build_ui()
        self._win.withdraw()

    def _build_ui(self):
        # 主区域: notebook 填充
        notebook = ttk.Notebook(self._win)
        notebook.pack(fill="both", expand=True, padx=10, pady=(10, 10))

        self._build_soul_tab(notebook)
        self._build_avatar_tab(notebook)
        self._build_tts_tab(notebook)

    def _build_soul_tab(self, notebook: ttk.Notebook):
        frame = ttk.Frame(notebook, padding=10)
        notebook.add(frame, text="灵魂")
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        ttk.Label(frame, text="人格设定（soul）— 修改后需要重启对话生效",
                  font=("Microsoft YaHei", 9)).grid(row=0, column=0, sticky="w")

        text_frame = ttk.Frame(frame)
        text_frame.grid(row=1, column=0, sticky="nsew", pady=(6, 0))
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

        self._soul_text = tk.Text(text_frame, wrap="word", font=("Microsoft YaHei", 10),
                                  relief="flat", borderwidth=1, height=12)
        self._soul_text.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self._soul_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self._soul_text.configure(yscrollcommand=scrollbar.set)

        self._soul_text.insert("1.0", get_soul())

        ttk.Label(frame, text="留空 = 默认性格  ·  支持 Markdown 格式",
                  font=("Microsoft YaHei", 8), foreground="gray").grid(row=2, column=0, sticky="w", pady=(4, 0))

        self._save_btn = tk.Button(
            frame, text="保存灵魂设定", command=self._save_soul,
            bg="#FF9F43", fg="white", font=("Microsoft YaHei", 10, "bold"),
            relief="raised", padx=16, pady=2, cursor="hand2",
        )
        self._save_btn.grid(row=3, column=0, sticky="e", pady=(6, 0))

    def _build_avatar_tab(self, notebook: ttk.Notebook):
        frame = ttk.Frame(notebook, padding=10)
        notebook.add(frame, text="头像")

        ttk.Label(frame, text="自定义桌宠头像（支持 .png / .jpg）", font=("Microsoft YaHei", 9)).pack(anchor="w")

        path_frame = ttk.Frame(frame)
        path_frame.pack(fill="x", pady=(10, 0))

        self._avatar_var = tk.StringVar(value=get_avatar_path() or "")
        avatar_entry = ttk.Entry(path_frame, textvariable=self._avatar_var, state="readonly")
        avatar_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        ttk.Button(path_frame, text="选择图片", command=self._choose_avatar).pack(side="right")
        ttk.Button(path_frame, text="清除", command=self._clear_avatar).pack(side="right", padx=(0, 4))

        preview_frame = ttk.LabelFrame(frame, text="预览", padding=10)
        preview_frame.pack(fill="both", expand=True, pady=(10, 0))
        self._preview_label = ttk.Label(preview_frame, text="未选择图片")
        self._preview_label.pack(expand=True)

        self._refresh_preview()

    def _build_tts_tab(self, notebook: ttk.Notebook):
        frame = ttk.Frame(notebook, padding=10)
        notebook.add(frame, text="语音（TTS）")

        ttk.Label(frame, text="语音合成功能开发中…", font=("Microsoft YaHei", 9),
                  foreground="gray").pack(expand=True)

    def _save_soul(self):
        text = self._soul_text.get("1.0", "end-1c").strip()
        set_soul(text)
        messagebox.showinfo("已保存", "灵魂设定已保存，重启对话后生效。", parent=self._win)

    def _choose_avatar(self):
        path = filedialog.askopenfilename(
            title="选择头像图片",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.gif *.bmp")],
            parent=self._win,
        )
        if path:
            self._avatar_var.set(path)
            set_avatar_path(path)
            self._refresh_preview()

    def _clear_avatar(self):
        self._avatar_var.set("")
        set_avatar_path(None)
        self._refresh_preview()

    def _refresh_preview(self):
        path = self._avatar_var.get()
        if path and Path(path).exists():
            try:
                from PIL import Image, ImageTk
                img = Image.open(path)
                img.thumbnail((120, 120))
                photo = ImageTk.PhotoImage(img)
                self._preview_label.config(image=photo, text="")
                self._preview_label.image = photo
            except Exception:
                self._preview_label.config(image="", text="无法加载图片")
        else:
            self._preview_label.config(image="", text="未选择图片")

    def show(self):
        self._win.deiconify()
        self._win.lift()
