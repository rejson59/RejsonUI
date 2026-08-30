"""Samodoskonalenie — bezpieczne narzędzia edycji własnego kodu.

Amber może przeglądać i edytować pliki WYŁĄCZNIE w obrębie katalogu projektu
(app_root) oraz swojego katalogu danych (~/.amber). Kopie zapasowe każdej
modyfikacji trafiają do ~/.amber/backups/.
"""
from __future__ import annotations

import os
import shutil
import time

from amber.config import writable_root, data_dir


class SelfImprove:
    def __init__(self, config: dict) -> None:
        self.enabled = bool(config.get("control", {}).get("allow_self_modify", True))
        self.project_root = writable_root()
        self.data_root = data_dir()

    # ------------------------------------------------------------------ #
    def _check(self, path: str) -> str:
        """Sprawdza, czy ścieżka leży w dozwolonym obszarze. Zwraca absolutną."""
        if not self.enabled:
            raise PermissionError("Samodoskonalenie wyłączone (control.allow_self_modify=false).")
        abs_path = os.path.abspath(os.path.expanduser(path))
        project = os.path.abspath(self.project_root)
        data = os.path.abspath(self.data_root)
        if not (abs_path == project or abs_path.startswith(project + os.sep)
                or abs_path == data or abs_path.startswith(data + os.sep)):
            raise PermissionError(
                f"Odmowa: ścieżka poza dozwolonym obszarem ({abs_path}). "
                f"Dozwolone: {project}, {data}"
            )
        return abs_path

    def list_files(self, path: str = ".") -> str:
        try:
            abs_path = self._check(path)
        except PermissionError as e:
            return str(e)
        if not os.path.isdir(abs_path):
            return f"'{path}' nie jest katalogiem."
        entries = sorted(os.listdir(abs_path))
        lines = []
        for e in entries:
            full = os.path.join(abs_path, e)
            tag = "DIR " if os.path.isdir(full) else "FILE"
            size = "" if os.path.isdir(full) else f" ({os.path.getsize(full)} B)"
            lines.append(f"{tag}  {e}{size}")
        if not lines:
            return "(pusty katalog)"
        return "\n".join(lines)

    def read_file(self, path: str) -> str:
        try:
            abs_path = self._check(path)
        except PermissionError as e:
            return str(e)
        if not os.path.isfile(abs_path):
            return f"Plik nie istnieje: {path}"
        try:
            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception as e:
            return f"Błąd odczytu: {e}"
        if len(content) > 12000:
            content = content[:12000] + "\n...[ucięto — plik za długi]..."
        return content

    def write_file(self, path: str, content: str) -> str:
        try:
            abs_path = self._check(path)
        except PermissionError as e:
            return str(e)
        try:
            os.makedirs(os.path.dirname(abs_path) or ".", exist_ok=True)
            if os.path.exists(abs_path):
                self._backup(abs_path)
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            return f"Błąd zapisu: {e}"
        return f"Zapisano plik: {abs_path}"

    def patch_file(self, path: str, old: str, new: str) -> str:
        try:
            abs_path = self._check(path)
        except PermissionError as e:
            return str(e)
        if not os.path.isfile(abs_path):
            return f"Plik nie istnieje: {path}"
        try:
            with open(abs_path, "r", encoding="utf-8") as f:
                content = f.read()
            if old not in content:
                return "Nie znaleziono fragmentu do zamiany (old)."
            if content.count(old) > 1:
                return "Fragment 'old' występuje wielokrotnie — uściślij kontekst."
            self._backup(abs_path)
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(content.replace(old, new, 1))
        except Exception as e:
            return f"Błąd edycji: {e}"
        return f"Zmodyfikowano plik: {abs_path}"

    def _backup(self, abs_path: str) -> None:
        backups = os.path.join(self.data_root, "backups")
        os.makedirs(backups, exist_ok=True)
        rel = os.path.relpath(abs_path, self.project_root).replace(os.sep, "__")
        stamp = time.strftime("%Y%m%d-%H%M%S")
        shutil.copy2(abs_path, os.path.join(backups, f"{rel}.{stamp}.bak"))

    def logs_tail(self, lines: int = 50) -> str:
        logfile = os.path.join(self.data_root, "amber.log")
        if not os.path.exists(logfile):
            return "(brak pliku logu)"
        with open(logfile, "r", encoding="utf-8", errors="replace") as f:
            data = f.readlines()
        return "".join(data[-lines:])
