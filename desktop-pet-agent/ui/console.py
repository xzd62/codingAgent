import threading
import tkinter as tk
from tkinter import ttk

from agent.core import Agent


class ConsoleWindow:
    """控制台窗口：宠物头像 + 对话界面。"""

    WIDTH = 420
    HEIGHT = 560
    PET_SIZE = 120

    def __init__(self, agent: Agent):
        self._agent = agent
        self._agent._on_status = self._append_status

        self._root = tk.Tk()
        self._root.title("CodePet")
        self._root.geometry(f"{self.WIDTH}x{self.HEIGHT}")
        self._root.resizable(False, False)
        self._root.protocol("WM_DELETE_WINDOW", self._hide)

        self._build_ui()
        self._root.withdraw()

    # ------------------------------------------------------------------
    # UI 构建
    # ------------------------------------------------------------------

    def _build_ui(self):
        self._root.columnconfigure(0, weight=1)
        self._root.rowconfigure(1, weight=1)

        # --- 宠物头像区域 ---
        pet_frame = ttk.Frame(self._root, padding=10)
        pet_frame.grid(row=0, column=0, sticky="ew")
        self._canvas = tk.Canvas(pet_frame, width=self.PET_SIZE, height=self.PET_SIZE + 10,
                                 highlightthickness=0, bg="#f0f0f0")
        self._canvas.pack()
        self._draw_pet()

        # --- 对话显示区域 ---
        chat_frame = ttk.Frame(self._root, padding=(10, 0, 10, 10))
        chat_frame.grid(row=1, column=0, sticky="nsew")
        chat_frame.columnconfigure(0, weight=1)
        chat_frame.rowconfigure(0, weight=1)

        self._chat_display = tk.Text(chat_frame, wrap="word", state="disabled",
                                     font=("Microsoft YaHei", 10), bg="white",
                                     relief="flat", borderwidth=1)
        self._chat_display.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(chat_frame, orient="vertical", command=self._chat_display.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self._chat_display.configure(yscrollcommand=scrollbar.set)

        # --- 输入区域 ---
        input_frame = ttk.Frame(self._root, padding=(10, 0, 10, 10))
        input_frame.grid(row=2, column=0, sticky="ew")
        input_frame.columnconfigure(0, weight=1)

        self._input_var = tk.StringVar()
        input_entry = ttk.Entry(input_frame, textvariable=self._input_var)
        input_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        input_entry.bind("<Return>", self._on_send)

        send_btn = ttk.Button(input_frame, text="发送", command=self._on_send)
        send_btn.grid(row=0, column=1)

    def _draw_pet(self):
        c = self._canvas
        cx, cy = self.PET_SIZE // 2, self.PET_SIZE // 2 + 4
        r = self.PET_SIZE // 4

        # 脸
        c.create_oval(cx - r, cy - r + 4, cx + r, cy + r + 4, fill="#FFB347", outline="")

        # 耳朵
        ear_color = "#FF9F43"
        c.create_polygon(cx - r + 4, cy - r + 4, cx - r - 6, cy - r - 10, cx - r + 18, cy - r + 6, fill=ear_color, outline="")
        c.create_polygon(cx + r - 4, cy - r + 4, cx + r + 6, cy - r - 10, cx + r - 18, cy - r + 6, fill=ear_color, outline="")
        # 内耳
        inner_ear = "#FFB8B8"
        c.create_polygon(cx - r + 8, cy - r + 4, cx - r - 2, cy - r - 6, cx - r + 14, cy - r + 6, fill=inner_ear, outline="")
        c.create_polygon(cx + r - 8, cy - r + 4, cx + r + 2, cy - r - 6, cx + r - 14, cy - r + 6, fill=inner_ear, outline="")

        # 眼睛
        eye_r = 4
        c.create_oval(cx - 10 - eye_r, cy - 2, cx - 10 + eye_r, cy + 6, fill="#333", outline="")
        c.create_oval(cx + 10 - eye_r, cy - 2, cx + 10 + eye_r, cy + 6, fill="#333", outline="")
        c.create_oval(cx - 10 - 1, cy, cx - 10 + 1, cy + 3, fill="white", outline="")
        c.create_oval(cx + 10 - 1, cy, cx + 10 + 1, cy + 3, fill="white", outline="")

        # 鼻子
        c.create_polygon(cx - 3, cy + 7, cx + 3, cy + 7, cx, cy + 11, fill="#FF6B6B", outline="")

        # 嘴巴
        c.create_arc(cx - 8, cy + 10, cx - 1, cy + 18, start=0, extent=180, fill="", outline="#555", width=1)
        c.create_arc(cx + 1, cy + 10, cx + 8, cy + 18, start=0, extent=180, fill="", outline="#555", width=1)

        # 胡须
        whisker_color = "#888"
        for side in [-1, 1]:
            dx = side * 6
            c.create_line(cx + dx, cy + 8, cx + side * 28, cy + 4, fill=whisker_color, width=1)
            c.create_line(cx + dx, cy + 10, cx + side * 28, cy + 10, fill=whisker_color, width=1)
            c.create_line(cx + dx, cy + 12, cx + side * 28, cy + 16, fill=whisker_color, width=1)

    # ------------------------------------------------------------------
    # 逻辑
    # ------------------------------------------------------------------

    def _on_send(self, event=None):
        user_text = self._input_var.get().strip()
        if not user_text:
            return
        self._input_var.set("")

        self._append_message("你", user_text, "#666")

        def worker():
            try:
                reply = self._agent.process(user_text)
                self._root.after(0, self._show_reply, reply)
            except Exception as e:
                self._root.after(0, self._show_stream_error, str(e))

        threading.Thread(target=worker, daemon=True).start()

    def _show_reply(self, text: str):
        self._chat_display.configure(state="normal")
        self._chat_display.insert("end", f"\nCodePet：{text}\n")
        self._chat_display.see("end")
        self._chat_display.configure(state="disabled")

    def _show_stream_error(self, msg: str):
        self._chat_display.configure(state="normal")
        self._chat_display.insert("end", f"\n（出错了：{msg}）\n")
        self._chat_display.see("end")
        self._chat_display.configure(state="disabled")

    def _append_status(self, msg: str):
        self._chat_display.configure(state="normal")
        self._chat_display.insert("end", f"\n  · {msg}")
        self._chat_display.tag_configure("status", foreground="#999", font=("Microsoft YaHei", 9, "italic"))
        self._chat_display.tag_add("status", "end-2l", "end-1l")
        self._chat_display.see("end")
        self._chat_display.configure(state="disabled")

    def _append_message(self, sender: str, text: str, color: str):
        self._chat_display.configure(state="normal")
        self._chat_display.insert("end", f"\n{sender}：", ("sender",))
        self._chat_display.insert("end", f"{text}\n")
        self._chat_display.tag_configure("sender", foreground=color, font=("Microsoft YaHei", 10, "bold"))
        self._chat_display.see("end")
        self._chat_display.configure(state="disabled")

    # ------------------------------------------------------------------
    # 窗口生命周期
    # ------------------------------------------------------------------

    def _hide(self):
        self._root.withdraw()

    def show(self):
        self._root.deiconify()
        self._root.lift()

    def run(self):
        self._root.mainloop()

    def quit(self):
        self._root.destroy()
