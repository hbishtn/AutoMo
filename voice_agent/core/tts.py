"""
Text-to-speech — fully offline via pyttsx3 (uses Windows SAPI5 voices).
No API key, no internet required.
"""
import logging
import threading

import pyttsx3

import config

logger = logging.getLogger("voice_agent.tts")

_engine = pyttsx3.init()
_engine.setProperty("rate", config.TTS_RATE)
_lock = threading.Lock()


def speak(text: str) -> None:
    """Speaks text aloud and logs it. Thread-safe, blocking."""
    if not text:
        return
    logger.info("Speaking: %s", text)
    with _lock:
        _engine.say(text)
        _engine.runAndWait()
