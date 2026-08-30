"""Narzędzia (tools) Amber — schematy funkcji i ich wykonanie.

To jest zestaw „rąk" Amber: sterowanie ekranem, powłoką, plikami, pamięcią
i programami. Model decyduje, którego narzędzia użyć (function calling).
"""
from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import time
import traceback
from typing import Any

from amber.core.events import log
from amber.core.memory import Memory
from amber.core.screen import Screen
from amber.core.self_improve import SelfImprove
from amber.core.voice import Voice

_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "see_screen",
            "description": "Wykonaj zrzut ekranu i przeanalizuj, co jest na nim widoczne. Użyj PRZED każdą akcją myszy/klawiatury, żeby zobaczyć aktualny stan.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": "Wykonaj polecenie w systemowej powłoce i zwróć wynik (stdout + stderr, do 6000 znaków).",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string", "description": "Polecenie do wykonania"}},
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_code",
            "description": "Wykonaj fragment kodu Python i zwróć wynik. Użyj do obliczeń/automatyzacji.",
            "parameters": {
                "type": "object",
                "properties": {"code": {"type": "string", "description": "Kod Python (print(...) pokaże wynik)"}},
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_program",
            "description": "Otwórz program, plik lub stronę internetową.",
            "parameters": {
                "type": "object",
                "properties": {"target": {"type": "string", "description": "Nazwa programu, ścieżka pliku lub URL"}},
                "required": ["target"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mouse_move",
            "description": "Przesuń kursor myszy we współrzędne ekranu (x, y).",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer"},
                    "y": {"type": "integer"},
                },
                "required": ["x", "y"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "click",
            "description": "Kliknij myszą (opcjonalnie we wskazanych współrzędnych).",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer"},
                    "y": {"type": "integer"},
                    "button": {"type": "string", "enum": ["left", "right", "middle"]},
                    "clicks": {"type": "integer"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "double_click",
            "description": "Podwójne kliknięcie (opcjonalnie we wskazanych współrzędnych).",
            "parameters": {
                "type": "object",
                "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "type_text",
            "description": "Wpisz tekst do aktywnego pola (tak jak klawiatura).",
            "parameters": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "press_key",
            "description": "Wciśnij pojedynczy klawisz (np. 'enter', 'esc', 'tab', 'ctrl', 'alt').",
            "parameters": {
                "type": "object",
                "properties": {"key": {"type": "string"}},
                "required": ["key"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "hotkey",
            "description": "Wciśnij kombinację klawiszy (np. 'ctrl','c' lub 'win','r').",
            "parameters": {
                "type": "object",
                "properties": {
                    "keys": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["keys"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scroll",
            "description": "Przewiń (dodatnie = w dół, ujemne = w górę).",
            "parameters": {
                "type": "object",
                "properties": {"amount": {"type": "integer"}},
                "required": ["amount"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remember",
            "description": "Zapamiętaj trwale ważną informację (wspomnienie) do przyszłych rozmów.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string"},
                    "category": {"type": "string", "enum": ["personal", "preference", "fact", "task", "general"]},
                    "importance": {"type": "number"},
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remember_about_me",
            "description": "Zapisz trwale fakt o użytkowniku (klucz -> wartość) w jego profilu.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "np. 'ulubiony_kolor', 'imie', 'zawod'"},
                    "value": {"type": "string"},
                },
                "required": ["key", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recall_memory",
            "description": "Przypomnij sobie zapamiętane informacje (opcjonalnie filtrując po słowach).",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "Wypisz zawartość katalogu projektu Amber.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Odczytaj plik z projektu Amber.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Nadpisz (lub utwórz) plik w projekcie Amber.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "patch_file",
            "description": "Zamień fragment pliku (old) na nowy (new). Użyj do ulepszania własnego kodu.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old": {"type": "string"},
                    "new": {"type": "string"},
                },
                "required": ["path", "old", "new"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_status",
            "description": "Pobierz informacje o systemie i stanie Amber (CPU, RAM, czas pracy).",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "speak",
            "description": "Powiedz coś na głos (realistyczny głos).",
            "parameters": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finish",
            "description": "Zakończ wykonywanie zadania i przekaż użytkownikowi podsumowanie.",
            "parameters": {
                "type": "object",
                "properties": {"summary": {"type": "string"}},
                "required": ["summary"],
            },
        },
    },
]


class ToolExecutor:
    def __init__(self, memory: Memory, screen: Screen, voice: Voice,
                 improver: SelfImprove, config: dict) -> None:
        self.memory = memory
        self.screen = screen
        self.voice = voice
        self.improver = improver
        self.cfg = config
        self.allow_shell = bool(config.get("control", {}).get("allow_shell", True))
        self.started_at = time.time()

    @staticmethod
    def schemas() -> list[dict]:
        return [s for s in _SCHEMAS]

    # ------------------------------------------------------------------ #
    def execute(self, name: str, args: dict) -> dict:
        """Wykonuje narzędzie. Zwraca {'name','result','ok'}."""
        method = getattr(self, f"tool_{name}", None)
        if method is None:
            return {"name": name, "result": f"Nieznane narzędzie: {name}", "ok": False}
        try:
            result = method(**args)
            ok = True
        except Exception as e:
            result = f"Błąd: {e}\n{traceback.format_exc(limit=3)}"
            ok = False
        result = str(result)
        self.memory.log_action(name, "ok" if ok else "error", result)
        return {"name": name, "result": result[:6000], "ok": ok}

    # ------------------------------------------------------------------ #
    #  Ekran
    # ------------------------------------------------------------------ #
    def tool_see_screen(self) -> str:
        b64 = self.screen.capture_jpeg_b64()
        size = self.screen.size()
        if not b64:
            return "Nie udało się przechwycić ekranu (brak wyświetlacza)."
        return json.dumps({
            "note": "Screenshot wykonany i dołączony do następnej analizy wizualnej.",
            "resolution": f"{size['width']}x{size['height']}",
        }, ensure_ascii=False)

    # ------------------------------------------------------------------ #
    #  System / powłoka / kod
    # ------------------------------------------------------------------ #
    def tool_run_shell(self, command: str) -> str:
        if not self.allow_shell:
            return "Wykonywanie poleceń powłoki jest wyłączone (control.allow_shell=false)."
        try:
            p = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=120, cwd=os.path.expanduser("~"),
            )
        except subprocess.TimeoutExpired:
            return "Polecenie przekroczyło limit czasu (120 s)."
        out = (p.stdout or "") + (("\n[stderr]\n" + p.stderr) if p.stderr else "")
        if not out.strip():
            out = f"(kod wyjścia: {p.returncode})"
        return out[:6000]

    def tool_run_code(self, code: str) -> str:
        buf = {"out": []}

        def _print(*a):
            buf["out"].append(" ".join(str(x) for x in a))

        env = {
            "print": _print,
            "memory": self.memory,
            "screen": self.screen,
            "os": os, "sys": sys, "time": time, "json": json,
        }
        try:
            exec(compile(code, "<amber_run_code>", "exec"), {"__builtins__": __builtins__, **env})
        except Exception as e:
            return f"Błąd wykonania kodu: {e}\n{traceback.format_exc(limit=3)}"
        return "\n".join(buf["out"]) or "(brak wyniku — użyj print(...))"

    def tool_open_program(self, target: str) -> str:
        sysname = platform.system()
        try:
            if target.startswith(("http://", "https://", "www.")):
                if not target.startswith(("http://", "https://")):
                    target = "https://" + target
                if sysname == "Windows":
                    os.startfile(target)  # type: ignore[attr-defined]
                elif sysname == "Darwin":
                    subprocess.run(["open", target], check=True)
                else:
                    subprocess.run(["xdg-open", target], check=True)
                return f"Otwarto stronę: {target}"
            if sysname == "Windows":
                os.startfile(target)  # type: ignore[attr-defined]
            elif sysname == "Darwin":
                subprocess.run(["open", target], check=True)
            else:
                subprocess.run(["xdg-open", target], check=True)
            return f"Otwarto: {target}"
        except Exception as e:
            # próba jako program z PATH
            try:
                subprocess.Popen([target], shell=True)
                return f"Uruchomiono program: {target}"
            except Exception as e2:
                return f"Nie udało się otworzyć '{target}': {e} / {e2}"

    # ------------------------------------------------------------------ #
    #  Mysz / klawiatura
    # ------------------------------------------------------------------ #
    def tool_mouse_move(self, x: int, y: int) -> str:
        return self.screen.move(x, y)

    def tool_click(self, x: int | None = None, y: int | None = None,
                   button: str = "left", clicks: int = 1) -> str:
        return self.screen.click(x, y, button, clicks)

    def tool_double_click(self, x: int | None = None, y: int | None = None) -> str:
        return self.screen.double_click(x, y)

    def tool_type_text(self, text: str) -> str:
        return self.screen.type_text(text)

    def tool_press_key(self, key: str) -> str:
        return self.screen.press(key)

    def tool_hotkey(self, keys: list[str]) -> str:
        return self.screen.hotkey(*keys)

    def tool_scroll(self, amount: int) -> str:
        return self.screen.scroll(amount)

    # ------------------------------------------------------------------ #
    #  Pamięć
    # ------------------------------------------------------------------ #
    def tool_remember(self, content: str, category: str = "general",
                      importance: float = 0.5) -> str:
        self.memory.remember(content, category, importance)
        return f"Zapamiętano [{category}]: {content}"

    def tool_remember_about_me(self, key: str, value: str) -> str:
        self.memory.set_profile(key, value)
        return f"Zapisano w profilu: {key} = {value}"

    def tool_recall_memory(self, query: str | None = None) -> str:
        mems = self.memory.recall(query)
        if not mems:
            return "Brak zapisanych wspomnień."
        return "\n".join(f"- [{m['category']}] {m['content']}" for m in mems)

    # ------------------------------------------------------------------ #
    #  Pliki / samodoskonalenie
    # ------------------------------------------------------------------ #
    def tool_list_files(self, path: str = ".") -> str:
        return self.improver.list_files(path)

    def tool_read_file(self, path: str) -> str:
        return self.improver.read_file(path)

    def tool_write_file(self, path: str, content: str) -> str:
        return self.improver.write_file(path, content)

    def tool_patch_file(self, path: str, old: str, new: str) -> str:
        return self.improver.patch_file(path, old, new)

    # ------------------------------------------------------------------ #
    #  Status / głos / koniec
    # ------------------------------------------------------------------ #
    def tool_get_status(self) -> str:
        info = [f"System: {platform.system()} {platform.release()}",
                f"Python: {platform.python_version()}",
                f"Uptime Amber: {int(time.time() - self.started_at)} s"]
        try:
            import psutil
            info.append(f"CPU: {psutil.cpu_percent(interval=0.2)}%")
            vm = psutil.virtual_memory()
            info.append(f"RAM: {vm.percent}% ({vm.used // (1024**2)} MB / {vm.total // (1024**2)} MB)")
        except Exception:
            pass
        info.append(f"Ekran: {self.screen.size()}")
        info.append(f"Pamięć: {self.memory.stats()}")
        return "\n".join(str(x) for x in info)

    def tool_speak(self, text: str) -> str:
        self.voice.speak(text)
        return f"Powiedziano: {text[:120]}"

    def tool_finish(self, summary: str) -> str:
        return summary
