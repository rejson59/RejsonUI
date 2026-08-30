"""Konfiguracja i ścieżki aplikacji Amber."""
from __future__ import annotations

import copy
import json
import os
import sys

DEFAULT_CONFIG = {
    "assistant": {
        "name": "Amber",
        "language": "pl",
        "personality": (
            "Amber to ciepła, energiczna i konkretna asystentka AI. Mówi po polsku, "
            "jest pomocna, bystra i dyskretna. Zna swojego użytkownika, pamięta ważne "
            "informacje o nim i dostosowuje się do jego stylu. Kiedy wykonuje zadania "
            "na komputerze, relacjonuje je krótko i pewnie."
        ),
    },
    "brain": {
        "backend": "ollama",      # ollama | openai | openrouter | anthropic | google | custom
        "model": "qwen2.5:7b",
        "base_url": "http://localhost:11434",
        "api_key": "",            # lub zmienna środowiskowa AMBER_API_KEY
        "temperature": 0.7,
        "max_tokens": 2048,
        "vision": True,
    },
    "voice": {
        "enabled": True,
        "engine": "edge",         # edge | system
        "edge_voice": "pl-PL-ZofiaNeural",
        "rate": "+0%",
        "volume": "+0%",
        "stt_enabled": False,
    },
    "screen": {"stream_fps": 6, "quality": 65, "scale": 1.0},
    "control": {
        "allow_shell": True,
        "allow_self_modify": True,
        "auto_screenshot_on_think": True,
        "max_tool_rounds": 8,
    },
    "ui": {
        "host": "0.0.0.0",
        "port": 8421,
        "window_mode": "browser",  # browser | webview | none
        "start_minimized": True,
    },
}


def project_root() -> str:
    """Katalog źródłowy projektu (development)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def frozen_extract_dir() -> str:
    """Katalog z zasobami wbudowanymi w .exe (tryb PyInstaller)."""
    return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))


def app_root() -> str:
    """Katalog zasobów (statyczne pliki UI, config.json)."""
    if getattr(sys, "frozen", False):
        return frozen_extract_dir()
    return project_root()


def writable_root() -> str:
    """Katalog, w którym Amber może czytać/edytować własny kod.

    W trybie PyInstaller zasoby są wypakowane do tymczasowego katalogu,
    więc do samodoskonalenia używamy katalogu obok pliku .exe.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return project_root()


def static_dir() -> str:
    return os.path.join(app_root(), "ui", "static")


def data_dir() -> str:
    d = os.path.join(os.path.expanduser("~"), ".amber")
    os.makedirs(d, exist_ok=True)
    return d


def config_path() -> str:
    return os.path.join(data_dir(), "config.json")


def _deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(path: str | None = None) -> dict:
    path = path or config_path()
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                user = json.load(f)
            cfg = _deep_merge(cfg, user)
        except Exception as e:  # uszkodzony plik — użyj domyślnych
            print(f"[Amber] Błąd odczytu konfiguracji: {e}")
    # Klucz API można też podać przez zmienną środowiskową.
    if not cfg["brain"].get("api_key"):
        cfg["brain"]["api_key"] = os.environ.get("AMBER_API_KEY", "")
    return cfg


def save_config(cfg: dict, path: str | None = None) -> None:
    path = path or config_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def ensure_user_config() -> str:
    """Kopiuje przykładowy config.json z projektu do ~/.amber przy pierwszym starcie."""
    path = config_path()
    if os.path.exists(path):
        return path
    bundled = os.path.join(app_root(), "config.json")
    if os.path.exists(bundled):
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(bundled, "r", encoding="utf-8") as src:
                data = src.read()
            with open(path, "w", encoding="utf-8") as dst:
                dst.write(data)
            return path
        except Exception:
            pass
    save_config(DEFAULT_CONFIG, path)
    return path
