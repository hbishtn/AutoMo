"""
Central configuration for the agent.
Reads everything from a local .env file — never hardcode keys here.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", encoding="utf-8-sig")

LOGS_DIR = BASE_DIR / "logs"
BACKUPS_DIR = BASE_DIR / "backups"
LOGS_DIR.mkdir(exist_ok=True)
BACKUPS_DIR.mkdir(exist_ok=True)

# --- STT ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_STT_MODEL = os.getenv("GROQ_STT_MODEL", "whisper-large-v3")
AGENT_LANGUAGE_HINT = os.getenv("AGENT_LANGUAGE_HINT", "").strip() or None
LISTEN_DURATION_SECONDS = int(os.getenv("LISTEN_DURATION_SECONDS", "4"))

# --- Reserved for later phases ---
GROQ_LLM_MODEL = os.getenv("GROQ_LLM_MODEL", "openai/gpt-oss-20b")
NVIDIA_NIM_API_KEY = os.getenv("NVIDIA_NIM_API_KEY", "").strip()

# --- TTS ---
TTS_RATE = int(os.getenv("TTS_RATE", "175"))
TTS_ENGINE = os.getenv("TTS_ENGINE", "edge").strip().lower()
TTS_EDGE_VOICE = os.getenv("TTS_EDGE_VOICE", "hi-IN-SwaraNeural").strip()

# --- Safety ---
MAX_AUTO_FIX_ATTEMPTS = 3  # used starting Phase 4

# --- Input mode: "voice" (default, mic) or "text" (type commands instead) ---
INPUT_MODE = os.getenv("INPUT_MODE", "voice").strip().lower()

def stt_backend() -> str:
    """Which STT backend is active, decided once at startup."""
    return "groq" if GROQ_API_KEY else "free_fallback"
