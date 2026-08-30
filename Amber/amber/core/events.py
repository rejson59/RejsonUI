"""Lekka magistrala zdarzeń + log systemowy (most do interfejsu)."""
from __future__ import annotations

import queue
import threading
import time
from typing import Any, Callable


class EventBus:
    """Prosta pub/sub — zdarzenia trafiają do kolejki i do subskrybentów."""

    def __init__(self) -> None:
        self._queue: "queue.Queue[dict]" = queue.Queue()
        self._subscribers: list[Callable[[dict], None]] = []
        self._lock = threading.Lock()

    def publish(self, etype: str, data: Any = None) -> None:
        evt = {"type": etype, "data": data, "ts": time.time()}
        self._queue.put(evt)
        with self._lock:
            subs = list(self._subscribers)
        for cb in subs:
            try:
                cb(evt)
            except Exception:
                pass

    def subscribe(self, cb: Callable[[dict], None]) -> None:
        with self._lock:
            if cb not in self._subscribers:
                self._subscribers.append(cb)

    def unsubscribe(self, cb: Callable[[dict], None]) -> None:
        with self._lock:
            if cb in self._subscribers:
                self._subscribers.remove(cb)

    def drain(self) -> list[dict]:
        """Pobiera wszystkie oczekujące zdarzenia (bez blokowania)."""
        events: list[dict] = []
        while True:
            try:
                events.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return events


# Wspólna, globalna instancja.
bus = EventBus()


def log(message: str, level: str = "info") -> None:
    """Zapisuje komunikat do logu i emituje zdarzenie 'log'."""
    print(f"[{level.upper()}] {message}")
    bus.publish("log", {"level": level, "message": message, "ts": time.time()})
