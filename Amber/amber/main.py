"""Punkt startowy Amber.

Uruchamia serwer, inicjalizuje wszystkie komponenty i (opcjonalnie) otwiera
okno interfejsu. Pracuje też jako `amber.server:app` (np. dla Gunicorn).
"""
from __future__ import annotations

import logging
import os
import threading
import time
import webbrowser

import uvicorn

from amber.config import data_dir, ensure_user_config, load_config
from amber.core.agent import Agent
from amber.core.brain import Brain
from amber.core.events import bus, log
from amber.core.memory import Memory
from amber.core.screen import Screen
from amber.core.voice import Voice


def _setup_logging() -> None:
    logfile = os.path.join(data_dir(), "amber.log")
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    try:
        fh = logging.FileHandler(logfile, encoding="utf-8")
        fh.setFormatter(fmt)
        root.addHandler(fh)
    except Exception:
        pass
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    root.addHandler(sh)


def build_components(config: dict):
    """Tworzy komponenty i przypisuje je do modułu serwera."""
    import amber.server as server

    memory = Memory(os.path.join(data_dir(), "amber.db"))
    brain = Brain(config)
    screen = Screen(config)
    voice = Voice(config)
    agent = Agent(config, memory, brain, screen, voice)

    server.agent = agent
    server.screen = screen
    server.voice = voice
    server.brain = brain
    server.config = config
    return memory, brain, screen, voice, agent


def _open_window(config: dict) -> None:
    mode = (config.get("ui", {}) or {}).get("window_mode", "browser")
    port = int((config.get("ui", {}) or {}).get("port", 8421))
    url = f"http://127.0.0.1:{port}"

    if mode == "webview":
        try:
            import webview
            def _start():
                webview.create_window("Amber", url, width=1400, height=900, min_size=(800, 560))
                webview.start(gui=None, debug=False)
            threading.Thread(target=_start, daemon=True).start()
            return
        except Exception:
            pass
    if mode in ("browser", "webview"):
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()


def run(config: dict | None = None) -> None:
    _setup_logging()
    config = config or load_config()
    build_components(config)

    port = int((config.get("ui", {}) or {}).get("port", 8421))
    host = (config.get("ui", {}) or {}).get("host", "0.0.0.0")

    log(f"Amber startuje na http://{host}:{port}")
    bus.publish("boot", {"ts": time.time()})

    mode = (config.get("ui", {}) or {}).get("window_mode", "browser")
    if mode != "none":
        _open_window(config)

    uvicorn.run("amber.server:app", host=host, port=port, log_level="warning")


def main() -> None:
    ensure_user_config()
    run(load_config())


if __name__ == "__main__":
    main()
