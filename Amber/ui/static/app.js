/* ============================================================
   AMBER — logika interfejsu hologramowego
   SSE (zdarzenia agenta) + WebSocket (żywy podgląd ekranu).
   ============================================================ */
"use strict";

const $ = (id) => document.getElementById(id);

// ---------- Stan ----------
const state = {
    busy: false,
    lastFrame: null,
    fps: 0,
    fpsCount: 0,
    fpsTime: performance.now(),
};

// ---------- Zegar ----------
function tickClock() {
    const now = new Date();
    $("clock-time").textContent = now.toLocaleTimeString("pl-PL", { hour12: false });
    $("clock-date").textContent = now.toLocaleDateString("pl-PL", {
        weekday: "short", day: "2-digit", month: "short", year: "numeric",
    }).toUpperCase();
}
setInterval(tickClock, 1000);
tickClock();

// ---------- Tryby: pełny / mini ----------
function setMode(mode) {
    const full = $("hologram");
    const mini = $("mini");
    if (mode === "mini") {
        full.classList.add("collapsed");
        mini.classList.remove("hidden");
    } else {
        full.classList.remove("collapsed");
        mini.classList.add("hidden");
    }
}
$("mini-expand").addEventListener("click", () => setMode("full"));

// ---------- Status ----------
function setStatus(stateId, text, msg) {
    const dot = $("status-dot");
    dot.className = "status-dot " + stateId;
    $("status-text").textContent = text;
    if (msg !== undefined) $("status-msg").textContent = msg;
}

// ---------- Czat ----------
function addMessage(role, text, whoLabel) {
    const log = $("chat-log");
    const div = document.createElement("div");
    div.className = "msg " + role;
    if (whoLabel) {
        const w = document.createElement("span");
        w.className = "who";
        w.textContent = whoLabel + " ";
        div.appendChild(w);
    }
    div.appendChild(document.createTextNode(text));
    log.appendChild(div);
    log.scrollTop = log.scrollHeight;
    return div;
}

function sendChat() {
    const input = $("chat-input");
    const text = input.value.trim();
    if (!text || state.busy) return;
    input.value = "";
    addMessage("user", text, "TY ❯");
    const includeScreen = $("toggle-screen").checked;

    setStatus("busy", "MYŚLI", "Amber analizuje polecenie…");
    setMode("mini");
    $("mini-status").textContent = "Analizuję…";

    fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, include_screen: includeScreen }),
    })
        .then((r) => r.json())
        .then((d) => {
            if (d.error) {
                addMessage("system", "⚠ " + d.error);
                setStatus("error", "BŁĄD", d.error);
                setMode("full");
            }
        })
        .catch((e) => {
            addMessage("system", "⚠ Błąd połączenia: " + e);
            setStatus("error", "BŁĄD", "Brak połączenia z serwerem");
            setMode("full");
        });
}
$("chat-form").addEventListener("submit", (e) => { e.preventDefault(); sendChat(); });

// ---------- Dziennik akcji ----------
function addAction(name, ok, result) {
    const log = $("action-log");
    const ph = log.querySelector(".placeholder");
    if (ph) ph.remove();
    const li = document.createElement("li");
    li.className = ok ? "a-ok" : "a-err";
    const nm = document.createElement("div");
    nm.className = "a-name";
    nm.textContent = (ok ? "✓ " : "✗ ") + name;
    li.appendChild(nm);
    if (result) {
        const rs = document.createElement("div");
        rs.className = "a-result";
        rs.textContent = result.length > 140 ? result.slice(0, 140) + "…" : result;
        li.appendChild(rs);
    }
    log.prepend(li);
    while (log.children.length > 60) log.removeChild(log.lastChild);
}

// ---------- Pamięć ----------
function renderProfile(profile) {
    const ul = $("profile-list");
    const keys = Object.keys(profile);
    if (!keys.length) {
        ul.innerHTML = '<li class="placeholder">(pusta)</li>';
        return;
    }
    ul.innerHTML = "";
    keys.forEach((k) => {
        const li = document.createElement("li");
        const b = document.createElement("b");
        b.textContent = k + ": ";
        li.appendChild(b);
        li.appendChild(document.createTextNode(profile[k]));
        ul.appendChild(li);
    });
}
function renderMemories(memories) {
    const ul = $("memory-list");
    if (!memories.length) {
        ul.innerHTML = '<li class="placeholder">(brak)</li>';
        return;
    }
    ul.innerHTML = "";
    memories.slice(0, 12).forEach((m) => {
        const li = document.createElement("li");
        const cat = document.createElement("span");
        cat.className = "cat";
        cat.textContent = "[" + m.category + "] ";
        li.appendChild(cat);
        li.appendChild(document.createTextNode(m.content));
        ul.appendChild(li);
    });
}
async function refreshMemory() {
    try {
        const d = await (await fetch("/api/memory")).json();
        renderProfile(d.profile);
        renderMemories(d.memories);
        // dziennik akcji z historii
        $("action-log").innerHTML = "";
        (d.actions || []).slice().reverse().forEach((a) =>
            addAction(a.command, a.status === "ok", a.result));
    } catch (e) { /* ignoruj */ }
}

// ---------- Status systemu ----------
async function refreshStatus() {
    try {
        const d = await (await fetch("/api/status")).json();
        const bs = $("brain-status");
        if (d.brain && d.brain.ok) {
            bs.textContent = "ONLINE";
            bs.className = "stat-val brain online";
        } else {
            bs.textContent = "OFFLINE";
            bs.className = "stat-val brain offline";
        }
        const vs = $("voice-status");
        vs.textContent = d.speaking ? "MÓWI" : "ON";
        vs.className = "stat-val brain " + (d.speaking ? "online" : "");
    } catch (e) { /* ignoruj */ }
}

// ---------- CPU / RAM (lokalnie przez API status rozszerzone) ----------
async function refreshStats() {
    try {
        const d = await (await fetch("/api/status")).json();
        // CPU/RAM pobieramy z get_status przez proste szacowanie; tu przybliżenie:
    } catch (e) { /* ignoruj */ }
}

// ---------- SSE: zdarzenia agenta ----------
function connectEvents() {
    const es = new EventSource("/api/events");
    es.onmessage = (ev) => {
        let msg;
        try { msg = JSON.parse(ev.data); } catch (e) { return; }
        handleEvent(msg);
    };
    es.onerror = () => { /* EventSource automatycznie ponawia */ };
}
function handleEvent(msg) {
    const t = msg.type, d = msg.data || {};
    switch (t) {
        case "run_start":
            state.busy = true;
            setStatus("busy", "PRACUJE", "Wykonuję: " + d.message);
            setMode("mini");
            break;
        case "thinking":
            $("mini-status").textContent = "Rozumiem: " + d.text.slice(0, 60);
            break;
        case "round":
            $("mini-status").textContent = "Krok " + d.n + "…";
            break;
        case "tool_start":
            addAction(d.name, null, JSON.stringify(d.args));
            $("mini-status").textContent = "Wykonuję: " + d.name;
            break;
        case "tool_result":
            // aktualizacja najnowszego wpisu
            break;
        case "log":
            // opcjonalne
            break;
        case "answer":
        case "final":
            state.busy = false;
            addMessage("amber", d.text, "AMBER ❯");
            setStatus("idle", "GOTOWA", "Amber czeka na polecenie…");
            setMode("full");
            refreshMemory();
            break;
    }
}

// ---------- WebSocket: żywy podgląd ekranu ----------
function connectStream() {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${location.host}/api/stream`);
    ws.onmessage = (ev) => {
        try {
            const d = JSON.parse(ev.data);
            if (d.img) {
                state.lastFrame = d.img;
                setFrame("screen-img", d.img);
                setFrame("mini-img", d.img);
                // fps
                state.fpsCount++;
                const now = performance.now();
                if (now - state.fpsTime > 1000) {
                    state.fps = state.fpsCount;
                    state.fpsCount = 0;
                    state.fpsTime = now;
                    $("screen-fps").textContent = state.fps + " fps";
                }
            }
        } catch (e) { /* ignoruj */ }
    };
    ws.onclose = () => setTimeout(connectStream, 3000);
}
function setFrame(id, b64) {
    const img = $(id);
    if (!img) return;
    const src = "data:image/jpeg;base64," + b64;
    if (img.getAttribute("src") !== src) img.setAttribute("src", src);
}

// ---------- Rozpoczęcie ----------
async function init() {
    connectEvents();
    connectStream();
    await refreshStatus();
    await refreshMemory();
    await refreshStats();
    addMessage("system", "System gotowy. Napisz polecenie lub pozwól Amber przejąć kontrolę.");
}
init();

// Odświeżaj status co 5 s
setInterval(refreshStatus, 5000);
