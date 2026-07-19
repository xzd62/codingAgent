from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "notes.db"


class NoteStore:
    def __init__(self, db_path: str | Path = ""):
        db_path = Path(db_path or _DB_PATH)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(db_path), check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        self._db.executescript("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workdir TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT '',
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)
        self._db.commit()

    def _auto_title(self, content: str) -> str:
        first_line = content.strip().split("\n")[0]
        return first_line[:30] if first_line else "未命名笔记"

    def create(self, content: str, title: str = "") -> int:
        from config.settings import get_work_dir
        workdir = str(get_work_dir())
        now = datetime.now().isoformat()
        if not title:
            title = self._auto_title(content)
        cur = self._db.execute(
            "INSERT INTO notes (workdir, title, content, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (workdir, title.strip(), content, now, now),
        )
        self._db.commit()
        return cur.lastrowid

    def list(self, limit: int = 50) -> list[dict]:
        from config.settings import get_work_dir
        workdir = str(get_work_dir())
        rows = self._db.execute(
            "SELECT id, title, content, created_at, updated_at FROM notes WHERE workdir=? ORDER BY updated_at DESC LIMIT ?",
            (workdir, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def get(self, note_id: int) -> dict | None:
        row = self._db.execute(
            "SELECT id, title, content, created_at, updated_at FROM notes WHERE id=?",
            (note_id,),
        ).fetchone()
        return dict(row) if row else None

    def update(self, note_id: int, title: str, content: str):
        now = datetime.now().isoformat()
        self._db.execute(
            "UPDATE notes SET title=?, content=?, updated_at=? WHERE id=?",
            (title.strip(), content, now, note_id),
        )
        self._db.commit()

    def delete(self, note_id: int):
        self._db.execute("DELETE FROM notes WHERE id=?", (note_id,))
        self._db.commit()

    def search(self, keyword: str, limit: int = 20) -> list[dict]:
        from config.settings import get_work_dir
        workdir = str(get_work_dir())
        like = f"%{keyword}%"
        rows = self._db.execute(
            "SELECT id, title, content, created_at FROM notes WHERE workdir=? AND (title LIKE ? OR content LIKE ?) ORDER BY updated_at DESC LIMIT ?",
            (workdir, like, like, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self):
        self._db.close()
