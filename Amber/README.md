# 🔶 AMBER — Holographic AI Assistant

**Amber** to osobista asystentka AI, która steruje Twoim laptopem: widzi ekran na
żywo, porusza myszą i klawiaturą, uruchamia programy, wykonuje polecenia, ma
**pamięć długotrwałą** i **realistyczny głos**. Interfejs to pomarańczowy,
hologramowy pulpit w stylu **eDEX-UI**, który podczas pracy chowa się do małego
pop-upu w rogu ekranu.

```
┌──────────────────────────────────────────────────────────┐
│  ◈ AMBER  HOLOGRAPHIC ASSISTANT     CPU  RAM  BRAIN  ⏱   │
│  ┌───────────┬──────────────────────┬───────────────┐    │
│  │  PAMIĘĆ   │   LIVE SCREEN        │   AKCJE       │    │
│  │  profil   │   (podgląd ekranu)   │   log na żywo │    │
│  │  wspom.   │   ─────────────────  │               │    │
│  │           │   ❯ konsola czatu    │               │    │
│  └───────────┴──────────────────────┴───────────────┘    │
└──────────────────────────────────────────────────────────┘
   (podczas pracy → zwija się do mini pop-upu w rogu 🔶)
```

---

## ✨ Co potrafi Amber

- **Widzi ekran na żywo** — strumień WebSocket + zrzuty analizowane przez model
  (vision), dzięki czemu „rozumie", co jest na ekranie przed każdą akcją.
- **Steruje komputerem** — mysz (ruchy, kliknięcia), klawiatura (pisanie,
  skróty), przewijanie, otwieranie programów i stron.
- **Wykonuje polecenia** — powłoka systemowa (`run_shell`) i kod Python
  (`run_code`) do pełnej automatyzacji.
- **Pamięć długotrwała** — baza SQLite (`~/.amber/amber.db`) przechowuje profil
  użytkownika, wspomnienia, dziennik akcji i historię rozmów. Po każdej rozmowie
  Amber **sama wyciąga i zapisuje** ważne informacje o Tobie.
- **Realistyczny głos** — darmowe neuronowe głosy Microsoft Edge TTS
  (`pl-PL-ZofiaNeural` i inne), plus opcjonalne rozpoznawanie mowy (STT).
- **Samodoskonalenie** — może czytać i edytować własny kod (z kopiami
  zapasowymi), aby z czasem poprawiać swoje działanie.
- **Start z systemem** — skrypt autostartu (Windows).
- **Dwa tryby interfejsu** — pełny hologram (spoczynek) ↔ mini popup (praca).

---

## 🚀 Szybki start

### 1. Wymagania
- **Python 3.10+**
- (opcjonalnie, dla darmowego i nielimitowanego „mózgu") **Ollama** —
  https://ollama.com

### 2. Instalacja

**Windows** — kliknij `install.bat` (albo w terminalu):
```bat
install.bat
start_amber.bat
```

**macOS / Linux**:
```bash
chmod +x install.sh start_amber.sh
./install.sh
./start_amber.sh
```

Ręcznie:
```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Interfejs otworzy się automatycznie pod adresem **http://localhost:8421**.

### 3. Konfiguracja mózgu (WAŻNE)

Plik konfiguracji: **`~/.amber/config.json`** (tworzony przy pierwszym
uruchomieniu na podstawie `config.json` z projektu).

#### Opcja A — lokalnie, bez limitu i bez kosztów (domyślna)
Zainstaluj [Ollama](https://ollama.com), potem:
```bash
ollama pull qwen2.5:7b        # dobry model z narzędziami (tool calling)
# lub lżejszy: ollama pull llama3.2
```
Amber działa od razu — bez kluczy, bez limitów, z pełną prywatnością.

#### Opcja B — chmura (OpenAI / OpenRouter / Google / Anthropic)
W `config.json` ustaw:
```json
"brain": {
  "backend": "openai",            // openai | openrouter | anthropic | google | custom
  "model": "gpt-4o",
  "api_key": "TWÓJ_KLUCZ"         // albo zmienna środowiskowa AMBER_API_KEY
}
```
> **Uwaga:** żaden dostawca chmurowy nie oferuje naprawdę „bez limitu i za
> darmo" — limity/opłaty wynikają z regulaminu dostawcy. Tryb lokalny (Ollama)
> jest w 100% darmowy i nielimitowany.

### 4. Głos
Domyślnie włączony (`edge`, głos `pl-PL-ZofiaNeural`). Inne głosy neuronowe:
`pl-PL-MarekNeural`, `pl-PL-AgnieszkaNeural`. Wyłącz w `voice.enabled: false`.

---

## 🖥️ Sterowanie / bezpieczeństwo

Amber ma realny dostęp do Twojego systemu, więc domyślnie:
- wykonywanie poleceń powłoki jest **włączone** (`control.allow_shell`),
- edycja własnego kodu ograniczona jest **wyłącznie** do katalogu Amber
  i `~/.amber` (z kopiami zapasowymi w `~/.amber/backups`).

Możesz to zawęzić w `config.json`:
```json
"control": { "allow_shell": true, "allow_self_modify": true }
```

---

## 📦 Budowa pliku `.exe` (Windows)

1. Zainstaluj zależności (`install.bat`).
2. Uruchom `build_exe.bat` (albo `build_exe.ps1`).
3. Gotowy program znajdziesz w **`dist\Amber\Amber.exe`**.

---

## 🔁 Autostart z systemem (Windows)

Uruchom `install_autostart.bat` — Amber będzie startować cicho przy każdym
logowaniu. Usunięcie:
```bat
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "Amber" /f
```

---

## 📁 Struktura projektu

```
Amber/
├── amber/                  # pakiet Pythona
│   ├── main.py             # punkt startowy
│   ├── config.py           # konfiguracja i ścieżki
│   ├── server.py           # FastAPI + SSE + WebSocket (ekran)
│   └── core/
│       ├── agent.py        # pętla agenta (model + narzędzia)
│       ├── brain.py        # backendy LLM (ollama/openai/…)
│       ├── actions.py      # narzędzia (schematy + wykonanie)
│       ├── memory.py       # pamięć długotrwała (SQLite)
│       ├── screen.py       # podgląd + sterowanie ekranem
│       ├── voice.py        # TTS/STT
│       ├── self_improve.py # edycja własnego kodu (z backupami)
│       └── events.py       # magistrala zdarzeń
├── ui/static/              # interfejs hologramowy (HTML/CSS/JS)
├── config.json             # przykładowa konfiguracja
├── run.py                  # launcher
├── install.bat / install.sh
├── start_amber.bat / start_amber.sh
├── install_autostart.bat
├── build_exe.bat / build_exe.ps1 / Amber.spec
└── requirements.txt
```

---

## ⚠️ Uwagi prawne i techniczne

- Amber wykonuje rzeczywiste akcje na komputerze. Używaj jej odpowiedzialnie
  i sprawdzaj krytyczne operacje (np. usuwanie plików).
- „Brak limitów API" jest możliwy tylko przy modelu **lokalnym** (Ollama).
  Modele chmurowe podlegają limitom i opłatom dostawców.
- Rozpoznawanie mowy (STT) jest opcjonalne i domyślnie wyłączone.
