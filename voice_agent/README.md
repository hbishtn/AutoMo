# Voice-Controlled AI Coding Agent

A Windows 10 desktop agent you control with **Hindi / Hinglish / English voice commands**.
It listens, understands, speaks back, and (in later phases) drives Chrome + VS Code to
write, fix, and test code for you — using your *existing* browser login to Claude/ChatGPT.

> **Status: Phase 1 only** — voice input/output + a small set of safe local commands
> (open app, tell time, stop/pause, echo). No browser or file automation yet.
> Later phases are added only after each prior phase is tested and working.

---

## 1. Why this design

| Requirement | How it's satisfied |
|---|---|
| No mandatory paid API | Speech-to-text works via **free-tier Groq API** (you bring your own free key) OR falls back to Windows' built-in `SpeechRecognition` (Google Web Speech, free, no key) |
| No local AI model | We call cloud APIs (Groq) instead of running Whisper locally — keeps RAM usage low on an 8 GB laptop |
| Never store password | Browser automation (later phases) attaches to **your already-logged-in Chrome** via Playwright's `persistent context` — the agent never sees or asks for credentials |
| API keys never hardcoded | All keys read from a local `.env` file (git-ignored), loaded via `python-dotenv` |
| Beginner-friendly, modular | Each capability is its own file under `core/`; `main.py` just wires them together |

---

## 2. Project structure

```
voice_agent/
├── main.py              # Entry point — the voice loop (Phase 1)
├── config.py             # Loads .env, central settings
├── requirements.txt
├── .env.example           # Copy to .env and fill in (all optional)
├── README.md
├── core/
│   ├── __init__.py
│   ├── stt.py             # Speech-to-text (Groq Whisper, with free fallback)
│   ├── tts.py              # Text-to-speech (pyttsx3, offline)
│   ├── intent.py            # Turns Hindi/Hinglish/English text into a command
│   └── commands.py           # Safe Phase-1 commands (time, open app, stop, echo)
├── logs/                  # Session logs (auto-created)
└── backups/                # Reserved for Phase 3 file-edit backups
```

---

## 3. Windows 10 + VS Code setup (exact commands)

### 3.1 Install Python 3.12
Download from https://www.python.org/downloads/ and **check "Add Python to PATH"** during install.
Verify in a new terminal:
```powershell
python --version
```

### 3.2 Open the project in VS Code
```powershell
cd path\to\voice_agent
code .
```

### 3.3 Create and activate a virtual environment
In VS Code's integrated terminal (PowerShell):
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```
> If PowerShell blocks the script, run this once (as your normal user, not admin):
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
> ```

### 3.4 Install dependencies
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

### 3.5 Install a microphone backend (Windows needs PyAudio)
`pyaudio` has no prebuilt wheel on some Python versions. If `pip install -r requirements.txt`
fails on `pyaudio`, run:
```powershell
pip install pipwin
pipwin install pyaudio
```

### 3.6 Set up your `.env`
```powershell
copy .env.example .env
```
Open `.env` in VS Code and, **optionally**, paste a free Groq API key
(get one at https://console.groq.com/keys — no credit card required).
If you leave it blank, Phase 1 automatically uses the free Google Web Speech fallback instead.

### 3.7 Run Phase 1
```powershell
python main.py
```
Say: **"status"**, **"time kya hai"**, **"notepad khol do"**, **"stop"** — and watch the console + hear the voice reply.

---

## 4. How Phase 1 works

1. `main.py` starts a loop: **listen → transcribe → understand → act → speak**.
2. `core/stt.py` records a few seconds of mic audio and transcribes it.
   - If `GROQ_API_KEY` is set in `.env`, it uses Groq's hosted Whisper (`whisper-large-v3`) — fast and multilingual (good for Hinglish).
   - If no key is set, it automatically falls back to `SpeechRecognition`'s free Google Web Speech API (needs internet, no key).
3. `core/intent.py` does lightweight keyword matching across Hindi/Hinglish/English phrasings (e.g. "ruk jao", "stop", "band karo" all map to `STOP`).
4. `core/commands.py` executes only a **safe, whitelisted** set of actions for Phase 1 — nothing touches files, browsers, or the terminal yet.
5. `core/tts.py` speaks the result back using `pyttsx3` (fully offline, no API needed).
6. Every turn is logged to `logs/session.log` for debugging.

### Supported Phase 1 commands (examples)
| You say (any of) | Agent does |
|---|---|
| "time kya hai", "what's the time", "samay batao" | Speaks current time |
| "notepad khol do", "open notepad" | Opens Notepad |
| "calculator kholo", "open calculator" | Opens Calculator |
| "status", "kya chal raha hai" | Speaks current agent state |
| "pause", "ruk jao" | Pauses listening until resumed |
| "resume", "shuru karo" | Resumes listening |
| "stop", "band karo", "exit" | Shuts the agent down safely |

---

## 5. Roadmap (not built yet — future phases, each tested before the next)

- **Phase 2**: Chrome automation via Playwright, attaching to your existing logged-in
  profile; type prompts into Claude/ChatGPT, read + copy responses, extract code blocks.
- **Phase 3**: Read/edit files in a selected VS Code project folder, with automatic
  Git-based backups and diff previews shown before any change is applied.
- **Phase 4**: Run project + terminal commands, detect errors, send them to the selected
  AI for a fix, apply the fix, retest — capped at 3 automatic attempts, then ask you.
- **Phase 5**: Risk gating — anything that deletes, overwrites, or runs unfamiliar
  shell commands pauses and asks for explicit voice/text confirmation first.

If a browser layout changes or any automation step fails, the agent will **say and log
the exact failure** — it will never silently pretend an action succeeded.
