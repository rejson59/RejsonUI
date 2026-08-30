"""Serwer HTTP Amber — API + interfejs + strumień ekranu na żywo."""
from __future__ import annotations

import asyncio
import base64
import json
import os
import threading
import time
import uuid
from typing import Any

from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from amber.config import static_dir
from amber.core.agent import Agent
from amber.core.events import bus, log
from amber.core.screen import Screen


@asynccontextmanager
async def lifespan(app: FastAPI):
    import amber.server as srv
    srv._loop = asyncio.get_event_loop()
    log("Serwer gotowy.")
    yield


app = FastAPI(title="Amber", version="1.0.0", lifespan=lifespan)

# Globalne komponenty — wstrzykiwane w main.py przed startem.
agent: Agent | None = None
screen: Screen | None = None
voice = None
brain = None
config: dict = {}

# Stan strumienia SSE.
_sse_clients: set[asyncio.Queue] = set()
_sse_lock = threading.Lock()
_loop: asyncio.AbstractEventLoop | None = None

# Ostatnia odpowiedź + kolejka oczekujących.
_current_run: dict = {"busy": False, "request": None}


# --------------------------------------------------------------------------- #
#  Bridge: zdarzenia (EventBus) -> kolejki asyncio (SSE)
# --------------------------------------------------------------------------- #
def _bridge(evt: dict) -> None:
    loop = _loop
    if loop is None:
        return
    data = json.dumps(evt, ensure_ascii=False, default=str)
    with _sse_lock:
        clients = list(_sse_clients)
    for q in clients:
        try:
            loop.call_soon_threadsafe(q.put_nowait, data)
        except Exception:
            pass


bus.subscribe(_bridge)


# --------------------------------------------------------------------------- #
#  SSE
# --------------------------------------------------------------------------- #
@app.get("/api/events")
async def events():
    q: asyncio.Queue = asyncio.Queue(maxsize=500)

    async def gen():
        with _sse_lock:
            _sse_clients.add(q)
        try:
            yield f"data: {json.dumps({'type': 'hello', 'data': {'ts': time.time()}})}\n\n"
            while True:
                try:
                    data = await asyncio.wait_for(q.get(), timeout=15)
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
                    continue
                yield f"data: {data}\n\n"
        finally:
            with _sse_lock:
                _sse_clients.discard(q)

    return StreamingResponse(gen(), media_type="text/event-stream")


# --------------------------------------------------------------------------- #
#  Strumień ekranu (WebSocket, klatki JPEG)
# --------------------------------------------------------------------------- #
@app.websocket("/api/stream")
async def stream_screen(ws: WebSocket):
    await ws.accept()
    fps = float((config.get("screen", {}) or {}).get("stream_fps", 6))
    interval = max(0.1, 1.0 / fps)
    try:
        while True:
            b64 = screen.capture_jpeg_b64() if screen else None
            if b64:
                await ws.send_text(json.dumps({"t": time.time(), "img": b64}))
            await asyncio.sleep(interval)
    except (WebSocketDisconnect, Exception):
        pass


# --------------------------------------------------------------------------- #
#  API
# --------------------------------------------------------------------------- #
@app.get("/api/status")
def api_status():
    brain_status = brain.test_connection() if brain else {"ok": False, "detail": "brak mózgu"}
    return {
        "name": (config.get("assistant", {}) or {}).get("name", "Amber"),
        "brain": brain_status,
        "backend": (config.get("brain", {}) or {}).get("backend"),
        "model": (config.get("brain", {}) or {}).get("model"),
        "screen": screen.size() if screen else {"available": False},
        "memory": agent.memory.stats() if agent else {},
        "speaking": voice.speaking if voice else False,
        "busy": _current_run["busy"],
        "version": "1.0.0",
    }


@app.post("/api/chat")
async def api_chat(payload: dict):
    if agent is None:
        return JSONResponse({"error": "Agent nie jest gotowy."}, status_code=500)
    message = (payload or {}).get("message", "").strip()
    if not message:
        return JSONResponse({"error": "Brak wiadomości."}, status_code=400)
    if _current_run["busy"]:
        return JSONResponse({"error": "Amber właśnie pracuje — poczekaj chwilę."}, status_code=429)

    include_screen = bool((payload or {}).get("include_screen", False))
    images = None
    if include_screen and screen:
        b64 = screen.capture_jpeg_b64()
        if b64:
            images = [b64]

    _current_run["busy"] = True
    _current_run["request"] = message

    def worker():
        try:
            bus.publish("run_start", {"message": message})
            answer = agent.run(message, images=images)
            bus.publish("answer", {"text": answer})
            if voice:
                voice.speak(answer)
        except Exception as e:
            log(f"Błąd w trakcie pracy agenta: {e}", "error")
            bus.publish("answer", {"text": f"Wystąpił błąd: {e}"})
        finally:
            _current_run["busy"] = False

    threading.Thread(target=worker, daemon=True).start()
    return {"accepted": True, "message": message}


@app.get("/api/history")
def api_history():
    if agent is None:
        return {"messages": []}
    return {"messages": agent.memory.get_history(limit=100)}


@app.get("/api/memory")
def api_memory():
    if agent is None:
        return {"profile": {}, "memories": [], "actions": []}
    return {
        "profile": agent.memory.all_profile(),
        "memories": agent.memory.recall(limit=50),
        "actions": agent.memory.recent_actions(limit=50),
    }


@app.post("/api/remember")
def api_remember(payload: dict):
    if agent is None:
        return {"ok": False}
    content = (payload or {}).get("content", "").strip()
    if content:
        agent.memory.remember(content, category="personal", importance=0.7)
    return {"ok": True}


@app.post("/api/speak")
def api_speak(payload: dict):
    text = (payload or {}).get("text", "").strip()
    if text and voice:
        voice.speak(text)
    return {"ok": True}


@app.post("/api/stop")
def api_stop():
    return {"ok": True}


# --------------------------------------------------------------------------- #
#  Pliki statyczne UI
# --------------------------------------------------------------------------- #
@app.get("/", response_class=HTMLResponse)
def index():
    path = os.path.join(static_dir(), "index.html")
    if os.path.exists(path):
        return HTMLResponse(open(path, encoding="utf-8").read())
    return HTMLResponse("<h1>Amber</h1><p>Brak interfejsu (ui/static).</p>")


if os.path.isdir(static_dir()):
    app.mount("/static", StaticFiles(directory=static_dir()), name="static")
