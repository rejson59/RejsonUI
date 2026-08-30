"""Głos Amber — realistyczna synteza mowy (TTS) i opcjonalne rozpoznawanie (STT).

Silniki TTS:
  * edge  — darmowe neuronowe głosy Microsoft Edge (bardzo realistyczne),
  * system — lokalny silnik systemowy (pyttsx3 / komendy OS).

Mowa odtwarzana jest w osobnym wątku, więc nie blokuje agenta.
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any


class Voice:
    def __init__(self, config: dict) -> None:
        self.cfg = config.get("voice", {})
        self.enabled = bool(self.cfg.get("enabled", True))
        self.engine = self.cfg.get("engine", "edge")
        self.edge_voice = self.cfg.get("edge_voice", "pl-PL-ZofiaNeural")
        self.rate = self.cfg.get("rate", "+0%")
        self.volume = self.cfg.get("volume", "+0%")
        self._speaking = threading.Event()
        self._thread: threading.Thread | None = None
        self._pygame = None
        try:
            import pygame  # noqa
            self._pygame = pygame
        except Exception:
            self._pygame = None

    # ------------------------------------------------------------------ #
    @property
    def speaking(self) -> bool:
        return self._speaking.is_set()

    def speak(self, text: str, block: bool = False) -> None:
        text = (text or "").strip()
        if not text or not self.enabled:
            return
        self._thread = threading.Thread(target=self._speak_worker, args=(text,), daemon=True)
        self._thread.start()
        if block:
            self._thread.join()

    def _speak_worker(self, text: str) -> None:
        self._speaking.set()
        try:
            if self.engine == "edge":
                self._speak_edge(text)
            else:
                self._speak_system(text)
        except Exception as e:
            print(f"[voice] błąd syntezy: {e}")
            try:
                self._speak_system(text)
            except Exception:
                pass
        finally:
            self._speaking.clear()

    # ------------------------------------------------------------------ #
    def _speak_edge(self, text: str) -> None:
        import edge_tts

        async def _gen(path: str) -> None:
            tts = edge_tts.Communicate(text, self.edge_voice, rate=self.rate, volume=self.volume)
            await tts.save(path)

        fd, path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        try:
            asyncio.run(_gen(path))
            self._play_file(path)
        finally:
            try:
                os.remove(path)
            except OSError:
                pass

    def _speak_system(self, text: str) -> None:
        # pyttsx3 (offline, głos systemowy)
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
            return
        except Exception:
            pass
        # Fallback: komendy systemowe
        if sys.platform == "win32":
            subprocess.run(
                ["powershell", "-c",
                 f"Add-Type -AssemblyName System.Speech;"
                 f"(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{text}')"],
                check=False,
            )
        elif sys.platform == "darwin":
            subprocess.run(["say", text], check=False)

    def _play_file(self, path: str) -> None:
        if self._pygame is not None:
            try:
                self._pygame.mixer.init()
                self._pygame.mixer.music.load(path)
                self._pygame.mixer.music.play()
                while self._pygame.mixer.music.get_busy():
                    time.sleep(0.05)
                return
            except Exception:
                pass
        # Fallback: domyślny odtwarzacz systemowy
        if sys.platform == "win32":
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["afplay", path], check=False)
        else:
            for cmd in (["mpv", "--no-video"], ["ffplay", "-nodisp", "-autoexit"],
                        ["aplay"], ["paplay"]):
                try:
                    subprocess.run(cmd + [path], check=True, timeout=60)
                    return
                except Exception:
                    continue

    # ------------------------------------------------------------------ #
    #  Rozpoznawanie mowy (opcjonalne)
    # ------------------------------------------------------------------ #
    def listen(self, timeout: int = 5) -> str | None:
        if not self.cfg.get("stt_enabled"):
            return None
        try:
            import speech_recognition as sr
        except Exception:
            return None
        r = sr.Recognizer()
        try:
            with sr.Microphone() as source:
                r.adjust_for_ambient_noise(source, duration=0.5)
                audio = r.listen(source, timeout=timeout, phrase_time_limit=12)
            try:
                return r.recognize_google(audio, language="pl-PL")
            except Exception:
                return r.recognize_google(audio, language="en-US")
        except Exception:
            return None
