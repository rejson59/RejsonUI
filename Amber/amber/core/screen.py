"""Przechwytywanie i sterowanie ekranem oraz myszą/klawiaturą.

Wszystkie importy są leniwe i opcjonalne — Amber startuje też w środowisku
bez wyświetlacza (np. serwer / tryb demo), a funkcje zwracają czytelny błąd.
"""
from __future__ import annotations

import base64
import io
import os
import time
from typing import Any


class Screen:
    def __init__(self, config: dict) -> None:
        self.cfg = config.get("screen", {})
        self.quality = int(self.cfg.get("quality", 65))
        self.scale = float(self.cfg.get("scale", 1.0))
        self._mss = None
        self._pyautogui = None
        self._win = None
        try:
            import mss  # noqa
            self._mss = mss.mss()
            self.available = True
        except Exception:
            self.available = False
        try:
            import pyautogui  # noqa
            self._pyautogui = pyautogui
            self._pyautogui.FAILSAFE = True
            self._pyautogui.PAUSE = 0.05
        except Exception:
            self._pyautogui = None

    # ------------------------------------------------------------------ #
    #  Podgląd
    # ------------------------------------------------------------------ #
    def capture_jpeg_b64(self) -> str | None:
        """Zwraca zrzut ekranu jako base64(JPEG) lub None."""
        if not self.available:
            return None
        try:
            with self._mss.mss() as sct:
                monitor = sct.monitors[0]  # cały ekran
                img = sct.grab(monitor)
            from PIL import Image
            pil = Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")
            if self.scale != 1.0:
                w, h = pil.size
                pil = pil.resize((int(w * self.scale), int(h * self.scale)))
            buf = io.BytesIO()
            pil.save(buf, format="JPEG", quality=self.quality)
            return base64.b64encode(buf.getvalue()).decode("ascii")
        except Exception as e:
            print(f"[screen] błąd przechwytywania: {e}")
            return None

    def screenshot_to_file(self, path: str) -> str:
        b64 = self.capture_jpeg_b64()
        if not b64:
            return "Brak dostępu do ekranu."
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "wb") as f:
            f.write(base64.b64decode(b64))
        return f"Zrzut zapisany: {path}"

    def size(self) -> dict:
        if not self.available:
            return {"width": 0, "height": 0, "available": False}
        try:
            with self._mss.mss() as sct:
                m = sct.monitors[0]
            return {"width": m["width"], "height": m["height"], "available": True}
        except Exception:
            return {"width": 0, "height": 0, "available": False}

    # ------------------------------------------------------------------ #
    #  Sterowanie (opcjonalne, przez PyAutoGUI)
    # ------------------------------------------------------------------ #
    def _gui(self):
        if self._pyautogui is None:
            raise RuntimeError("PyAutoGUI niedostępne (brak biblioteki lub ekranu).")
        return self._pyautogui

    def move(self, x: int, y: int) -> str:
        self._gui().moveTo(int(x), int(y), duration=0.2)
        return f"Przesunięto kursor do ({x}, {y})."

    def click(self, x: int | None = None, y: int | None = None,
              button: str = "left", clicks: int = 1) -> str:
        gui = self._gui()
        if x is not None and y is not None:
            gui.moveTo(int(x), int(y), duration=0.15)
        gui.click(button=button, clicks=int(clicks))
        return f"Kliknięto ({button}) x{clicks}."

    def double_click(self, x: int | None = None, y: int | None = None) -> str:
        gui = self._gui()
        if x is not None and y is not None:
            gui.moveTo(int(x), int(y), duration=0.15)
        gui.doubleClick()
        return "Podwójne kliknięcie."

    def type_text(self, text: str, interval: float = 0.03) -> str:
        self._gui().write(text, interval=interval)
        return f"Wpisano tekst: {text[:80]}"

    def press(self, key: str) -> str:
        self._gui().press(key)
        return f"Wciśnięto klawisz: {key}"

    def hotkey(self, *keys: str) -> str:
        self._gui().hotkey(*keys)
        return f"Skrót klawiszowy: {'+'.join(keys)}"

    def scroll(self, amount: int) -> str:
        self._gui().scroll(int(amount))
        return f"Przewinięto o {amount}."

    def position(self) -> str:
        x, y = self._gui().position()
        return f"Pozycja kursora: ({x}, {y})."

    def active_window(self) -> str:
        if self._win is None:
            try:
                import pygetwindow as gw
                self._win = gw
            except Exception:
                return "Brak aktywnego okna (pygetwindow niedostępne)."
        try:
            w = self._win.getActiveWindow()
            return f"Aktywne okno: {w.title}" if w else "Brak aktywnego okna."
        except Exception:
            return "Nie udało się odczytać aktywnego okna."
