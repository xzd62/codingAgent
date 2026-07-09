"""会话管理器 — SQLite 持久化，按工作目录隔离。"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from config.settings import get_work_dir
from stm.context import SessionContext


_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "sessions.db"


class SessionManager:
    def __init__(self, db_path: str | Path = ""):
        db_path = Path(db_path or _DB_PATH)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(db_path), check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._init_db()
        self._current_id: int | None = None

    def _init_db(self):
        self._db.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workdir TEXT NOT NULL,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT,
                tool_calls TEXT,
                tool_call_id TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            );
        """)
        self._db.commit()

    # ------------------------------------------------------------------
    # 会话列表
    # ------------------------------------------------------------------

    def list_conversations(self) -> list[dict]:
        workdir = str(get_work_dir())
        rows = self._db.execute(
            "SELECT id, name, created_at FROM conversations WHERE workdir=? ORDER BY id DESC",
            (workdir,),
        ).fetchall()
        return [dict(r) for r in rows]

    def create_conversation(self, name: str = "") -> int:
        workdir = str(get_work_dir())
        if not name:
            now = datetime.now().strftime("%m-%d %H:%M")
            name = f"对话 {now}"
        cur = self._db.execute(
            "INSERT INTO conversations (workdir, name, created_at) VALUES (?, ?, ?)",
            (workdir, name, datetime.now().isoformat()),
        )
        self._db.commit()
        return cur.lastrowid

    def rename_conversation(self, conv_id: int, name: str):
        self._db.execute("UPDATE conversations SET name=? WHERE id=?", (name, conv_id))
        self._db.commit()

    def delete_conversation(self, conv_id: int):
        self._db.execute("DELETE FROM messages WHERE conversation_id=?", (conv_id,))
        self._db.execute("DELETE FROM conversations WHERE id=?", (conv_id,))
        self._db.commit()

    # ------------------------------------------------------------------
    # 消息读写
    # ------------------------------------------------------------------

    def save_messages(self, conv_id: int, messages: list[dict]):
        self._db.execute("DELETE FROM messages WHERE conversation_id=?", (conv_id,))
        now = datetime.now().isoformat()
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            tool_calls_json = json.dumps(msg.get("tool_calls")) if msg.get("tool_calls") else None
            tool_call_id = msg.get("tool_call_id")
            self._db.execute(
                "INSERT INTO messages (conversation_id, role, content, tool_calls, tool_call_id, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (conv_id, role, content, tool_calls_json, tool_call_id, now),
            )
        self._db.commit()

    def load_messages(self, conv_id: int) -> list[dict]:
        rows = self._db.execute(
            "SELECT role, content, tool_calls, tool_call_id FROM messages WHERE conversation_id=? ORDER BY id",
            (conv_id,),
        ).fetchall()
        messages = []
        for r in rows:
            msg = {"role": r["role"], "content": r["content"]}
            if r["tool_calls"]:
                msg["tool_calls"] = json.loads(r["tool_calls"])
            if r["tool_call_id"]:
                msg["tool_call_id"] = r["tool_call_id"]
            messages.append(msg)
        return messages

    # ------------------------------------------------------------------
    # 会话切换
    # ------------------------------------------------------------------

    def get_current_id(self) -> int | None:
        return self._current_id

    def ensure_session(self, stm: SessionContext) -> int:
        """确保当前有激活的会话，没有则创建。"""
        if self._current_id is not None:
            return self._current_id
        convs = self.list_conversations()
        if convs:
            self._current_id = convs[0]["id"]
            msgs = self.load_messages(self._current_id)
            stm.load_messages(msgs)
            return self._current_id
        return self.new_session(stm)

    def switch_to(self, conv_id: int, stm: SessionContext):
        """切换到指定会话（先保存当前，再加载目标）。"""
        if self._current_id is not None:
            self.save_messages(self._current_id, stm.get_messages(include_status=True))
        self._current_id = conv_id
        msgs = self.load_messages(conv_id)
        stm.load_messages(msgs)

    def new_session(self, stm: SessionContext) -> int:
        """保存当前对话并创建新对话。"""
        if self._current_id is not None:
            self.save_messages(self._current_id, stm.get_messages(include_status=True))
        conv_id = self.create_conversation()
        self._current_id = conv_id
        stm.clear()
        return conv_id

    def close(self):
        self._db.close()
