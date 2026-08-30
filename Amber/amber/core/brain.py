"""Mózg Amber — ujednolicone wywołania do modeli językowych.

Wspierane backendy (czysty HTTP/JSON, bez zewnętrznych SDK):
  * ollama        — lokalny, darmowy, bez limitu i bez klucza (domyślny),
  * openai        — OpenAI Chat Completions,
  * openrouter    — OpenRouter (jedno API do wielu modeli),
  * custom        — dowolny serwer kompatybilny z OpenAI (LM Studio, vLLM…),
  * anthropic     — Claude,
  * google        — Gemini.

Wiadomości trzymane są w formacie kanonicznym (OpenAI):
  system | user | assistant[+tool_calls] | tool

Każde wywołanie zwraca: {"text": str, "tool_calls": [{"id","name","arguments"}]}
"""
from __future__ import annotations

import json
from typing import Any

import requests

_ENDPOINTS = {
    "ollama": "{base}/api/chat",
    "openai": "https://api.openai.com/v1/chat/completions",
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
    "custom": "{base}/chat/completions",
    "anthropic": "https://api.anthropic.com/v1/messages",
    "google": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
}


class BrainError(RuntimeError):
    pass


class Brain:
    def __init__(self, config: dict) -> None:
        self.cfg = config.get("brain", {})
        self.backend = self.cfg.get("backend", "ollama")
        self.model = self.cfg.get("model", "qwen2.5:7b")
        self.base_url = self.cfg.get("base_url", "http://localhost:11434").rstrip("/")
        self.api_key = self.cfg.get("api_key", "")
        self.temperature = self.cfg.get("temperature", 0.7)
        self.max_tokens = self.cfg.get("max_tokens", 2048)
        self.vision = bool(self.cfg.get("vision", True))
        self._session = requests.Session()

    # ------------------------------------------------------------------ #
    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_choice: str = "auto",
        images: list[str] | None = None,
    ) -> dict:
        dispatch = {
            "ollama": self._chat_ollama,
            "openai": self._chat_openai_compat,
            "openrouter": self._chat_openai_compat,
            "custom": self._chat_openai_compat,
            "anthropic": self._chat_anthropic,
            "google": self._chat_google,
        }
        fn = dispatch.get(self.backend)
        if fn is None:
            raise BrainError(f"Nieznany backend: {self.backend}")
        try:
            return fn(messages, tools, tool_choice, images)
        except BrainError:
            raise
        except requests.RequestException as e:
            raise BrainError(f"Błąd połączenia z modelem ({self.backend}): {e}") from e

    def test_connection(self) -> dict:
        if self.backend == "ollama":
            try:
                r = self._session.get(f"{self.base_url}/api/tags", timeout=5)
                if r.status_code != 200:
                    return {"ok": False, "detail": f"Ollama HTTP {r.status_code}"}
                models = [m.get("name", "") for m in r.json().get("models", [])]
                if not models:
                    return {"ok": False, "detail": "Ollama działa, ale brak pobranych modeli."}
                return {"ok": True, "detail": f"Dostępne modele: {', '.join(models[:8])}"}
            except requests.RequestException as e:
                return {
                    "ok": False,
                    "detail": f"Ollama niedostępna pod {self.base_url} ({e}). "
                              "Uruchom `ollama serve` i pobierz model: `ollama pull qwen2.5:7b`",
                }
        if not self.api_key:
            return {"ok": False, "detail": "Brak klucza API (config.json → brain.api_key lub AMBER_API_KEY)."}
        return {"ok": True, "detail": f"{self.backend} / {self.model} skonfigurowany."}

    # ------------------------------------------------------------------ #
    #  Backendy
    # ------------------------------------------------------------------ #
    def _chat_ollama(self, messages, tools, tool_choice, images) -> dict:
        url = _ENDPOINTS["ollama"].format(base=self.base_url)
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": self._ollama_messages(messages, images),
            "stream": False,
            "options": {"temperature": self.temperature, "num_predict": self.max_tokens},
        }
        if tools:
            payload["tools"] = tools
        r = self._session.post(url, json=payload, timeout=300)
        r.raise_for_status()
        data = r.json()
        msg = data.get("message", {})
        return self._normalize(msg.get("content", ""), msg.get("tool_calls"))

    def _chat_openai_compat(self, messages, tools, tool_choice, images) -> dict:
        if self.backend == "openai":
            url = _ENDPOINTS["openai"]
        elif self.backend == "openrouter":
            url = _ENDPOINTS["openrouter"]
        else:
            url = _ENDPOINTS["custom"].format(base=self.base_url)

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        if self.backend == "openrouter":
            headers["HTTP-Referer"] = "https://amber.local"
            headers["X-Title"] = "Amber"

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": self._openai_messages(messages, images),
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice

        r = self._session.post(url, json=payload, headers=headers, timeout=300)
        if r.status_code != 200:
            raise BrainError(f"HTTP {r.status_code}: {r.text[:400]}")
        data = r.json()
        msg = data["choices"][0]["message"]
        return self._normalize(msg.get("content", "") or "", msg.get("tool_calls"))

    def _chat_anthropic(self, messages, tools, tool_choice, images) -> dict:
        url = _ENDPOINTS["anthropic"]
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        system, msgs = self._anthropic_messages(messages)
        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": msgs,
        }
        if system:
            payload["system"] = system
        if tools:
            payload["tools"] = self._tools_to_anthropic(tools)

        r = self._session.post(url, json=payload, headers=headers, timeout=300)
        if r.status_code != 200:
            raise BrainError(f"HTTP {r.status_code}: {r.text[:400]}")
        data = r.json()
        text_parts, tool_calls = [], []
        for block in data.get("content", []):
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                tool_calls.append({
                    "id": block.get("id", ""),
                    "name": block.get("name", ""),
                    "arguments": block.get("input", {}),
                })
        return {"text": "\n".join(text_parts), "tool_calls": tool_calls}

    def _chat_google(self, messages, tools, tool_choice, images) -> dict:
        url = _ENDPOINTS["google"].format(model=self.model)
        params = {"key": self.api_key}
        system, contents = self._google_messages(messages)
        payload: dict[str, Any] = {"contents": contents}
        if system:
            payload["system_instruction"] = {"parts": [{"text": system}]}
        if tools:
            payload["tools"] = self._tools_to_google(tools)

        r = self._session.post(url, params=params, json=payload, timeout=300)
        if r.status_code != 200:
            raise BrainError(f"HTTP {r.status_code}: {r.text[:400]}")
        data = r.json()
        cand = (data.get("candidates") or [{}])[0]
        text_parts, tool_calls = [], []
        for part in cand.get("content", {}).get("parts", []):
            if "text" in part:
                text_parts.append(part["text"])
            elif "functionCall" in part:
                fc = part["functionCall"]
                tool_calls.append({
                    "id": fc.get("name", ""),
                    "name": fc.get("name", ""),
                    "arguments": fc.get("args", {}),
                })
        return {"text": "".join(text_parts), "tool_calls": tool_calls}

    # ------------------------------------------------------------------ #
    #  Konwersja wiadomości kanonicznych → format backendu
    # ------------------------------------------------------------------ #
    @staticmethod
    def _ollama_messages(messages, images):
        msgs = [dict(m) for m in messages]
        # Ollama: zamień tool_calls asystenta na formę bezpośrednią.
        for m in msgs:
            if m.get("role") == "assistant" and m.get("tool_calls"):
                m["tool_calls"] = [
                    {
                        "function": {
                            "name": tc["function"]["name"],
                            "arguments": tc["function"]["arguments"],
                        }
                    }
                    for tc in m["tool_calls"]
                ]
        if images and msgs:
            msgs[-1]["images"] = [img for img in images]
        return msgs

    @staticmethod
    def _openai_messages(messages, images):
        msgs = [dict(m) for m in messages]
        if images and msgs:
            last = msgs[-1]
            content = [{"type": "text", "text": last.get("content", "")}]
            content += [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img}"}}
                for img in images
            ]
            last["content"] = content
        return msgs

    @staticmethod
    def _anthropic_messages(messages):
        system = "\n".join(m["content"] for m in messages if m["role"] == "system")
        out = []
        for m in messages:
            role = m["role"]
            if role == "system":
                continue
            if role == "tool":
                out.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": m.get("tool_call_id", ""),
                        "content": m.get("content", ""),
                    }],
                })
            elif role == "assistant" and m.get("tool_calls"):
                content = []
                if m.get("content"):
                    content.append({"type": "text", "text": m["content"]})
                for tc in m["tool_calls"]:
                    content.append({
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": tc["function"]["name"],
                        "input": tc["function"]["arguments"],
                    })
                out.append({"role": "assistant", "content": content})
            else:
                out.append({"role": "user" if role == "user" else "assistant",
                            "content": m.get("content", "")})
        return system, out

    @staticmethod
    def _google_messages(messages):
        system = "\n".join(m["content"] for m in messages if m["role"] == "system")
        out = []
        for m in messages:
            role = m["role"]
            if role == "system":
                continue
            if role == "tool":
                out.append({
                    "role": "user",
                    "parts": [{
                        "functionResponse": {
                            "name": m.get("name", ""),
                            "response": {"result": m.get("content", "")},
                        }
                    }],
                })
            elif role == "assistant" and m.get("tool_calls"):
                parts = []
                if m.get("content"):
                    parts.append({"text": m["content"]})
                for tc in m["tool_calls"]:
                    parts.append({
                        "functionCall": {
                            "name": tc["function"]["name"],
                            "args": tc["function"]["arguments"],
                        }
                    })
                out.append({"role": "model", "parts": parts})
            else:
                out.append({
                    "role": "model" if role == "assistant" else "user",
                    "parts": [{"text": m.get("content", "")}],
                })
        return system, out

    # ------------------------------------------------------------------ #
    @staticmethod
    def _normalize(text: str, tool_calls: list | None) -> dict:
        calls = []
        for tc in tool_calls or []:
            fn = tc.get("function", tc) if isinstance(tc, dict) else {}
            args = fn.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            calls.append({
                "id": tc.get("id", fn.get("name", "")),
                "name": fn.get("name", ""),
                "arguments": args or {},
            })
        return {"text": text or "", "tool_calls": calls}

    @staticmethod
    def _tools_to_anthropic(tools):
        out = []
        for t in tools:
            fn = t.get("function", t)
            out.append({
                "name": fn.get("name"),
                "description": fn.get("description", ""),
                "input_schema": fn.get("parameters", {"type": "object"}),
            })
        return out

    @staticmethod
    def _tools_to_google(tools):
        decls = []
        for t in tools:
            fn = t.get("function", t)
            decls.append({
                "name": fn.get("name"),
                "description": fn.get("description", ""),
                "parameters": fn.get("parameters", {"type": "object"}),
            })
        return [{"functionDeclarations": decls}]
