"""Agent — orkiestracja pętli modelu i narzędzi (Agentic Loop).

Amber: rozumie polecenie, w razie potrzeby wykonuje narzędzia (ekran, powłoka,
pliki, pamięć), analizuje ich wyniki, a na końcu odpowiada i zapamiętuje
ważne informacje o użytkowniku.
"""
from __future__ import annotations

import json
import time
from typing import Any

from amber.core.brain import Brain, BrainError
from amber.core.events import bus, log
from amber.core.memory import Memory
from amber.core.screen import Screen
from amber.core.voice import Voice
from amber.core.self_improve import SelfImprove
from amber.core.actions import ToolExecutor

_SYSTEM_PROMPT = """Jesteś {name} — osobista asystentka AI użytkownika, działająca na jego komputerze.
Osobowość i styl:
{personality}

Twoje możliwości (masz do nich dostęp jako narzędzia/funkcje):
- widzisz ekran na żywo (see_screen + analiza zrzutu),
- sterujesz myszą, klawiaturą i programami,
- wykonujesz polecenia powłoki i kod Python,
- czytasz i edytujesz własny kod (samodoskonalenie),
- masz pamięć długotrwałą (remember, remember_about_me, recall_memory).

Zasady:
1. Mów po polsku, chyba że użytkownik prosi inaczej. Bądź naturalna i zwięzła.
2. Gdy zadanie wymaga zobaczenia ekranu, NAJPIERW wywołaj see_screen i przeanalizuj wynik.
3. Wykonuj zadania krok po kroku, wywołując narzędzia, aż osiągniesz cel.
4. Ważne informacje o użytkowniku ZAPISUJ do pamięci (remember / remember_about_me).
5. Gdy skończysz zadanie, wywołaj finish z krótkim podsumowaniem po polsku.
6. Nie wymyślaj wyników — jeśli narzędzie zwróciło błąd, powiedz o tym szczerze.

AKTUALNY KONTEKST (pamięć długotrwała):
{context}
"""


class Agent:
    def __init__(self, config: dict, memory: Memory, brain: Brain,
                 screen: Screen, voice: Voice) -> None:
        self.cfg = config
        self.memory = memory
        self.brain = brain
        self.screen = screen
        self.voice = voice
        self.improver = SelfImprove(config)
        self.tools = ToolExecutor(memory, screen, voice, self.improver, config)
        self.assistant_name = config.get("assistant", {}).get("name", "Amber")
        self.max_rounds = int(config.get("control", {}).get("max_tool_rounds", 8))
        self.auto_shot = bool(config.get("control", {}).get("auto_screenshot_on_think", True))

    # ------------------------------------------------------------------ #
    def _system_prompt(self) -> str:
        ctx = self.memory.context_string() or "(brak zapisanych informacji)"
        return _SYSTEM_PROMPT.format(
            name=self.assistant_name,
            personality=self.cfg.get("assistant", {}).get("personality", ""),
            context=ctx,
        )

    def run(self, user_text: str, images: list[str] | None = None) -> str:
        """Wykonuje pełną pętlę agenta. Zwraca ostateczną odpowiedź."""
        messages: list[dict] = [{"role": "system", "content": self._system_prompt()}]
        history = self.memory.get_history(limit=20)
        for h in history:
            messages.append({"role": h["role"], "content": h["content"]})

        # Dołączamy ewentualny zrzut ekranu przesłany przez użytkownika.
        call_images = images
        messages.append({"role": "user", "content": user_text})

        self.memory.add_message("user", user_text)
        bus.publish("thinking", {"text": user_text})

        final_text = ""
        for round_no in range(self.max_rounds):
            bus.publish("round", {"n": round_no + 1})
            try:
                resp = self.brain.chat(messages, tools=self.tools.schemas(), images=call_images)
            except BrainError as e:
                log(f"Błąd mózgu: {e}", "error")
                final_text = f"Przepraszam, mam problem z połączeniem z modelem AI: {e}"
                break
            call_images = None  # zrzut tylko przy pierwszym wywołaniu

            text = resp.get("text", "")
            tool_calls = resp.get("tool_calls", [])

            if not tool_calls:
                final_text = text
                break

            # Zapisz odpowiedź asystenta (z tool_calls) w kontekście.
            assistant_msg: dict[str, Any] = {
                "role": "assistant",
                "content": text or "",
            }
            if tool_calls:
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {"name": tc["name"], "arguments": json.dumps(tc["arguments"], ensure_ascii=False)},
                    }
                    for tc in tool_calls
                ]
            messages.append(assistant_msg)

            # Wykonaj wszystkie narzędzia.
            for tc in tool_calls:
                name, args = tc["name"], tc["arguments"]
                bus.publish("tool_start", {"name": name, "args": args})
                log(f"Wykonuję: {name} {args}")
                result = self.tools.execute(name, args)
                bus.publish("tool_result", result)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "name": name,
                    "content": result["result"],
                })
        else:
            # Wyczerpano limit rund — wymuś podsumowanie.
            final_text = "Wykonano część zadania (limit kroków)." if not final_text else final_text

        final_text = final_text.strip() or "Gotowe."
        self.memory.add_message("assistant", final_text)
        self._extract_memories(user_text, final_text)
        bus.publish("final", {"text": final_text})
        return final_text

    # ------------------------------------------------------------------ #
    def _extract_memories(self, user_text: str, final_text: str) -> None:
        """Po rozmowie wyciąga fakty o użytkowniku i zapisuje do pamięci."""
        prompt = (
            "Na podstawie poniższej rozmowy wyodrębnij WAŻNE, trwałe informacje o użytkowniku "
            "(jego dane, preferencje, charakter, kontekst życia) oraz istotne fakty/zadania. "
            "Odpowiedz WYŁĄCZNIE jako JSON (bez komentarzy):\n"
            '{"facts": ["krótki fakt", ...], "profile": {"klucz": "wartość", ...}}\n'
            "Jeśli nic istotnego — zwróć puste listy. Rozmowa:\n"
            f"Użytkownik: {user_text}\nAmber: {final_text}"
        )
        try:
            resp = self.brain.chat(
                [{"role": "user", "content": prompt}],
                tools=None,
            )
        except Exception:
            return
        txt = resp.get("text", "").strip()
        # Wytnij fragment JSON.
        start, end = txt.find("{"), txt.rfind("}")
        if start == -1 or end == -1:
            return
        try:
            data = json.loads(txt[start:end + 1])
        except json.JSONDecodeError:
            return
        for fact in data.get("facts", []):
            if isinstance(fact, str) and fact.strip():
                self.memory.remember(fact.strip(), category="personal", importance=0.7)
        for k, v in (data.get("profile") or {}).items():
            if isinstance(v, str) and v.strip():
                self.memory.set_profile(k, v)
