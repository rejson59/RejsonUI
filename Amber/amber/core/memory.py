"""Pamięć długotrwała Amber (SQLite).

Przechowuje:
  * profil użytkownika (klucz -> wartość),
  * wspomnienia (ważne informacje o użytkowniku i otoczeniu),
  * dziennik wykonanych akcji,
  * historię rozmów.
"""
from __future__ import annotations

import os
import sqlite3
import threading
import time
from typing import Any


class Memory:
    def __init__(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.path = path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    # ---------- init ----------
    def _create_tables(self) -> None:
        with self._lock:
            c = self._conn.cursor()
            c.execute(
                "CREATE TABLE IF NOT EXISTS profile ("
                "key TEXT PRIMARY KEY, value TEXT)"
            )
            c.execute(
                "CREATE TABLE IF NOT EXISTS memories ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "category TEXT, content TEXT, importance REAL DEFAULT 0.5,"
                "created_at REAL)"
            )
            c.execute(
                "CREATE TABLE IF NOT EXISTS actions ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL,"
                "command TEXT, status TEXT, result TEXT)"
            )
            c.execute(
                "CREATE TABLE IF NOT EXISTS conversations ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL,"
                "role TEXT, content TEXT)"
            )
            self._conn.commit()

    # ---------- profil ----------
    def set_profile(self, key: str, value: Any) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO profile(key, value) VALUES(?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, str(value)),
            )
            self._conn.commit()

    def get_profile(self, key: str) -> str | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT value FROM profile WHERE key=?", (key,)
            ).fetchone()
        return row["value"] if row else None

    def all_profile(self) -> dict[str, str]:
        with self._lock:
            rows = self._conn.execute("SELECT key, value FROM profile").fetchall()
        return {r["key"]: r["value"] for r in rows}

    # ---------- wspomnienia ----------
    def remember(self, content: str, category: str = "general", importance: float = 0.5) -> int:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO memories(category, content, importance, created_at) "
                "VALUES(?,?,?,?)",
                (category, content, importance, time.time()),
            )
            self._conn.commit()
            return int(cur.lastrowid)

    def recall(self, query: str | None = None, limit: int = 12) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, category, content, importance, created_at "
                "FROM memories ORDER BY created_at DESC LIMIT 500"
            ).fetchall()
        results = [dict(r) for r in rows]
        if query:
            q = set(query.lower().split())
            def score(m: dict) -> float:
                words = set(m["content"].lower().split())
                overlap = len(q & words)
                recency = 1.0 / (1.0 + (time.time() - m["created_at"]) / (3600 * 24 * 30))
                return overlap * 3.0 + m["importance"] * 2.0 + recency
            results.sort(key=score, reverse=True)
            results = [m for m in results if score(m) > 0.4]
        else:
            results.sort(key=lambda m: (m["importance"], m["created_at"]), reverse=True)
        return results[:limit]

    # ---------- dziennik akcji ----------
    def log_action(self, command: str, status: str, result: str = "") -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO actions(ts, command, status, result) VALUES(?,?,?,?)",
                (time.time(), command, status, result[:4000]),
            )
            self._conn.commit()

    def recent_actions(self, limit: int = 10) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM actions ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    # ---------- rozmowy ----------
    def add_message(self, role: str, content: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO conversations(ts, role, content) VALUES(?,?,?)",
                (time.time(), role, content[:8000]),
            )
            self._conn.commit()

    def get_history(self, limit: int = 30) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT role, content FROM ("
                "SELECT * FROM conversations ORDER BY id DESC LIMIT ?"
                ") ORDER BY id ASC",
                (limit,),
            ).fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in rows]

    def clear_history(self) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM conversations")
            self._conn.commit()

    # ---------- podsumowania ----------
    def context_string(self, recall_limit: int = 12) -> str:
        """Zwięzły blok kontekstu wstrzykiwany do promptu systemowego."""
        parts: list[str] = []

        prof = self.all_profile()
        if prof:
            parts.append("PROFIL UŻYTKOWNIKA:\n" + "\n".join(f"- {k}: {v}" for k, v in prof.items()))

        mems = self.recall(limit=recall_limit)
        if mems:
            parts.append(
                "WAŻNE WSPOMNIENIA:\n"
                + "\n".join(f"- [{m['category']}] {m['content']}" for m in mems)
            )

        acts = self.recent_actions(limit=8)
        if acts:
            parts.append(
                "OSTATNIO WYKONANE AKCJE:\n"
                + "\n".join(f"- {a['command']} → {a['status']}" for a in acts)
            )
        return "\n\n".join(parts)

    def stats(self) -> dict:
        with self._lock:
            mem = self._conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            act = self._conn.execute("SELECT COUNT(*) FROM actions").fetchone()[0]
            prof = self._conn.execute("SELECT COUNT(*) FROM profile").fetchone()[0]
        return {"memories": mem, "actions": act, "profile_entries": prof}
